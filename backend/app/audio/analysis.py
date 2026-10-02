import os
import librosa
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.riff import Riff

MIDI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/midi"))
os.makedirs(MIDI_DIR, exist_ok=True)


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

        # ── Basic Pitch (MIDI Extraction) ─────────────────────────────────────
        try:
            from basic_pitch.inference import predict_and_save
            predict_and_save(
                [riff.filepath],
                MIDI_DIR,
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False
            )
            base_filename = os.path.splitext(os.path.basename(riff.filepath))[0]
            expected_output = os.path.join(MIDI_DIR, f"{base_filename}_basic_pitch.mid")
            if os.path.exists(expected_output):
                riff.midi_filepath = expected_output
        except Exception as e:
            print(f"Basic Pitch failed for riff {riff.id}: {e}")

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
