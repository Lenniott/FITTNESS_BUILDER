"""
Integration tests for the downloader component.
Tests real functionality with actual URLs.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
import tempfile
from app.services.downloaders import download_media_and_metadata

class TestDownloaderIntegration:
    """Integration tests for downloader functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_youtube_download_integration(self):
        """Test downloading a real YouTube video."""
        # Use a short, safe test video
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll (short, safe)
        
        try:
            result = await download_media_and_metadata(test_url)
            
            # Verify the result structure
            assert result['source'] == 'youtube'
            assert len(result['files']) > 0
            assert result['temp_dir'] is not None
            assert result['link'] == test_url
            
            # Verify files were actually downloaded
            for file_path in result['files']:
                assert os.path.exists(file_path)
                assert os.path.getsize(file_path) > 0
            
            print(f"✅ Integration test passed: Downloaded {len(result['files'])} files")
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_platform_downloads(self):
        """Test downloading videos from multiple platforms."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
            ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
            ("https://www.youtube.com/shorts/JWbqsdkXdKg", "youtube"),
            ("https://www.tiktok.com/@tiktok/video/7232182952942128430", "tiktok"),
            ("https://www.instagram.com/reel/DK4xvp2v9hC/", "instagram"),
            ("https://www.instagram.com/p/DLFuQo8RhzI/", "instagram"),
        ]
        
        results = []
        
        for url, expected_source in test_cases:
            try:
                print(f"\n📥 Downloading: {url}")
                result = await download_media_and_metadata(url)
                
                # Verify the result
                assert result['source'] == expected_source
                assert len(result['files']) > 0
                assert result['temp_dir'] is not None
                assert result['link'] == url
                
                # Show file details
                total_size = 0
                for file_path in result['files']:
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                        filename = os.path.basename(file_path)
                        print(f"   📄 {filename} ({size:,} bytes)")
                
                print(f"   💾 Total: {total_size:,} bytes")
                print(f"   ✅ {expected_source.upper()} download successful")
                
                results.append({
                    'url': url,
                    'source': expected_source,
                    'files_count': len(result['files']),
                    'total_size': total_size,
                    'success': True
                })
                
            except Exception as e:
                print(f"   ❌ Failed: {str(e)}")
                results.append({
                    'url': url,
                    'source': expected_source,
                    'error': str(e),
                    'success': False
                })
        
        # Summary
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"\n📊 DOWNLOAD SUMMARY:")
        print(f"✅ Successful: {len(successful)}/{len(test_cases)}")
        print(f"❌ Failed: {len(failed)}/{len(test_cases)}")
        
        if successful:
            total_size = sum(r['total_size'] for r in successful)
            print(f"💾 Total downloaded: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        
        if failed:
            print(f"\n❌ Failed downloads:")
            for result in failed:
                print(f"   {result['source']}: {result['url']} - {result['error']}")
        
        # Keep files for inspection
        print(f"\n🔍 All downloaded files preserved in app/temp/")
        print("   (Files will remain for manual inspection)")
        
        assert len(successful) > 0, "At least one download should succeed"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_integration(self):
        """Test error handling with invalid URLs."""
        invalid_urls = [
            "https://invalid-url.com",
            "https://instagram.com/p/",
        ]
        
        for url in invalid_urls:
            try:
                await download_media_and_metadata(url)
                pytest.fail(f"Should have failed for invalid URL: {url}")
            except Exception:
                # Expected to fail
                pass
        
        print("✅ Error handling integration test passed") 