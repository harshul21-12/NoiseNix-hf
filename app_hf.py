#!/usr/bin/env python3
"""
NoiseNix - Hugging Face Spaces Entry Point
"""
import uvicorn
import os
import sys
import logging
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging for Hugging Face Spaces
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    # Hugging Face Spaces specific configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 7860))
    
    print("🎵 Starting NoiseNix on Hugging Face Spaces...")
    print(f"📍 Server: http://{host}:{port}")
    print("🤗 Optimized for Hugging Face Spaces")
    
    # Import app after setting up paths and logging
    from app.main import app
    
    # Run the application with Hugging Face Spaces settings
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,  # Always False in production
        log_level="info",
        access_log=True
    )