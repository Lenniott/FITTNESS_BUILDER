# New Routine Architecture Plan

## Overview
Simplify the routine generation system by removing the complex LLM selection step and giving users direct control over exercise curation.

## Current Problem
- Complex 5-step pipeline with multiple LLM calls
- Hard to debug when things go wrong
- Users have no control over exercise selection
- Single point of failure in the selection logic

## Proposed Architecture

### Story Generation Philosophy

The story generation should act as a **fitness coach** analyzing user requirements, not just generating exercise names. Each story should capture:

1. **Pain Points**: What problems they're experiencing (tight hips, weak shoulders, etc.)
2. **Counteractions**: What sedentary habits they're trying to overcome (sitting all day, poor posture, etc.)
3. **Fitness Goals**: What skills they want to achieve (handstand, muscle up, splits, etc.)
4. **Constraints**: Time limitations, equipment availability, environment restrictions
5. **Intensity Needs**: Appropriate difficulty level based on their current fitness
6. **Progression Path**: What they need to work on to achieve their goals

**Example Transformation:**
- **User Input**: "I need like a 5 minute routine i can do at work when i stand up from my desk, i sit alot for work and want to make sure i dont ruin my lower back shoulder, neck and hip posture"
- **Good Story**: "Tight hip mobility training for someone who sits all day and has lower back soreness"
- **Bad Story**: "**Assisted Pull-ups (Band or Machine):** Use a strong resistance band..."

**Story Generation Prompt Structure:**
```
<role>
You are a fitness coach specializing in analyzing user requirements and creating exercise requirement stories for video compilation systems.
</role>

<tone>
Be empathetic, practical, and solution-focused. Understand user pain points and constraints while providing actionable exercise requirements.
</tone>

<context>
User Input: "{user_prompt}"
</context>

<task>
Analyze the user's requirements and create exercise requirement stories that capture:
1. Pain Points: What problems they're experiencing
2. Counteractions: What sedentary habits they're trying to overcome
3. Fitness Goals: What skills they want to achieve
4. Constraints: Time limitations, equipment availability, environment restrictions
5. Intensity Needs: Appropriate difficulty level based on their current fitness
6. Progression Path: What they need to work on to achieve their goals

Create 4-6 requirement stories that are descriptive paragraphs (not exercise names).
</task>

<output_format>
Return an array of requirement stories like:
[
    "Tight hip mobility training for someone who sits all day and has lower back soreness",
    "Shoulder strength and flexibility development for handstand progression",
    "Beginner-friendly strength building for someone who hasn't exercised in months",
    "Chest-to-knee compression work for handstand preparation"
]
</output_format>
```

### Core Endpoints

#### 1. Story Generation
```http
POST /api/v1/stories/generate
```
**Request:**
```json
{
  "user_prompt": "I need like a 5 minute routine i can do at work when i stand up from my desk, i sit alot for work and want to make sure i dont ruin my lower back shoulder, neck and hip posture, as well as just want to keep mobile and flexible without needing to shower. think of it as movement nutrition not exercise routine persay",
  "story_count": 5
}
```
**Response:**
```json
{
  "stories": [
    "Tight hip mobility training for someone who sits all day and has lower back soreness",
    "Shoulder and neck flexibility work to counteract forward head posture from desk work",
    "Gentle core activation exercises to support spine and prevent lower back pain",
    "Quick standing mobility drills that can be done in office clothes without sweating",
    "Postural correction movements to reset alignment after hours of sitting"
  ]
}
```

#### 2. Semantic Search
```http
POST /api/v1/exercises/semantic-search
```
**Request:**
```json
{
  "query": "story text here",
  "limit": 10
}
```
**Response:**
```json
{
  "exercise_ids": ["id1", "id2", "id3"],
  "total_found": 3
}
```

#### 3. Routine Management

**Create Routine:**
```http
POST /api/v1/routines/create
```
**Request:**
```json
{
  "exercise_ids": ["id1", "id2", "id3"],
  "name": "My Pull-up Routine",
  "description": "Optional description"
}
```
**Response:**
```json
{
  "routine_id": "uuid",
  "name": "My Pull-up Routine",
  "exercise_count": 3,
  "created_at": "2025-07-26T..."
}
```

**Get Routine (Update Existing):**
```http
GET /api/v1/routines/{routine_id}
```
**Response:**
```json
{
  "routine_id": "uuid",
  "name": "My Pull-up Routine",
  "exercise_ids": ["id1", "id2", "id3"],
  "created_at": "2025-07-26T...",
  "updated_at": "2025-07-26T..."
}
```

**List Routines (New):**
```http
GET /api/v1/routines
```
**Response:**
```json
[
  {
    "routine_id": "uuid1",
    "name": "My Pull-up Routine",
    "exercise_count": 3,
    "created_at": "2025-07-26T..."
  },
  {
    "routine_id": "uuid2", 
    "name": "Office Mobility Routine",
    "exercise_count": 5,
    "created_at": "2025-07-26T..."
  }
]
```

**Update Routine (New):**
```http
PUT /api/v1/routines/{routine_id}
```
**Request:**
```json
{
  "exercise_ids": ["id1", "id2", "id3", "id4"],
  "name": "Updated Routine Name",
  "description": "Updated description"
}
```

**Delete Routine (New):**
```http
DELETE /api/v1/routines/{routine_id}
```
**Response:**
```json
{
  "success": true,
  "message": "Routine deleted successfully"
}
```

#### 4. Bulk Exercise Fetch (Already exists)
```http
POST /api/v1/exercises/bulk
```
**Request:**
```json
{
  "exercise_ids": ["id1", "id2", "id3"]
}
```
**Response:**
```json
[
  {
    "id": "id1",
    "exercise_name": "Proper Pull-up Technique",
    "how_to": "...",
    "benefits": "...",
    "video_path": "..."
  }
]
```

## UI Flow

### Step 1: Generate Stories
```typescript
const stories = await generateStories(prompt, count: 5);
// Display stories to user like:
// - "Tight hip mobility training for someone who sits all day and has lower back soreness"
// - "Shoulder and neck flexibility work to counteract forward head posture from desk work"
// - "Gentle core activation exercises to support spine and prevent lower back pain"
```

### Step 2: Get Exercise Suggestions
```typescript
const exerciseSuggestions = await Promise.all(
  stories.map(story => semanticSearch(story))
);
// Display exercise lists per story
```

### Step 3: User Curation
```typescript
// User removes/keeps exercises in UI
// User can see exercise details via bulk fetch
const selectedExercises = userCuratedList;
```

### Step 4: Save Routine
```typescript
const routine = await createRoutine({
  exercise_ids: selectedExercises,
  name: "My Custom Routine"
});
```

## Pros

### Technical Benefits
- **Simpler Architecture**: 4 focused endpoints vs 1 complex pipeline
- **Easier Debugging**: Clear separation of concerns
- **Better Performance**: No complex LLM selection logic
- **Reusable Components**: Each endpoint can be used independently
- **Easier Testing**: Simple, focused functions

### User Experience Benefits
- **User Control**: Users curate exactly what they want
- **Transparency**: Users see why each exercise was suggested
- **Educational**: Users learn about exercise selection
- **Flexibility**: Users can mix exercises from different stories
- **Iterative**: Users can refine their routine over time

### Development Benefits
- **Faster Development**: Simpler to implement and maintain
- **Easier Scaling**: Each component can be optimized independently
- **Better Error Handling**: Clear error boundaries
- **API Reusability**: Endpoints can be used by other features

## Cons

### Technical Challenges
- **More API Calls**: Multiple semantic searches instead of one selection
- **UI Complexity**: Need to build curation interface
- **State Management**: UI needs to track user selections

### User Experience Challenges
- **User Responsibility**: Users need to understand exercise selection
- **Potential for Poor Choices**: Users might pick suboptimal combinations
- **Learning Curve**: Users need to learn how to curate effectively

### Business Considerations
- **User Education**: Need to guide users on effective curation
- **Quality Control**: No automated quality filtering
- **Support Burden**: Users might need help with selection

## Complexity Analysis

### Current System
- **Complexity**: High (5-step pipeline)
- **Debugging**: Difficult (multiple failure points)
- **Testing**: Complex (integration testing required)
- **Maintenance**: High (tightly coupled components)

### Proposed System
- **Complexity**: Low (4 simple endpoints)
- **Debugging**: Easy (isolated functions)
- **Testing**: Simple (unit testing sufficient)
- **Maintenance**: Low (loosely coupled components)

## Implementation Plan

### Current State Analysis

#### ✅ Already Implemented:
- **Story Generation Logic** - `generate_exercise_stories()` in `app/core/exercise_story_generator.py`
- **Semantic Search** - `POST /api/v1/exercises/semantic-search` (returns full exercise data)
- **Bulk Exercise Fetch** - `POST /api/v1/exercises/bulk` (returns full exercise data)
- **Get Routine** - `GET /api/v1/routines/{routine_id}` (complex response format)
- **Database Functions** - `get_workout_routine()`, `get_recent_workout_routines()`, `delete_workout_routine()`

#### 🔄 Needs Updates:
- **Story Generator Endpoint** - Extract from current pipeline to standalone endpoint
- **Semantic Search Response** - Modify to return only exercise IDs
- **Get Routine Response** - Simplify to return just exercise_ids
- **Database Schema** - Add `name` and `description` fields to routines table

#### ❌ Missing:
- **Create Routine Endpoint** - `POST /api/v1/routines/create`
- **List Routines Endpoint** - `GET /api/v1/routines`
- **Update Routine Endpoint** - `PUT /api/v1/routines/{routine_id}`
- **Delete Routine Endpoint** - `DELETE /api/v1/routines/{routine_id}`

### Phase 1: Core Endpoints (Week 1)
1. **Extract Story Generator** from current pipeline to standalone endpoint
2. **Modify Semantic Search** to return only IDs instead of full exercise data
3. **Update Get Routine** to return simplified format with exercise_ids
4. **Create Missing Routine CRUD** endpoints (Create, List, Update, Delete)
5. **Add comprehensive tests**

### Phase 2: UI Integration (Week 2)
1. **Story Display Component** - Show generated stories
2. **Exercise List Component** - Display search results per story
3. **Curation Interface** - Add/remove exercises with drag-drop
4. **Routine Saving** - Save final selection

### Phase 3: Enhancement (Week 3)
1. **Story Quality** - Improve story generation prompts
2. **Search Tuning** - Optimize semantic search parameters
3. **User Guidance** - Add hints/tips for effective curation
4. **Performance Optimization** - Cache and optimize API calls

## Migration Strategy

### Backward Compatibility
- Keep current endpoint as `/api/v1/generate-routine-legacy`
- Build new endpoints alongside existing ones
- Test thoroughly before removing old system

### Gradual Rollout
1. **Internal Testing** - Test with development team
2. **Beta Testing** - Test with select users
3. **Feature Flag** - Allow switching between old/new systems
4. **Full Rollout** - Remove old system after validation

## Risk Assessment

### High Risk
- **User Adoption**: Users might prefer automated selection
- **Quality Concerns**: User-curated routines might be suboptimal

### Medium Risk
- **UI Complexity**: Curation interface might be confusing
- **Performance**: Multiple API calls might be slow

### Low Risk
- **Technical Implementation**: Simple endpoints are easy to build
- **Data Migration**: No complex data migration required

## Success Metrics

### Technical Metrics
- **API Response Time**: < 2 seconds for each endpoint
- **Error Rate**: < 1% for all endpoints
- **Test Coverage**: > 90% for new endpoints

### User Experience Metrics
- **User Engagement**: % of users who complete routine creation
- **Routine Quality**: User satisfaction with created routines
- **Time to Create**: Average time to create a routine

### Business Metrics
- **Feature Adoption**: % of users using new system
- **Support Tickets**: Reduction in routine-related issues
- **Development Velocity**: Faster feature development

## Unknowns & Assumptions

### Unknowns
1. **Story Quality**: Will generated stories be diverse and useful?
2. **Search Quality**: Will semantic search return relevant exercises?
3. **User Behavior**: How will users actually curate routines?
4. **UI Complexity**: How complex will the curation interface be?

### Assumptions
1. **User Capability**: Users can make good exercise choices with guidance
2. **Story Diversity**: Generated stories will cover different aspects
3. **Search Accuracy**: Semantic search will find relevant exercises
4. **UI Usability**: Curation interface will be intuitive

## Next Steps

### Immediate Actions
1. **Create Story Generator Endpoint** - Extract from current pipeline
2. **Modify Semantic Search** - Return exercise IDs only
3. **Create Simple Routine CRUD** - Basic routine management
4. **Write Tests** - Comprehensive test coverage

### Short Term (1-2 weeks)
1. **Build UI Components** - Story display and exercise lists
2. **Implement Curation Interface** - Add/remove exercises
3. **Add User Guidance** - Tips and hints for curation
4. **Performance Testing** - Optimize API calls

### Medium Term (1 month)
1. **User Testing** - Gather feedback on new system
2. **Quality Improvements** - Enhance story and search quality
3. **Feature Polish** - Refine UI and user experience
4. **Documentation** - Complete API and user documentation

## Conclusion

This simplified architecture offers significant advantages:
- **Reduced Complexity**: Easier to build, test, and maintain
- **Better User Control**: Users get exactly what they want
- **Improved Transparency**: Users understand the reasoning
- **Enhanced Flexibility**: More adaptable to different use cases

The trade-offs (more UI work, user responsibility) are outweighed by the benefits of simplicity, transparency, and user control. This approach aligns better with modern UX principles of giving users agency while providing intelligent assistance.

**Recommendation: Proceed with implementation of the new architecture.** 