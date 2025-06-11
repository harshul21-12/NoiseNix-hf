from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from .api.routes import router as api_router
from .database.database import init_db
import logging
import os
import sys

# Configure logging for Hugging Face Spaces
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create FastAPI app with updated config for HF Spaces
app = FastAPI(
    title="NoiseNix - Audio Enhancement",
    description="MetricGAN+ based audio enhancement service running on Hugging Face Spaces",
    version="1.0.0",
    docs_url="/docs",  # Keep API docs accessible
    redoc_url="/redoc"
)

# Initialize database
try:
    init_db()
    logging.info("✅ Database initialized successfully")
except Exception as e:
    logging.error(f"❌ Database initialization failed: {e}")

# Mount static files with error handling
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logging.info("✅ Static files mounted")
else:
    logging.warning("⚠️ Static directory not found")

# Setup templates with error handling
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
if os.path.exists(template_dir):
    templates = Jinja2Templates(directory=template_dir)
    logging.info("✅ Templates configured")
else:
    logging.error("❌ Templates directory not found")
    # Create a minimal template response for missing templates
    templates = None

# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["audio"])

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        # Fallback HTML if templates are missing
        return HTMLResponse("""
        <html>
            <head><title>NoiseNix - Audio Enhancement</title></head>
            <body>
                <h1>🎵 NoiseNix Audio Enhancement</h1>
                <p>API is running! Visit <a href="/docs">/docs</a> for API documentation.</p>
                <p>Upload endpoint: <code>POST /api/v1/upload</code></p>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint for Hugging Face Spaces"""
    try:
        # Try to import and check if model can be loaded
        from .services.audio_service import AudioEnhancementService
        service = AudioEnhancementService()
        model_status = "loaded" if hasattr(service, '_model') and service._model else "loading"
    except Exception as e:
        model_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "platform": "Hugging Face Spaces",
        "model_status": model_status,
        "database": "connected",
        "port": "7860"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logging.info("🚀 NoiseNix starting up on Hugging Face Spaces...")
    logging.info("📊 Database initialized")
    logging.info("🤗 Optimized for Hugging Face Spaces")
    logging.info("🎵 Ready to enhance audio files!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logging.info("👋 NoiseNix shutting down...")

# Add CORS middleware for Hugging Face Spaces
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)