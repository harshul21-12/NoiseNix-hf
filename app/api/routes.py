from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..database.models import AudioFile
from ..services.audio_service import AudioDatabaseService, process_audio_enhancement
from ..models.schemas import AudioFileUploadResponse, AudioFileStatusResponse, AudioFileResponse
import io
import logging
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()

# File validation
ALLOWED_EXTENSIONS = {".wav"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_audio_file(file: UploadFile) -> bool:
    """Validate uploaded file"""
    # Check file extension
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False
    
    # Check file size (this is approximate as we haven't read the full file yet)
    return True

@router.post("/upload", response_model=AudioFileUploadResponse)
async def upload_audio_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload audio file for enhancement"""
    try:
        # Validate file
        if not validate_audio_file(file):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file. Only .wav files are supported."
            )
        
        # Read file contents
        file_contents = await file.read()
        
        # Check file size
        if len(file_contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        if len(file_contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Store in database
        db_service = AudioDatabaseService()
        audio_file = db_service.create_audio_file(db, file.filename, file_contents)
        
        # Start background enhancement process
        background_tasks.add_task(process_audio_enhancement, db, str(audio_file.id))
        
        return AudioFileUploadResponse(
            message="File uploaded successfully. Enhancement in progress.",
            file_id=audio_file.id,
            filename=audio_file.original_filename,
            file_size=audio_file.file_size,
            status=audio_file.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/status/{file_id}", response_model=AudioFileStatusResponse)
async def get_audio_status(file_id: str, db: Session = Depends(get_db)):
    """Get processing status of audio file"""
    try:
        db_service = AudioDatabaseService()
        audio_file = db_service.get_audio_file(db, file_id)
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Determine progress message
        progress_messages = {
            "uploaded": "File uploaded, waiting to start processing...",
            "processing": "Enhancing audio with MetricGAN+...",
            "enhanced": "Enhancement completed successfully!",
            "error": "Enhancement failed. Please try again."
        }
        
        return AudioFileStatusResponse(
            file_id=audio_file.id,
            filename=audio_file.original_filename,
            status=audio_file.status,
            error_message=audio_file.error_message,
            progress=progress_messages.get(audio_file.status, "Unknown status"),
            created_at=audio_file.created_at,
            processed_at=audio_file.processed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Status check failed")

@router.get("/download/{file_id}")
async def download_enhanced_audio(file_id: str, db: Session = Depends(get_db)):
    """Download enhanced audio file"""
    try:
        db_service = AudioDatabaseService()
        audio_file = db_service.get_audio_file(db, file_id)
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        if audio_file.status != "enhanced" or not audio_file.enhanced_audio:
            raise HTTPException(
                status_code=400, 
                detail="Enhanced audio not available. Check processing status."
            )
        
        # Create file stream
        audio_stream = io.BytesIO(audio_file.enhanced_audio)
        
        # Generate filename
        base_name = audio_file.original_filename.rsplit('.', 1)[0]
        enhanced_filename = f"{base_name}_enhanced.wav"
        
        return StreamingResponse(
            io.BytesIO(audio_file.enhanced_audio),
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={enhanced_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")

@router.get("/stream/{file_id}")
async def stream_audio(file_id: str, audio_type: str = "enhanced", db: Session = Depends(get_db)):
    """Stream audio for web playback"""
    try:
        db_service = AudioDatabaseService()
        audio_file = db_service.get_audio_file(db, file_id)
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Determine which audio to stream
        if audio_type == "original":
            audio_bytes = audio_file.original_audio
        elif audio_type == "enhanced":
            if audio_file.status != "enhanced" or not audio_file.enhanced_audio:
                raise HTTPException(
                    status_code=400, 
                    detail="Enhanced audio not available"
                )
            audio_bytes = audio_file.enhanced_audio
        else:
            raise HTTPException(status_code=400, detail="Invalid audio type")
        
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Streaming failed")

@router.get("/files", response_model=List[AudioFileResponse])
async def list_audio_files(db: Session = Depends(get_db)):
    """List all audio files (for debugging/admin)"""
    try:
        files = db.query(AudioFile).order_by(AudioFile.created_at.desc()).limit(20).all()
        return files
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve files")

@router.delete("/files/{file_id}")
async def delete_audio_file(file_id: str, db: Session = Depends(get_db)):
    """Delete audio file"""
    try:
        audio_file = db.query(AudioFile).filter(AudioFile.id == file_id).first()
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        db.delete(audio_file)
        db.commit()
        
        return {"message": "Audio file deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Delete failed")