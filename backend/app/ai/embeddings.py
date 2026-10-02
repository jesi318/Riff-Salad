"""
LocalEmbeddingService
Generates and stores text embeddings locally using sentence-transformers.
Embeddings are saved as .npy files alongside audio/midi data.
Model is configurable via EMBEDDING_MODEL env var.
"""
import os
import numpy as np
from app.core.config import EMBEDDING_MODEL, DATA_DIR

EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

_model = None  # lazy singleton


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


class EmbeddingService:
    def embed(self, text: str) -> np.ndarray:
        raise NotImplementedError

    def save(self, riff_id: int, embedding: np.ndarray) -> str:
        path = os.path.join(EMBEDDINGS_DIR, f"riff_{riff_id}.npy")
        np.save(path, embedding)
        return path

    def load(self, path: str) -> np.ndarray:
        return np.load(path)


class LocalEmbeddingService(EmbeddingService):
    def embed(self, text: str) -> np.ndarray:
        model = _load_model()
        return model.encode(text, normalize_embeddings=True)


def get_embedding_service() -> EmbeddingService:
    return LocalEmbeddingService()


def build_embedding_text(riff) -> str:
    """Combine all searchable text fields into one embedding document."""
    parts = []
    if riff.ai_description:
        parts.append(riff.ai_description)
    if riff.tags:
        import json
        try:
            tags = json.loads(riff.tags)
            parts.append(" ".join(tags))
        except Exception:
            parts.append(riff.tags)
    if riff.voice_note_transcript:
        parts.append(riff.voice_note_transcript)
    if riff.user_notes:
        parts.append(riff.user_notes)
    if riff.key:
        parts.append(riff.key)
    if riff.bpm:
        parts.append(f"{int(riff.bpm)} bpm")
    return " ".join(parts) or riff.title


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Returns cosine similarity in [0, 1] for normalised embeddings."""
    return float(np.dot(a, b))
