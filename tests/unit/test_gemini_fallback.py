"""
Unit tests for Gemini API fallback mechanism.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from app.core.processor import VideoProcessor


class TestGeminiFallback:
    """Test Gemini API fallback mechanism."""
    
    def test_get_gemini_model_primary_success(self):
        """Test successful primary API key usage."""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_primary_key',
            'GEMINI_API_BACKUP_KEY': 'test_backup_key'
        }):
            processor = VideoProcessor()
            model = processor._get_gemini_model(use_backup=False)
            assert model is not None
    
    def test_get_gemini_model_backup_success(self):
        """Test successful backup API key usage."""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_primary_key',
            'GEMINI_API_BACKUP_KEY': 'test_backup_key'
        }):
            processor = VideoProcessor()
            model = processor._get_gemini_model(use_backup=True)
            assert model is not None
    
    def test_get_gemini_model_no_keys(self):
        """Test error when no API keys are set."""
        with patch.dict(os.environ, {}, clear=True):
            processor = VideoProcessor()
            with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable not set"):
                processor._get_gemini_model(use_backup=False)
    
    def test_get_gemini_model_no_backup_key(self):
        """Test error when backup key is not set."""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_primary_key'
        }):
            processor = VideoProcessor()
            with pytest.raises(ValueError, match="Both GEMINI_API_KEY and GEMINI_API_BACKUP_KEY environment variables not set"):
                processor._get_gemini_model(use_backup=True)
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_fallback_mechanism_integration(self, mock_model, mock_configure):
        """Test the complete fallback mechanism."""
        # Mock the Gemini model
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_primary_key',
            'GEMINI_API_BACKUP_KEY': 'test_backup_key'
        }):
            processor = VideoProcessor()
            
            # Test primary key usage
            model = processor._get_gemini_model(use_backup=False)
            assert model is not None
            mock_configure.assert_called_with(api_key='test_primary_key')
            
            # Test backup key usage
            model = processor._get_gemini_model(use_backup=True)
            assert model is not None
            mock_configure.assert_called_with(api_key='test_backup_key') 