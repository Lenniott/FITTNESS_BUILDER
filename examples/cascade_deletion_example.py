#!/usr/bin/env python3
"""
Example script demonstrating the new cascade deletion features.

This script shows how to use the enhanced deletion endpoints to clean up
bad clips and manage storage efficiently.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

async def make_request(session: aiohttp.ClientSession, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to the API."""
    url = f"{API_BASE_URL}{endpoint}"
    
    if method == "GET":
        async with session.get(url, params=kwargs) as response:
            return await response.json()
    elif method == "DELETE":
        async with session.delete(url, params=kwargs) as response:
            return await response.json()
    else:
        raise ValueError(f"Unsupported method: {method}")

async def analyze_storage(session: aiohttp.ClientSession):
    """Analyze current storage usage and get cleanup recommendations."""
    print("🔍 Analyzing storage usage...")
    
    result = await make_request(session, "GET", "/cleanup/analysis")
    
    print(f"📊 Storage Analysis:")
    print(f"  - Total size: {result.get('storage_analysis', {}).get('total_size_gb', 0):.2f} GB")
    print(f"  - Clips: {result.get('storage_analysis', {}).get('clips', {}).get('file_count', 0)} files")
    print(f"  - Compiled workouts: {result.get('storage_analysis', {}).get('compiled_workouts', {}).get('file_count', 0)} files")
    
    recommendations = result.get('recommendations', [])
    if recommendations:
        print(f"\n💡 Cleanup Recommendations:")
        for rec in recommendations:
            print(f"  - {rec['priority'].upper()}: {rec['description']}")
            print(f"    Action: {rec['action']}")
            print(f"    Estimated savings: {rec['estimated_savings_mb']:.1f} MB")
    else:
        print("✅ No cleanup recommendations - storage looks good!")

async def find_orphaned_files(session: aiohttp.ClientSession):
    """Find orphaned files (files not referenced in database)."""
    print("\n🔍 Finding orphaned files...")
    
    result = await make_request(session, "GET", "/cleanup/orphaned-files")
    
    orphaned_clips = result.get('orphaned_clips', [])
    orphaned_compiled = result.get('orphaned_compiled', [])
    
    print(f"📁 Orphaned Files Found:")
    print(f"  - Clips: {len(orphaned_clips)} files")
    print(f"  - Compiled workouts: {len(orphaned_compiled)} files")
    print(f"  - Total size: {result.get('total_orphaned_size_mb', 0):.1f} MB")
    
    if orphaned_clips or orphaned_compiled:
        print("\n📋 Sample orphaned files:")
        for clip in orphaned_clips[:3]:
            print(f"  - {clip['path']} ({clip['size_mb']:.1f} MB)")
        for compiled in orphaned_compiled[:3]:
            print(f"  - {compiled['path']} ({compiled['size_mb']:.1f} MB)")

async def preview_low_quality_deletion(session: aiohttp.ClientSession):
    """Preview deletion of low-quality exercises."""
    print("\n🔍 Previewing low-quality exercise deletion...")
    
    # Preview deletion of exercises with fitness level <= 3 and intensity <= 3
    result = await make_request(
        session, "GET", "/exercises/deletion-preview",
        fitness_level_max=3,
        intensity_max=3
    )
    
    preview_count = result.get('preview_count', 0)
    print(f"📋 Would delete {preview_count} low-quality exercises")
    
    if preview_count > 0:
        print("\n📋 Sample exercises that would be deleted:")
        for exercise in result.get('exercises', [])[:5]:
            print(f"  - {exercise.get('exercise_name', 'Unknown')}")
            print(f"    Fitness level: {exercise.get('fitness_level', 'Unknown')}")
            print(f"    Intensity: {exercise.get('intensity', 'Unknown')}")

async def purge_low_quality_exercises(session: aiohttp.ClientSession, confirm: bool = False):
    """Purge low-quality exercises."""
    print(f"\n🧹 Purging low-quality exercises (confirm={confirm})...")
    
    if not confirm:
        print("⚠️  Running in preview mode - no files will be deleted")
    
    result = await make_request(
        session, "DELETE", "/exercises/purge-low-quality",
        fitness_level_threshold=3,
        intensity_threshold=3,
        confirm=confirm
    )
    
    deleted_count = result.get('deleted_count', 0)
    print(f"✅ Deleted {deleted_count} low-quality exercises")
    
    if deleted_count > 0:
        print(f"📊 Quality thresholds used:")
        print(f"  - Fitness level threshold: {result.get('quality_thresholds', {}).get('fitness_level_threshold', 'Unknown')}")
        print(f"  - Intensity threshold: {result.get('quality_thresholds', {}).get('intensity_threshold', 'Unknown')}")

async def cleanup_orphaned_files(session: aiohttp.ClientSession, confirm: bool = False):
    """Clean up orphaned files."""
    print(f"\n🧹 Cleaning up orphaned files (confirm={confirm})...")
    
    if not confirm:
        print("⚠️  Running in preview mode - no files will be deleted")
    
    result = await make_request(
        session, "DELETE", "/cleanup/orphaned-files",
        confirm=confirm
    )
    
    if confirm:
        deleted_count = result.get('total_deleted', 0)
        print(f"✅ Deleted {deleted_count} orphaned files")
        print(f"📊 Total size freed: {result.get('total_size_mb', 0):.1f} MB")
    else:
        print("📋 Preview mode - showing what would be deleted")
        print(f"  Would delete: {result.get('would_delete', {}).get('total_orphaned_files', 0)} files")
        print(f"  Total size: {result.get('total_size_mb', 0):.1f} MB")

async def cleanup_temp_files(session: aiohttp.ClientSession, confirm: bool = False):
    """Clean up old temporary files."""
    print(f"\n🧹 Cleaning up old temp files (confirm={confirm})...")
    
    if not confirm:
        print("⚠️  Running in preview mode - no files will be deleted")
    
    result = await make_request(
        session, "DELETE", "/cleanup/temp-files",
        days_old=7,
        confirm=confirm
    )
    
    if confirm:
        deleted_count = result.get('deleted_count', 0)
        print(f"✅ Deleted {deleted_count} old temp files")
        print(f"📊 Total size freed: {result.get('total_size_mb', 0):.1f} MB")
    else:
        print("📋 Preview mode - showing what would be deleted")
        print(f"  Would delete: {result.get('total_files', 0)} files")
        print(f"  Total size: {result.get('total_size_mb', 0):.1f} MB")

async def batch_delete_by_criteria(session: aiohttp.ClientSession, confirm: bool = False):
    """Demonstrate batch deletion by criteria."""
    print(f"\n🗑️  Batch deletion by criteria (confirm={confirm})...")
    
    if not confirm:
        print("⚠️  Running in preview mode - no files will be deleted")
        return
    
    # Example: Delete exercises with "test" in the name
    result = await make_request(
        session, "DELETE", "/exercises/batch",
        exercise_name_pattern="test"
    )
    
    deleted_count = result.get('deleted_count', 0)
    print(f"✅ Deleted {deleted_count} exercises with 'test' in name")

async def main():
    """Main function demonstrating cascade deletion features."""
    print("🚀 Cascade Deletion Example")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Analyze current storage
        await analyze_storage(session)
        
        # Step 2: Find orphaned files
        await find_orphaned_files(session)
        
        # Step 3: Preview low-quality deletion
        await preview_low_quality_deletion(session)
        
        # Step 4: Preview cleanup operations
        print("\n🔍 Previewing all cleanup operations...")
        result = await make_request(session, "GET", "/cleanup/preview")
        
        total_savings = result.get('total_potential_savings_mb', 0)
        print(f"📊 Total potential savings: {total_savings:.1f} MB")
        
        # Step 5: Demonstrate actual cleanup (commented out for safety)
        print("\n⚠️  ACTUAL CLEANUP OPERATIONS (commented out for safety)")
        print("Uncomment the lines below to perform actual cleanup:")
        
        # await purge_low_quality_exercises(session, confirm=True)
        # await cleanup_orphaned_files(session, confirm=True)
        # await cleanup_temp_files(session, confirm=True)
        # await batch_delete_by_criteria(session, confirm=True)
        
        print("\n✅ Example completed!")
        print("\n💡 To perform actual cleanup, uncomment the lines above")

if __name__ == "__main__":
    asyncio.run(main()) 