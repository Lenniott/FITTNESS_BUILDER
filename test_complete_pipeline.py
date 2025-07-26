"""
Complete pipeline test: From user prompt to final JSON structure.

This script tests the entire RAG pipeline:
1. Generate exercise stories from user prompt
2. Search for diverse exercises for each story
3. Select and order exercises for routine
4. Create final JSON structure for UI
"""

import asyncio
import json
import logging
from app.core.exercise_story_generator import generate_exercise_stories
from app.database.vectorization import search_diverse_exercises_with_database_data
from app.core.exercise_selector import exercise_selector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_PROMPT = "I sit all day, my hips are tight, I want to do handstands"

async def test_complete_pipeline():
    """Test the complete pipeline from user prompt to final JSON."""
    
    print(f"🚀 Testing Complete RAG Pipeline")
    print(f"User prompt: {USER_PROMPT}\n")
    
    # Step 1: Generate exercise stories
    print("📝 Step 1: Generating exercise stories...")
    stories = generate_exercise_stories(USER_PROMPT)
    print(f"Generated {len(stories)} stories")
    print()
    
    # Step 2: Search for exercises for each story
    print("🔍 Step 2: Searching for exercises for each story...")
    all_exercise_results = []
    
    for i, story in enumerate(stories, 1):
        print(f"Searching for story {i}: {story[:50]}...")
        results = await search_diverse_exercises_with_database_data(
            story, target_count=3, initial_limit=40, score_threshold=0.3
        )
        print(f"  Found {len(results)} exercises for story {i}")
        all_exercise_results.extend(results)
    
    print(f"\nTotal exercises found: {len(all_exercise_results)}")
    print()
    
    # Step 3: Select and order exercises for routine
    print("🎯 Step 3: Selecting and ordering exercises for routine...")
    selected_database_ids = await exercise_selector.select_routine_from_stories_and_results(
        original_prompt=USER_PROMPT,
        exercise_stories=stories,
        exercise_results=all_exercise_results
    )
    
    print(f"Selected {len(selected_database_ids)} exercises for routine")
    print()
    
    # Step 4: Create final JSON structure
    print("📋 Step 4: Creating final JSON structure for UI...")
    final_routine_json = await exercise_selector.create_final_routine_json(
        selected_database_ids=selected_database_ids,
        exercise_results=all_exercise_results
    )
    
    # Display the final JSON structure
    print("\n✅ Final JSON Structure:")
    print(json.dumps(final_routine_json, indent=2))
    
    # Display summary
    routine = final_routine_json['routine']
    exercises = routine['exercises']
    metadata = routine['metadata']
    
    print(f"\n📊 Summary:")
    print(f"  Total exercises: {metadata['total_exercises']}")
    print(f"  Database IDs: {metadata['database_operations']['database_ids']}")
    print(f"  Qdrant IDs: {metadata['database_operations']['qdrant_ids']}")
    print(f"  Video paths: {metadata['database_operations']['video_paths']}")
    
    print(f"\n🎯 Exercises for UI:")
    for exercise in exercises:
        print(f"  {exercise['order']}. {exercise['exercise_name']}")
        print(f"     Fitness Level: {exercise['fitness_level']}/10")
        print(f"     Intensity: {exercise['intensity']}/10")
        print(f"     Benefits: {exercise['benefits'][:80]}...")
        print()
    
    print("🎉 Complete pipeline test finished!")
    return final_routine_json

if __name__ == "__main__":
    asyncio.run(test_complete_pipeline()) 