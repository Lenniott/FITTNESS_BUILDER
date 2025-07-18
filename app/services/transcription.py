"""
Transcription service using OpenAI Whisper for audio-to-text conversion.
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any

import whisper
from openai import OpenAI

logger = logging.getLogger(__name__)

async def transcribe_audio(video_file: str) -> List[Dict[str, Any]]:
    """
    Transcribe audio from video file, checking for existing subtitles first.
    
    Args:
        video_file: Path to video file
        
    Returns:
        List of transcript segments with timestamps
    """
    try:
        # First, check if there are existing subtitle files from yt-dlp
        subtitle_file = await _find_subtitle_file(video_file)
        
        if subtitle_file:
            logger.info(f"Found existing subtitle file: {subtitle_file}")
            return await _parse_subtitle_file(subtitle_file)
        
        # If no subtitle file found, use Whisper
        logger.info("No subtitle file found, using Whisper for transcription")
        return await _transcribe_with_whisper(video_file)
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        # Return empty transcript on error
        return []

async def _find_subtitle_file(video_file: str) -> Optional[str]:
    """Find subtitle file in the same directory as the video file."""
    video_dir = os.path.dirname(video_file)
    video_name = os.path.splitext(os.path.basename(video_file))[0]
    
    # Look for subtitle files with common extensions
    subtitle_extensions = ['.vtt', '.srt', '.ass', '.ssa', '.sub']
    
    for ext in subtitle_extensions:
        subtitle_file = os.path.join(video_dir, f"{video_name}{ext}")
        if os.path.exists(subtitle_file):
            return subtitle_file
    
    # Also check for files with language codes (e.g., .en.vtt)
    for ext in subtitle_extensions:
        for lang in ['en', 'en-US', 'en-GB']:
            subtitle_file = os.path.join(video_dir, f"{video_name}.{lang}{ext}")
            if os.path.exists(subtitle_file):
                return subtitle_file
    
    # Only check .txt files if they look like actual subtitles (not Instagram captions)
    txt_file = os.path.join(video_dir, f"{video_name}.txt")
    if os.path.exists(txt_file):
        # Check if it's a subtitle file by looking for timestamp patterns
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # If it contains timestamp patterns like "00:00:00 --> 00:00:05", it's a subtitle
                if '-->' in content or any(line.strip().count(':') >= 2 for line in content.split('\n')):
                    return txt_file
                # If it's just a short caption (like Instagram), skip it
                elif len(content.strip()) < 200:  # Instagram captions are usually short
                    logger.info(f"Skipping short caption file: {txt_file}")
                    return None
        except Exception as e:
            logger.warning(f"Error checking txt file: {str(e)}")
    
    return None

async def _parse_subtitle_file(subtitle_file: str) -> List[Dict[str, Any]]:
    """Parse subtitle file (VTT, SRT, etc.) into segments."""
    try:
        ext = os.path.splitext(subtitle_file)[1].lower()
        
        if ext == '.vtt':
            return await _parse_vtt_file(subtitle_file)
        elif ext == '.srt':
            return await _parse_srt_file(subtitle_file)
        elif ext == '.txt':
            return await _parse_txt_file(subtitle_file)
        else:
            logger.warning(f"Unsupported subtitle format: {ext}")
            return await _transcribe_with_whisper(subtitle_file)
            
    except Exception as e:
        logger.error(f"Error parsing subtitle file: {str(e)}")
        return []

async def _parse_vtt_file(vtt_file: str) -> List[Dict[str, Any]]:
    """Parse VTT subtitle file."""
    segments = []
    
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple VTT parser
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and WEBVTT header
            if not line or line == 'WEBVTT':
                i += 1
                continue
            
            # Look for timestamp line
            if '-->' in line:
                try:
                    # Parse timestamps
                    start_time, end_time = line.split(' --> ')
                    start_seconds = _parse_timestamp(start_time)
                    end_seconds = _parse_timestamp(end_time)
                    
                    # Get text (next lines until empty line or next timestamp)
                    text_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = ' '.join(text_lines).strip()
                    if text:
                        segments.append({
                            'start': start_seconds,
                            'end': end_seconds,
                            'text': text
                        })
                except Exception as e:
                    logger.warning(f"Error parsing VTT timestamp: {str(e)}")
                    i += 1
            else:
                i += 1
        
        logger.info(f"Parsed {len(segments)} segments from VTT file")
        return segments
        
    except Exception as e:
        logger.error(f"Error parsing VTT file: {str(e)}")
        return []

async def _parse_srt_file(srt_file: str) -> List[Dict[str, Any]]:
    """Parse SRT subtitle file."""
    segments = []
    
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple SRT parser
        blocks = content.split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # Parse timestamp line
                    timestamp_line = lines[1]
                    start_time, end_time = timestamp_line.split(' --> ')
                    start_seconds = _parse_timestamp(start_time)
                    end_seconds = _parse_timestamp(end_time)
                    
                    # Get text
                    text = ' '.join(lines[2:]).strip()
                    if text:
                        segments.append({
                            'start': start_seconds,
                            'end': end_seconds,
                            'text': text
                        })
                except Exception as e:
                    logger.warning(f"Error parsing SRT block: {str(e)}")
                    continue
        
        logger.info(f"Parsed {len(segments)} segments from SRT file")
        return segments
        
    except Exception as e:
        logger.error(f"Error parsing SRT file: {str(e)}")
        return []

async def _parse_txt_file(txt_file: str) -> List[Dict[str, Any]]:
    """Parse simple text file as transcript."""
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if text:
            # Create a single segment for the entire text
            segments = [{
                'start': 0.0,
                'end': 0.0,  # Duration unknown
                'text': text
            }]
            logger.info("Parsed text file as transcript")
            return segments
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error parsing text file: {str(e)}")
        return []

def _parse_timestamp(timestamp: str) -> float:
    """Parse timestamp string to seconds."""
    try:
        # Handle different timestamp formats
        if ',' in timestamp:
            # Format: HH:MM:SS,mmm
            time_part, ms_part = timestamp.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            milliseconds = int(ms_part)
            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        elif '.' in timestamp:
            # Format: HH:MM:SS.mmm
            time_part, ms_part = timestamp.split('.')
            hours, minutes, seconds = map(int, time_part.split(':'))
            milliseconds = int(ms_part)
            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        else:
            # Format: HH:MM:SS
            hours, minutes, seconds = map(int, timestamp.split(':'))
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
        return 0.0

async def _transcribe_with_whisper(video_file: str) -> List[Dict[str, Any]]:
    """Transcribe using Whisper as fallback."""
    try:
        # Load Whisper model
        model = whisper.load_model("base")
        
        # Run transcription in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, model.transcribe, video_file)
        
        # Format transcript segments
        segments = []
        if result and isinstance(result, dict) and 'segments' in result:
            for segment in result['segments']:
                if isinstance(segment, dict):
                    segments.append({
                        'start': float(segment.get('start', 0.0)),
                        'end': float(segment.get('end', 0.0)),
                        'text': str(segment.get('text', '')).strip()
                    })
        
        logger.info(f"Transcribed {len(segments)} segments with Whisper")
        return segments
        
    except Exception as e:
        logger.error(f"Error transcribing with Whisper: {str(e)}")
        return []

async def transcribe_with_openai(video_file: str) -> List[Dict]:
    """
    Alternative transcription using OpenAI API (more accurate but costs money).
    
    Args:
        video_file: Path to video file
        
    Returns:
        List of transcript segments with timestamps
    """
    try:
        # Import here to avoid import-time errors
        from app.core.processor import processor
        client = processor._get_openai_client()
        
        with open(video_file, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        # Format segments
        segments = []
        if transcript and hasattr(transcript, 'segments') and transcript.segments:
            for segment in transcript.segments:
                segments.append({
                    'start': float(segment.start),
                    'end': float(segment.end),
                    'text': str(segment.text).strip()
                })
        
        logger.info(f"Transcribed {len(segments)} segments using OpenAI API")
        return segments
        
    except Exception as e:
        logger.error(f"Error transcribing with OpenAI API: {str(e)}")
        # Fallback to local Whisper
        return await transcribe_audio(video_file)
