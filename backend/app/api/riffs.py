import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.riff import Riff
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import FileResponse
from app.audio.analysis import analyze_audio_task

router = APIRouter()

AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)

class RiffResponse(BaseModel):
    id: int
    title: str
    filename: str
    filepath: str
    created_at: datetime
    analysis_status: str
    analysis_progress: Optional[float] = 0.0
    bpm: Optional[float] = None
    key: Optional[str] = None
    duration: Optional[float] = None
    energy: Optional[float] = None
    onset_density: Optional[float] = None
    midi_filepath: Optional[str] = None
    voice_note_transcript: Optional[str] = None
    user_notes: Optional[str] = None
    tags: Optional[str] = None
    ai_description: Optional[str] = None
    embedding_path: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/", response_model=RiffResponse)
async def create_riff(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['wav', 'mp3', 'm4a']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Must be WAV, MP3, or M4A.")
        
    filepath = os.path.join(AUDIO_DIR, file.filename)
    
    # Check if file exists, add timestamp if it does to prevent overwrite
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(AUDIO_DIR, filename)
    else:
        filename = file.filename

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    db_riff = Riff(
        title=filename,
        filename=filename,
        filepath=filepath
    )
    db.add(db_riff)
    db.commit()
    db.refresh(db_riff)
    
    background_tasks.add_task(analyze_audio_task, db_riff.id)
    
    return db_riff

@router.get("/", response_model=List[RiffResponse])
def read_riffs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    riffs = db.query(Riff).offset(skip).limit(limit).all()
    return riffs

@router.post("/{riff_id}/analyze", response_model=RiffResponse)
def reanalyze_riff(riff_id: int, background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
    riff.analysis_status = "pending"
    riff.analysis_progress = 0.0
    db.commit()
    db.refresh(riff)
    background_tasks.add_task(analyze_audio_task, riff_id)
    return riff

@router.get("/{riff_id}", response_model=RiffResponse)
def read_riff(riff_id: int, db: Session = Depends(get_db)):
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
    return riff

@router.get("/{riff_id}/audio")
def get_riff_audio(riff_id: int, db: Session = Depends(get_db)):
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
    
    if not os.path.exists(riff.filepath):
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
        
    return FileResponse(riff.filepath)

@router.delete("/{riff_id}")
def delete_riff(riff_id: int, db: Session = Depends(get_db)):
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
        
    # Delete audio file
    if riff.filepath and os.path.exists(riff.filepath):
        try:
            os.remove(riff.filepath)
        except Exception:
            pass
            
    # Delete MIDI file
    if riff.midi_filepath and os.path.exists(riff.midi_filepath):
        try:
            os.remove(riff.midi_filepath)
        except Exception:
            pass
            
    db.delete(riff)
    db.commit()
    return {"message": "Riff deleted successfully"}


class TitleUpdate(BaseModel):
    title: str


@router.patch("/{riff_id}/title", response_model=RiffResponse)
def update_title(riff_id: int, body: TitleUpdate, db: Session = Depends(get_db)):
    """Rename a riff title inline."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    riff.title = title
    db.commit()
    db.refresh(riff)
    return riff


class MetaUpdate(BaseModel):
    bpm: Optional[float] = None
    key: Optional[str] = None


@router.patch("/{riff_id}/meta", response_model=RiffResponse)
def update_meta(riff_id: int, body: MetaUpdate, db: Session = Depends(get_db)):
    """Manually override BPM or Key metadata."""
    riff = db.query(Riff).filter(Riff.id == riff_id).first()
    if riff is None:
        raise HTTPException(status_code=404, detail="Riff not found")
    if body.bpm is not None:
        riff.bpm = body.bpm
    if body.key is not None:
        riff.key = body.key.strip() or None
    db.commit()
    db.refresh(riff)
    return riff
