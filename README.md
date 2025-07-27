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
3. **Mount volumes** for persistent storage:
   - `fitness_storage` → `/app/storage` (individual clip storage)
   - `fitness_temp` → `/app/storage/temp` (temporary processing)
4. **Set environment variables** from your `.env` file
5. **Expose port** 8000

**Note**: The container expects video clips to be stored in `/app/storage/clips/` inside the container, which maps to your host volume `fitness_storage`.

## 📊 API Contract Documentation

### 🔗 Base URL
```
http://localhost:8000/api/v1
```

### 📋 Data Structure Concepts

#### Exercise Entity
An **exercise** in this system consists of three interconnected components:
1. **Stored Clip File** - Video file in `storage/clips/` directory
2. **PostgreSQL Row** - Metadata stored in `exercises` table
3. **Qdrant Vector** - AI embedding for semantic search

All three components are linked via `qdrant_id` and `database_id` fields.

#### Routine Entity
A **routine** is a complete workout structure containing:
- **Exercises Array** - Ordered list of exercises with UI-ready data
- **Metadata** - Database operations info (database_ids, qdrant_ids, video_paths)
- **User Requirements** - Original prompt and parameters
- **Processing Info** - Creation time, processing duration

---

## 🏋️ ROUTINE MANAGEMENT (CRUD)

### Story Generation
**Generate exercise requirement stories from user prompt**

```http
POST /api/v1/stories/generate
```

**Request Body:**
```json
{
  "user_prompt": "I need a quick 5-minute routine I can do at my desk when I stand up, I sit a lot for work",
  "story_count": 3
}
```

**Response:**
```json
{
  "stories": [
    "A quick 5-minute standing routine focused on gentle hip and lower back mobility to counteract the stiffness and discomfort often experienced from prolonged sitting, designed to be performed at a desk with no equipment, encouraging consistent short breaks to improve daily comfort.",
    "A brief 5-minute standing sequence designed to alleviate tension in the neck, shoulders, and upper back, and to improve posture for individuals who spend long hours hunched over a desk, requiring no specialized equipment and suitable for a non-sweat, office-friendly break."
  ]
}
```

### Semantic Search (IDs Only)
**Search for exercises and return only PostgreSQL IDs**

```http
POST /api/v1/exercises/semantic-search-ids
```

**Request Body:**
```json
{
  "query": "A quick 5-minute standing routine focused on gentle hip and lower back mobility...",
  "limit": 5
}
```

**Response:**
```json
{
  "exercise_ids": [
    "047cb042-a3cf-49cc-a763-10290014ac96",
    "5bb68483-8edc-4a4b-ab4c-371b9b61a237",
    "10c7c447-c16c-4c37-b4da-28e5d8cdd132"
  ],
  "total_found": 3
}
```

### Create Routine
**Create a routine with exercise IDs**

```http
POST /api/v1/routines
```

**Request Body:**
```json
{
  "name": "5-Minute Desk Mobility",
  "description": "A quick standing routine for desk workers",
  "exercise_ids": [
    "047cb042-a3cf-49cc-a763-10290014ac96",
    "5bb68483-8edc-4a4b-ab4c-371b9b61a237",
    "10c7c447-c16c-4c37-b4da-28e5d8cdd132"
  ]
}
```

**Response:**
```json
{
  "routine_id": "57243567-9e4e-4df6-a18d-d4e4ccbd2d38",
  "name": "5-Minute Desk Mobility",
  "description": "A quick standing routine for desk workers",
  "exercise_ids": [
    "047cb042-a3cf-49cc-a763-10290014ac96",
    "5bb68483-8edc-4a4b-ab4c-371b9b61a237",
    "10c7c447-c16c-4c37-b4da-28e5d8cdd132"
  ],
  "created_at": "2025-07-27T13:56:39.356021"
}
```

### List Routines
**Get all routines**

```http
GET /api/v1/routines
```

**Query Parameters:**
- `limit` (optional): Number of routines to return (default: 50, max: 100)

**Response:**
```json
[
  {
    "routine_id": "57243567-9e4e-4df6-a18d-d4e4ccbd2d38",
    "name": "5-Minute Desk Mobility",
    "description": "A quick standing routine for desk workers",
    "exercise_ids": ["047cb042-a3cf-49cc-a763-10290014ac96", "5bb68483-8edc-4a4b-ab4c-371b9b61a237"],
    "created_at": "2025-07-27 13:56:39.658759+00:00"
  }
]
```

### Get Routine
**Get a specific routine by ID**

```http
GET /api/v1/routines/{routine_id}
```

**Response:** Same structure as Create Routine response

### Delete Routine
**Delete a routine by ID**

```http
DELETE /api/v1/routines/{routine_id}
```

**Response:**
```json
{
  "message": "Routine deleted successfully"
}
```

### UI Integration Pattern

The new routine system is designed for user-curated workflows:

1. **Generate Stories** - Create exercise requirement stories from user prompt
2. **Semantic Search** - Find relevant exercises (returns IDs only)
3. **User Curation** - UI allows user to add/remove exercises
4. **Create Routine** - Save final curated list as routine
5. **Fetch Exercise Details** - Use bulk endpoint to get full exercise data

**Example UI Flow:**
```typescript
// 1. Generate stories from user prompt
const stories = await generateStories(userPrompt);

// 2. Search for exercises based on stories
const exerciseIds = await semanticSearchIds(stories[0]);

// 3. User curates the list in UI (add/remove exercises)

// 4. Create routine with final exercise IDs
const routine = await createRoutine({
  name: "My Custom Routine",
  description: "A personalized workout",
  exercise_ids: finalExerciseIds
});

// 5. Fetch full exercise details for display
const exercises = await getExercisesByIds(routine.exercise_ids);
```

**Benefits:**
- **User Control** - Users have full control over exercise selection
- **Simple Data Structure** - Clean, minimal routine storage
- **Consistent API Pattern** - Same exercise fetching as existing endpoints
- **Better Performance** - No complex LLM selection logic

---

## 🎥 URL PROCESSING

### Process Video from URL
**Extract exercises from fitness video**

```http
POST /api/v1/process
```

**Request Body:**
```json
{
  "url": "https://www.instagram.com/p/CxYz123ABC/",
  "background": false
}
```

**Supported Platforms:**
- YouTube: `https://www.youtube.com/watch?v=VIDEO_ID`
- Instagram: `https://www.instagram.com/p/POST_ID/`
- TikTok: `https://www.tiktok.com/@user/video/VIDEO_ID`

**Synchronous Response:**
```json
{
  "success": true,
  "processed_clips": [
    {
      "exercise_name": "Push-up",
      "video_path": "storage/clips/push-up_abc123.mp4",
      "start_time": 10.5,
      "end_time": 25.3
    }
  ],
  "total_clips": 1,
  "processing_time": 45.2,
  "temp_dir": "storage/temp/gilgamesh_download_abc123"
}
```

**Asynchronous Response:**
```json
{
  "success": true,
  "processed_clips": [],
  "total_clips": 0,
  "processing_time": 0.0,
  "temp_dir": null,
  "job_id": "e513927a-2f60-4ead-b3e6-fa9597f50066"
}
```

### Check Job Status
**Poll for background processing status**

```http
GET /api/v1/job-status/{job_id}
```

**Response States:**
```json
// In Progress
{
  "status": "in_progress",
  "result": null
}

// Completed
{
  "status": "done",
  "result": {
    "success": true,
    "processed_clips": [...],
    "total_clips": 1,
    "processing_time": 45.2,
    "temp_dir": "storage/temp/gilgamesh_download_abc123"
  }
}

// Failed
{
  "status": "failed",
  "result": {
    "error": "Some error message"
  }
}
```

---

## 💪 EXERCISE MANAGEMENT (CRUD)

### Create Exercise
**Exercises are created automatically during video processing**

### Read Exercises

#### List All Exercises
```http
GET /api/v1/exercises
```

**Query Parameters:**
- `url` (optional): Filter by source URL

**Response:**
```json
[
  {
    "id": "c8c8d8dd-4223-44e9-88c7-f20695bc1e35",
    "exercise_name": "Push-up",
    "video_path": "storage/clips/push-up_abc123.mp4",
    "start_time": 10.5,
    "end_time": 25.3,
    "how_to": "Start in plank position...",
    "benefits": "Strengthens chest, shoulders, and triceps",
    "counteracts": "Improves upper body pushing strength",
    "fitness_level": 3,
    "rounds_reps": "3 sets of 10-15 reps",
    "intensity": 5,
    "qdrant_id": "77c6856e-e4a2-42a7-b361-bc73808ac812",
    "created_at": "2025-07-26T06:08:17.423912"
  }
]
```

> **Note:** The `qdrant_id` field is always returned as a string (UUID format) in API responses, even if stored as a UUID in the database.

#### Get Specific Exercise
```http
GET /api/v1/exercises/{exercise_id}
```

**Response:** Single exercise object (same structure as above)

#### Get Multiple Exercises by IDs
```http
POST /api/v1/exercises/bulk
```

**Request Body:**
```json
{
  "exercise_ids": ["c8c8d8dd-4223-44e9-88c7-f20695bc1e35", "a2de96ab-3d00-4d6f-9da5-0566a5b47002"]
}
```

**Response:** Array of exercise objects (same structure as individual exercise)

> **UI Integration Pattern:**
> This endpoint is designed to work with the routine generation API. After generating a routine (which returns `exercise_ids`), use this endpoint to fetch the full exercise details for display in the UI.

### Update Exercise
**Exercises are immutable - updates require reprocessing the video**

### Delete Exercises

#### Delete by ID
```http
DELETE /api/v1/exercises/{exercise_id}
```

**Response:**
```json
{
  "message": "Exercise deleted successfully"
}
```

> **Cascade Cleanup:**
> - This endpoint will remove the exercise from PostgreSQL, delete the associated video file from storage, and remove the vector from Qdrant. All three storage layers are cleaned up automatically.

---

## 🗑️ Verified Delete Workflow

When you delete an exercise using `DELETE /api/v1/exercises/{exercise_id}`:
- The exercise row is removed from PostgreSQL
- The associated video file is deleted from `storage/clips/`
- The vector is removed from Qdrant
- The API will return `{"detail": "Exercise not found"}` if you try to fetch a deleted exercise
- The file will not be present in the file system
- The vector will not be returned in semantic search results

This ensures **full cleanup** of all exercise data across the system.

**Response:**
```json
{
  "message": "Exercise deleted successfully"
}
```

---

## 🔧 UTILITY ENDPOINTS

### Health Checks
```http
GET /
GET /health
GET /api/v1/health/database
GET /api/v1/health/vector
```

**Root Health Check Response:**
```json
{
  "message": "Gilgamesh Video Processing API",
  "status": "healthy"
}
```

**Detailed Health Check Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "qdrant": "connected",
    "ai_services": "available"
  }
}
```

**Database Health Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "exercises_count": 150
}
```

**Vector Health Response:**
```json
{
  "status": "healthy",
  "vector_db": "connected",
  "collection_info": {
    "vectors_count": 150,
    "points_count": 150
  }
}
```

### Statistics
```http
GET /api/v1/stats
```

**Response:**
```json
{
  "total_exercises": 150,
  "avg_fitness_level": 5.2,
  "avg_intensity": 6.1,
  "unique_urls": 25
}
```

---

## 📡 API Usage Examples

### Generate Exercise Stories
```bash
curl -X POST http://localhost:8000/api/v1/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "I want to get good at pull ups but i can only do 1 at the moment",
    "story_count": 3
  }'
```

### Search for Exercise IDs
```bash
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search-ids \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need a beginner workout for my back that helps with posture",
    "limit": 5
  }'
```

### Create a Routine
```bash
curl -X POST http://localhost:8000/api/v1/routines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pull-up Progression",
    "description": "A routine to build pull-up strength",
    "exercise_ids": ["c8c8d8dd-4223-44e9-88c7-f20695bc1e35", "a2de96ab-3d00-4d6f-9da5-0566a5b47002"]
  }'
```

### Process Instagram Fitness Video
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CxYz123ABC/",
    "background": true
  }'
```

### Get Exercise Details
```bash
curl -X POST http://localhost:8000/api/v1/exercises/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_ids": ["c8c8d8dd-4223-44e9-88c7-f20695bc1e35", "a2de96ab-3d00-4d6f-9da5-0566a5b47002"]
  }'
```

---

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

# Test story generation
curl -X POST http://localhost:8000/api/v1/stories/generate \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "I need a beginner workout for my back", "story_count": 3}'

# Test semantic search IDs
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search-ids \
  -H "Content-Type: application/json" \
  -d '{"query": "I need a beginner workout for my back", "limit": 5}'
```

## 🌐 UI API Base URL Configuration (LAN, Tailscale, or Public)

Your UI should NOT hardcode the API base URL. Instead, use an environment variable or config file so you can easily switch between:
- Local LAN (e.g., http://192.168.0.47:8000)
- Tailscale (e.g., http://100.x.x.x:8000)
- Public IP or domain

**Example (React):**
```js
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
fetch(`${API_BASE_URL}/api/v1/exercises`)
```

**Example (.env):**
```
REACT_APP_API_BASE_URL=http://100.x.x.x:8000
```

**Result:**
- UI works locally, remotely (Tailscale), or publicly by changing one variable
- Video clips and all API endpoints will work as long as the API is reachable

## 📂 Static File Serving

The API now serves all video clips and files from `/app/storage` at the `/storage` URL path. For example:
```
http://<API_HOST>:8000/storage/clips/filename.mp4
```
No changes are needed to Docker volumes or the UI code. Just ensure the UI uses the correct API base URL.
