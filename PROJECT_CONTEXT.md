# Gilgamesh Media Processing Service - Project Context

## Project Overview
Gilgamesh is a modular video processing and AI analysis service that automatically analyzes videos, generates clips, and provides AI-powered curation. The service follows a "serene clarity" design philosophy with natural light, negative space, and textural contrast.

## Core Architecture
- **FastAPI Backend**: Modern async web framework with rate limiting and CORS
- **Modular Structure**: Clear separation between API, core logic, database, services, and utils
- **PostgreSQL**: Primary database for exercise metadata storage with timing data
- **Qdrant**: Vector database for AI embeddings and semantic search
- **AI Providers**: Google Gemini (primary + backup keys, cost-effective) + OpenAI (fallback)
- **Video Processing**: FFmpeg for clip generation, OpenCV for frame analysis

## Key Components
- **Video Processing**: yt-dlp for downloads, FFmpeg for clip generation, OpenCV for frame analysis
- **Audio Processing**: OpenAI Whisper for transcription with Instagram caption handling
- **AI Analysis**: Exercise detection with Gemini multimodal analysis (automatic fallback between API keys), scene detection, content analysis
- **Storage**: Permanent clip storage in `storage/clips/` with database metadata
- **Database**: PostgreSQL for exercise data with start/end timing, Qdrant for vector search
- **Testing**: Pytest with async support and coverage reporting
- **Carousel Support**: Proper Instagram carousel detection and individual item processing
- **Data Management**: Comprehensive delete endpoints for cleanup across database, vector store, and files

## Development Workflow
1. Local development with docker-compose
2. Git push to main branch
3. Portainer image creation from main
4. Container deployment with UI configuration

## Container Volume Configuration
- **fitness_storage** → `/app/storage` (individual clip storage)
- **fitness_compiled** → `/app/storage/compiled_workouts` (compiled workout videos)
- **fitness_temp** → `/app/app/temp` (temporary processing)
- Video clips are stored in `/app/storage/clips/` inside container
- Compiled workouts are stored in `/app/storage/compiled_workouts/` inside container
- Database stores paths relative to container filesystem

## Environment Setup
- Python 3.11+ required
- FFmpeg for video processing
- Environment variables for API keys and database connections
- Docker containerization for production deployment

## Design Philosophy
- "Invisible made visible" through chaos-to-organization animations
- Grounded, clear, systems-first approach
- Avoid gloss/glassmorphism, use natural materials and textures
- Color palette: off-white, charcoal-navy, olive, rust, muted-gold
- Typography: Inter + Crimson Text

## File Structure
```
app/
├── api/          # FastAPI endpoints and middleware
├── core/         # Main processing pipeline and AI analysis
├── database/     # PostgreSQL operations and vectorization
├── services/     # External services (AI, transcription, storage)
└── utils/        # Video utilities, clip operations, cleanup
```

## Dependencies Focus
- Video processing: yt-dlp, ffmpeg-python, opencv-python-headless
- AI/ML: openai, google-generativeai, openai-whisper
- Database: asyncpg, psycopg2-binary, qdrant-client
- Web framework: fastapi, uvicorn, python-multipart
- Testing: pytest, pytest-asyncio, pytest-cov
- Environment: python-dotenv for configuration management 