# 🎯 JSON-Based Workout Routine System - Refactor Context

## **Current System Analysis**

### **What We Have Now**
- **Video Processing Pipeline**: Extracts exercise clips from fitness videos
- **PostgreSQL Database**: Stores exercise metadata (name, timing, instructions, fitness_level, intensity)
- **Qdrant Vector Store**: Semantic search with OpenAI embeddings
- **Video Compilation System**: Creates MP4 workout videos using FFmpeg
- **Comprehensive Deletion**: Cascade cleanup across database, vector store, and files

### **Current Workflow**
1. User provides natural language requirements
2. AI generates "requirement stories" (4-6 descriptive paragraphs)
3. Vector search finds relevant clips for each story
4. FFmpeg compiles clips into MP4 video
5. Stores video file in `/app/storage/compiled_workouts/`

### **Current Limitations**
- **Video Files**: Large storage, difficult to modify, not frontend-friendly
- **Simple Selection**: Basic vector similarity, no uniqueness validation
- **No Variety Control**: Can include similar exercises
- **Fixed Output**: Once compiled, can't easily modify
- **Frontend Integration**: Difficult to create interactive UI

---

## **What We're Changing**

### **New Approach: JSON-Based Routines**
- **Replace video compilation** with JSON routine generation
- **Second LLM** for intelligent clip selection and uniqueness validation
- **JSON objects** with complete metadata for frontend consumption
- **Card-based UI** with swipe interactions (separate frontend project)

### **Key Benefits**
1. **Frontend-Ready**: JSON structure designed for card-based UI
2. **Intelligent Selection**: Second LLM ensures variety and progression
3. **Complete Metadata**: All deletion info included for cleanup
4. **Flexible**: Easy to modify routines without regenerating videos
5. **Scalable**: JSON storage is much more efficient than video files
6. **User-Friendly**: Swipe interface for intuitive interaction

---

## **New System Architecture**

### **Database Changes**
- **New Table**: `workout_routines` for JSON storage
- **Enhanced Schema**: Complete metadata including deletion info
- **JSONB Storage**: Efficient JSON storage with indexing

### **API Changes**
- **New Endpoints**: Replace compilation endpoints with routine endpoints
- **JSON Responses**: Structured data for frontend consumption
- **Deletion Integration**: Complete cascade cleanup system

### **Core Logic Changes**
- **New Compiler**: `RoutineCompiler` replaces `WorkoutCompiler`
- **Second LLM**: Intelligent exercise selection and validation
- **Variety Control**: Ensures unique, diverse exercise selection
- **Progression Logic**: Creates logical workout flow

### **Frontend Integration**
- **Card UI**: Swipe left/right interface
- **Exercise Cards**: Complete metadata for each exercise
- **Deletion Support**: Built-in cleanup functionality
- **Interactive Experience**: Real-time routine modification

---

## **Implementation Strategy**

### **Phase 1: Database & Core Structure**
- Create new database table and operations
- Implement core routine compiler structure
- Set up basic JSON generation

### **Phase 2: API Endpoints**
- Create new routine endpoints
- Implement request/response models
- Replace compilation endpoints

### **Phase 3: Intelligent Selection**
- Implement second LLM for exercise selection
- Add variety and progression validation
- Create comprehensive scoring system

### **Phase 4: Testing & Validation**
- Test routine generation with various inputs
- Validate JSON structure for frontend compatibility
- Performance testing and optimization

---

## **Technical Requirements**

### **Database Schema**
```sql
CREATE TABLE workout_routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_requirements TEXT NOT NULL,
    target_duration INTEGER NOT NULL,
    intensity_level VARCHAR(20) NOT NULL,
    format VARCHAR(20) DEFAULT 'vertical',
    routine_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **JSON Structure**
```json
{
  "routine_id": "uuid",
  "user_requirements": "beginner workout for tight hips",
  "target_duration": 300,
  "intensity_level": "beginner",
  "exercises": [
    {
      "exercise_id": "uuid",
      "exercise_name": "Hip Flexor Stretch",
      "video_path": "/app/storage/clips/...",
      "deletion_metadata": {
        "exercise_id": "uuid",
        "qdrant_id": "uuid",
        "video_path": "/app/storage/clips/...",
        "cascade_cleanup": true
      }
    }
  ]
}
```

### **API Endpoints**
- `POST /api/v1/routine/generate` - Generate JSON routine
- `GET /api/v1/routine/{id}` - Get routine by ID
- `GET /api/v1/routines` - List all routines
- `DELETE /api/v1/routine/{id}` - Delete routine
- `POST /api/v1/routine/{id}/exercise/{exercise_id}/remove` - Remove exercise

---

## **Success Criteria**

### **Functional Requirements**
- ✅ Generate JSON routines from natural language input
- ✅ Intelligent exercise selection with variety control
- ✅ Complete metadata including deletion info
- ✅ Frontend-ready JSON structure
- ✅ Cascade deletion system integration

### **Performance Requirements**
- ✅ Fast routine generation (< 30 seconds)
- ✅ Efficient JSON storage and retrieval
- ✅ Scalable to large clip databases
- ✅ Responsive API endpoints

### **Quality Requirements**
- ✅ Unique exercise selection
- ✅ Logical progression flow
- ✅ Appropriate fitness level matching
- ✅ Complete error handling and validation

---

## **Migration Strategy**

### **Backward Compatibility**
- Keep existing video compilation endpoints (deprecated)
- Maintain existing database tables
- Gradual migration to new system

### **Data Migration**
- No data migration required (new system)
- Existing clips remain available
- New routines use existing clip database

### **API Migration**
- Add new endpoints alongside existing ones
- Deprecate old compilation endpoints
- Update documentation and examples

---

## **Testing Strategy**

### **Unit Tests**
- Database operations
- Routine compiler logic
- JSON structure validation
- Deletion cascade functionality

### **Integration Tests**
- End-to-end routine generation
- API endpoint functionality
- Vector search integration
- LLM interaction testing

### **Performance Tests**
- Large clip database handling
- Concurrent routine generation
- JSON storage efficiency
- API response times

---

## **Documentation Requirements**

### **API Documentation**
- Complete endpoint documentation
- Request/response examples
- Error handling guide
- Migration guide

### **Developer Documentation**
- Architecture overview
- Database schema documentation
- LLM prompt engineering guide
- Frontend integration guide

### **User Documentation**
- Routine generation guide
- JSON structure reference
- Deletion system guide
- Frontend integration examples 