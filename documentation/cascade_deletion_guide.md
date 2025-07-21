# Cascade Deletion Guide

This guide explains how to use the enhanced cascade deletion system to clean up bad clips and manage storage efficiently.

## Overview

The cascade deletion system provides comprehensive cleanup capabilities that remove data from:
- **Database**: PostgreSQL exercise records
- **Vector Store**: Qdrant embeddings
- **File System**: Video clips and compiled workouts
- **Compiled Workouts**: Any compiled workouts that reference deleted exercises

## Quick Start

### 1. Analyze Your Storage

First, understand what's taking up space:

```bash
curl "http://localhost:8000/api/v1/cleanup/analysis"
```

This will show you:
- Total storage usage
- Number of files in each directory
- Cleanup recommendations
- Potential storage savings

### 2. Find Orphaned Files

Find files that exist in storage but aren't referenced in the database:

```bash
curl "http://localhost:8000/api/v1/cleanup/orphaned-files"
```

### 3. Preview Deletions

Before deleting, always preview what would be deleted:

```bash
# Preview low-quality exercise deletion
curl "http://localhost:8000/api/v1/exercises/deletion-preview?fitness_level_max=3&intensity_max=3"

# Preview all cleanup operations
curl "http://localhost:8000/api/v1/cleanup/preview"
```

### 4. Perform Cleanup

Once you're satisfied with the preview, perform the actual cleanup:

```bash
# Clean up orphaned files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/orphaned-files?confirm=true"

# Purge low-quality exercises
curl -X DELETE "http://localhost:8000/api/v1/exercises/purge-low-quality?fitness_level_threshold=3&intensity_threshold=3&confirm=true"

# Clean up old temp files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/temp-files?days_old=7&confirm=true"
```

## API Endpoints

### Storage Analysis

#### `GET /api/v1/cleanup/analysis`
Analyze storage usage and get cleanup recommendations.

**Response:**
```json
{
  "recommendations": [
    {
      "type": "orphaned_files",
      "priority": "high",
      "description": "Found 15 orphaned files (45.2 MB)",
      "action": "cleanup_orphaned_files",
      "estimated_savings_mb": 45.2
    }
  ],
  "storage_analysis": {
    "total_size_gb": 2.5,
    "clips": {
      "file_count": 150,
      "total_size_mb": 1200.5
    },
    "compiled_workouts": {
      "file_count": 25,
      "total_size_mb": 800.3
    }
  }
}
```

### Orphaned File Management

#### `GET /api/v1/cleanup/orphaned-files`
Find files not referenced in the database.

#### `DELETE /api/v1/cleanup/orphaned-files`
Clean up orphaned files.

**Parameters:**
- `confirm` (required): Set to `true` to actually delete files

### Exercise Deletion

#### `DELETE /api/v1/exercises/{exercise_id}`
Delete a single exercise with cascade cleanup.

#### `DELETE /api/v1/exercises/batch`
Delete multiple exercises based on criteria.

**Parameters:**
- `fitness_level_min/max`: Filter by fitness level (0-10)
- `intensity_min/max`: Filter by intensity (0-10)
- `exercise_name_pattern`: Pattern to match exercise names
- `created_before/after`: Date filters (ISO format)

#### `DELETE /api/v1/exercises/purge-low-quality`
Specialized endpoint for removing low-quality exercises.

**Parameters:**
- `fitness_level_threshold`: Delete exercises below this fitness level (default: 3)
- `intensity_threshold`: Delete exercises below this intensity level (default: 3)
- `name_patterns`: Comma-separated patterns to match for deletion
- `confirm`: Set to `true` to actually delete

#### `GET /api/v1/exercises/deletion-preview`
Preview what would be deleted based on criteria.

### Temporary File Cleanup

#### `DELETE /api/v1/cleanup/temp-files`
Clean up old temporary files.

**Parameters:**
- `days_old`: Delete files older than this many days (default: 7)
- `confirm`: Set to `true` to actually delete

## Common Use Cases

### 1. Remove Bad Clips

If you have low-quality clips that were incorrectly processed:

```bash
# Preview what would be deleted
curl "http://localhost:8000/api/v1/exercises/deletion-preview?fitness_level_max=2&intensity_max=2"

# Actually delete them
curl -X DELETE "http://localhost:8000/api/v1/exercises/purge-low-quality?fitness_level_threshold=2&intensity_threshold=2&confirm=true"
```

### 2. Clean Up Test Content

Remove exercises with "test" or "demo" in the name:

```bash
curl -X DELETE "http://localhost:8000/api/v1/exercises/batch?exercise_name_pattern=test&confirm=true"
```

### 3. Remove Old Content

Delete exercises created before a certain date:

```bash
curl -X DELETE "http://localhost:8000/api/v1/exercises/batch?created_before=2024-01-01&confirm=true"
```

### 4. Free Up Storage

Clean up orphaned files and old temp files:

```bash
# Clean orphaned files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/orphaned-files?confirm=true"

# Clean old temp files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/temp-files?days_old=7&confirm=true"
```

## Safety Features

### 1. Confirmation Required
All deletion endpoints require explicit confirmation:
- Set `confirm=true` parameter
- Prevents accidental deletions

### 2. Preview Mode
Always preview before deleting:
- Use preview endpoints to see what would be deleted
- No actual deletion occurs during preview

### 3. Cascade Cleanup
When you delete an exercise, the system automatically:
- Removes the database record
- Deletes the vector embedding
- Removes the video file
- Cleans up any compiled workouts that reference it

### 4. Error Handling
The system gracefully handles:
- Missing files
- Database errors
- Vector store errors
- File system errors

## Example Script

Run the example script to see all features in action:

```bash
python examples/cascade_deletion_example.py
```

This script demonstrates:
- Storage analysis
- Finding orphaned files
- Previewing deletions
- Performing cleanup operations

## Best Practices

### 1. Always Preview First
```bash
# Preview before deleting
curl "http://localhost:8000/api/v1/exercises/deletion-preview?fitness_level_max=3"
```

### 2. Use Conservative Thresholds
Start with higher thresholds and lower them if needed:
```bash
# Start conservative
curl -X DELETE "http://localhost:8000/api/v1/exercises/purge-low-quality?fitness_level_threshold=2&intensity_threshold=2&confirm=true"

# Then more aggressive if needed
curl -X DELETE "http://localhost:8000/api/v1/exercises/purge-low-quality?fitness_level_threshold=3&intensity_threshold=3&confirm=true"
```

### 3. Regular Maintenance
Set up regular cleanup tasks:
```bash
# Weekly cleanup of orphaned files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/orphaned-files?confirm=true"

# Monthly cleanup of old temp files
curl -X DELETE "http://localhost:8000/api/v1/cleanup/temp-files?days_old=30&confirm=true"
```

### 4. Monitor Storage
Regularly check storage usage:
```bash
curl "http://localhost:8000/api/v1/cleanup/analysis"
```

## Troubleshooting

### Files Not Deleted
- Check if files exist in the expected locations
- Verify file permissions
- Check container paths vs host paths

### Database Errors
- Verify database connection
- Check if tables exist
- Ensure proper permissions

### Vector Store Errors
- Verify Qdrant connection
- Check if collection exists
- Ensure proper API keys

## Storage Locations

The system manages files in these locations:
- **Clips**: `/app/storage/clips/` (inside container)
- **Compiled Workouts**: `/app/storage/compiled_workouts/` (inside container)
- **Temp Files**: `/app/app/temp/` (inside container)

## Database Tables

The cascade deletion affects these tables:
- **exercises**: Main exercise records
- **compiled_workouts**: Compiled workout videos
- **qdrant**: Vector embeddings (external)

## Performance Considerations

- **Batch Operations**: Use batch deletion for multiple exercises
- **Preview First**: Always preview to avoid unnecessary operations
- **Regular Cleanup**: Schedule regular cleanup to prevent storage bloat
- **Monitor Growth**: Track storage growth to identify issues early 