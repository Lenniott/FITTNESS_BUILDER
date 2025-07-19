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
    temp_dir = tempfile.mkdtemp(prefix="gilgamesh_download_", dir="app/temp")
    
    try:
        # Determine source and delegate to appropriate downloader
        if "youtube.com" in url or "youtu.be" in url or "tiktok.com" in url:
            return await download_youtube(url, temp_dir)
        elif "instagram.com" in url:
            # For Instagram, check if it's a carousel and download all items
            if '/p/' in url and 'img_index=' not in url:
                return await download_instagram_carousel(url, temp_dir)
            else:
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
                return _download_via_cli(clean_url, temp_dir)
            
            return {
                'caption': post.caption or '',
                'hashtags': [tag for tag in post.caption.split() if tag.startswith('#')] if post.caption else [],
                'files': video_files if video_files else all_files,
                'is_carousel': len(video_files) > 1 if video_files else len(all_files) > 1,
                'carousel_count': len(video_files) if video_files else len(all_files)
            }
            
        except Exception as e:
            logger.warning(f"Instaloader library failed: {str(e)}, trying CLI fallback")
            return _download_via_cli(clean_url, temp_dir)
    
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

async def download_instagram_carousel(url: str, temp_dir: str) -> Dict:
    """
    Download all carousel items from Instagram properly.
    
    Args:
        url: Instagram carousel URL
        temp_dir: Temporary directory for downloads
        
    Returns:
        Dict with all carousel files, metadata, and temp directory
    """
    def _get_carousel_count_sync():
        """Get the actual number of carousel items using instaloader."""
        try:
            clean_url = url.split('?')[0]
            L = instaloader.Instaloader()
            shortcode = clean_url.split('/')[-2] if clean_url.endswith('/') else clean_url.split('/')[-1]
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            # Get the actual number of carousel items
            sidecar_nodes = list(post.get_sidecar_nodes()) if hasattr(post, 'get_sidecar_nodes') else []
            carousel_count = len(sidecar_nodes) if sidecar_nodes else 1
            if post.is_video and carousel_count == 0:
                carousel_count = 1  # Single video
                
            logger.info(f"Detected {carousel_count} carousel items for {shortcode}")
            return carousel_count
            
        except Exception as e:
            logger.warning(f"Could not detect carousel count: {str(e)}")
            return 1  # Fallback to single item
    
    # First, detect the actual carousel count
    loop = asyncio.get_event_loop()
    carousel_count = await loop.run_in_executor(None, _get_carousel_count_sync)
    
    all_files = []
    caption = ""
    hashtags = []
    
    # Download each carousel item individually
    for carousel_index in range(1, carousel_count + 1):
        try:
            logger.info(f"Downloading carousel item {carousel_index}/{carousel_count}")
            
            # Create a separate temp directory for each carousel item to avoid conflicts
            item_temp_dir = os.path.join(temp_dir, f"item_{carousel_index}")
            os.makedirs(item_temp_dir, exist_ok=True)
            
            # Download this specific carousel item only
            result = await download_instagram_single_item(url, item_temp_dir, carousel_index)
            
            if result['files']:
                all_files.extend(result['files'])
                if not caption and result.get('description'):
                    caption = result['description']
                if not hashtags and result.get('tags'):
                    hashtags = result['tags']
                logger.info(f"Successfully downloaded carousel item {carousel_index}")
            else:
                logger.warning(f"No files found for carousel item {carousel_index}")
                
        except Exception as e:
            logger.error(f"Failed to download carousel item {carousel_index}: {str(e)}")
    
    logger.info(f"Downloaded {len(all_files)} total carousel items")
    
    return {
        'files': all_files,
        'tags': hashtags,
        'description': caption,
        'source': 'instagram',
        'temp_dir': temp_dir,
        'link': url,
        'is_carousel': len(all_files) > 1,
        'carousel_count': len(all_files)
    }

async def download_instagram_single_item(url: str, temp_dir: str, carousel_index: int = 1) -> Dict:
    """
    Download a single carousel item from Instagram.
    
    Args:
        url: Instagram URL
        temp_dir: Temporary directory for downloads
        carousel_index: Index of the carousel item to download
        
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
            
            # Since instaloader downloads all carousel items, we need to identify which one
            # corresponds to our carousel_index. We'll use a simple approach: take the nth file
            if video_files and carousel_index <= len(video_files):
                # Take the specific carousel item (1-indexed)
                selected_file = video_files[carousel_index - 1]
                video_files = [selected_file]
                logger.info(f"Selected carousel item {carousel_index}: {selected_file}")
            elif video_files:
                # If we have fewer files than expected, just take the first one
                logger.warning(f"Expected carousel item {carousel_index}, but only found {len(video_files)} files")
                video_files = [video_files[0]]
            
            logger.info(f"Downloaded {len(video_files)} video files for carousel item {carousel_index}")
            
            return {
                'caption': post.caption or '',
                'hashtags': [tag for tag in post.caption.split() if tag.startswith('#')] if post.caption else [],
                'files': video_files,
                'is_carousel': False,  # This is a single item
                'carousel_count': 1
            }
            
        except Exception as e:
            logger.warning(f"Instaloader library failed: {str(e)}, trying CLI fallback")
            return _download_via_cli(url, temp_dir)
    
    # Run the download in thread pool
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

def _download_via_cli(url: str, temp_dir: str) -> Dict:
    """
    Fallback method using instaloader CLI.
    
    Args:
        url: Instagram post URL (should be sanitized)
        temp_dir: Temporary directory for downloads
        
    Returns:
        Dict with file paths and metadata
    """
    try:
        # Use instaloader CLI as fallback with simplified flags
        cmd = [
            'instaloader',
            '--dirname-pattern', temp_dir,
            '--filename-pattern', '{date_utc:%Y-%m-%d_%H-%M-%S}_UTC_{shortcode}',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"Instaloader CLI failed: {result.stderr}")
        
        # Extract metadata from the downloaded files
        files = _get_instagram_files(temp_dir)
        video_files = [f for f in files if f.endswith('.mp4')]
        caption = _extract_caption_from_files(temp_dir)
        hashtags = [tag for tag in caption.split() if tag.startswith('#')] if caption else []
        
        return {
            'caption': caption,
            'hashtags': hashtags,
            'files': video_files if video_files else files,
            'is_carousel': len(video_files) > 1 if video_files else len(files) > 1,
            'carousel_count': len(video_files) if video_files else len(files)
        }
        
    except Exception as e:
        logger.error(f"Instaloader CLI fallback failed: {str(e)}")
        raise

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
