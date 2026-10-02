"""
LocalEmbeddingService
Generates rich, differentiated text embeddings that capture the specific
musical character of each riff — including numeric BPM, key, and energy —
so that similarity search is meaningful rather than generic.
"""
import os
import numpy as np
from app.core.config import EMBEDDING_MODEL, DATA_DIR

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

class EmbeddingService:
    def embed(self, text: str) -> np.ndarray:
        raise NotImplementedError

    def save(self, riff_id: int, embedding: np.ndarray) -> str:
        path = os.path.join(EMBEDDINGS_DIR, f"riff_{riff_id}.npy")
        np.save(path, embedding)
        return path

    def load(self, path: str) -> np.ndarray:
        return np.load(path)

import requests

class OllamaEmbeddingService(EmbeddingService):
    def embed(self, text: str) -> np.ndarray:
        try:
            resp = requests.post(f"{OLLAMA_HOST}/api/embeddings", json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            })
            resp.raise_for_status()
            emb = resp.json()["embedding"]
            # Normalize vector (like sentence-transformers normalize_embeddings=True)
            vec = np.array(emb, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec
        except Exception as e:
            print(f"Ollama embedding failed: {e}")
            raise

def get_embedding_service() -> EmbeddingService:
    return OllamaEmbeddingService()


def build_embedding_text(riff) -> str:
    """
    Build a rich, specific document for embedding that captures the actual
    musical character of the riff. Numeric values are included verbatim
    so the model can differentiate between e.g. 60 BPM vs 140 BPM.
    """
    import json
    parts = []

    # --- Numeric musical facts (most important for differentiation) ---
    if riff.bpm:
        bpm = round(riff.bpm)
        if bpm < 70:    tempo_word = "very slow doom"
        elif bpm < 90:  tempo_word = "slow heavy"
        elif bpm < 110: tempo_word = "mid-tempo"
        elif bpm < 130: tempo_word = "driving uptempo"
        elif bpm < 160: tempo_word = "fast aggressive"
        else:           tempo_word = "very fast frantic"
        parts.append(f"{bpm} BPM {tempo_word} tempo")

    if riff.key:
        key = riff.key
        parts.append(f"key of {key}")
        if "minor" in key.lower():
            parts.append("minor key dark mood")
        elif "major" in key.lower():
            parts.append("major key bright sound")

    if riff.energy is not None:
        e = riff.energy
        if e > 0.15:    parts.append("very high energy loud heavy distorted")
        elif e > 0.08:  parts.append("high energy")
        elif e > 0.04:  parts.append("moderate energy")
        else:           parts.append("low energy quiet delicate clean")

    if riff.onset_density is not None:
        od = riff.onset_density
        if od > 5:      parts.append("extremely dense note density shredding many notes fast picking")
        elif od > 3:    parts.append("dense busy playing many notes")
        elif od > 1.5:  parts.append("moderate note density")
        else:           parts.append("sparse few notes slow held chords minimal")

    if riff.duration:
        parts.append(f"{riff.duration:.1f} seconds duration")

    # --- AI-generated labels ---
    if riff.ai_description:
        parts.append(riff.ai_description)

    if riff.tags:
        try:
            tags = json.loads(riff.tags)
            parts.append(" ".join(tags))
        except Exception:
            parts.append(riff.tags)

    if riff.voice_note_transcript:
        parts.append(f"voice note: {riff.voice_note_transcript}")

    if riff.user_notes:
        parts.append(f"notes: {riff.user_notes}")

    # Fallback
    return " ".join(parts) or riff.title


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Returns cosine similarity in [-1, 1] for normalised embeddings."""
    return float(np.dot(a, b))


def feature_similarity(riff_a, riff_b) -> float:
    """
    Compute a deterministic feature-based similarity score [0, 1] based on
    BPM proximity, key match, and energy proximity. This anchors the
    similarity score in measurable musical facts.
    """
    score = 0.0
    weight_total = 0.0

    # BPM proximity (weight: 40%)
    if riff_a.bpm and riff_b.bpm:
        bpm_diff = abs(riff_a.bpm - riff_b.bpm)
        # Within 5 BPM = full score, tapers to 0 at 60+ BPM apart
        bpm_score = max(0.0, 1.0 - (bpm_diff / 60.0))
        score += bpm_score * 0.40
        weight_total += 0.40

    # Key match (weight: 35%)
    if riff_a.key and riff_b.key:
        if riff_a.key == riff_b.key:
            key_score = 1.0
        elif riff_a.key.split()[0] == riff_b.key.split()[0]:
            # Same root note, different mode (e.g. E Major vs E Minor)
            key_score = 0.4
        else:
            key_score = 0.0
        score += key_score * 0.35
        weight_total += 0.35

    # Energy proximity (weight: 25%)
    if riff_a.energy is not None and riff_b.energy is not None:
        max_energy = 0.3  # normalise against typical max
        e_diff = abs(riff_a.energy - riff_b.energy)
        energy_score = max(0.0, 1.0 - (e_diff / max_energy))
        score += energy_score * 0.25
        weight_total += 0.25

    if weight_total == 0:
        return 0.5  # neutral if no features available
    return score / weight_total
