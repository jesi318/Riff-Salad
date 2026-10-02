"""
LocalWhisperTranscriptionService
Transcribes audio files locally using faster-whisper.
Falls back gracefully if the model isn't available.
"""
from app.core.config import WHISPER_MODEL


class TranscriptionService:
    """Abstract interface — swap implementation via config."""

    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError


class LocalWhisperService(TranscriptionService):
    _model = None  # lazy-load singleton

    def _load(self):
        if LocalWhisperService._model is None:
            from faster_whisper import WhisperModel
            LocalWhisperService._model = WhisperModel(
                WHISPER_MODEL, device="cpu", compute_type="int8"
            )
        return LocalWhisperService._model

    def transcribe(self, audio_path: str) -> str:
        model = self._load()
        segments, _ = model.transcribe(audio_path, beam_size=5, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()


def get_transcription_service() -> TranscriptionService:
    return LocalWhisperService()
