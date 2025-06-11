from sqlalchemy import Column, String, LargeBinary, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class AudioFile(Base):
    __tablename__ = "audio_files"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String(255), nullable=False)
    original_audio = Column(LargeBinary, nullable=False)
    enhanced_audio = Column(LargeBinary, nullable=True)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), default="uploaded")  # uploaded, processing, enhanced, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.original_filename}, status={self.status})>"
