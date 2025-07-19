# Fitness Builder

AI-powered fitness video processing pipeline that extracts exercises, creates clips, and enables semantic search.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose
- Existing PostgreSQL database
- Existing Qdrant vector database
- OpenAI or Gemini API key

### 1. Environment Setup
```bash
cp env.production.example .env
# Edit .env with your database and API credentials
```

### 2. Build and Deploy
```bash
docker-compose up -d --build
```

### 3. Portainer Deployment
1. **Build the image** using the Dockerfile
2. **Assign network** to your existing PostgreSQL and Qdrant network
3. **Mount volumes** for persistent clip storage:
   - `/app/storage` → Your clips directory
   - `/app/app/temp` → Temporary processing directory
4. **Set environment variables** from your `.env` file
5. **Expose port** 8000

## 📊 API Endpoints

### Core Processing
- `POST /api/v1/process` - Process fitness video from URL
- `GET /api/v1/exercises` - List all exercises
- `GET /api/v1/exercises/{id}` - Get specific exercise

### Search & Discovery
- `POST /api/v1/exercises/search` - Search exercises with filters
- `POST /api/v1/exercises/semantic-search` - Semantic search
- `GET /api/v1/exercises/similar/{id}` - Find similar exercises

### Data Management
- `DELETE /api/v1/exercises/{id}` - Delete specific exercise
- `DELETE /api/v1/exercises/url/{url}` - Delete exercises for specific URL
- `DELETE /api/v1/exercises/all` - Delete all exercises and clips

### Health & Monitoring
- `GET /health` - Health check
- `GET /api/v1/health/database` - Database health check
- `GET /api/v1/health/vector` - Vector database health check
- `GET /api/v1/stats` - Processing statistics

## 🔧 Configuration

### Environment Variables
- `PG_HOST` - PostgreSQL host
- `PG_DBNAME` - Database name
- `PG_USER` - Database user
- `PG_PASSWORD` - Database password
- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant API key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Gemini API key (primary)
- `GEMINI_API_BACKUP_KEY` - Gemini API key (backup/fallback)

## 🏗️ Architecture

- **FastAPI** - REST API backend
- **PostgreSQL** - Exercise metadata storage
- **Qdrant** - Vector database for semantic search
- **FFmpeg** - Video processing and clip generation
- **OpenAI/Gemini** - AI analysis and transcription (with automatic fallback)
- **Instagram Carousel Support** - Automatic detection and processing of multi-item posts

## 📁 Project Structure

```
app/
├── api/          # FastAPI endpoints
├── core/         # Video processing pipeline
├── database/     # Database operations
├── services/     # External services (AI, storage)
└── utils/        # Utility functions
```

## 📡 API Usage Guide

### Process Video from URL

**Endpoint**: `POST /api/v1/process`

**Supported Platforms**:
- YouTube: `https://www.youtube.com/watch?v=VIDEO_ID`
- Instagram: `https://www.instagram.com/p/POST_ID/`
- TikTok: `https://www.tiktok.com/@user/video/VIDEO_ID`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CxYz123ABC/",
    "background": false
  }'
```

**Response**:
```json
{
  "success": true,
  "processed_clips": [
    {
      "exercise_name": "Push-ups",
      "start_time": 5.2,
      "end_time": 15.8,
      "clip_path": "/app/storage/clips/push_ups_001.mp4",
      "how_to": "Start in plank position...",
      "benefits": "Strengthens chest, shoulders, and triceps",
      "fitness_level": 5,
      "intensity": 7
    }
  ],
  "total_clips": 1,
  "processing_time": 45.2,
  "temp_dir": "/app/app/temp/gilgamesh_download_abc123"
}
```

### List All Exercises

**Endpoint**: `GET /api/v1/exercises`

**Query Parameters**:
- `url` (optional): Filter by source URL
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Request**:
```bash
curl "http://localhost:8000/api/v1/exercises?url=https://www.instagram.com/p/CxYz123ABC/&limit=10"
```

### Search Exercises

**Endpoint**: `POST /api/v1/exercises/search`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/exercises/search \
  -H "Content-Type: application/json" \
  -d '{
    "fitness_level": [3, 7],
    "intensity": [5, 10],
    "exercise_name": "push",
    "limit": 20
  }'
```

### Semantic Search

**Endpoint**: `POST /api/v1/exercises/semantic-search`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need a beginner workout for my back that helps with posture",
    "limit": 10,
    "score_threshold": 0.7
  }'
```

### Delete Exercises

**Delete by ID**:
```bash
curl -X DELETE http://localhost:8000/api/v1/exercises/123e4567-e89b-12d3-a456-426614174000
```

**Delete by URL**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/exercises/url/https%3A//www.instagram.com/p/CxYz123ABC/"
```

**Delete All**:
```bash
curl -X DELETE http://localhost:8000/api/v1/exercises/all
```

### Health Checks

**API Health**:
```bash
curl http://localhost:8000/health
```

**Database Health**:
```bash
curl http://localhost:8000/api/v1/health/database
```

**Vector Store Health**:
```bash
curl http://localhost:8000/api/v1/health/vector
```

**Processing Statistics**:
```bash
curl http://localhost:8000/api/v1/stats
```

## 🔍 Supported URL Formats

### YouTube
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

### Instagram
- `https://www.instagram.com/p/POST_ID/`
- `https://www.instagram.com/reel/POST_ID/`
- Carousel posts are automatically detected and all items processed

### TikTok
- `https://www.tiktok.com/@username/video/VIDEO_ID`
- `https://vm.tiktok.com/CODE/`

## ⚡ Processing Pipeline

1. **Download**: Video downloaded from URL
2. **Transcribe**: Audio transcribed with Whisper
3. **Extract Frames**: Key frames extracted for AI analysis
4. **AI Detection**: Gemini AI analyzes video + transcript + frames
5. **Generate Clips**: FFmpeg creates individual exercise clips
6. **Store**: Metadata in PostgreSQL, embeddings in Qdrant

## 🚨 Error Handling

- **Rate Limits**: Automatic fallback between Gemini API keys
- **Invalid URLs**: Clear error messages for unsupported platforms
- **Processing Failures**: Detailed error logs in temp directories
- **Network Issues**: Retry logic for downloads and API calls

## 🧪 Testing

```bash
# Test the API
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/fitness-video.mp4"}'

# Test semantic search
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "I need a beginner workout for my back"}'
```
