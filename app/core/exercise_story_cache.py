"""
Smart exercise story generation with caching and reuse.

Requirements and flow:
- Input: user prompt (string), story count (int)
- Process: Check for existing similar stories in cache first
- If similar story found: Return cached story and update usage
- If no similar story: Generate new stories, cache them, and return
- Output: list of exercise stories (strings)
- LLM: Gemini for generation, OpenAI for embeddings
- Storage: PostgreSQL for metadata, Qdrant for vector search

This file implements the intelligent story caching system that reduces
LLM costs and improves response times by reusing similar stories.
"""

import hashlib
import logging
from typing import List, Dict, Optional
from app.core.exercise_story_generator import generate_exercise_stories
from app.database.operations import (
    store_exercise_story, 
    get_story_by_hash, 
    update_story_usage
)
from app.database.vectorization import (
    store_story_embedding, 
    search_similar_stories
)

logger = logging.getLogger(__name__)

def normalize_prompt(user_prompt: str) -> str:
    """
    Normalize user prompt for consistent hashing and comparison.
    
    Args:
        user_prompt: The raw user prompt
        
    Returns:
        Normalized prompt string
    """
    # Convert to lowercase and strip whitespace
    normalized = user_prompt.lower().strip()
    
    # Remove extra whitespace and normalize punctuation
    import re
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized

def create_prompt_hash(user_prompt: str) -> str:
    """
    Create SHA-256 hash of normalized prompt for exact matching.
    
    Args:
        user_prompt: The user prompt
        
    Returns:
        SHA-256 hash string
    """
    normalized = normalize_prompt(user_prompt)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

async def find_similar_cached_stories(
    user_prompt: str, 
    similarity_threshold: float = 0.8
) -> List[Dict]:
    """
    Search for similar cached stories using vector search.
    
    Args:
        user_prompt: The user's prompt
        similarity_threshold: Minimum similarity score for reuse
        
    Returns:
        List of similar cached stories with metadata
    """
    try:
        # Search for similar stories in vector database
        similar_stories = await search_similar_stories(
            query=user_prompt,
            limit=3,
            score_threshold=similarity_threshold
        )
        
        if similar_stories:
            logger.info(f"Found {len(similar_stories)} similar cached stories")
            return similar_stories
        else:
            logger.info("No similar cached stories found")
            return []
            
    except Exception as e:
        logger.error(f"Error searching similar stories: {str(e)}")
        return []

async def cache_new_story(
    original_prompt: str,
    story_text: str
) -> Optional[str]:
    """
    Cache a new story in both PostgreSQL and Qdrant.
    
    Args:
        original_prompt: The user's original prompt
        story_text: The generated story text
        
    Returns:
        Story ID if successful, None if failed
    """
    try:
        # Create prompt hash
        prompt_hash = create_prompt_hash(original_prompt)
        
        # Store in PostgreSQL first (get database ID)
        story_id = await store_exercise_story(
            original_prompt=original_prompt,
            story_text=story_text,
            prompt_hash=prompt_hash,
            qdrant_id=""  # Will be updated after vector storage
        )
        
        # Store embedding in Qdrant
        qdrant_id = await store_story_embedding(
            story_text=story_text,
            original_prompt=original_prompt,
            prompt_hash=prompt_hash,
            database_id=story_id
        )
        
        # Update PostgreSQL with the Qdrant ID
        # Note: We could add an update function or include it in the initial insert
        # For now, the qdrant_id is stored in the vector metadata
        
        logger.info(f"Successfully cached new story with ID: {story_id}")
        return story_id
        
    except Exception as e:
        logger.error(f"Error caching new story: {str(e)}")
        return None

async def generate_cached_exercise_stories(
    user_prompt: str, 
    story_count: int = 5,
    similarity_threshold: float = 0.8
) -> List[str]:
    """
    Generate exercise stories with smart caching and reuse.
    
    This function implements the main logic:
    1. Check for exact prompt hash match
    2. Search for similar stories using vector search
    3. If good matches found, reuse and update usage
    4. If no good matches, generate new stories and cache them
    
    Args:
        user_prompt: The user's natural language requirements
        story_count: Number of stories to generate/return
        similarity_threshold: Minimum similarity for story reuse
        
    Returns:
        List of exercise requirement stories
    """
    try:
        # Step 1: Check for exact hash match
        prompt_hash = create_prompt_hash(user_prompt)
        exact_match = await get_story_by_hash(prompt_hash)
        
        if exact_match:
            logger.info(f"Found exact match for prompt hash: {prompt_hash}")
            await update_story_usage(exact_match['id'])
            return [exact_match['story_text']]
        
        # Step 2: Search for similar stories
        similar_stories = await find_similar_cached_stories(
            user_prompt, 
            similarity_threshold
        )
        
        if similar_stories:
            # Use the best matching story
            best_match = similar_stories[0]
            story_data = best_match['metadata']
            
            logger.info(f"Reusing similar story with score: {best_match['score']:.3f}")
            
            # Update usage count for the reused story
            database_id = story_data.get('database_id')
            if database_id:
                await update_story_usage(database_id)
            
            return [story_data['story_text']]
        
        # Step 3: No suitable cached stories found, generate new ones
        logger.info("No suitable cached stories found, generating new stories")
        
        # Generate new stories using the original generator
        new_stories = generate_exercise_stories(user_prompt, story_count)
        
        if not new_stories:
            logger.error("Failed to generate new stories")
            return ["Quick workout routine for general fitness"]
        
        # Step 4: Cache the first/best story for future reuse
        if new_stories:
            best_story = new_stories[0]  # Cache the first story as it's usually the best
            await cache_new_story(user_prompt, best_story)
        
        logger.info(f"Generated and cached {len(new_stories)} new stories")
        return new_stories
        
    except Exception as e:
        logger.error(f"Error in cached story generation: {str(e)}")
        # Fallback to original generator if caching fails
        try:
            return generate_exercise_stories(user_prompt, story_count)
        except:
            return ["Basic fitness routine for general health and wellness"]

async def get_cached_story_stats() -> Dict:
    """
    Get statistics about cached stories.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        from app.database.operations import search_stories
        
        stories = await search_stories(limit=100)
        
        if not stories:
            return {
                'total_stories': 0,
                'total_usage': 0,
                'avg_usage': 0,
                'most_used_count': 0
            }
        
        total_usage = sum(story['usage_count'] for story in stories)
        avg_usage = total_usage / len(stories) if stories else 0
        most_used_count = max(story['usage_count'] for story in stories) if stories else 0
        
        return {
            'total_stories': len(stories),
            'total_usage': total_usage,
            'avg_usage': round(avg_usage, 2),
            'most_used_count': most_used_count
        }
        
    except Exception as e:
        logger.error(f"Error getting story stats: {str(e)}")
        return {
            'total_stories': 0,
            'total_usage': 0,
            'avg_usage': 0,
            'most_used_count': 0,
            'error': str(e)
        }