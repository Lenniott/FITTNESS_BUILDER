# Gilgamesh Media Processing Service - Project Context

## Project Overview
Gilgamesh is a modular video processing and AI analysis service that automatically analyzes videos, generates clips, and provides AI-powered curation. The service follows a "serene clarity" design philosophy with natural light, negative space, and textural contrast.

## 🎯 **Future Vision: Fitness Knowledge Bank**

### **Core Mission**
Build a comprehensive fitness knowledge bank with curated exercise clips and on-demand workout routines based on user preferences and requirements.

### **Key Concepts**
- **Cut**: Single piece of continuous footage from source video
- **Clip**: Created content that may combine multiple cuts for better exercise representation
- **Flow**: Series of exercises done in succession creating one complete movement pattern
- **Story**: Standalone exercise outcome with problem, goal, and solution

### **User Experience Vision**
- **On-Demand Workouts**: Personalized routines based on user requirements
- **Fitness Knowledge Bank**: Curated exercise library with complete movement demonstrations
- **Social Media Integration**: Smart content extraction from fitness influencers
- **Quality Curation**: Only high-quality, complete movement demonstrations
- **Easy Management**: URL tracking for simple content management

### **Technical Vision**
- **JSON Workout Structure**: Structured workout data for easy UI consumption
- **Multi-Stage Compilation**: Intelligent workout creation pipeline
- **Quality Validation**: Comprehensive movement range and form validation
- **Deduplication System**: Variety and effectiveness in workout routines
- **URL Attribution**: Complete content tracking and management

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
  - **Note:** Postgres and Qdrant are external services, typically running on the same Docker network in production. They are not part of this project's containers, and the processor connects to them via their network IPs (e.g., `192.168.0.47`) or Docker network aliases.
- **Testing**: Pytest with async support and coverage reporting
- **Carousel Support**: Proper Instagram carousel detection and individual item processing
- **Data Management**: Comprehensive delete endpoints for cleanup across database, vector store, and files

## Major Pipeline & Frame Extraction Updates (2024-07)
- **Enhanced Frame Extraction**: All frames from the extraction folder are used for AI analysis (no filtering, no artificial limits, consistent naming)
- **Processor Logic**:
  - Adds carousel context to the AI prompt (first video in carousel is often an intro/hook, skip if no exercise is present)
  - Prevents multiple clips with start times within 3 seconds of each other
  - Consolidates overlapping exercises (>50% overlap)
  - Extends single exercises to cover the full video duration if needed
  - Uses improved AI prompt with explicit rules for non-overlapping, non-duplicate, and complete movement detection
- **Robustness**: The pipeline is now robust against duplicate, overlapping, or fragmented exercise detection
- **Instagram Carousel Handling**: All videos are downloaded once, and each is processed individually. The system is robust for both single-cut and multi-cut videos, and for carousels with intro/hook videos.

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
- **External Services:** Postgres and Qdrant must be running and accessible on the same Docker network (or via their network IPs) for the processor to function. These are not included in this project's containers.

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

---

## 🔗 **Cross-Document Dependencies**

### **Pipeline Issues Dependencies**
- **Issue #13-16**: AI Exercise Detection and Validation Issues
- **Issue #17**: URL Tracking System
- **Issue #18-22**: Social Media Content and Quality Issues

### **AI Pipeline Upgrades Dependencies**
- **Improvement #1**: Social Media Content Understanding
- **Improvement #2**: Movement Range Validation
- **Improvement #3**: URL Tracking System
- **Improvement #4**: Exercise vs Flow Classification
- **Improvement #5**: Deduplication System
- **Improvement #6**: Enhanced Frame Analysis

### **Future Vision Dependencies**
- **Quality Standards**: Complete movement demonstration requirements
- **User Experience**: On-demand workout routine generation
- **Content Management**: URL tracking and attribution systems
- **Technical Architecture**: JSON workout structure and multi-stage compilation 