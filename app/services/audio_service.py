import io
import torch
import torchaudio
from speechbrain.inference import SpectralMaskEnhancement
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from ..database.models import AudioFile
from datetime import datetime
import logging
import os
import tempfile
import gc

# Set up logging
logger = logging.getLogger(__name__)

class AudioEnhancementService:
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to load model only once"""
        if cls._instance is None:
            cls._instance = super(AudioEnhancementService, cls).__new__(cls)
            cls._instance._initialize_model()
        return cls._instance
    
    def _initialize_model(self):
        """Initialize the MetricGAN+ model once - optimized for HF Spaces"""
        try:
            logger.info("🤗 Loading MetricGAN+ model for Hugging Face Spaces...")
            
            # Set cache directory for model downloads
            cache_dir = os.path.join(os.getcwd(), "pretrained_models")
            os.makedirs(cache_dir, exist_ok=True)
            os.environ['SPEECHBRAIN_CACHE'] = cache_dir
            
            # Set torch settings for better memory usage
            torch.set_num_threads(2)  # Limit threads for HF Spaces
            
            self._model = SpectralMaskEnhancement.from_hparams(
                source="speechbrain/metricgan-plus-voicebank",
                savedir=os.path.join(cache_dir, "metricgan-plus-voicebank")
            )
            
            logger.info("✅ MetricGAN+ model loaded successfully on HF Spaces!")
            
        except Exception as e:
            logger.error(f"❌ Failed to load MetricGAN+ model: {str(e)}")
            raise RuntimeError(f"Model initialization failed: {str(e)}")
    
    def bytes_to_tensor(self, audio_bytes: bytes) -> Tuple[torch.Tensor, int]:
        """Convert audio bytes to tensor"""
        try:
            audio_buffer = io.BytesIO(audio_bytes)
            waveform, sample_rate = torchaudio.load(audio_buffer)
            return waveform, sample_rate
        except Exception as e:
            raise ValueError(f"Failed to convert bytes to tensor: {str(e)}")
    
    def tensor_to_bytes(self, tensor: torch.Tensor, sample_rate: int = 16000) -> bytes:
        """Convert tensor back to bytes"""
        try:
            buffer = io.BytesIO()
            if tensor.dim() == 1:
                tensor = tensor.unsqueeze(0)
            torchaudio.save(buffer, tensor, sample_rate, format="wav")
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            raise ValueError(f"Failed to convert tensor to bytes: {str(e)}")
    
    def enhance_from_bytes(self, audio_bytes: bytes) -> bytes:
        """Main enhancement function optimized for HF Spaces"""
        try:
            logger.info("🎵 Starting audio enhancement on HF Spaces...")
            
            # Clear GPU cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            waveform, original_sample_rate = self.bytes_to_tensor(audio_bytes)
            logger.info(f"📊 Original: {waveform.shape}, {original_sample_rate}Hz")
            
            # Resample to 16kHz if needed
            if original_sample_rate != 16000:
                logger.info(f"🔄 Resampling from {original_sample_rate}Hz to 16000Hz")
                resampler = torchaudio.transforms.Resample(
                    orig_freq=original_sample_rate,
                    new_freq=16000
                )
                waveform = resampler(waveform)
            
            # Ensure mono and correct shape
            if waveform.shape[0] > 1:
                logger.info(f"🎵 Converting {waveform.shape[0]} channels to mono")
                waveform = waveform.mean(dim=0, keepdim=True)
            
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            
            logger.info(f"📊 Pre-enhancement shape: {waveform.shape}")
            
            # Create temporary files for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_input:
                temp_input_path = temp_input.name
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            try:
                # Save input tensor to temporary file
                torchaudio.save(temp_input_path, waveform, 16000, format="wav")
                logger.info("💾 Saved input to temporary file")
                
                # Enhance using file-based approach
                enhanced_waveform = self._model.enhance_file(temp_input_path, temp_output_path)
                
                # Load enhanced audio
                if os.path.exists(temp_output_path):
                    enhanced_waveform, _ = torchaudio.load(temp_output_path)
                    logger.info(f"✅ Enhanced shape: {enhanced_waveform.shape}")
                else:
                    if enhanced_waveform is None:
                        raise RuntimeError("Enhancement failed: no output produced")
                    logger.info(f"✅ Enhanced shape: {enhanced_waveform.shape}")
                
                # Convert back to bytes
                enhanced_bytes = self.tensor_to_bytes(enhanced_waveform, 16000)
                logger.info("🎉 Audio enhancement completed successfully!")
                
                # Force garbage collection to free memory
                del waveform, enhanced_waveform
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                return enhanced_bytes
                
            finally:
                # Clean up temporary files
                for temp_path in [temp_input_path, temp_output_path]:
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except Exception as cleanup_error:
                            logger.warning(f"⚠️ Cleanup failed for {temp_path}: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"❌ Enhancement failed: {str(e)}")
            # Force cleanup on error
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise RuntimeError(f"Enhancement failed: {str(e)}")

# Keep the AudioDatabaseService and process_audio_enhancement functions as they are
class AudioDatabaseService:
    """Service for database operations"""
    
    @staticmethod
    def create_audio_file(db: Session, filename: str, audio_bytes: bytes) -> AudioFile:
        """Store uploaded audio file in database"""
        try:
            audio_file = AudioFile(
                original_filename=filename,
                original_audio=audio_bytes,
                file_size=len(audio_bytes),
                status="uploaded"
            )
            db.add(audio_file)
            db.commit()
            db.refresh(audio_file)
            logger.info(f"💾 Audio file stored: {filename} ({len(audio_bytes)} bytes)")
            return audio_file
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to store audio file: {str(e)}")
            raise
    
    @staticmethod
    def get_audio_file(db: Session, file_id: str) -> Optional[AudioFile]:
        """Retrieve audio file by ID"""
        try:
            return db.query(AudioFile).filter(AudioFile.id == file_id).first()
        except Exception as e:
            logger.error(f"❌ Failed to retrieve audio file {file_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_audio_status(db: Session, file_id: str, status: str, error_message: str = None):
        """Update audio file status"""
        try:
            audio_file = db.query(AudioFile).filter(AudioFile.id == file_id).first()
            if audio_file:
                audio_file.status = status
                audio_file.error_message = error_message
                if status == "enhanced":
                    audio_file.processed_at = datetime.utcnow()
                db.commit()
                logger.info(f"✅ Updated {file_id} status to {status}")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to update status for {file_id}: {str(e)}")
    
    @staticmethod
    def store_enhanced_audio(db: Session, file_id: str, enhanced_bytes: bytes):
        """Store enhanced audio bytes"""
        try:
            audio_file = db.query(AudioFile).filter(AudioFile.id == file_id).first()
            if audio_file:
                audio_file.enhanced_audio = enhanced_bytes
                audio_file.status = "enhanced"
                audio_file.processed_at = datetime.utcnow()
                db.commit()
                logger.info(f"💾 Enhanced audio stored for {file_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to store enhanced audio for {file_id}: {str(e)}")
            raise

async def process_audio_enhancement(db: Session, file_id: str):
    """Process audio enhancement asynchronously"""
    enhancement_service = AudioEnhancementService()
    db_service = AudioDatabaseService()
    
    try:
        db_service.update_audio_status(db, file_id, "processing")
        audio_file = db_service.get_audio_file(db, file_id)
        
        if not audio_file:
            raise ValueError(f"Audio file {file_id} not found")
        
        enhanced_bytes = enhancement_service.enhance_from_bytes(audio_file.original_audio)
        db_service.store_enhanced_audio(db, file_id, enhanced_bytes)
        
        logger.info(f"🎉 Audio enhancement completed for {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Audio enhancement failed for {file_id}: {str(e)}")
        db_service.update_audio_status(db, file_id, "error", str(e))
        return False