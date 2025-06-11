# NoiseNix - Audio Enhancement with MetricGAN+

🎵 **NoiseNix** is an advanced audio enhancement web application powered by MetricGAN+ and deployed on Hugging Face Spaces.

## 🚀 Features

- **Advanced Audio Enhancement**: Uses MetricGAN+ for state-of-the-art noise reduction
- **Web Interface**: Simple drag-and-drop file upload
- **Real-time Processing**: Background processing with status updates  
- **Multiple Formats**: Supports WAV audio files
- **Free Hosting**: Deployed on Hugging Face Spaces

## 🔧 API Endpoints

- `POST /api/v1/upload` - Upload audio file for enhancement
- `GET /api/v1/status/{file_id}` - Check processing status
- `GET /api/v1/download/{file_id}` - Download enhanced audio
- `GET /api/v1/stream/{file_id}` - Stream audio for playback

## 🤗 Hugging Face Spaces

This application is optimized for Hugging Face Spaces deployment with:
- Port 7860 configuration
- Memory-optimized model loading
- Automatic cleanup routines
- Comprehensive logging

## 📝 License

MIT License - Feel free to use and modify!