"""
Vector database operations using Qdrant for semantic search.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
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
            'qdrant_id': str(uuid.uuid4())
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
