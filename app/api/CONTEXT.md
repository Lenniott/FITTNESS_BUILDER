# API Folder Context

## Overview
The `/api` folder contains the FastAPI application that serves as the REST API backend for the Fitness Builder service. This API provides endpoints for video processing, exercise management, routine creation, and semantic search functionality.

## File Structure and Responsibilities

### 📁 `main.py` - FastAPI Application Entry Point
**Purpose:** Main FastAPI application configuration and startup

**Key Functions:**
- Creates and configures the FastAPI app instance
- Sets up static file serving for video clips (`/storage` endpoint)
- Configures middleware (CORS, trusted hosts)
- Includes API routers with `/api/v1` prefix
- Provides basic health check endpoints

**Endpoints:**
- `GET /` - Basic health check
- `GET /health` - Detailed health check with service status
- `GET /storage/*` - Static file serving for video clips

**Dependencies:**
- `app.api.middleware` - Middleware configuration
- `app.api.endpoints` - Main API router

### 📁 `endpoints.py` - Core API Endpoints
**Purpose:** Contains all the main API endpoints for the service

**Key Endpoint Categories:**

#### 🎥 Video Processing
- `POST /api/v1/process` - Process video URL to extract exercise clips
  - Supports background processing with job polling
  - Handles YouTube, Instagram, TikTok URLs
  - Returns processed clips or job_id for background tasks

#### 🏋️ Routine Management (CRUD)
- `POST /api/v1/routines` - Create new routine with exercise IDs
- `GET /api/v1/routines` - List all routines with pagination
- `GET /api/v1/routines/{routine_id}` - Get specific routine
- `DELETE /api/v1/routines/{routine_id}` - Delete routine

#### 💪 Exercise Management (CRUD)
- `GET /api/v1/exercises` - List all exercises (optional URL filter)
- `GET /api/v1/exercises/{exercise_id}` - Get specific exercise
- `POST /api/v1/exercises/bulk` - Get multiple exercises by IDs
- `DELETE /api/v1/exercises/{exercise_id}` - Delete exercise with cascade cleanup

#### 🔍 Semantic Search & Story Generation
- `POST /api/v1/stories/generate` - Generate exercise requirement stories from user prompt
- `POST /api/v1/exercises/semantic-search-ids` - Search exercises and return only IDs

#### 📊 System Health & Statistics
- `GET /api/v1/health/database` - Database health check
- `GET /api/v1/health/vector` - Vector database health check
- `GET /api/v1/stats` - Processing statistics

#### 🔄 Background Job Management
- `GET /api/v1/job-status/{job_id}` - Poll background job status

**Key Pydantic Models:**
- `ProcessRequest/Response` - Video processing
- `CreateRoutineRequest/Response` - Routine creation
- `ExerciseResponse` - Exercise data structure
- `StoryGenerationRequest/Response` - Story generation
- `SemanticSearchRequest/Response` - Semantic search

**Dependencies:**
- `app.core.processor` - Video processing pipeline
- `app.database.operations` - Database operations
- `app.database.vectorization` - Vector search
- `app.database.job_status` - Background job management
- `app.core.exercise_story_generator` - Story generation
- `app.core.exercise_selector` - Exercise selection

### 📁 `routine_models.py` - Pydantic Models for Routines
**Purpose:** Defines data models for routine-related API operations

**Key Models:**
- `RoutineRequest` - User requirements for routine generation
- `ExerciseData` - Exercise data within routines
- `RoutineMetadata` - Routine metadata (duration, variety, etc.)
- `RoutineData` - Complete routine structure
- `RoutineResponse` - API response for routine operations
- `RoutineListResponse` - Paginated routine listing
- `DeleteResponse` - Deletion operation responses
- `RemoveExerciseRequest` - Exercise removal from routines

**Note:** This file contains models for the old complex routine system that was replaced with the simpler user-curated routine system. The models are kept for potential future use but the current system uses simpler models defined in `endpoints.py`.

### 📁 `middleware.py` - FastAPI Middleware Configuration
**Purpose:** Configures middleware for the FastAPI application

**Key Functions:**
- `setup_middleware(app)` - Configures all middleware components

**Middleware Components:**
- **CORS Middleware** - Enables cross-origin requests (configured for all origins)
- **Trusted Host Middleware** - Host validation (configured for all hosts)

**Note:** Current configuration is permissive for development. Should be tightened for production.

### 📁 `__init__.py` - Package Initialization
**Purpose:** Empty package initialization file

## API Architecture Patterns

### 🔄 Background Processing Pattern
1. **Synchronous Processing:** Direct video processing with immediate response
2. **Asynchronous Processing:** Background job creation with polling endpoint
3. **Job Status Polling:** `GET /api/v1/job-status/{job_id}` for progress tracking

### 🏗️ User-Curated Routine Workflow
1. **Story Generation:** `POST /api/v1/stories/generate` - Create exercise requirements
2. **Semantic Search:** `POST /api/v1/exercises/semantic-search-ids` - Find relevant exercises
3. **User Curation:** UI allows adding/removing exercises
4. **Routine Creation:** `POST /api/v1/routines` - Save final curated list
5. **Exercise Details:** `POST /api/v1/exercises/bulk` - Fetch full exercise data

### 🗄️ Data Storage Architecture
Each exercise consists of three interconnected components:
1. **PostgreSQL Row** - Metadata stored in `exercises` table
2. **Video File** - Stored in `storage/clips/` directory
3. **Qdrant Vector** - AI embedding for semantic search

All components are linked via `qdrant_id` and `database_id` fields.

### 🧹 Cascade Cleanup Pattern
When deleting exercises:
- PostgreSQL row removal
- Video file deletion from storage
- Qdrant vector removal
- Complete data cleanup across all storage layers

## Error Handling Strategy

### 🔍 Error Message Escaping
- `escape_error_message()` function prevents format specifier errors
- All error messages are properly escaped before logging/returning

### 🚨 HTTP Status Codes
- `404` - Resource not found (exercise, routine, job)
- `500` - Internal server errors
- `503` - Service unavailable (database/vector connection issues)

### 📝 Logging Strategy
- Structured logging with consistent error message format
- Detailed error context for debugging
- Warning logs for missing resources

## Security Considerations

### 🔒 CORS Configuration
- Currently configured for all origins (`*`)
- Should be restricted for production deployment

### 🛡️ Trusted Hosts
- Currently configured for all hosts (`*`)
- Should be restricted for production deployment

### 🗑️ Input Validation
- Pydantic models provide automatic request validation
- URL validation for video processing
- UUID validation for database operations

## Performance Optimizations

### ⚡ Static File Serving
- Video clips served directly from `/storage` endpoint
- No additional processing overhead for file access

### 🔄 Background Processing
- Long-running video processing moved to background tasks
- Non-blocking API responses with job polling

### 📊 Bulk Operations
- `POST /api/v1/exercises/bulk` for efficient multiple exercise retrieval
- Reduces database round trips for routine display

## Integration Points

### 🔗 External Services
- **PostgreSQL** - Exercise metadata storage
- **Qdrant** - Vector database for semantic search
- **OpenAI/Gemini** - AI analysis and transcription
- **FFmpeg** - Video processing and clip generation

### 📱 Frontend Integration
- RESTful API design for easy frontend integration
- Consistent JSON response format
- CORS enabled for web application access
- Static file serving for video clip access





## Future Considerations

### 🔧 Technical Debt
- ✅ Remove unused import of `compilation_endpoints` - **COMPLETED**
- Tighten security middleware for production
- Add comprehensive API documentation with OpenAPI/Swagger

### 🚀 Scalability
- Consider caching layer for frequently accessed data
- Implement rate limiting for API endpoints
- Add monitoring and metrics collection

### 🔒 Security Enhancements
- Implement proper authentication/authorization
- Add request rate limiting
- Configure proper CORS origins for production
- Add input sanitization and validation

## Testing Strategy

### 🧪 API Testing
- Health check endpoints for service monitoring
- Error handling validation
- Request/response format validation
- Background job processing validation

### 🔍 Integration Testing
- Database connection testing
- Vector search functionality testing
- Video processing pipeline testing
- File storage and retrieval testing 