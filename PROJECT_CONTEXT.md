# Fitness Builder Project Context

## Overview
Fitness Builder is an AI-powered fitness video processing pipeline that extracts exercises from videos, creates clips, and enables semantic search. The system uses a dual-storage architecture with PostgreSQL for metadata and Qdrant for vector embeddings, supporting user-curated routine creation.

## Project Architecture

### 🏗️ **Core Components**
- **FastAPI Backend** - REST API for video processing and exercise management
- **PostgreSQL Database** - Structured metadata storage for exercises and routines
- **Qdrant Vector Database** - Semantic search and similarity matching
- **AI Processing Pipeline** - Multi-LLM system for exercise detection and story generation
- **Video Processing** - FFmpeg-based clip generation and frame extraction
- **Background Job System** - Async processing with status tracking

### 🔄 **Data Flow Architecture**
1. **Video Input** → Download → Transcribe → Extract Frames → AI Analysis → Generate Clips → Store
2. **User Prompt** → Story Generation → Semantic Search → User Curation → Routine Creation
3. **Exercise Data** → PostgreSQL (metadata) + Qdrant (vectors) + File System (clips)

## Folder Structure and Context Files

### 📁 `/app/api` - REST API Layer
**Context File:** `app/api/CONTEXT.md`

**Purpose:** FastAPI application serving as the REST API backend for video processing, exercise management, routine creation, and semantic search.

**Key Files:**
- **`main.py`** - FastAPI application entry point with middleware and static file serving
- **`endpoints.py`** - Core API endpoints for all service functionality
- **`routine_models.py`** - Pydantic models for routine operations (legacy system)
- **`middleware.py`** - CORS and trusted host middleware configuration

**API Endpoints:**
- **Video Processing:** `POST /api/v1/process` - Extract exercises from video URLs
- **Routine Management:** CRUD operations for user-curated routines
- **Exercise Management:** CRUD operations with cascade cleanup
- **Semantic Search:** Story generation and exercise search by IDs
- **System Health:** Database and vector health checks
- **Background Jobs:** Job status polling for async processing

**Integration Points:**
- **Core Processor** - Video processing pipeline
- **Database Layer** - PostgreSQL and Qdrant operations
- **Job System** - Background processing tracking
- **Story Generation** - AI-powered exercise requirement stories

### 📁 `/app/core` - Processing Pipeline
**Context File:** `app/core/CONTEXT.md`

**Purpose:** Central processing pipeline and AI-driven components for video processing and exercise analysis.

**Key Files:**
- **`processor.py`** - Main video processing pipeline (39KB, 808 lines)
- **`exercise_story_generator.py`** - Exercise requirement story generation using Gemini LLM
- **`ai_editor_pipeline.py`** - Empty placeholder for future AI editing functionality

**Processing Pipeline:**
1. **Download** - Video and metadata extraction
2. **Transcribe** - Audio transcription with subtitle parsing
3. **Extract Frames** - Keyframe extraction for AI analysis
4. **AI Analysis** - Exercise detection using Gemini LLM
5. **Generate Clips** - FFmpeg clip creation
6. **Store Data** - PostgreSQL metadata + Qdrant vectors
7. **Cleanup** - Temporary file removal

**AI Components:**
- **Story Generation** - Converts user prompts to exercise requirements
- **Exercise Detection** - LLM-based video content analysis
- **Multi-LLM Architecture** - Different models for different tasks

**Integration Points:**
- **Services Layer** - Video downloading and transcription
- **Database Layer** - Data storage and retrieval
- **Utils Layer** - URL processing and frame extraction
- **API Layer** - Endpoint consumption

### 📁 `/app/database` - Data Persistence Layer
**Context File:** `app/database/CONTEXT.md`

**Purpose:** All database-related operations including PostgreSQL metadata storage, Qdrant vector operations, and job status management.

**Key Files:**
- **`operations.py`** - PostgreSQL database operations (22KB, 686 lines)
- **`vectorization.py`** - Qdrant vector database operations (20KB, 590 lines)
- **`job_status.py`** - Background job status management (1.5KB, 46 lines)

**Database Schema:**
- **`exercises` table** - Exercise metadata with comprehensive fields
- **`workout_routines` table** - User-curated routine storage
- **`exercise_job_status` table** - Background job tracking

**Dual Storage Architecture:**
- **PostgreSQL** - Structured metadata storage
- **Qdrant** - Vector embeddings for semantic search
- **File System** - Video clip storage
- **Linked IDs** - Consistent data across storage layers

**Key Features:**
- **Connection Pooling** - Efficient database connection management
- **Cascade Cleanup** - Complete data removal across all layers
- **Semantic Search** - Natural language query matching
- **Diverse Selection** - Intelligent exercise variety
- **Job Tracking** - Real-time background processing status

**Integration Points:**
- **Core Processor** - Stores exercise data and embeddings
- **API Layer** - Retrieves and manages data
- **Job System** - Tracks background processing
- **Vector Search** - Provides semantic search capabilities

### 📁 `/app/services` - External Service Integration
**Context File:** `app/services/CONTEXT.md`

**Purpose:** External service integrations for video downloading, audio transcription, and other specialized processing.

**Key Files:**
- **`downloaders.py`** - Video download service (6.8KB, 205 lines)
- **`transcription.py`** - Audio transcription service (11KB, 308 lines)

**Supported Platforms:**
- **YouTube** - Video downloads with metadata
- **Instagram** - Posts, reels, and carousel support
- **TikTok** - Video downloads with metadata

**Transcription Process:**
1. **Subtitle Check** - Look for existing subtitle files (VTT, SRT, TXT)
2. **Format Parsing** - Parse subtitle files if found
3. **Whisper Fallback** - Use OpenAI Whisper if no subtitles
4. **Quality Validation** - Basic text cleaning and validation

**Key Features:**
- **Carousel Detection** - Handles Instagram multi-video posts
- **Metadata Extraction** - Platform-specific data extraction
- **Subtitle Priority** - Uses existing subtitles when available
- **Error Handling** - Graceful fallback mechanisms

**Integration Points:**
- **Core Processor** - Consumes download and transcription results
- **API Layer** - Provides service results to endpoints
- **Database Layer** - Stores transcription metadata

### 📁 `/app/utils` - Utility Functions
**Context File:** `app/utils/CONTEXT.md`

**Purpose:** Specialized utility functions and helper components that support the core processing pipeline.

**Key Files:**
- **`url_processor.py`** - URL processing utilities (2.9KB, 108 lines)
- **`enhanced_keyframe_extraction.py`** - Enhanced keyframe extraction (24KB, 512 lines)

**URL Processing Features:**
- **Carousel Detection** - Identifies Instagram multi-video posts
- **URL Normalization** - Removes query parameters for consistent processing
- **Platform Recognition** - Distinguishes between different video platforms
- **Index Extraction** - Extracts carousel item indices

**Frame Extraction Process:**
1. **Cut Detection** - Identify scene changes in video
2. **Frame Extraction** - Extract frames at 8 FPS for each cut segment
3. **Change Analysis** - Find frames with biggest visual changes
4. **Rate Constraints** - Apply 1-8 FPS constraints
5. **Cleanup** - Remove duplicate and low-quality frames

**Key Features:**
- **Cut Detection** - Identifies scene changes for better frame selection
- **Adaptive Frame Rate** - 1-8 FPS based on video content
- **Change Analysis** - Keeps frames with significant visual differences
- **Optimized Processing** - Fast frame difference calculations

**Integration Points:**
- **Core Processor** - Consumes URL processing and frame extraction results
- **Download Service** - Uses URL processing for carousel detection
- **AI Analysis** - Uses extracted keyframes for exercise detection

## System Integration Patterns

### 🔄 **Video Processing Workflow**
1. **URL Input** → URL Processing → Download Service → Video Files
2. **Video Files** → Transcription Service → Transcript Segments
3. **Video + Transcript** → Frame Extraction → Keyframes
4. **All Data** → AI Analysis → Exercise Detection
5. **Detected Exercises** → Clip Generation → Storage (PostgreSQL + Qdrant + Files)

### 🏋️ **Routine Creation Workflow**
1. **User Prompt** → Story Generation → Exercise Requirements
2. **Requirements** → Semantic Search → Exercise IDs
3. **Exercise IDs** → User Curation → Final Selection
4. **Final Selection** → Routine Creation → Database Storage
5. **Routine Data** → API Response → UI Display

### 🗄️ **Data Storage Architecture**
Each exercise consists of three interconnected components:
1. **PostgreSQL Row** - Metadata stored in `exercises` table
2. **Video File** - Stored in `storage/clips/` directory
3. **Qdrant Vector** - AI embedding for semantic search

All components are linked via `qdrant_id` and `database_id` fields.

### 🧹 **Cascade Cleanup Pattern**
When deleting exercises:
- PostgreSQL row removal
- Video file deletion from storage
- Qdrant vector removal
- Complete data cleanup across all storage layers

## Technology Stack

### 🏗️ **Backend Framework**
- **FastAPI** - Modern, fast web framework for building APIs
- **Pydantic** - Data validation and settings management
- **Uvicorn** - ASGI server for FastAPI

### 🗄️ **Databases**
- **PostgreSQL** - Primary metadata storage with asyncpg driver
- **Qdrant** - Vector database for semantic search and similarity matching

### 🤖 **AI Services**
- **OpenAI** - Text embedding generation and Whisper transcription
- **Gemini** - Primary LLM for story generation and exercise detection
- **Multi-LLM Architecture** - Different models for different tasks

### 🎥 **Video Processing**
- **FFmpeg** - Video processing and clip generation
- **OpenCV** - Frame extraction and analysis
- **yt-dlp** - Video downloading from various platforms

### 🔄 **Async Processing**
- **asyncio** - Asynchronous programming for non-blocking operations
- **Background Tasks** - FastAPI feature for long-running operations
- **Job Status Tracking** - Real-time progress monitoring

## Security and Performance

### 🔒 **Security Considerations**
- **Environment Variables** - Secure API key and database credential storage
- **CORS Configuration** - Cross-origin resource sharing (currently permissive)
- **Input Validation** - Pydantic models provide automatic validation
- **Error Handling** - Secure error message handling

### ⚡ **Performance Optimizations**
- **Connection Pooling** - Efficient database connection management
- **Async Operations** - Non-blocking I/O operations
- **Background Processing** - Long-running tasks moved to background
- **Static File Serving** - Direct video clip access
- **Indexed Queries** - Optimized database search performance

## Deployment Architecture

### 🐳 **Docker Deployment**
- **Docker Compose** - Multi-service orchestration
- **Portainer UI** - Container management interface
- **Volume Mounts** - Persistent storage for clips and temp files
- **Network Configuration** - External PostgreSQL and Qdrant instances

### 🌐 **Network Configuration**
- **LAN Access** - Local network deployment
- **Tailscale** - Secure remote access
- **Public Access** - Internet-accessible deployment
- **Static File Serving** - Direct video clip access via `/storage` endpoint

## Current Status

### ✅ **Active Components**
All folder context files have been created and document the current state:
- **`/api`** - Complete API layer with all endpoints active
- **`/core`** - Processing pipeline with AI components active
- **`/database`** - Dual storage system with all operations active
- **`/services`** - External service integrations active
- **`/utils`** - Utility functions for URL processing and frame extraction active

### 🧹 **Clean Architecture**
- **No Unused Components** - All files are actively used in the system
- **Well-Documented** - Comprehensive context files for each folder
- **Consistent Patterns** - Standardized error handling and integration
- **Technical Debt Addressed** - Removed unused files and imports

### 📊 **System Health**
- **Dual Storage** - PostgreSQL and Qdrant working together
- **Multi-LLM** - Different AI models for different tasks
- **Background Processing** - Async job system for long-running tasks
- **Error Recovery** - Graceful failure handling throughout

## Future Roadmap

### 🚀 **Scalability Enhancements**
- **Database Sharding** - Horizontal scaling for large datasets
- **Vector Clustering** - Efficient vector search for large collections
- **Caching Layer** - Redis for frequently accessed data
- **Queue System** - Proper job queuing for high throughput

### 🔧 **Technical Improvements**
- **Migration System** - Database schema versioning
- **Backup Strategy** - Automated data backup
- **Monitoring** - Comprehensive metrics and monitoring
- **API Documentation** - OpenAPI/Swagger integration

### 🔒 **Security Enhancements**
- **Authentication/Authorization** - User management system
- **Rate Limiting** - API endpoint protection
- **Data Encryption** - Encrypt sensitive data at rest
- **Audit Logging** - Comprehensive operation logging

## Context File Summary

### 📋 **Available Context Files**
1. **`app/api/CONTEXT.md`** - API layer documentation and endpoint details
2. **`app/core/CONTEXT.md`** - Processing pipeline and AI components
3. **`app/database/CONTEXT.md`** - Database operations and dual storage architecture
4. **`app/services/CONTEXT.md`** - External service integrations
5. **`app/utils/CONTEXT.md`** - Utility functions and helper components
6. **`PROJECT_CONTEXT.md`** - This comprehensive project overview

### 🎯 **Context File Purpose**
Each context file provides:
- **File-by-file breakdown** with purposes and functions
- **Integration patterns** and data flow analysis
- **Performance characteristics** and optimization strategies
- **Security considerations** and error handling
- **Current usage status** and technical debt items
- **Future considerations** and scalability plans

This comprehensive documentation ensures that developers can quickly understand the system architecture, locate specific functionality, and maintain the codebase effectively. 