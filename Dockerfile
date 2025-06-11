FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p static templates pretrained_models logs

# Expose Hugging Face Spaces port
EXPOSE 7860

# Set environment variables for Hugging Face Spaces
ENV HOST=0.0.0.0
ENV PORT=7860
ENV GRADIO_SERVER_PORT=7860

# Run the application
CMD ["python", "app_hf.py"]