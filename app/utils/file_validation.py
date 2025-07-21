"""
Comprehensive file validation utilities for video processing pipeline.
Handles download corruption detection and video quality validation.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class FileValidator:
    """Comprehensive file validation for video processing pipeline."""
    
    def __init__(self):
        self.min_duration = 10.0  # Minimum video duration in seconds
        self.max_duration = 600.0  # Maximum video duration in seconds (10 minutes)
        self.min_resolution = (320, 240)  # Minimum resolution (width, height)
        self.min_fps = 10.0  # Minimum frame rate
        self.min_file_size = 1024 * 1024  # Minimum file size (1MB)
        self.max_file_size = 500 * 1024 * 1024  # Maximum file size (500MB)
    
    async def validate_downloaded_file(self, file_path: str, source_url: str) -> Dict[str, Any]:
        """
        Comprehensive validation of downloaded file.
        
        Args:
            file_path: Path to downloaded file
            source_url: Original source URL for context
            
        Returns:
            Dict with validation results and metadata
        """
        validation_result = {
            'file_path': file_path,
            'source_url': source_url,
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {},
            'validation_steps': []
        }
        
        try:
            # Step 1: Basic file existence and size check
            validation_result['validation_steps'].append('file_existence')
            if not await self._check_file_existence(file_path):
                validation_result['errors'].append("File does not exist")
                return validation_result
            
            # Step 2: File size validation
            validation_result['validation_steps'].append('file_size')
            size_check = await self._validate_file_size(file_path)
            if not size_check['valid']:
                validation_result['errors'].extend(size_check['errors'])
                validation_result['warnings'].extend(size_check['warnings'])
            
            # Step 3: File format validation
            validation_result['validation_steps'].append('file_format')
            format_check = await self._validate_file_format(file_path)
            if not format_check['valid']:
                validation_result['errors'].extend(format_check['errors'])
                validation_result['warnings'].extend(format_check['warnings'])
            
            # Step 4: Video content validation
            validation_result['validation_steps'].append('video_content')
            video_check = await self._validate_video_content(file_path)
            if not video_check['valid']:
                validation_result['errors'].extend(video_check['errors'])
                validation_result['warnings'].extend(video_check['warnings'])
            
            # Step 5: Audio validation (if applicable)
            validation_result['validation_steps'].append('audio_content')
            audio_check = await self._validate_audio_content(file_path)
            if not audio_check['valid']:
                validation_result['warnings'].extend(audio_check['warnings'])
            
            # Step 6: Playability test
            validation_result['validation_steps'].append('playability')
            playability_check = await self._test_playability(file_path)
            if not playability_check['valid']:
                validation_result['errors'].extend(playability_check['errors'])
            
            # Step 7: Corruption detection
            validation_result['validation_steps'].append('corruption_detection')
            corruption_check = await self._detect_corruption(file_path)
            if not corruption_check['valid']:
                validation_result['errors'].extend(corruption_check['errors'])
            
            # Determine overall validity
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            validation_result['metadata'] = {
                'file_size': size_check.get('metadata', {}),
                'video_properties': video_check.get('metadata', {}),
                'audio_properties': audio_check.get('metadata', {}),
                'format_info': format_check.get('metadata', {})
            }
            
            if validation_result['is_valid']:
                logger.info(f"✅ File validation passed: {file_path}")
            else:
                logger.error(f"❌ File validation failed: {file_path}")
                logger.error(f"Errors: {validation_result['errors']}")
                logger.error(f"Warnings: {validation_result['warnings']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error during file validation: {str(e)}")
            validation_result['errors'].append(f"Validation error: {str(e)}")
            return validation_result
    
    async def _check_file_existence(self, file_path: str) -> bool:
        """Check if file exists and is accessible."""
        try:
            return os.path.exists(file_path) and os.path.isfile(file_path)
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False
    
    async def _validate_file_size(self, file_path: str) -> Dict[str, Any]:
        """Validate file size is within acceptable limits."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            file_size = os.path.getsize(file_path)
            result['metadata']['file_size_bytes'] = file_size
            result['metadata']['file_size_mb'] = file_size / (1024 * 1024)
            
            if file_size < self.min_file_size:
                result['errors'].append(f"File too small: {file_size:,} bytes (< {self.min_file_size:,} bytes)")
            
            if file_size > self.max_file_size:
                result['warnings'].append(f"File very large: {file_size:,} bytes (> {self.max_file_size:,} bytes)")
            
            result['valid'] = len(result['errors']) == 0
            return result
            
        except Exception as e:
            result['errors'].append(f"Error checking file size: {str(e)}")
            return result
    
    async def _validate_file_format(self, file_path: str) -> Dict[str, Any]:
        """Validate file format using FFmpeg probe."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            # Use FFmpeg probe to get file information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result['errors'].append(f"FFprobe failed: {stderr.decode()}")
                return result
            
            # Parse JSON output
            import json
            probe_data = json.loads(stdout.decode())
            
            # Check if video stream exists
            video_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video']
            if not video_streams:
                result['errors'].append("No video stream found")
                return result
            
            # Store format information
            result['metadata']['format'] = probe_data.get('format', {})
            result['metadata']['video_streams'] = video_streams
            result['metadata']['audio_streams'] = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
            
            # Check video codec
            video_stream = video_streams[0]
            codec_name = video_stream.get('codec_name', 'unknown')
            if codec_name in ['h264', 'h265', 'vp8', 'vp9', 'av1']:
                result['metadata']['codec'] = codec_name
            else:
                result['warnings'].append(f"Unusual video codec: {codec_name}")
            
            result['valid'] = True
            return result
            
        except Exception as e:
            result['errors'].append(f"Error validating file format: {str(e)}")
            return result
    
    async def _validate_video_content(self, file_path: str) -> Dict[str, Any]:
        """Validate video content using OpenCV."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                result['errors'].append("Cannot open video file with OpenCV")
                return result
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate duration
            duration = total_frames / fps if fps > 0 else 0
            
            # Store metadata
            result['metadata'] = {
                'fps': fps,
                'total_frames': total_frames,
                'width': width,
                'height': height,
                'duration': duration,
                'resolution': f"{width}x{height}"
            }
            
            # Validate duration
            if duration < self.min_duration:
                result['errors'].append(f"Video too short: {duration:.1f}s (< {self.min_duration}s)")
            
            if duration > self.max_duration:
                result['warnings'].append(f"Video very long: {duration:.1f}s (> {self.max_duration}s)")
            
            # Validate resolution
            if width < self.min_resolution[0] or height < self.min_resolution[1]:
                result['errors'].append(f"Resolution too low: {width}x{height} (< {self.min_resolution[0]}x{self.min_resolution[1]})")
            
            # Validate frame rate
            if fps < self.min_fps:
                result['errors'].append(f"Frame rate too low: {fps:.1f} fps (< {self.min_fps} fps)")
            
            # Check if video has content (not just black frames)
            frame_count = 0
            has_content = False
            
            while frame_count < min(10, total_frames):  # Check first 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Check if frame has content (not just black)
                if frame is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if np.std(gray) > 10:  # Frame has some variation
                        has_content = True
                        break
                
                frame_count += 1
            
            cap.release()
            
            if not has_content:
                result['warnings'].append("Video appears to have no meaningful content (possibly black frames)")
            
            result['valid'] = len(result['errors']) == 0
            return result
            
        except Exception as e:
            result['errors'].append(f"Error validating video content: {str(e)}")
            return result
    
    async def _validate_audio_content(self, file_path: str) -> Dict[str, Any]:
        """Validate audio content using FFmpeg."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            # Check if audio stream exists
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'a',
                '-show_entries', 'stream=codec_name,sample_rate,channels',
                '-of', 'json',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result['warnings'].append("No audio stream found or cannot read audio")
                return result
            
            # Parse audio information
            import json
            audio_data = json.loads(stdout.decode())
            audio_streams = audio_data.get('streams', [])
            
            if audio_streams:
                audio_stream = audio_streams[0]
                result['metadata'] = {
                    'audio_codec': audio_stream.get('codec_name', 'unknown'),
                    'sample_rate': audio_stream.get('sample_rate', 'unknown'),
                    'channels': audio_stream.get('channels', 'unknown')
                }
                
                # Check audio quality
                sample_rate = audio_stream.get('sample_rate')
                if sample_rate and int(sample_rate) < 22050:
                    result['warnings'].append(f"Low audio sample rate: {sample_rate} Hz")
            else:
                result['warnings'].append("No audio stream found")
            
            result['valid'] = True
            return result
            
        except Exception as e:
            result['warnings'].append(f"Error validating audio: {str(e)}")
            result['valid'] = True  # Audio validation failure is not critical
            return result
    
    async def _test_playability(self, file_path: str) -> Dict[str, Any]:
        """Test if video can be played without errors."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            # Use FFmpeg to test playability
            cmd = [
                'ffmpeg',
                '-v', 'error',
                '-i', file_path,
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result['errors'].append(f"Video not playable: {stderr.decode()}")
                return result
            
            # Check for warnings in stderr
            stderr_output = stderr.decode()
            if stderr_output:
                result['warnings'].append(f"Playability warnings: {stderr_output}")
            
            result['valid'] = True
            return result
            
        except Exception as e:
            result['errors'].append(f"Error testing playability: {str(e)}")
            return result
    
    async def _detect_corruption(self, file_path: str) -> Dict[str, Any]:
        """Detect file corruption using multiple methods."""
        result = {'valid': False, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            # Method 1: Check file integrity with FFmpeg
            cmd = [
                'ffmpeg',
                '-v', 'error',
                '-i', file_path,
                '-c', 'copy',
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result['errors'].append(f"File corruption detected: {stderr.decode()}")
                return result
            
            # Method 2: Check for common corruption patterns
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                result['errors'].append("File is empty (0 bytes)")
                return result
            
            # Method 3: Try to read first and last few bytes
            try:
                with open(file_path, 'rb') as f:
                    # Read first 1KB
                    f.seek(0)
                    header = f.read(1024)
                    
                    # Read last 1KB
                    f.seek(max(0, file_size - 1024))
                    footer = f.read(1024)
                    
                    # Check for common corruption indicators
                    if b'\x00\x00\x00\x00' * 100 in header:
                        result['warnings'].append("File may have null byte corruption in header")
                    
                    if b'\x00\x00\x00\x00' * 100 in footer:
                        result['warnings'].append("File may have null byte corruption in footer")
                        
            except Exception as e:
                result['warnings'].append(f"Error reading file for corruption check: {str(e)}")
            
            result['valid'] = True
            return result
            
        except Exception as e:
            result['errors'].append(f"Error detecting corruption: {str(e)}")
            return result
    
    async def cleanup_invalid_file(self, file_path: str, validation_result: Dict[str, Any]) -> bool:
        """
        Clean up invalid file and log details.
        
        Args:
            file_path: Path to invalid file
            validation_result: Result from validate_downloaded_file
            
        Returns:
            True if cleanup successful
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️  Cleaned up invalid file: {file_path}")
                logger.info(f"Errors: {validation_result['errors']}")
                logger.info(f"Warnings: {validation_result['warnings']}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up invalid file {file_path}: {str(e)}")
            return False

# Global validator instance
file_validator = FileValidator() 