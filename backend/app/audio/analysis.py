import os
import librosa
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.riff import Riff

MIDI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/midi"))
os.makedirs(MIDI_DIR, exist_ok=True)

# ── Basic-Pitch ONNX model (downloaded once from HuggingFace) ────────────────
_BASIC_PITCH_HF_REPO = "spotify/basic-pitch-onnx"
_BASIC_PITCH_MODEL_FILE = "basic_pitch.onnx"

# Model constants (match basic-pitch 0.4.x training config)
_BP_SAMPLE_RATE = 22050
_BP_FFT_HOP = 256
_BP_ANNOTATIONS_FPS = _BP_SAMPLE_RATE / _BP_FFT_HOP   # ≈ 86.13 fps
_BP_FREQ_BINS_IN  = 264   # model input frequency bins
_BP_MIDI_OFFSET   = 21    # lowest MIDI note modelled (A0)
_BP_NOTE_THRESHOLD  = 0.5
_BP_ONSET_THRESHOLD = 0.5
_BP_MIN_NOTE_LEN    = 0.058   # seconds (~5 frames)
_BP_ENERGY_THRESHOLD = 0.1    # minimum mean frame energy to keep a note


def _load_basic_pitch_session():
    """Download (once) and return an onnxruntime InferenceSession for basic-pitch."""
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    model_path = hf_hub_download(repo_id=_BASIC_PITCH_HF_REPO,
                                 filename=_BASIC_PITCH_MODEL_FILE)
    sess = ort.InferenceSession(model_path,
                                providers=["CPUExecutionProvider"])
    return sess


def _extract_midi_onnx(audio_path: str, output_dir: str) -> None:
    """
    Run basic-pitch ONNX model on *audio_path* and write a MIDI file to
    *output_dir/<stem>_basic_pitch.mid*.

    Uses only: librosa, numpy, scipy, onnxruntime, mido — all already in
    requirements.txt. No tensorflow or basic-pitch package needed.
    """
    import mido
    from scipy.ndimage import label as scipy_label

    # ── 1. Load & resample audio ─────────────────────────────────────────────
    y, _ = librosa.load(audio_path, sr=_BP_SAMPLE_RATE, mono=True)

    # ── 2. Build CQT input the same way basic-pitch does ────────────────────
    #  basic-pitch expects a log-magnitude CQT (264 bins, hop=256)
    n_bins = _BP_FREQ_BINS_IN
    cqt = librosa.cqt(y, sr=_BP_SAMPLE_RATE,
                      hop_length=_BP_FFT_HOP,
                      n_bins=n_bins,
                      bins_per_octave=36)
    log_cqt = librosa.amplitude_to_db(np.abs(cqt), ref=np.max)
    # shape: (n_bins, n_frames) → normalise to [0, 1]
    log_cqt = (log_cqt - log_cqt.min()) / (log_cqt.max() - log_cqt.min() + 1e-8)
    # model expects (batch, frames, bins, 1)
    frames = log_cqt.T  # (n_frames, n_bins)
    model_input = frames[np.newaxis, :, :, np.newaxis].astype(np.float32)

    # ── 3. Run ONNX inference ────────────────────────────────────────────────
    sess = _load_basic_pitch_session()
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: model_input})
    # basic-pitch outputs: [note_probs, onset_probs, contour]
    note_probs   = outputs[0][0]   # (n_frames, 88)
    onset_probs  = outputs[1][0]   # (n_frames, 88)

    # ── 4. Convert frame-level predictions → MIDI notes ─────────────────────
    mid = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))  # 120 BPM

    secs_per_frame = 1.0 / _BP_ANNOTATIONS_FPS
    ticks_per_sec  = 480 * 2  # at 120 BPM, 480 ticks/beat × 2 beats/sec

    notes = []
    for pitch_idx in range(note_probs.shape[1]):
        midi_note = pitch_idx + _BP_MIDI_OFFSET
        if midi_note > 127:
            break
        active = (note_probs[:, pitch_idx] >= _BP_NOTE_THRESHOLD).astype(np.int8)
        labeled, n_segs = scipy_label(active)
        for seg_id in range(1, n_segs + 1):
            seg_frames = np.where(labeled == seg_id)[0]
            if len(seg_frames) == 0:
                continue
            start_f, end_f = int(seg_frames[0]), int(seg_frames[-1])
            duration_s = (end_f - start_f + 1) * secs_per_frame
            if duration_s < _BP_MIN_NOTE_LEN:
                continue
            # require at least one onset detection in this segment
            if onset_probs[start_f:end_f + 1, pitch_idx].max() < _BP_ONSET_THRESHOLD:
                continue
            # velocity from mean note probability
            velocity = int(np.clip(note_probs[start_f:end_f + 1, pitch_idx].mean() * 127, 20, 127))
            notes.append((start_f, end_f, midi_note, velocity))

    # Sort by onset frame, then emit note_on / note_off as delta-time events
    notes.sort(key=lambda n: n[0])
    events = []
    for start_f, end_f, midi_note, velocity in notes:
        events.append((start_f * secs_per_frame, "on",  midi_note, velocity))
        events.append((end_f   * secs_per_frame, "off", midi_note, 0))
    events.sort(key=lambda e: e[0])

    prev_tick = 0
    for t_sec, kind, midi_note, velocity in events:
        tick = int(t_sec * ticks_per_sec)
        delta = max(0, tick - prev_tick)
        prev_tick = tick
        msg_type = "note_on" if kind == "on" else "note_off"
        track.append(mido.Message(msg_type, note=midi_note,
                                  velocity=velocity, time=delta))

    # ── 5. Write MIDI file ───────────────────────────────────────────────────
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    out_path = os.path.join(output_dir, f"{stem}_basic_pitch.mid")
    mid.save(out_path)



def estimate_bpm(y, sr):
    """
    Multi-strategy BPM estimation for guitar content.
    Uses harmonic/percussive separation so rhythmic content drives the estimate,
    then cross-validates several candidate tempos to pick the most musically
    plausible value (avoids halftime / doubletime errors).
    """
    # Separate harmonic and percussive components
    y_harm, y_perc = librosa.effects.hpss(y)

    # Use percussive component for beat tracking — more reliable for rhythm
    onset_env_perc = librosa.onset.onset_strength(y=y_perc, sr=sr, aggregate=np.median)
    # Also run on the full signal for a blended picture
    onset_env_full = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)

    # Collect tempo candidates from both sources
    candidates = []

    for onset_env in (onset_env_perc, onset_env_full):
        # tempo() returns multiple candidates ordered by confidence
        tempos = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
        if len(tempos) > 0:
            candidates.append(float(tempos[0]))
        # Also grab the top result via beat_track for a second opinion
        t, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        candidates.append(float(t[0]) if isinstance(t, np.ndarray) else float(t))

    if not candidates:
        return 120.0

    # Normalise all candidates into the 60-180 BPM range (common music range)
    # by halving or doubling outliers, then vote by histogram
    def normalise(bpm):
        while bpm < 60:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        return bpm

    normalised = [normalise(c) for c in candidates if c > 0]

    # Cluster candidates within ±5 BPM of each other and pick the
    # cluster with the most votes; break ties by preferring higher count
    cluster_sum = 0.0
    cluster_count = 0
    best_cluster_val = normalised[0]
    best_count = 1

    for ref in normalised:
        near = [c for c in normalised if abs(c - ref) < 5]
        if len(near) > best_count or (len(near) == best_count and near[0] > best_cluster_val):
            best_count = len(near)
            best_cluster_val = float(np.mean(near))

    return round(best_cluster_val, 1)


def estimate_key(y, sr):
    """
    Improved key detection using:
    1. Harmonic source separation (removes noise/percussion from chroma)
    2. CQT-based chroma (more pitch-accurate than STFT chroma)
    3. CENS smoothing (normalises chroma over time for robustness)
    4. Krumhansl-Kessler tonal hierarchy profiles
    """
    # Isolate harmonic component only — percussion pollutes chroma
    y_harm, _ = librosa.effects.hpss(y)

    # CQT chroma is more accurate than STFT chroma, especially for guitar
    chroma_cqt = librosa.feature.chroma_cqt(y=y_harm, sr=sr, bins_per_octave=36)

    # CENS (Chroma Energy Normalized Statistics) smoothing makes it more robust
    chroma_cens = librosa.feature.chroma_cens(y=y_harm, sr=sr)

    # Blend both representations for best accuracy
    chroma_mean = np.mean(chroma_cqt, axis=1) * 0.5 + np.mean(chroma_cens, axis=1) * 0.5

    # Krumhansl-Kessler tonal hierarchy profiles (most referenced in literature)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                               2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                               2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F',
                  'F#', 'G', 'G#', 'A', 'A#', 'B']

    best_corr = -2.0
    best_key = "Unknown"

    for i in range(12):
        maj_prof = np.roll(major_profile, i)
        min_prof = np.roll(minor_profile, i)

        maj_corr = float(np.corrcoef(chroma_mean, maj_prof)[0, 1])
        min_corr = float(np.corrcoef(chroma_mean, min_prof)[0, 1])

        if maj_corr > best_corr:
            best_corr = maj_corr
            best_key = f"{note_names[i]} Major"
        if min_corr > best_corr:
            best_corr = min_corr
            best_key = f"{note_names[i]} Minor"

    return best_key


def analyze_audio_task(riff_id: int):
    """Main analysis task — runs in a background thread."""
    db: Session = SessionLocal()
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        db.close()
        return

    try:
        riff.analysis_status = "processing"
        riff.analysis_progress = 0.1
        db.commit()

        # ── Load ─────────────────────────────────────────────────────────────
        # Resample to 22 050 Hz — better performance without quality loss for
        # the features we compute
        y, sr = librosa.load(riff.filepath, sr=22050)
        
        # Normalize audio to [-1.0, 1.0] to remove recording volume bias.
        # This makes RMS energy reflect the crest factor (compression/distortion)
        # rather than the raw microphone gain.
        y = librosa.util.normalize(y)

        riff.analysis_progress = 0.3
        db.commit()

        # ── Duration ─────────────────────────────────────────────────────────
        duration = librosa.get_duration(y=y, sr=sr)

        # ── BPM ──────────────────────────────────────────────────────────────
        bpm = estimate_bpm(y, sr)

        # ── Energy ───────────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))

        riff.analysis_progress = 0.6
        db.commit()

        # ── Onset Density ─────────────────────────────────────────────────────
        # Use sensitive parameters to properly catch fast legato notes (shredding)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onsets = librosa.onset.onset_detect(
            onset_envelope=onset_env, 
            sr=sr,
            pre_max=1, post_max=1, pre_avg=3, post_avg=3, delta=0.05, wait=1
        )
        onset_density = float(len(onsets) / duration) if duration > 0 else 0.0

        # ── Key ───────────────────────────────────────────────────────────────
        key = estimate_key(y, sr)

        riff.duration = duration
        riff.bpm = bpm
        riff.energy = energy
        riff.onset_density = onset_density
        riff.key = key

        riff.analysis_progress = 0.8
        db.commit()

        # ── Basic Pitch (MIDI Extraction via ONNX) ───────────────────────────
        try:
            _extract_midi_onnx(riff.filepath, MIDI_DIR)
            base_filename = os.path.splitext(os.path.basename(riff.filepath))[0]
            expected_output = os.path.join(MIDI_DIR, f"{base_filename}_basic_pitch.mid")
            if os.path.exists(expected_output):
                riff.midi_filepath = expected_output
        except Exception as e:
            print(f"Basic Pitch ONNX failed for riff {riff.id}: {e}")

        riff.analysis_status = "completed"
        riff.analysis_progress = 1.0
        db.commit()
        db.close()
        db = None
        # Chain AI metadata (LLM + embeddings) — graceful if Ollama not running
        generate_ai_metadata(riff_id)
        return

    except Exception as e:
        print(f"Analysis failed for riff {riff.id}: {e}")
        riff.analysis_status = "failed"

    finally:
        if db:
            db.commit()
            db.close()


def generate_ai_metadata(riff_id: int):
    """
    Separate task: run LLM tagging and embedding generation.
    Designed to be called after audio analysis is complete,
    but can also run standalone (e.g. re-tag).
    Fails gracefully if Ollama isn't running.
    """
    import json
    db: Session = SessionLocal()
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        db.close()
        return

    try:
        # ── LLM: Tags + Description ───────────────────────────────────────────
        try:
            from app.ai.llm import get_llm_service
            llm = get_llm_service()
            result = llm.generate_tags_and_description({
                "bpm": riff.bpm,
                "key": riff.key,
                "energy": riff.energy,
                "onset_density": riff.onset_density,
                "voice_note_transcript": riff.voice_note_transcript or "",
                "user_notes": riff.user_notes or "",
            })
            if result.get("tags"):
                riff.tags = json.dumps(result["tags"])
            if result.get("description"):
                riff.ai_description = result["description"]
            db.commit()
        except Exception as e:
            print(f"LLM tagging skipped for riff {riff_id}: {e}")

        # ── Embeddings ────────────────────────────────────────────────────────
        try:
            from app.ai.embeddings import get_embedding_service, build_embedding_text
            emb_service = get_embedding_service()
            text = build_embedding_text(riff)
            embedding = emb_service.embed(text)
            path = emb_service.save(riff_id, embedding)
            riff.embedding_path = path
            db.commit()
        except Exception as e:
            print(f"Embedding generation skipped for riff {riff_id}: {e}")

    finally:
        db.close()
