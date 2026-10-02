import os
import librosa
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.riff import Riff

MIDI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/midi"))
os.makedirs(MIDI_DIR, exist_ok=True)

def analyze_audio_task(riff_id: int):
    # This runs in a separate thread
    db: Session = SessionLocal()
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        db.close()
        return

    try:
        riff.analysis_status = "processing"
        db.commit()

        # Load audio
        y, sr = librosa.load(riff.filepath, sr=None)
        
        # Duration
        duration = librosa.get_duration(y=y, sr=sr)
        
        # BPM
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        
        # Energy (RMS)
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))
        
        # Onset Density
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        onset_density = float(len(onsets) / duration) if duration > 0 else 0.0

        riff.duration = duration
        riff.bpm = bpm
        riff.energy = energy
        riff.onset_density = onset_density
        
        # Basic Pitch (MIDI Extraction)
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
            
            # Predict and save creates a file with '_basic_pitch.mid' suffix
            base_filename = os.path.splitext(os.path.basename(riff.filepath))[0]
            expected_output = os.path.join(MIDI_DIR, f"{base_filename}_basic_pitch.mid")
            if os.path.exists(expected_output):
                riff.midi_filepath = expected_output
        except Exception as e:
            print(f"Basic Pitch failed for {riff.id}: {e}")
            # Ignore and continue

        riff.analysis_status = "completed"
    
    except Exception as e:
        print(f"Analysis failed for {riff.id}: {e}")
        riff.analysis_status = "failed"
    
    finally:
        db.commit()
        db.close()
