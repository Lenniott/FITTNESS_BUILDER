"""
Unit tests for the downloader component.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.downloaders import (
    download_media_and_metadata,
    download_youtube,
    download_instagram,
    _get_instagram_files,
    _extract_caption_from_files
)

class TestDownloaders:
    """Test cases for downloader functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir
    
    @pytest.mark.asyncio
    async def test_download_media_and_metadata_youtube(self, temp_dir):
        """Test downloading from YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('app.services.downloaders.download_youtube') as mock_download:
            mock_download.return_value = {
                'files': ['/tmp/video.mp4'],
                'tags': ['test'],
                'description': 'Test video',
                'source': 'youtube',
                'temp_dir': temp_dir,
                'link': url
            }
            
            result = await download_media_and_metadata(url)
            
            assert result['source'] == 'youtube'
            assert result['files'] == ['/tmp/video.mp4']
            assert result['tags'] == ['test']
            assert result['description'] == 'Test video'
            assert result['link'] == url
    
    @pytest.mark.asyncio
    async def test_download_media_and_metadata_instagram(self, temp_dir):
        """Test downloading from Instagram URL."""
        url = "https://www.instagram.com/p/ABC123/"
        
        with patch('app.services.downloaders.download_instagram') as mock_download:
            mock_download.return_value = {
                'files': ['/tmp/image.jpg'],
                'tags': ['#test'],
                'description': 'Test post #test',
                'source': 'instagram',
                'temp_dir': temp_dir,
                'link': url
            }
            
            result = await download_media_and_metadata(url)
            
            assert result['source'] == 'instagram'
            assert result['files'] == ['/tmp/image.jpg']
            assert result['tags'] == ['#test']
            assert result['description'] == 'Test post #test'
            assert result['link'] == url
    
    @pytest.mark.asyncio
    async def test_download_media_and_metadata_unsupported_url(self):
        """Test error handling for unsupported URLs."""
        url = "https://unsupported-platform.com/video"
        
        with pytest.raises(ValueError, match="Unsupported URL domain"):
            await download_media_and_metadata(url)
    
    @pytest.mark.asyncio
    async def test_download_youtube_success(self, temp_dir):
        """Test successful YouTube download."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Create mock video file
        video_file = os.path.join(temp_dir, "test_video.mp4")
        with open(video_file, 'w') as f:
            f.write("mock video content")
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_instance = MagicMock()
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            mock_instance.extract_info.return_value = {
                'description': 'Test video description',
                'tags': ['test', 'video'],
                'title': 'Test Video Title'
            }
            
            result = await download_youtube(url, temp_dir)
            
            assert result['source'] == 'youtube'
            assert len(result['files']) > 0
            assert result['description'] == 'Test video description'
            assert result['tags'] == ['test', 'video']
    
    @pytest.mark.asyncio
    async def test_download_instagram_success(self, temp_dir):
        """Test successful Instagram download."""
        url = "https://www.instagram.com/p/ABC123/"
        
        # Create mock image file
        image_file = os.path.join(temp_dir, "test_image.jpg")
        with open(image_file, 'w') as f:
            f.write("mock image content")
        
        with patch('instaloader.Instaloader') as mock_loader:
            mock_instance = MagicMock()
            mock_loader.return_value = mock_instance
            
            mock_post = MagicMock()
            mock_post.caption = "Test post #test #instagram"
            
            with patch('instaloader.Post.from_shortcode') as mock_post_class:
                mock_post_class.return_value = mock_post
                
                result = await download_instagram(url, temp_dir)
                
                assert result['source'] == 'instagram'
                assert len(result['files']) > 0
                assert result['description'] == "Test post #test #instagram"
                assert '#test' in result['tags']
                assert '#instagram' in result['tags']
    
    def test_get_instagram_files(self, temp_dir):
        """Test getting Instagram files from directory."""
        # Create test files
        files_to_create = [
            'video.mp4',
            'image.jpg',
            'thumbnail.png',
            'metadata.txt',
            'ignore.txt'
        ]
        
        for file_name in files_to_create:
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        result = _get_instagram_files(temp_dir)
        
        # Should only return media files, not text files
        assert len(result) == 3  # mp4, jpg, png
        assert any('video.mp4' in f for f in result)
        assert any('image.jpg' in f for f in result)
        assert any('thumbnail.png' in f for f in result)
        assert not any('metadata.txt' in f for f in result)
    
    def test_extract_caption_from_files(self, temp_dir):
        """Test extracting caption from files."""
        # Create caption file
        caption_file = os.path.join(temp_dir, "caption.txt")
        with open(caption_file, 'w', encoding='utf-8') as f:
            f.write("This is a test caption with #hashtags")
        
        result = _extract_caption_from_files(temp_dir)
        
        assert result == "This is a test caption with #hashtags"
    
    def test_extract_caption_no_file(self, temp_dir):
        """Test extracting caption when no caption file exists."""
        result = _extract_caption_from_files(temp_dir)
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_download_youtube_error_handling(self, temp_dir):
        """Test YouTube download error handling."""
        url = "https://www.youtube.com/watch?v=invalid"
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_instance = MagicMock()
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            mock_instance.extract_info.side_effect = Exception("Download failed")
            
            with pytest.raises(Exception, match="Download failed"):
                await download_youtube(url, temp_dir)
    
    @pytest.mark.asyncio
    async def test_download_instagram_fallback(self, temp_dir):
        """Test Instagram download with library fallback."""
        url = "https://www.instagram.com/p/ABC123/"
        
        with patch('instaloader.Instaloader') as mock_loader:
            mock_instance = MagicMock()
            mock_loader.return_value = mock_instance
            
            # Make library fail
            mock_instance.download_post.side_effect = Exception("Library failed")
            
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value.returncode = 0
                mock_subprocess.return_value.stderr = ""
                
                # Create mock files for CLI fallback
                image_file = os.path.join(temp_dir, "test_image.jpg")
                with open(image_file, 'w') as f:
                    f.write("mock image content")
                
                result = await download_instagram(url, temp_dir)
                
                assert result['source'] == 'instagram'
                assert len(result['files']) > 0 