import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# In-memory job store for prototyping
_job_store: Dict[str, Dict[str, Any]] = {}

async def create_job(job_id: str):
    """Create a new job record with 'pending' status."""
    _job_store[job_id] = {
        'status': 'pending',
        'result': None
    }
    logger.info(f"Created job {job_id} with status 'pending'")

async def update_job_status(job_id: str, status: str, result: Optional[Any] = None):
    """Update job status and optionally result."""
    if job_id in _job_store:
        _job_store[job_id]['status'] = status
        if result is not None:
            _job_store[job_id]['result'] = result
        logger.info(f"Updated job {job_id} to status '{status}'")
    else:
        logger.warning(f"Tried to update non-existent job {job_id}")

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve job status and result by job ID."""
    return _job_store.get(job_id) 