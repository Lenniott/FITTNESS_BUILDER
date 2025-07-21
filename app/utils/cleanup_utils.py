"""
Utility functions for cleanup and cascade deletion operations.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def analyze_storage_usage() -> Dict:
    """
    Analyze storage usage and identify potential cleanup opportunities.
    
    Returns:
        Dictionary with storage analysis information
    """
    try:
        # Try container paths first, then fall back to local paths
        clips_dir = Path("/app/storage/clips")
        compiled_dir = Path("/app/storage/compiled_workouts")
        temp_dir = Path("/app/app/temp")
        
        # If container paths don't exist, try local paths
        if not clips_dir.exists():
            clips_dir = Path("storage/clips")
        if not compiled_dir.exists():
            compiled_dir = Path("storage/compiled_workouts")
        if not temp_dir.exists():
            temp_dir = Path("app/temp")
        
        clips_info = await _analyze_directory(clips_dir, "*.mp4")
        compiled_info = await _analyze_directory(compiled_dir, "*.mp4")
        temp_info = await _analyze_directory(temp_dir, "*")
        
        return {
            "clips": clips_info,
            "compiled_workouts": compiled_info,
            "temp": temp_info,
            "total_size_gb": (clips_info["total_size"] + compiled_info["total_size"] + temp_info["total_size"]) / (1024**3),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing storage usage: {str(e)}")
        return {}

async def _analyze_directory(directory: Path, pattern: str) -> Dict:
    """Analyze a directory for file information."""
    if not directory.exists():
        return {
            "exists": False,
            "file_count": 0,
            "total_size": 0,
            "oldest_file": None,
            "newest_file": None
        }
    
    files = list(directory.glob(pattern))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    
    file_times = []
    for file in files:
        if file.is_file():
            stat = file.stat()
            file_times.append((file, stat.st_mtime))
    
    oldest_file = min(file_times, key=lambda x: x[1]) if file_times else None
    newest_file = max(file_times, key=lambda x: x[1]) if file_times else None
    
    return {
        "exists": True,
        "file_count": len(files),
        "total_size": total_size,
        "total_size_mb": total_size / (1024**2),
        "oldest_file": {
            "name": oldest_file[0].name,
            "date": datetime.fromtimestamp(oldest_file[1]).isoformat()
        } if oldest_file else None,
        "newest_file": {
            "name": newest_file[0].name,
            "date": datetime.fromtimestamp(newest_file[1]).isoformat()
        } if newest_file else None
    }

async def find_orphaned_files() -> Dict:
    """
    Find files that exist in storage but not referenced in the database.
    
    Returns:
        Dictionary with orphaned file information
    """
    try:
        from app.database.operations import get_database_connection
        
        # Get all video paths from database
        pool = await get_database_connection()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT video_path FROM exercises")
            db_paths = {row['video_path'] for row in rows}
        
        # Try container paths first, then fall back to local paths
        clips_dir = Path("/app/storage/clips")
        compiled_dir = Path("/app/storage/compiled_workouts")
        
        if not clips_dir.exists():
            clips_dir = Path("storage/clips")
        if not compiled_dir.exists():
            compiled_dir = Path("storage/compiled_workouts")
        
        orphaned_clips = []
        if clips_dir.exists():
            for clip_file in clips_dir.glob("*.mp4"):
                # Convert to relative path for comparison with database
                clip_path = str(clip_file)
                relative_path = str(clip_file.relative_to(Path.cwd())) if clip_file.is_relative_to(Path.cwd()) else clip_path
                
                # Check both absolute and relative paths
                if relative_path not in db_paths and clip_path not in db_paths:
                    orphaned_clips.append({
                        "path": clip_path,
                        "size_mb": clip_file.stat().st_size / (1024**2),
                        "modified": datetime.fromtimestamp(clip_file.stat().st_mtime).isoformat()
                    })
        
        orphaned_compiled = []
        if compiled_dir.exists():
            for compiled_file in compiled_dir.glob("*.mp4"):
                compiled_path = str(compiled_file)
                # For compiled workouts, we'll check if they're referenced in the compiled_workouts table
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT id FROM compiled_workouts WHERE video_path = $1", compiled_path)
                    if not row:
                        orphaned_compiled.append({
                            "path": compiled_path,
                            "size_mb": compiled_file.stat().st_size / (1024**2),
                            "modified": datetime.fromtimestamp(compiled_file.stat().st_mtime).isoformat()
                        })
        
        return {
            "orphaned_clips": orphaned_clips,
            "orphaned_compiled": orphaned_compiled,
            "total_orphaned_files": len(orphaned_clips) + len(orphaned_compiled),
            "total_orphaned_size_mb": sum(f["size_mb"] for f in orphaned_clips + orphaned_compiled)
        }
        
    except Exception as e:
        logger.error(f"Error finding orphaned files: {str(e)}")
        return {}

async def cleanup_orphaned_files(confirm: bool = False) -> Dict:
    """
    Clean up orphaned files (files not referenced in database).
    
    Args:
        confirm: If True, actually delete files. If False, just return what would be deleted.
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        orphaned_info = await find_orphaned_files()
        
        if not confirm:
            return {
                "message": "Preview mode - no files deleted",
                "would_delete": orphaned_info,
                "total_size_mb": orphaned_info["total_orphaned_size_mb"]
            }
        
        # Actually delete orphaned files
        deleted_clips = 0
        deleted_compiled = 0
        
        for clip_info in orphaned_info["orphaned_clips"]:
            try:
                Path(clip_info["path"]).unlink()
                deleted_clips += 1
            except Exception as e:
                logger.error(f"Error deleting orphaned clip {clip_info['path']}: {str(e)}")
        
        for compiled_info in orphaned_info["orphaned_compiled"]:
            try:
                Path(compiled_info["path"]).unlink()
                deleted_compiled += 1
            except Exception as e:
                logger.error(f"Error deleting orphaned compiled file {compiled_info['path']}: {str(e)}")
        
        return {
            "message": f"Successfully deleted {deleted_clips + deleted_compiled} orphaned files",
            "deleted_clips": deleted_clips,
            "deleted_compiled": deleted_compiled,
            "total_deleted": deleted_clips + deleted_compiled,
            "total_size_mb": orphaned_info["total_orphaned_size_mb"]
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned files: {str(e)}")
        return {"error": str(e)}

async def cleanup_old_temp_files(days_old: int = 7, confirm: bool = False, include_recent: bool = False) -> Dict:
    """
    Clean up old temporary files.
    
    Args:
        days_old: Delete files older than this many days
        confirm: If True, actually delete files. If False, just return what would be deleted.
        include_recent: If True, also delete recent temp files (for manual cleanup)
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        # Try container path first, then fall back to local path
        temp_dir = Path("/app/app/temp")
        if not temp_dir.exists():
            temp_dir = Path("app/temp")
        
        if not temp_dir.exists():
            return {"message": "Temp directory does not exist"}
        
        cutoff_time = datetime.now() - timedelta(days=days_old)
        old_files = []
        
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                # Include all files if include_recent is True, otherwise only old files
                if include_recent or file_time < cutoff_time:
                    old_files.append({
                        "path": str(file_path),
                        "size_mb": file_path.stat().st_size / (1024**2),
                        "modified": file_time.isoformat()
                    })
        
        if not confirm:
            return {
                "message": "Preview mode - no files deleted",
                "would_delete": old_files,
                "total_files": len(old_files),
                "total_size_mb": sum(f["size_mb"] for f in old_files)
            }
        
        # Actually delete old files and empty directories
        deleted_count = 0
        deleted_dirs = 0
        processed_dirs = set()
        
        for file_info in old_files:
            try:
                file_path = Path(file_info["path"])
                file_path.unlink()
                deleted_count += 1
                
                # Track the parent directory for cleanup
                parent_dir = file_path.parent
                if parent_dir != temp_dir and str(parent_dir) not in processed_dirs:
                    processed_dirs.add(str(parent_dir))
                    
            except Exception as e:
                logger.error(f"Error deleting old temp file {file_info['path']}: {str(e)}")
        
        # Clean up empty directories
        for dir_path_str in processed_dirs:
            try:
                dir_path = Path(dir_path_str)
                if dir_path.exists() and dir_path.is_dir():
                    # Check if directory is empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        deleted_dirs += 1
                        logger.info(f"Deleted empty temp directory: {dir_path}")
            except Exception as e:
                logger.error(f"Error deleting empty temp directory {dir_path_str}: {str(e)}")
        
        return {
            "message": f"Successfully deleted {deleted_count} old temp files and {deleted_dirs} empty directories",
            "deleted_count": deleted_count,
            "deleted_directories": deleted_dirs,
            "total_size_mb": sum(f["size_mb"] for f in old_files)
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old temp files: {str(e)}")
        return {"error": str(e)}

async def get_cleanup_recommendations() -> Dict:
    """
    Get recommendations for cleanup operations based on current system state.
    
    Returns:
        Dictionary with cleanup recommendations
    """
    try:
        # Analyze storage usage
        storage_analysis = await analyze_storage_usage()
        
        # Find orphaned files
        orphaned_info = await find_orphaned_files()
        
        recommendations = []
        
        # Check for orphaned files
        if orphaned_info["total_orphaned_files"] > 0:
            recommendations.append({
                "type": "orphaned_files",
                "priority": "high",
                "description": f"Found {orphaned_info['total_orphaned_files']} orphaned files ({orphaned_info['total_orphaned_size_mb']:.1f} MB)",
                "action": "cleanup_orphaned_files",
                "estimated_savings_mb": orphaned_info["total_orphaned_size_mb"]
            })
        
        # Check for large temp directory
        if storage_analysis.get("temp", {}).get("total_size_mb", 0) > 100:
            recommendations.append({
                "type": "large_temp_directory",
                "priority": "medium",
                "description": f"Temp directory is {storage_analysis['temp']['total_size_mb']:.1f} MB",
                "action": "cleanup_old_temp_files",
                "estimated_savings_mb": storage_analysis["temp"]["total_size_mb"]
            })
        
        # Check for old files
        if storage_analysis.get("clips", {}).get("oldest_file"):
            oldest_date = datetime.fromisoformat(storage_analysis["clips"]["oldest_file"]["date"])
            days_old = (datetime.now() - oldest_date).days
            if days_old > 30:
                recommendations.append({
                    "type": "old_files",
                    "priority": "low",
                    "description": f"Oldest files are {days_old} days old",
                    "action": "review_old_files",
                    "estimated_savings_mb": 0  # Unknown
                })
        
        return {
            "recommendations": recommendations,
            "storage_analysis": storage_analysis,
            "orphaned_files": orphaned_info
        }
        
    except Exception as e:
        logger.error(f"Error getting cleanup recommendations: {str(e)}")
        return {"error": str(e)} 