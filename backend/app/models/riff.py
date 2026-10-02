from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Riff(Base):
    __tablename__ = "riffs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, default="Untitled Riff")
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Audio Intelligence Fields
    analysis_status = Column(String, default="pending")
    analysis_progress = Column(Float, default=0.0)
    bpm = Column(Float, nullable=True)
    key = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    energy = Column(Float, nullable=True)
    onset_density = Column(Float, nullable=True)
    midi_filepath = Column(String, nullable=True)
    # Milestone 3 — AI Search
    voice_note_transcript = Column(String, nullable=True)
    user_notes = Column(String, nullable=True)
    tags = Column(String, nullable=True)          # JSON array stored as string
    ai_description = Column(String, nullable=True)
    embedding_path = Column(String, nullable=True)
