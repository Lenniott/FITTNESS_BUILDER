#!/usr/bin/env python3
"""
Simple test script to verify downloader functionality.
Run this to test the downloader with real URLs.
"""

import asyncio
import os
import sys
from app.services.downloaders import download_media_and_metadata

async def test_downloader():
    """Test the downloader with sample URLs."""
    
    # Test URLs (replace with real URLs for testing)
    test_urls = [
        # "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # YouTube
        # "https://www.instagram.com/p/ABC123/",  # Instagram
        # "https://www.tiktok.com/@user/video/1234567890",  # TikTok
    ]
    
    print("Downloader Test Script")
    print("=" * 50)
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            result = await download_media_and_metadata(url)
            
            print(f"✅ Success!")
            print(f"   Source: {result['source']}")
            print(f"   Files: {len(result['files'])} files")
            print(f"   Tags: {result['tags']}")
            print(f"   Description: {result['description'][:100]}...")
            print(f"   Temp Dir: {result['temp_dir']}")
            
            # List files in temp directory
            if os.path.exists(result['temp_dir']):
                print(f"   Files in temp directory:")
                for file in os.listdir(result['temp_dir']):
                    file_path = os.path.join(result['temp_dir'], file)
                    size = os.path.getsize(file_path)
                    print(f"     - {file} ({size} bytes)")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Test completed. Check app/temp/ for downloaded files.")

if __name__ == "__main__":
    # Ensure temp directory exists
    os.makedirs("storage/temp", exist_ok=True)
    
    # Run the test
    asyncio.run(test_downloader()) 