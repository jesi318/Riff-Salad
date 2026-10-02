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
    bpm = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    energy = Column(Float, nullable=True)
    onset_density = Column(Float, nullable=True)
    midi_filepath = Column(String, nullable=True)
