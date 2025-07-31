"""
Vector database operations using Qdrant for semantic search.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PointIdsList
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Qdrant client
_qdrant_client = None

def get_qdrant_client():
    """Get Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        
        if api_key:
            _qdrant_client = QdrantClient(url=qdrant_url, api_key=api_key)
        else:
            _qdrant_client = QdrantClient(url=qdrant_url)
    return _qdrant_client

async def init_vector_store():
    """Initialize Qdrant vector store."""
    client = get_qdrant_client()
    
    # Create fitness_video_clips collection if it doesn't exist
    try:
        client.get_collection("fitness_video_clips")
        logger.info("Qdrant collection 'fitness_video_clips' already exists")
    except Exception:
        client.create_collection(
            collection_name="fitness_video_clips",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        logger.info("Created Qdrant collection 'fitness_video_clips'")

async def store_embedding(exercise_data: Dict) -> str:
    """
    Store exercise embedding in Qdrant with comprehensive text chunk.
    
    Args:
        exercise_data: Complete exercise data including name, instructions, benefits, etc.
        
    Returns:
        Qdrant point ID
    """
    try:
        # Create comprehensive text chunk for semantic search
        text_chunk = f"""
Exercise: {exercise_data['exercise_name']}

Instructions: {exercise_data['how_to']}

Benefits: {exercise_data['benefits']}

Problems it solves: {exercise_data['counteracts']}

Duration/Reps: {exercise_data['rounds_reps']}

Fitness Level: {exercise_data['fitness_level']}/10 (Beginner: 1-3, Intermediate: 4-7, Advanced: 8-10)

Intensity: {exercise_data['intensity']}/10 (Low: 1-3, Moderate: 4-7, High: 8-10)

This exercise is suitable for {exercise_data['fitness_level']} level fitness and has {exercise_data['intensity']} intensity.
It helps with {exercise_data['counteracts']} and provides {exercise_data['benefits']}.
        """.strip()
        
        # Create metadata for filtering and retrieval
        metadata = {
            'exercise_name': exercise_data['exercise_name'],
            'video_path': exercise_data['video_path'],
            'fitness_level': exercise_data['fitness_level'],
            'intensity': exercise_data['intensity'],
            'start_time': exercise_data.get('start_time'),
            'end_time': exercise_data.get('end_time'),
            'duration': exercise_data.get('end_time', 0) - exercise_data.get('start_time', 0),
            'how_to': exercise_data['how_to'],
            'benefits': exercise_data['benefits'],
            'counteracts': exercise_data['counteracts'],
            'rounds_reps': exercise_data['rounds_reps'],
            'original_url': exercise_data.get('url', ''),
            'qdrant_id': str(uuid.uuid4()),
            'database_id': str(exercise_data['id'])  # Store PostgreSQL ID
        }
        
        # Generate embedding using OpenAI
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text_chunk
        )
        
        embedding = response.data[0].embedding
        
        # Store in Qdrant
        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(
            collection_name="fitness_video_clips",
            points=[
                PointStruct(
                    id=metadata['qdrant_id'],
                    vector=embedding,
                    payload=metadata
                )
            ]
        )
        
        logger.info(f"Stored embedding for {exercise_data['exercise_name']} with ID: {metadata['qdrant_id']}")
        return metadata['qdrant_id']
        
    except Exception as e:
        logger.error(f"Error storing embedding: {str(e)}")
        raise

async def search_similar_exercises(
    query: str,
    limit: int = 10,
    score_threshold: float = 0.7
) -> List[Dict]:
    """
    Search for similar exercises using semantic similarity.
    
    Args:
        query: Search query
        limit: Maximum results to return
        score_threshold: Minimum similarity score
        
    Returns:
        List of similar exercises with scores
    """
    try:
        # Generate embedding for query
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        )
        
        query_embedding = response.data[0].embedding
        
        # Search in Qdrant
        qdrant_client = get_qdrant_client()
        search_result = qdrant_client.search(
            collection_name="fitness_video_clips",
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        
        results = []
        for point in search_result:
            results.append({
                'id': point.id,
                'score': point.score,
                'metadata': point.payload
            })
        
        logger.info(f"Found {len(results)} similar exercises for query: {query}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching similar exercises: {str(e)}")
        return []

async def search_diverse_exercises(
    query: str,
    target_count: int = 5,
    initial_limit: int = 30,
    score_threshold: float = 0.4
) -> List[Dict]:
    """
    Search for diverse exercises by retrieving more candidates and removing duplicates.
    
    Args:
        query: Search query
        target_count: Number of diverse exercises to return
        initial_limit: Initial number of candidates to retrieve
        score_threshold: Minimum similarity score for initial retrieval
        
    Returns:
        List of diverse exercises with scores
    """
    try:
        # Get more candidates initially with lower threshold
        candidates = await search_similar_exercises(query, limit=initial_limit, score_threshold=score_threshold)
        
        if not candidates:
            return []
        
        # Deduplicate based on exercise names and content similarity
        diverse_exercises = []
        seen_names = set()
        seen_keywords = set()
        seen_exercise_types = set()
        
        for candidate in candidates:
            metadata = candidate['metadata']
            exercise_name = metadata.get('exercise_name', '').lower()
            
            # Skip if we've seen this exact exercise name
            if exercise_name in seen_names:
                continue
            
            # Extract key movement keywords from exercise name
            keywords = _extract_movement_keywords(exercise_name)
            exercise_type = _categorize_exercise_type(exercise_name)
            
            # Skip if we've seen too many similar movement patterns
            similar_keywords = _count_similar_keywords(keywords, seen_keywords)
            if similar_keywords > 1:  # Reduced from 2 to 1 for more diversity
                continue
            
            # Skip if we have too many of the same exercise type
            if exercise_type in seen_exercise_types and len([e for e in diverse_exercises if _categorize_exercise_type(e['metadata'].get('exercise_name', '').lower()) == exercise_type]) >= 2:
                continue
            
            # Add to diverse set
            diverse_exercises.append(candidate)
            seen_names.add(exercise_name)
            seen_keywords.update(keywords)
            seen_exercise_types.add(exercise_type)
            
            # Stop when we have enough diverse exercises
            if len(diverse_exercises) >= target_count:
                break
        
        logger.info(f"Found {len(diverse_exercises)} diverse exercises from {len(candidates)} candidates for query: {query}")
        return diverse_exercises
        
    except Exception as e:
        logger.error(f"Error searching diverse exercises: {str(e)}")
        return []

async def delete_embedding(point_id: str) -> bool:
    """
    Delete embedding from Qdrant.
    
    Args:
        point_id: Qdrant point ID
        
    Returns:
        True if deleted, False if not found
    """
    try:
        qdrant_client = get_qdrant_client()
        qdrant_client.delete(
            collection_name="fitness_video_clips",
            points_selector=[point_id]
        )
        
        logger.info(f"Deleted embedding: {point_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting embedding: {str(e)}")
        return False

async def delete_embeddings_by_url(url: str) -> int:
    """
    Delete all embeddings for a specific URL.
    
    Args:
        url: Video URL to delete embeddings for
        
    Returns:
        Number of embeddings deleted
    """
    try:
        qdrant_client = get_qdrant_client()
        
        # Search for points with matching URL
        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="original_url",
                    match=MatchValue(value=url)
                )
            ]
        )
        
        search_result = qdrant_client.scroll(
            collection_name="fitness_video_clips",
            scroll_filter=scroll_filter,
            limit=1000
        )
        
        if search_result[0]:
            point_ids = [point.id for point in search_result[0]]
            if point_ids:
                qdrant_client.delete(
                    collection_name="fitness_video_clips",
                    points_selector=PointIdsList(points=point_ids)
                )
                logger.info(f"Deleted {len(point_ids)} embeddings for URL: {url}")
                return len(point_ids)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error deleting embeddings for URL {url}: {str(e)}")
        return 0

async def delete_all_embeddings() -> int:
    """
    Delete ALL embeddings from Qdrant.
    
    Returns:
        Number of embeddings deleted
    """
    try:
        qdrant_client = get_qdrant_client()
        
        # Get all points
        search_result = qdrant_client.scroll(
            collection_name="fitness_video_clips",
            limit=10000
        )
        
        if search_result[0]:
            point_ids = [point.id for point in search_result[0]]
            if point_ids:
                qdrant_client.delete(
                    collection_name="fitness_video_clips",
                    points_selector=PointIdsList(points=point_ids)
                )
                logger.info(f"Deleted {len(point_ids)} embeddings from vector store")
                return len(point_ids)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error deleting all embeddings: {str(e)}")
        return 0

async def get_collection_info() -> Dict:
    """
    Get information about the exercises collection.
    
    Returns:
        Collection information
    """
    try:
        qdrant_client = get_qdrant_client()
        collection_info = qdrant_client.get_collection("fitness_video_clips")
        
        return {
            'name': 'fitness_video_clips',
            'vectors_count': collection_info.points_count,
            'vector_size': 1536,
            'distance': 'COSINE'
        }
        
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        return {}

async def enrich_vector_results_with_database_data(vector_results: List[Dict]) -> List[Dict]:
    """
    Enrich vector search results with complete database data from PostgreSQL.
    
    Args:
        vector_results: List of results from vector search with metadata
        
    Returns:
        List of enriched results with complete database data
    """
    try:
        from app.database.operations import get_database_connection
        
        if not vector_results:
            return []
        
        # Get database connection
        pool = await get_database_connection()
        
        # Extract qdrant_ids from vector results
        qdrant_ids = [result['metadata'].get('qdrant_id') for result in vector_results if result['metadata'].get('qdrant_id')]
        
        logger.info(f"Found {len(qdrant_ids)} qdrant_ids in vector results: {qdrant_ids[:3]}...")
        
        if not qdrant_ids:
            logger.warning("No qdrant_ids found in vector results")
            return vector_results
        
        # Query database for complete exercise data using qdrant_id
        async with pool.acquire() as conn:
            # Use parameterized query to avoid SQL injection
            placeholders = ','.join([f'${i+1}' for i in range(len(qdrant_ids))])
            query = f"""
                SELECT 
                    id,
                    url,
                    normalized_url,
                    carousel_index,
                    exercise_name,
                    video_path,
                    start_time,
                    end_time,
                    how_to,
                    benefits,
                    counteracts,
                    fitness_level,
                    rounds_reps,
                    intensity,
                    qdrant_id,
                    created_at
                FROM exercises 
                WHERE qdrant_id = ANY($1)
            """
            
            logger.info(f"Executing query with qdrant_ids: {qdrant_ids[:3]}...")
            rows = await conn.fetch(query, qdrant_ids)
            logger.info(f"Found {len(rows)} matching database records")
            
            if rows:
                logger.info(f"Sample row: {dict(rows[0])}")
            
            # Create lookup dictionary using qdrant_id as key
            db_data_lookup = {str(row['qdrant_id']): dict(row) for row in rows}
            logger.info(f"Lookup keys: {list(db_data_lookup.keys())[:3]}...")
        
        # Enrich vector results with database data
        enriched_results = []
        for vector_result in vector_results:
            qdrant_id = vector_result['metadata'].get('qdrant_id')
            db_data = db_data_lookup.get(qdrant_id, {})
            
            # Merge vector metadata with database data
            enriched_metadata = {
                **vector_result['metadata'],  # Vector metadata (includes qdrant_id, video_path, etc.)
                **db_data,  # Database data (includes id, url, created_at, etc.)
            }
            
            enriched_result = {
                'id': vector_result['id'],
                'score': vector_result['score'],
                'metadata': enriched_metadata,
                'database_id': db_data.get('id'),
                'url': db_data.get('url'),
                'normalized_url': db_data.get('normalized_url'),
                'carousel_index': db_data.get('carousel_index'),
                'exercise_name': db_data.get('exercise_name') or vector_result['metadata'].get('exercise_name'),
                'video_path': db_data.get('video_path') or vector_result['metadata'].get('video_path'),
                'start_time': db_data.get('start_time') or vector_result['metadata'].get('start_time'),
                'end_time': db_data.get('end_time') or vector_result['metadata'].get('end_time'),
                'how_to': db_data.get('how_to') or vector_result['metadata'].get('how_to'),
                'benefits': db_data.get('benefits') or vector_result['metadata'].get('benefits'),
                'counteracts': db_data.get('counteracts') or vector_result['metadata'].get('counteracts'),
                'fitness_level': db_data.get('fitness_level') or vector_result['metadata'].get('fitness_level'),
                'rounds_reps': db_data.get('rounds_reps') or vector_result['metadata'].get('rounds_reps'),
                'intensity': db_data.get('intensity') or vector_result['metadata'].get('intensity'),
                'created_at': db_data.get('created_at'),
                'qdrant_id': qdrant_id
            }
            
            enriched_results.append(enriched_result)
        
        logger.info(f"Enriched {len(enriched_results)} vector results with database data")
        return enriched_results
        
    except Exception as e:
        logger.error(f"Error enriching vector results with database data: {str(e)}")
        # Return original results if enrichment fails
        return vector_results

async def search_diverse_exercises_with_database_data(
    query: str,
    target_count: int = 5,
    initial_limit: int = 30,
    score_threshold: float = 0.4
) -> List[Dict]:
    """
    Search for diverse exercises and enrich with complete database data.
    
    Args:
        query: Search query
        target_count: Number of diverse exercises to return
        initial_limit: Initial number of candidates to retrieve
        score_threshold: Minimum similarity score for initial retrieval
        
    Returns:
        List of diverse exercises with complete database data
    """
    try:
        # Get diverse exercises from vector search
        diverse_exercises = await search_diverse_exercises(
            query, target_count, initial_limit, score_threshold
        )
        
        # Enrich with database data
        enriched_exercises = await enrich_vector_results_with_database_data(diverse_exercises)
        
        return enriched_exercises
        
    except Exception as e:
        logger.error(f"Error in search_diverse_exercises_with_database_data: {str(e)}")
        return []

def _extract_movement_keywords(exercise_name: str) -> set:
    """Extract key movement keywords from exercise name."""
    # Common movement patterns to identify
    movement_patterns = {
        'stretch', 'flexor', 'bridge', 'plank', 'sit', 'push', 'pull', 'hold',
        'lunge', 'squat', 'deadlift', 'press', 'row', 'curl', 'extension',
        'rotation', 'twist', 'bend', 'reach', 'lift', 'lower', 'raise',
        'handstand', 'headstand', 'cartwheel', 'split', 'bridge', 'wheel',
        'wall', 'floor', 'standing', 'kneeling', 'lying', 'seated'
    }
    
    words = exercise_name.split()
    keywords = set()
    
    for word in words:
        # Clean the word
        clean_word = word.lower().strip('()[]{}.,!?')
        if clean_word in movement_patterns:
            keywords.add(clean_word)
    
    return keywords

def _count_similar_keywords(new_keywords: set, seen_keywords: set) -> int:
    """Count how many keywords are similar to already seen ones."""
    if not seen_keywords:
        return 0
    
    # Count overlapping keywords
    overlap = len(new_keywords.intersection(seen_keywords))
    
    # Also count similar movement patterns
    similar_patterns = 0
    for new_key in new_keywords:
        for seen_key in seen_keywords:
            # Check for similar movement patterns
            if (new_key in seen_key or seen_key in new_key) and len(new_key) > 3:
                similar_patterns += 1
    
    return overlap + similar_patterns

def _categorize_exercise_type(exercise_name: str) -> str:
    """Categorize exercise into broad types for better deduplication."""
    exercise_name_lower = exercise_name.lower()
    
    # Handstand variations
    if any(word in exercise_name_lower for word in ['handstand', 'headstand', 'inverted']):
        return 'handstand'
    
    # Stretching/mobility
    if any(word in exercise_name_lower for word in ['stretch', 'flexor', 'mobility', 'opener']):
        return 'stretch'
    
    # Core exercises
    if any(word in exercise_name_lower for word in ['hollow', 'plank', 'crunch', 'sit-up', 'core']):
        return 'core'
    
    # Push exercises
    if any(word in exercise_name_lower for word in ['push', 'press', 'dip']):
        return 'push'
    
    # Hip/leg exercises
    if any(word in exercise_name_lower for word in ['hip', 'lunge', 'squat', 'leg']):
        return 'hip_leg'
    
    # Balance/stability
    if any(word in exercise_name_lower for word in ['balance', 'stability', 'hold', 'stand']):
        return 'balance'
    
    # Wall exercises
    if 'wall' in exercise_name_lower:
        return 'wall'
    
    # Floor exercises
    if any(word in exercise_name_lower for word in ['floor', 'lying', 'seated', 'kneeling']):
        return 'floor'
    
    return 'other'

async def store_story_embedding(
    story_text: str,
    original_prompt: str,
    prompt_hash: str,
    database_id: str
) -> str:
    """
    Store exercise story embedding in Qdrant.
    
    Args:
        story_text: The generated story text to embed
        original_prompt: The user's original prompt
        prompt_hash: SHA-256 hash of the normalized prompt
        database_id: PostgreSQL story ID
        
    Returns:
        Qdrant point ID
    """
    try:
        # Create comprehensive text chunk for embedding
        text_chunk = f"""
User Requirements: {original_prompt}

Exercise Story: {story_text}

This story describes exercise requirements and user needs for fitness routines.
        """.strip()
        
        # Create metadata for filtering and retrieval
        metadata = {
            'content_type': 'exercise_story',
            'original_prompt': original_prompt,
            'story_text': story_text,
            'prompt_hash': prompt_hash,
            'database_id': database_id,
            'qdrant_id': str(uuid.uuid4())
        }
        
        # Generate embedding using OpenAI
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_chunk
        )
        
        embedding = response.data[0].embedding
        
        # Store in Qdrant (same collection as exercises, differentiated by content_type)
        qdrant_client = get_qdrant_client()
        point_id = metadata['qdrant_id']
        
        qdrant_client.upsert(
            collection_name="fitness_video_clips",
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=metadata
                )
            ]
        )
        
        logger.info(f"Stored story embedding in Qdrant with ID: {point_id}")
        return point_id
        
    except Exception as e:
        logger.error(f"Error storing story embedding: {str(e)}")
        raise

async def search_similar_stories(
    query: str,
    limit: int = 5,
    score_threshold: float = 0.7
) -> List[Dict]:
    """
    Search for similar exercise stories using vector search.
    
    Args:
        query: Search query (user prompt)
        limit: Maximum number of results
        score_threshold: Minimum similarity score
        
    Returns:
        List of similar stories with scores
    """
    try:
        # Generate embedding for the query
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        
        query_embedding = response.data[0].embedding
        
        # Search in Qdrant with content_type filter
        qdrant_client = get_qdrant_client()
        search_result = qdrant_client.search(
            collection_name="fitness_video_clips",
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="content_type",
                        match=MatchValue(value="exercise_story")
                    )
                ]
            )
        )
        
        results = []
        for point in search_result:
            results.append({
                'id': point.id,
                'score': point.score,
                'metadata': point.payload
            })
        
        logger.info(f"Found {len(results)} similar stories for query: {query}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching similar stories: {str(e)}")
        return []

async def delete_story_embedding(point_id: str) -> bool:
    """
    Delete story embedding from Qdrant.
    
    Args:
        point_id: Qdrant point ID to delete
        
    Returns:
        True if deleted successfully
    """
    try:
        qdrant_client = get_qdrant_client()
        qdrant_client.delete(
            collection_name="fitness_video_clips",
            points_selector=PointIdsList(points=[point_id])
        )
        
        logger.info(f"Deleted story embedding with ID: {point_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting story embedding: {str(e)}")
        return False
