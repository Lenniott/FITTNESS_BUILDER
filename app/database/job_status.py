import logging
from typing import Optional, Dict, Any
import asyncpg
import json
from app.database.operations import get_database_connection

logger = logging.getLogger(__name__)

async def create_job(job_id: str):
    pool = await get_database_connection()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO exercise_job_status (job_id, status, created_at, updated_at)
            VALUES ($1, 'pending', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING
            """,
            job_id
        )
        logger.info(f"Created job {job_id} with status 'pending'")

async def update_job_status(job_id: str, status: str, result: Optional[Any] = None):
    pool = await get_database_connection()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE exercise_job_status
            SET status = $2,
                result = $3,
                updated_at = NOW()
            WHERE job_id = $1
            """,
            job_id, status, json.dumps(result) if result is not None else None
        )
        logger.info(f"Updated job {job_id} to status '{status}'")

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_database_connection()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, result FROM exercise_job_status WHERE job_id = $1",
            job_id
        )
        if row:
            return {"status": row["status"], "result": row["result"]}
        return None 