# Core Folder Context

## Overview
The `/core` folder contains the central processing pipeline and AI-driven components of the Fitness Builder service. This folder houses the main video processing engine, exercise story generation, and intelligent exercise selection systems that form the backbone of the application.

## File Structure and Responsibilities

### 📁 `processor.py` - Main Video Processing Pipeline
**Purpose:** Core video processing pipeline for exercise clip extraction from fitness videos

**Key Functions:**
- `process_video(url, job_id)` - Main entry point for video processing
- `_detect_exercises()` - AI-powered exercise detection using Gemini LLM
- `_generate_clips()` - FFmpeg-based video clip generation
- `_store_exercises()` - Database and vector store storage
- `_cleanup_temp_files()` - Temporary file cleanup

**Processing Pipeline:**
1. **Download** - Video and metadata extraction via `services/downloaders.py`
2. **Transcribe** - Audio transcription via `services/transcription.py`
3. **Extract Frames** - Keyframe extraction via `utils/enhanced_keyframe_extraction.py`
4. **AI Analysis** - Exercise detection using Gemini LLM with all frames + transcript
5. **Generate Clips** - FFmpeg clip creation from detected exercise segments
6. **Store Data** - Save to PostgreSQL (metadata) and Qdrant (vectors)
7. **Cleanup** - Remove temporary files

**Key Features:**
- **Carousel Support** - Handles Instagram multi-video posts
- **Background Processing** - Job status updates for async operations
- **Error Handling** - Fallback mechanisms for API failures
- **Multi-format Support** - YouTube, Instagram, TikTok URLs
- **Quality Validation** - Minimum duration and time validation

**Dependencies:**
- `app.services.downloaders` - Video downloading
- `app.services.transcription` - Audio transcription
- `app.database.operations` - Database storage
- `app.database.vectorization` - Vector storage
- `app.utils.enhanced_keyframe_extraction` - Frame extraction
- `app.database.job_status` - Background job management

**Input:** Video URL. **Output:** Processed exercise clips, metadata, and database records.

### 📁 `exercise_story_generator.py` - Exercise Requirement Story Generation
**Purpose:** Generate exercise requirement stories from user prompts using Gemini LLM

**Key Functions:**
- `generate_exercise_stories(user_prompt, story_count)` - Main story generation function

**Story Generation Process:**
1. **Prompt Engineering** - Structured fitness coach prompts with:
   - Pain points analysis (tight hips, weak shoulders, etc.)
   - Counteraction identification (sitting all day, poor posture, etc.)
   - Fitness goals (handstand, muscle up, splits, etc.)
   - Constraints (time, equipment, environment)
   - Intensity needs and progression paths

2. **LLM Processing** - Uses `gemini-2.5-flash` model for:
   - Empathetic, practical, solution-focused responses
   - Descriptive paragraph generation (not just exercise names)
   - Multiple story variations based on user requirements

3. **Response Parsing** - Handles multiple response formats:
   - JSON array parsing
   - Numbered/bulleted list parsing
   - Quote removal and formatting cleanup

**Fallback Strategy:**
- Returns predefined exercise stories if API fails
- Ensures service reliability even with LLM issues

**Input:** User prompt (string). **Output:** List of exercise requirement stories (strings).



### 📁 `ai_editor_pipeline.py` - AI Editor Pipeline (Empty)
**Purpose:** Placeholder file for future AI editing functionality

**Current Status:** Empty file (1 line)
**Future Use:** May contain AI-powered video editing capabilities

### 📁 `__init__.py` - Package Initialization
**Purpose:** Empty package initialization file

## Core Architecture Patterns

### 🔄 Multi-LLM Pipeline Architecture
1. **First LLM** (`exercise_story_generator.py`) - Generates exercise requirement stories
2. **Second LLM** (`processor.py`) - Detects exercises in video content

### 🎥 Video Processing Pipeline
1. **Download Phase** - Video and metadata extraction
2. **Analysis Phase** - Transcription and frame extraction
3. **AI Detection Phase** - LLM-based exercise detection
4. **Generation Phase** - Clip creation and storage
5. **Cleanup Phase** - Temporary file removal

### 🧠 AI-Driven Decision Making
- **Story Generation** - Converts user prompts to exercise requirements
- **Content Analysis** - Natural language understanding of exercise content
- **Intelligent Selection** - LLM-based routine curation
- **Quality Validation** - AI-powered exercise detection and validation

## Error Handling Strategy

### 🔄 Fallback Mechanisms
- **API Failures** - Predefined responses when LLM APIs fail
- **Processing Errors** - Graceful degradation with error logging
- **Validation Failures** - Simple selection when complex validation fails

### 📝 Logging Strategy
- **Structured Logging** - Consistent error message format
- **Progress Tracking** - Step-by-step processing logs
- **Debug Information** - Detailed context for troubleshooting

## Performance Optimizations

### ⚡ Lazy Initialization
- **LLM Clients** - Initialized only when needed
- **API Keys** - Loaded on-demand to avoid startup errors
- **Model Caching** - Reuse model instances when possible

### 🔄 Background Processing
- **Job Status Updates** - Real-time progress tracking
- **Async Operations** - Non-blocking video processing
- **Resource Management** - Automatic cleanup of temporary files

## Integration Points

### 🔗 External Services
- **Gemini API** - Primary LLM for story generation and exercise selection
- **OpenAI API** - Backup LLM for exercise detection
- **FFmpeg** - Video processing and clip generation
- **PostgreSQL** - Exercise metadata storage
- **Qdrant** - Vector database for semantic search

### 📱 Service Integration
- **API Layer** - Endpoints consume core processing results
- **Database Layer** - Core components store and retrieve data
- **Utility Layer** - Core components use utility functions for specialized tasks

## Security Considerations

### 🔒 API Key Management
- **Environment Variables** - Secure API key storage
- **Backup Keys** - Automatic fallback between API keys
- **Error Handling** - Graceful failure when keys are missing

### 🛡️ Input Validation
- **URL Validation** - Secure video URL processing
- **Content Validation** - Exercise data validation before storage
- **Duration Limits** - Minimum/maximum clip duration validation

## Testing Strategy

### 🧪 Unit Testing
- **Story Generation** - Test story generation with various prompts
- **Exercise Selection** - Test selection logic with mock data
- **Video Processing** - Test processing pipeline with sample videos

### 🔍 Integration Testing
- **LLM Integration** - Test API interactions and fallbacks
- **Database Integration** - Test storage and retrieval operations
- **Video Processing** - Test end-to-end video processing pipeline

## Future Considerations

### 🚀 Scalability
- **Batch Processing** - Process multiple videos simultaneously
- **Caching Layer** - Cache frequently accessed LLM responses
- **Queue System** - Implement proper job queuing for background processing

### 🔧 Technical Debt
- **Empty Files** - Clean up or implement `ai_editor_pipeline.py`
- **Error Handling** - Enhance error recovery mechanisms
- **Monitoring** - Add comprehensive metrics and monitoring

### 🔒 Security Enhancements
- **Rate Limiting** - Implement API rate limiting
- **Input Sanitization** - Enhanced input validation
- **Audit Logging** - Comprehensive operation logging

## Key Insights

### 🎯 Single Responsibility Principle
- **`processor.py`** - Video processing pipeline only
- **`exercise_story_generator.py`** - Story generation only

### 🔄 Separation of Concerns
- **AI Components** - Separate LLM interactions from business logic
- **Processing Pipeline** - Clear separation between download, analysis, generation
- **Error Handling** - Isolated error handling per component

### 📊 Data Flow
1. **User Input** → Story Generation → Exercise Selection → Video Processing
2. **Video URL** → Download → Analysis → AI Detection → Clip Generation → Storage
3. **Exercise Data** → Database Storage → Vector Storage → API Access 