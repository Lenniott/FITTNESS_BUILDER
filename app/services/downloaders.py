"""
Downloader component for fetching media and metadata from social media platforms.
"""

import asyncio
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import logging

import instaloader
import yt_dlp

logger = logging.getLogger(__name__)

async def download_media_and_metadata(url: str) -> Dict:
    """
    Main entry point for downloading media and metadata from social platforms.
    
    Args:
        url: The URL to download from
        
    Returns:
        Dict containing files, tags, description, source, temp_dir, and link
    """
    # Create unique temporary directory
    temp_dir = tempfile.mkdtemp(prefix="gilgamesh_download_", dir="storage/temp")
    
    try:
        # Determine source and delegate to appropriate downloader
        if "youtube.com" in url or "youtu.be" in url or "tiktok.com" in url:
            return await download_youtube(url, temp_dir)
        elif "instagram.com" in url:
            # For Instagram, just download all videos from the URL
            return await download_instagram(url, temp_dir)
        else:
            raise ValueError(f"Unsupported URL domain: {url}")
            
    except Exception as e:
        logger.error(f"Error downloading from {url}: {str(e)}")
        raise

async def download_youtube(url: str, temp_dir: str) -> Dict:
    """
    Download video from YouTube or TikTok using yt-dlp.
    
    Args:
        url: YouTube or TikTok URL
        temp_dir: Temporary directory for downloads
        
    Returns:
        Dict with file paths, metadata, and temp directory
    """
    def _download_sync():
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'writesubtitles': True,  # Keep subtitles for transcript
            'writeautomaticsub': True,  # Keep auto subtitles
            'writethumbnail': False,  # Skip thumbnail - not needed
            'writeinfojson': False,  # Skip verbose JSON - we extract what we need
            'extractaudio': False,
            'merge_output_format': 'mp4',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    
    # Run synchronous yt-dlp in thread pool
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _download_sync)
    
    # Collect downloaded files
    files = []
    for file in os.listdir(temp_dir):
        if file.endswith(('.mp4', '.webm', '.mkv')):
            files.append(os.path.join(temp_dir, file))
    
    # Extract metadata
    description = info.get('description', '') if info else ''
    tags = info.get('tags', []) if info else []
    title = info.get('title', '') if info else ''
    
    return {
        'files': files,
        'tags': tags,
        'description': description or title,
        'source': 'youtube' if 'youtube' in url else 'tiktok',
        'temp_dir': temp_dir,
        'link': url
    }

async def download_instagram(url: str, temp_dir: str) -> Dict:
    """
    Download media from Instagram using instaloader.
    
    Args:
        url: Instagram post URL
        temp_dir: Temporary directory for downloads
        
    Returns:
        Dict with file paths, metadata, and temp directory
    """
    def _download_sync():
        try:
            # Sanitize URL - remove query parameters
            clean_url = url.split('?')[0]
            
            # Try using instaloader library first
            L = instaloader.Instaloader(
                dirname_pattern=temp_dir,
                filename_pattern='{date_utc:%Y-%m-%d_%H-%M-%S}_UTC_{shortcode}',
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False
            )
            
            # Extract shortcode from clean URL
            shortcode = clean_url.split('/')[-2] if clean_url.endswith('/') else clean_url.split('/')[-1]
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            # Download the post (this will download all carousel items)
            L.download_post(post, target=temp_dir)
            
            # Get all downloaded files and filter for videos only
            all_files = _get_instagram_files(temp_dir)
            video_files = [f for f in all_files if f.endswith('.mp4')]
            
            logger.info(f"Downloaded {len(video_files)} video files from Instagram")
            
            # If no videos found, try downloading with CLI which might get all carousel items
            if not video_files:
                logger.info("No videos found with library method, trying CLI for carousel items")
                
            
            return {
                'caption': post.caption or '',
                'hashtags': [tag for tag in post.caption.split() if tag.startswith('#')] if post.caption else [],
                'files': video_files if video_files else all_files,
                'is_carousel': len(video_files) > 1 if video_files else len(all_files) > 1,
                'carousel_count': len(video_files) if video_files else len(all_files)
            }
            
        except Exception as e:
            logger.error(f"Instagram download failed: {str(e)}")
            raise
    
    # Run synchronous instaloader in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _download_sync)
    
    return {
        'files': result['files'],
        'tags': result['hashtags'],
        'description': result['caption'],
        'source': 'instagram',
        'temp_dir': temp_dir,
        'link': url
    }

def _get_instagram_files(temp_dir: str) -> List[str]:
    """
    Get list of downloaded Instagram files.
    
    Args:
        temp_dir: Directory containing downloaded files
        
    Returns:
        List of file paths
    """
    files = []
    for file in os.listdir(temp_dir):
        if file.endswith(('.mp4', '.jpg', '.jpeg', '.png')):
            files.append(os.path.join(temp_dir, file))
    return files

def _extract_caption_from_files(temp_dir: str) -> str:
    """
    Extract caption from downloaded Instagram files.
    
    Args:
        temp_dir: Directory containing downloaded files
        
    Returns:
        Caption text or empty string
    """
    # Look for caption in any text files or try to extract from filename
    for file in os.listdir(temp_dir):
        if file.endswith('.txt'):
            try:
                with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except:
                continue
    
    # If no caption file found, return empty string
    return ""
