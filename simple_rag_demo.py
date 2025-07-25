"""
Demo: Simple RAG pipeline for exercise routine generation.

- Uses Gemini to generate exercise stories from a user prompt
- Uses OpenAI vector search (Qdrant) to retrieve diverse exercises for each story
- Enriches results with complete PostgreSQL database data
- Prints the stories and top 5 diverse exercises for each

This script is minimal and composable for testing the core RAG flow.
"""

import asyncio
from app.core.exercise_story_generator import generate_exercise_stories
from app.database.vectorization import search_diverse_exercises_with_database_data

USER_PROMPT = "I sit all day, my hips are tight, I want to do handstands"

async def main():
    print(f"User prompt: {USER_PROMPT}\n")
    stories = generate_exercise_stories(USER_PROMPT)
    print("Generated Exercise Stories:")
    for i, story in enumerate(stories, 1):
        print(f"  {i}. {story}")
    print("\nRetrieving diverse exercises with database data for each story...\n")
    for i, story in enumerate(stories, 1):
        print(f"Story {i}: {story}")
        results = await search_diverse_exercises_with_database_data(story, target_count=5, initial_limit=40, score_threshold=0.3)
        print(f"Found {len(results)} results for story {i}")
        if not results:
            print("  No similar exercises found.")
        else:
            for res in results:
                print(f"  - {res.get('exercise_name', 'N/A')} (video: {res.get('video_path', 'N/A')}) [score: {res.get('score', 0):.2f}]")
                print(f"    URL: {res.get('url', 'N/A')}")
                print(f"    Database ID: {res.get('database_id', 'N/A')}")
                print(f"    Qdrant ID: {res.get('qdrant_id', 'N/A')}")
                print(f"    Benefits: {res.get('benefits', 'N/A')[:100]}...")
                print(f"    Fitness Level: {res.get('fitness_level', 'N/A')}/10, Intensity: {res.get('intensity', 'N/A')}/10")
                print()
        print()

if __name__ == "__main__":
    asyncio.run(main()) 