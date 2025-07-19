"""
URL processing utilities for handling carousel detection and URL normalization.
"""

import re
from typing import Tuple, List
from urllib.parse import urlparse, parse_qs

def normalize_url(url: str) -> str:
    """
    Normalize URL by removing query parameters.
    
    Args:
        url: Original URL with potential query parameters
        
    Returns:
        Normalized URL without query parameters
    """
    # Remove query parameters
    if '?' in url:
        return url.split('?')[0]
    return url

def extract_carousel_info(url: str) -> Tuple[str, int]:
    """
    Extract carousel index from URL and normalize it.
    
    Args:
        url: Original URL (may contain carousel index)
        
    Returns:
        Tuple of (normalized_url, carousel_index)
    """
    normalized_url = normalize_url(url)
    
    # Extract carousel index from Instagram URLs
    if 'instagram.com' in url:
        # Check for img_index parameter
        if 'img_index=' in url:
            try:
                # Parse query parameters
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                carousel_index = int(params.get('img_index', [1])[0])
                return normalized_url, carousel_index
            except (ValueError, IndexError):
                pass
    
    # Default to index 1 for single videos
    return normalized_url, 1

def detect_carousel_items(url: str) -> List[Tuple[str, int]]:
    """
    Detect if URL is a carousel and return all items.
    
    Args:
        url: Original URL
        
    Returns:
        List of (normalized_url, carousel_index) tuples
    """
    normalized_url, carousel_index = extract_carousel_info(url)
    
    # For Instagram carousels, we'll process all items
    # For single videos, just return the one item
    if 'instagram.com' in url and '/p/' in url:
        # This is an Instagram post - could be carousel
        # We'll let the downloader determine how many items
        return [(normalized_url, carousel_index)]
    else:
        # Single video platforms
        return [(normalized_url, 1)]

def is_instagram_carousel(url: str) -> bool:
    """
    Check if Instagram URL is likely a carousel.
    
    Args:
        url: Instagram URL
        
    Returns:
        True if URL contains carousel indicators
    """
    return 'img_index=' in url or '/p/' in url

def is_single_video(url: str) -> bool:
    """
    Check if URL is for a single video (not carousel).
    
    Args:
        url: Video URL
        
    Returns:
        True if single video
    """
    # YouTube, TikTok, Instagram reels are always single videos
    if any(domain in url for domain in ['youtube.com', 'youtu.be', 'tiktok.com']):
        return True
    
    # Instagram reels are single videos
    if '/reel/' in url:
        return True
    
    # Instagram posts with img_index=1 are single videos
    if 'instagram.com' in url and 'img_index=1' in url:
        return True
    
    return False 