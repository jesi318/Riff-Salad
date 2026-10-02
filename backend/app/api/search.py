"""
Search endpoints:
  GET  /api/search?q=...          — Natural-language + semantic search
  GET  /api/riffs/{id}/similar    — Find musically similar riffs
  POST /api/riffs/{id}/transcribe — Transcribe a voice-note audio file
  PATCH /api/riffs/{id}/notes     — Update user notes and re-embed
  POST /api/riffs/{id}/tag        — Re-run LLM tagging
"""
import json
import os
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models.riff import Riff
from app.api.riffs import RiffResponse

router = APIRouter()

VOICE_NOTES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/voice_notes")
)
os.makedirs(VOICE_NOTES_DIR, exist_ok=True)


# ── Search ────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    riff: RiffResponse
    score: Optional[float] = None
    match_type: str  # "semantic" | "filter" | "text"


@router.get("/search", response_model=List[SearchResult])
def search_riffs(q: str, db: Session = Depends(get_db)):
    """
    Four-layer search pipeline:
    1. LLM+synonym table parse query into structured filters
    2. Deterministic SQL + in-memory filtering narrows candidates
    3. Semantic embedding re-ranking orders results
    4. Text fallback if embedding unavailable
    """
    all_riffs = db.query(Riff).all()
    if not all_riffs:
        return []

    # ── 1. LLM: Parse structured filters ─────────────────────────────────────
    filters = {}
    try:
        from app.ai.llm import get_llm_service
        filters = get_llm_service().parse_search_intent(q)
    except Exception as e:
        print(f"[search] LLM parsing failed, falling back to text: {e}")
        filters = {}

    print(f"[search] query={q!r} filters={filters}")

    # ── 2. Filter candidates ──────────────────────────────────────────────────
    # Hard SQL filters for BPM and key (indexed, efficient)
    filter_clauses = []
    has_structural = False

    if filters.get("bpm_min") is not None:
        filter_clauses.append(Riff.bpm >= filters["bpm_min"])
        has_structural = True
    if filters.get("bpm_max") is not None:
        filter_clauses.append(Riff.bpm <= filters["bpm_max"])
        has_structural = True
    if filters.get("key"):
        filter_clauses.append(Riff.key.ilike(f"%{filters['key']}%"))
        has_structural = True

    if filter_clauses:
        candidates = db.query(Riff).filter(and_(*filter_clauses)).all()
    else:
        candidates = all_riffs

    # Soft in-memory filters (energy, density, key_mode) — applied as scoring
    # penalties rather than hard cuts to avoid over-filtering small libraries
    def _structural_penalty(riff: "Riff") -> float:
        """
        Returns a multiplier [0, 1] based on how well the riff matches
        soft structural constraints. 1.0 = perfect match; penalizes mismatches.
        """
        penalty = 1.0

        # Energy constraints
        energy_min = filters.get("energy_min")
        energy_max = filters.get("energy_max")
        if riff.energy is not None:
            if energy_min is not None and riff.energy < energy_min:
                shortfall = (energy_min - riff.energy) / energy_min
                penalty *= max(0.2, 1.0 - shortfall * 2)
            if energy_max is not None and riff.energy > energy_max:
                excess = (riff.energy - energy_max) / energy_max
                penalty *= max(0.2, 1.0 - excess * 2)
        elif energy_min is not None or energy_max is not None:
            penalty *= 0.7  # unknown energy when filter is set

        # Note density constraints
        density_min = filters.get("density_min")
        density_max = filters.get("density_max")
        if riff.onset_density is not None:
            if density_min is not None and riff.onset_density < density_min:
                shortfall = (density_min - riff.onset_density) / density_min
                penalty *= max(0.2, 1.0 - shortfall * 1.5)
            if density_max is not None and riff.onset_density > density_max:
                excess = (riff.onset_density - density_max) / density_max
                penalty *= max(0.2, 1.0 - excess * 1.5)

        # Key mode (minor/major) — soft filter since key detection isn't perfect
        key_mode = filters.get("key_mode")
        if key_mode and riff.key:
            if key_mode.lower() not in riff.key.lower():
                penalty *= 0.6  # strong but not total penalty for mode mismatch

        return penalty

    print(f"[search] candidates after SQL filter: {[r.id for r in candidates]}")

    # ── 3. Semantic embedding re-ranking ──────────────────────────────────────
    try:
        from app.ai.embeddings import get_embedding_service, cosine_similarity
        emb_service = get_embedding_service()
        q_vec = emb_service.embed(q)  # embed full original query

        scored = []
        for riff in candidates:
            sem_score = 0.0
            has_embedding = riff.embedding_path and os.path.exists(riff.embedding_path)

            if has_embedding:
                r_vec = emb_service.load(riff.embedding_path)
                # normalize cosine [-1, 1] → [0, 1]
                sem_score = (cosine_similarity(q_vec, r_vec) + 1) / 2

            # Apply soft structural penalty
            struct_penalty = _structural_penalty(riff)

            if has_structural:
                # SQL already ensured BPM/key hard match — boost base score,
                # then apply soft penalty on top.
                base = min(sem_score + 0.2, 1.0) if has_embedding else 0.5
                final = base * struct_penalty
                scored.append((riff, final, "filter"))
            else:
                # Pure semantic — apply threshold and soft penalty
                penalized = sem_score * struct_penalty
                if sem_score >= 0.50 and penalized >= 0.45:  # ensure it's still decent after penalties
                    scored.append((riff, penalized, "semantic"))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            print(f"[search] returning {len(scored)} semantic results")
            return [
                SearchResult(riff=r, score=round(s, 4), match_type=mt)
                for r, s, mt in scored[:20]
            ]
    except Exception as e:
        print(f"[search] Semantic search failed: {e}, falling back to text")

    # ── 4. Text fallback ──────────────────────────────────────────────────────
    query_words = [w for w in q.lower().split() if len(w) > 2]
    # Also use LLM text_hint if present
    if filters.get("text_hint"):
        query_words.extend(filters["text_hint"].lower().split())

    results = []
    for riff in candidates:
        haystack = " ".join(filter(None, [
            riff.title,
            riff.ai_description,
            riff.tags,
            riff.voice_note_transcript,
            riff.user_notes,
            riff.key,
            str(int(riff.bpm)) if riff.bpm else "",
        ])).lower()
        if any(w in haystack for w in query_words):
            results.append(SearchResult(riff=riff, score=None, match_type="text"))

    print(f"[search] returning {len(results)} text-fallback results")
    return results[:20]



# ── Similar Riff Search ───────────────────────────────────────────────────────

class SimilarResult(BaseModel):
    riff: RiffResponse
    similarity: float  # 0–1


@router.get("/riffs/{riff_id}/similar", response_model=List[SimilarResult])
def find_similar(riff_id: int, db: Session = Depends(get_db)):
    """
    Hybrid similarity search:
    - 60% semantic embedding similarity (text + tags + description)
    - 40% deterministic feature similarity (BPM, key, energy)
    Only returns riffs above a 30% combined threshold.
    Similarity is approximate — not objective musical equivalence.
    """
    source = db.query(Riff).filter(Riff.id == riff_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Riff not found")
    if not source.embedding_path or not os.path.exists(source.embedding_path):
        raise HTTPException(
            status_code=422,
            detail="No embedding available — click the ✨ Sparkles button to generate one."
        )

    from app.ai.embeddings import get_embedding_service, cosine_similarity, feature_similarity
    emb_service = get_embedding_service()
    src_vec = emb_service.load(source.embedding_path)

    others = db.query(Riff).filter(Riff.id != riff_id).all()
    scored = []
    for riff in others:
        # Semantic score
        emb_score = 0.0
        if riff.embedding_path and os.path.exists(riff.embedding_path):
            r_vec = emb_service.load(riff.embedding_path)
            emb_score = (cosine_similarity(src_vec, r_vec) + 1) / 2

        # Feature score (BPM, key, energy)
        feat_score = feature_similarity(source, riff)

        # Hybrid: 60% semantic, 40% feature
        combined = (emb_score * 0.6) + (feat_score * 0.4)

        if combined >= 0.30:
            scored.append((riff, combined))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        SimilarResult(riff=r, similarity=round(s, 4))
        for r, s in scored[:10]
    ]


# ── Voice Note Transcription ──────────────────────────────────────────────────

@router.post("/riffs/{riff_id}/transcribe", response_model=RiffResponse)
async def transcribe_voice_note(
    riff_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Upload a voice note audio file and transcribe it locally with Whisper."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        raise HTTPException(status_code=404, detail="Riff not found")

    ext = os.path.splitext(file.filename or ".wav")[1] or ".webm"
    save_path = os.path.join(VOICE_NOTES_DIR, f"riff_{riff_id}_voice{ext}")
    with open(save_path, "wb") as f:
        f.write(await file.read())

    background_tasks.add_task(_transcribe_and_update, riff_id, save_path)
    return riff


def _transcribe_and_update(riff_id: int, audio_path: str):
    from app.database import SessionLocal
    from app.audio.analysis import generate_ai_metadata
    db = SessionLocal()
    try:
        from app.ai.transcription import get_transcription_service
        text = get_transcription_service().transcribe(audio_path)
        riff = db.query(Riff).filter(Riff.id == riff_id).first()
        if riff:
            riff.voice_note_transcript = text
            db.commit()
        db.close()
        db = None
        generate_ai_metadata(riff_id)
    except Exception as e:
        print(f"Transcription failed for riff {riff_id}: {e}")
    finally:
        if db:
            db.close()


# ── User Notes ────────────────────────────────────────────────────────────────

class NotesUpdate(BaseModel):
    user_notes: str


@router.patch("/riffs/{riff_id}/notes", response_model=RiffResponse)
def update_notes(
    riff_id: int,
    body: NotesUpdate,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Update the user's manual notes and regenerate embedding + AI tags."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        raise HTTPException(status_code=404, detail="Riff not found")
    riff.user_notes = body.user_notes
    db.commit()
    db.refresh(riff)
    from app.audio.analysis import generate_ai_metadata
    background_tasks.add_task(generate_ai_metadata, riff_id)
    return riff


# ── Re-tag (LLM + Embeddings only) ───────────────────────────────────────────

@router.post("/riffs/{riff_id}/tag", response_model=RiffResponse)
def retag_riff(
    riff_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Re-run LLM tagging and embedding generation without re-analyzing audio."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        raise HTTPException(status_code=404, detail="Riff not found")
    from app.audio.analysis import generate_ai_metadata
    background_tasks.add_task(generate_ai_metadata, riff_id)
    return riff
