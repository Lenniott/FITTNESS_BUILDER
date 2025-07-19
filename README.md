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

- `GET /health` - Health check
- `POST /api/v1/process` - Process fitness video
- `GET /api/v1/exercises` - List all exercises
- `POST /api/v1/exercises/semantic-search` - Semantic search

## 🔧 Configuration

### Environment Variables
- `PG_HOST` - PostgreSQL host
- `PG_DBNAME` - Database name
- `PG_USER` - Database user
- `PG_PASSWORD` - Database password
- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant API key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Gemini API key

## 🏗️ Architecture

- **FastAPI** - REST API backend
- **PostgreSQL** - Exercise metadata storage
- **Qdrant** - Vector database for semantic search
- **FFmpeg** - Video processing and clip generation
- **OpenAI/Gemini** - AI analysis and transcription

## 📁 Project Structure

```
app/
├── api/          # FastAPI endpoints
├── core/         # Video processing pipeline
├── database/     # Database operations
├── services/     # External services (AI, storage)
└── utils/        # Utility functions
```

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
