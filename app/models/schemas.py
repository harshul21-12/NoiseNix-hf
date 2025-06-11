from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

class AudioFileResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AudioFileUploadResponse(BaseModel):
    message: str
    file_id: uuid.UUID
    filename: str
    file_size: int
    status: str

class AudioFileStatusResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    status: str
    error_message: Optional[str] = None
    progress: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None