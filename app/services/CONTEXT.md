# Services Folder Context

## Overview
The `/services` folder contains external service integrations and specialized processing components. This folder houses video downloading, audio transcription, and other service-oriented functionality that supports the core processing pipeline.

## File Structure and Responsibilities

### 📁 `downloaders.py` - Video Download Service
**Purpose:** Download videos and metadata from various social media platforms

**Key Functions:**
- `download_media_and_metadata(url)` - Main download function
- Platform-specific download handlers
- Metadata extraction (description, tags, carousel info)
- Temporary file management

**Supported Platforms:**
- **YouTube** - Video downloads with metadata
- **Instagram** - Posts, reels, and carousel support
- **TikTok** - Video downloads with metadata

**Key Features:**
- **Carousel Detection** - Handles Instagram multi-video posts
- **Metadata Extraction** - Description, tags, and platform-specific data
- **Temporary Storage** - Organized temp directory structure
- **Error Handling** - Graceful failure with detailed logging

**Dependencies:**
- `yt-dlp` - Video downloading library
- `asyncio` - Async processing
- `os` - File system operations

**Input:** Video URL. **Output:** Downloaded video files and metadata.

### 📁 `transcription.py` - Audio Transcription Service (Active)
**Purpose:** Convert audio to text using OpenAI Whisper and subtitle parsing

**Key Functions:**
- `transcribe_audio(video_file)` - Main transcription function
- `_find_subtitle_file()` - Locate existing subtitle files
- `_parse_subtitle_file()` - Parse various subtitle formats
- `_transcribe_with_whisper()` - OpenAI Whisper transcription

**Transcription Process:**
1. **Subtitle Check** - Look for existing subtitle files (VTT, SRT, TXT)
2. **Format Parsing** - Parse subtitle files if found
3. **Whisper Fallback** - Use OpenAI Whisper if no subtitles
4. **Quality Validation** - Basic text cleaning and validation

**Supported Formats:**
- **VTT** - WebVTT subtitle files
- **SRT** - SubRip subtitle files
- **TXT** - Text files with timestamps
- **Whisper** - OpenAI Whisper API for audio transcription

**Key Features:**
- **Subtitle Priority** - Uses existing subtitles when available
- **Multiple Formats** - Supports various subtitle formats
- **Error Handling** - Graceful fallback to Whisper
- **Timestamp Parsing** - Accurate time segment extraction

**Dependencies:**
- `openai` - OpenAI Whisper API
- `whisper` - Local Whisper model
- `asyncio` - Async processing

**Input:** Video file path. **Output:** List of transcript segments with timestamps.



### 📁 `__init__.py` - Package Initialization
**Purpose:** Empty package initialization file

## Service Integration Patterns

### 🔄 Download → Transcribe → Process Flow
1. **Download Service** - Fetches video and metadata
2. **Transcription Service** - Converts audio to text
3. **Core Processor** - Uses transcript for AI analysis

### 🎯 Single Responsibility Principle
- **`downloaders.py`** - Video downloading only
- **`transcription.py`** - Audio transcription only

### 🔄 Error Handling Strategy
- **Graceful Degradation** - Fallback mechanisms for service failures
- **Detailed Logging** - Comprehensive error reporting
- **Resource Cleanup** - Automatic temporary file cleanup

## Performance Optimizations

### ⚡ Async Processing
- **Concurrent Downloads** - Multiple video processing
- **Non-blocking Operations** - Async service calls
- **Resource Management** - Efficient memory and file handling

### 🔄 Caching Strategy
- **Subtitle Caching** - Reuse existing subtitle files
- **Metadata Caching** - Cache platform metadata
- **Temporary File Management** - Organized temp directory structure

## Integration Points

### 🔗 External Services
- **yt-dlp** - Video downloading library
- **OpenAI Whisper** - Audio transcription API
- **FFmpeg** - Video/audio processing (enhanced service)
- **Platform APIs** - YouTube, Instagram, TikTok

### 📱 Service Integration
- **Core Processor** - Consumes download and transcription results
- **API Layer** - Provides service results to endpoints
- **Database Layer** - Stores transcription metadata

## Security Considerations

### 🔒 URL Validation
- **Platform Validation** - Supported platform checking
- **Content Validation** - Safe video content processing
- **Error Handling** - Secure error message handling

### 🛡️ File System Security
- **Temporary File Isolation** - Secure temp directory usage
- **File Permission Management** - Proper file access controls
- **Cleanup Procedures** - Automatic temporary file removal

## Testing Strategy

### 🧪 Unit Testing
- **Download Service** - Test platform-specific downloads
- **Transcription Service** - Test subtitle parsing and Whisper
- **Error Handling** - Test service failure scenarios

### 🔍 Integration Testing
- **End-to-End Processing** - Test complete download → transcribe → process flow
- **Platform Integration** - Test with real platform URLs
- **Error Recovery** - Test service failure recovery

## Future Considerations

### 🚀 Scalability
- **Batch Processing** - Process multiple videos simultaneously
- **Service Caching** - Cache frequently accessed content
- **Queue System** - Implement proper service queuing

### 🔧 Technical Debt
- **Enhanced Transcription** - Decide whether to integrate or remove
- **Error Handling** - Enhance error recovery mechanisms
- **Monitoring** - Add comprehensive service metrics

### 🔒 Security Enhancements
- **Content Validation** - Enhanced content safety checks
- **Rate Limiting** - Implement service rate limiting
- **Audit Logging** - Comprehensive service operation logging

## Key Insights

### 🎯 Service Architecture
- **Modular Design** - Each service has a single responsibility
- **Async Processing** - Non-blocking service operations
- **Error Isolation** - Service failures don't cascade

### 🔄 Data Flow
1. **URL Input** → Download Service → Video Files + Metadata
2. **Video Files** → Transcription Service → Transcript Segments
3. **Transcript + Video** → Core Processor → Exercise Detection

### 📊 Quality Management
- **Subtitle Priority** - Uses existing subtitles when available
- **Quality Validation** - Basic validation in active service
- **Enhanced Features** - Available in unused enhanced service

## Current Usage Status

### ✅ **Active Services:**
- **`downloaders.py`** - Used by core processor for video downloading
- **`transcription.py`** - Used by core processor for audio transcription

### 🧹 **Clean Architecture:**
- All services in the folder are actively used
- No unused or legacy components
- Simple, focused service structure 