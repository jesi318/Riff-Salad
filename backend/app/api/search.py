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
    Natural-language search with three layers:
    1. Parse structured filters via LLM
    2. Apply deterministic SQL filters
    3. Re-rank results by semantic embedding similarity
    The LLM interprets intent; the database retrieves records.
    """
    riffs = db.query(Riff).all()
    if not riffs:
        return []

    # ── 1. Try LLM to extract filters ────────────────────────────────────────
    filters = {}
    try:
        from app.ai.llm import get_llm_service
        filters = get_llm_service().parse_search_intent(q)
    except Exception as e:
        print(f"LLM search parsing failed, falling back to text: {e}")
        filters = {"text": q}

    # ── 2. Apply deterministic filters ───────────────────────────────────────
    query = db.query(Riff)

    if "bpm_min" in filters:
        query = query.filter(Riff.bpm >= filters["bpm_min"])
    if "bpm_max" in filters:
        query = query.filter(Riff.bpm <= filters["bpm_max"])
    if "key" in filters and filters["key"]:
        query = query.filter(Riff.key.ilike(f"%{filters['key']}%"))
    if "tags" in filters:
        for tag in filters["tags"]:
            query = query.filter(Riff.tags.ilike(f"%{tag}%"))

    candidates = query.all()

    # ── 3. Text / semantic re-ranking ─────────────────────────────────────────
    text_query = filters.get("text", q).strip()

    # Try semantic (embedding) search first
    try:
        from app.ai.embeddings import get_embedding_service, cosine_similarity
        emb_service = get_embedding_service()
        q_vec = emb_service.embed(text_query)

        scored = []
        for riff in (candidates if filters else riffs):
            if riff.embedding_path and os.path.exists(riff.embedding_path):
                r_vec = emb_service.load(riff.embedding_path)
                score = cosine_similarity(q_vec, r_vec)
                scored.append((riff, score, "semantic"))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            return [
                SearchResult(riff=r, score=round(s, 4), match_type=mt)
                for r, s, mt in scored[:20]
            ]
    except Exception as e:
        print(f"Semantic search failed, falling back to text: {e}")

    # Plain text fallback — search title, description, tags, transcript, notes
    text_lower = text_query.lower()
    results = []
    for riff in (candidates if candidates else riffs):
        haystack = " ".join(filter(None, [
            riff.title, riff.ai_description, riff.tags,
            riff.voice_note_transcript, riff.user_notes,
        ])).lower()
        if text_lower in haystack:
            results.append(SearchResult(riff=riff, score=None, match_type="text"))

    return results[:20]


# ── Similar Riff Search ───────────────────────────────────────────────────────

class SimilarResult(BaseModel):
    riff: RiffResponse
    similarity: float  # 0–1


@router.get("/riffs/{riff_id}/similar", response_model=List[SimilarResult])
def find_similar(riff_id: int, db: Session = Depends(get_db)):
    """
    Find riffs similar to the given one using stored embeddings.
    Similarity score is approximate — not objective musical equivalence.
    """
    source = db.query(Riff).filter(Riff.id == riff_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Riff not found")
    if not source.embedding_path or not os.path.exists(source.embedding_path):
        raise HTTPException(
            status_code=422,
            detail="No embedding available for this riff — re-analyze to generate one."
        )

    from app.ai.embeddings import get_embedding_service, cosine_similarity
    emb_service = get_embedding_service()
    src_vec = emb_service.load(source.embedding_path)

    others = db.query(Riff).filter(Riff.id != riff_id).all()
    scored = []
    for riff in others:
        if riff.embedding_path and os.path.exists(riff.embedding_path):
            r_vec = emb_service.load(riff.embedding_path)
            score = cosine_similarity(src_vec, r_vec)
            scored.append((riff, score))

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

    save_path = os.path.join(VOICE_NOTES_DIR, f"riff_{riff_id}_voice{os.path.splitext(file.filename or '.wav')[1]}")
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


# ── User Notes ───────────────────────────────────────────────────────────────

class NotesUpdate(BaseModel):
    user_notes: str


@router.patch("/riffs/{riff_id}/notes", response_model=RiffResponse)
def update_notes(riff_id: int, body: NotesUpdate, background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
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
def retag_riff(riff_id: int, background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
    """Re-run LLM tagging and embedding generation without re-analyzing audio."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if not riff:
        raise HTTPException(status_code=404, detail="Riff not found")
    from app.audio.analysis import generate_ai_metadata
    background_tasks.add_task(generate_ai_metadata, riff_id)
    return riff
