# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Integration tests for downloader component (`tests/integration/test_downloader_integration.py`)
- Real YouTube video download testing with actual URLs
- URL validation integration tests
- Error handling integration tests

### Fixed
- Installed ffmpeg dependency for video processing
- Fixed downloader to handle video format merging properly
- Improved error handling for invalid URLs
- Optimized YouTube downloader to skip unnecessary files (thumbnails, verbose JSON)
- Restored subtitle/transcript downloads for fitness video analysis

### Tested
- All 13 tests passing (10 unit tests + 3 integration tests)
- YouTube download functionality working with real videos
- URL detection and validation working correctly
- Error handling for unsupported domains working

### Dependencies
- Added ffmpeg via Homebrew for video processing
- Installed pytest, pytest-asyncio, pytest-mock for testing
- Installed yt-dlp and instaloader for media downloading

## [Initial] - 2025-01-18

### Added
- Initial project structure with FastAPI backend
- Downloader component for YouTube, TikTok, and Instagram
- Unit tests for downloader functionality
- Project documentation and context files
