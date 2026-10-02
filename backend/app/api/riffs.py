import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.riff import Riff
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import FileResponse

router = APIRouter()

AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)

class RiffResponse(BaseModel):
    id: int
    title: str
    filename: str
    filepath: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/", response_model=RiffResponse)
async def create_riff(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
    return db_riff

@router.get("/", response_model=List[RiffResponse])
def read_riffs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    riffs = db.query(Riff).offset(skip).limit(limit).all()
    return riffs

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
