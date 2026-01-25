#!/usr/bin/env python3
"""
Unit tests for cache manager
"""

import unittest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock, AsyncMock
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import CacheManager
from utils.database import DatabaseManager


class TestCacheManager(unittest.TestCase):
    """Test CacheManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        self.audio_dir = os.path.join(self.cache_dir, "audio")
        self.normalized_dir = os.path.join(self.cache_dir, "normalized")
        
        os.makedirs(self.audio_dir)
        os.makedirs(self.normalized_dir)
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        
        # Create cache manager with mocked config
        with patch('utils.cache_manager.config') as mock_config:
            mock_config.cache_directory = self.cache_dir
            mock_config.cache_enabled = True
            mock_config.cache_max_size = 100
            mock_config.cache_max_age = 30
            self.cache_manager = CacheManager()
            self.cache_manager.cache_dir = self.cache_dir
            self.cache_manager.audio_dir = self.audio_dir
            self.cache_manager.normalized_dir = self.normalized_dir
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_extract_youtube_id_standard_url(self):
        """Test extracting YouTube ID from standard URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        youtube_id = self.cache_manager.extract_youtube_id(url)
        self.assertEqual(youtube_id, "dQw4w9WgXcQ")
    
    def test_extract_youtube_id_short_url(self):
        """Test extracting YouTube ID from short URL"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        youtube_id = self.cache_manager.extract_youtube_id(url)
        self.assertEqual(youtube_id, "dQw4w9WgXcQ")
    
    def test_extract_youtube_id_embed_url(self):
        """Test extracting YouTube ID from embed URL"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        youtube_id = self.cache_manager.extract_youtube_id(url)
        self.assertEqual(youtube_id, "dQw4w9WgXcQ")
    
    def test_extract_youtube_id_with_params(self):
        """Test extracting YouTube ID from URL with additional parameters"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"
        youtube_id = self.cache_manager.extract_youtube_id(url)
        self.assertEqual(youtube_id, "dQw4w9WgXcQ")
    
    def test_extract_youtube_id_invalid_url(self):
        """Test extracting YouTube ID from invalid URL"""
        url = "https://www.example.com/video"
        youtube_id = self.cache_manager.extract_youtube_id(url)
        self.assertIsNone(youtube_id)
    
    def test_extract_youtube_id_none_input(self):
        """Test extracting YouTube ID from None"""
        youtube_id = self.cache_manager.extract_youtube_id(None)
        self.assertIsNone(youtube_id)
    
    def test_get_cache_file_path_audio(self):
        """Test getting cache file path for audio"""
        youtube_id = "testid12345"
        expected_path = os.path.join(self.normalized_dir, "testid12345_normalized.mp3")
        
        # Need to reset the normalized_dir since it was set during __init__
        self.cache_manager.normalized_dir = self.normalized_dir
        actual_path = self.cache_manager.get_cache_file_path(youtube_id, is_normalized=True)
        self.assertEqual(actual_path, expected_path)
    
    def test_get_cache_file_path_normalized(self):
        """Test getting cache file path for normalized audio"""
        youtube_id = "testid12345"
        expected_path = os.path.join(self.audio_dir, "testid12345.mp3")
        
        self.cache_manager.audio_dir = self.audio_dir
        actual_path = self.cache_manager.get_cache_file_path(youtube_id, is_normalized=False)
        self.assertEqual(actual_path, expected_path)


class TestCacheManagerAsync(unittest.TestCase):
    """Async tests for CacheManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        self.audio_dir = os.path.join(self.cache_dir, "audio")
        self.normalized_dir = os.path.join(self.cache_dir, "normalized")
        
        os.makedirs(self.audio_dir)
        os.makedirs(self.normalized_dir)
        
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        
        with patch('utils.cache_manager.config') as mock_config:
            mock_config.cache_directory = self.cache_dir
            mock_config.cache_enabled = True
            mock_config.cache_max_size = 100
            mock_config.cache_max_age = 30
            self.cache_manager = CacheManager()
            self.cache_manager.cache_dir = self.cache_dir
            self.cache_manager.audio_dir = self.audio_dir
            self.cache_manager.normalized_dir = self.normalized_dir
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def _run_async(self, coro):
        """Helper to run async tests"""
        return asyncio.get_event_loop().run_until_complete(coro)
    
    def test_get_cached_song_not_found(self):
        """Test getting cached song that doesn't exist"""
        with patch('utils.cache_manager.db') as mock_db:
            mock_db.get_cached_song = AsyncMock(return_value=None)
            
            result = self._run_async(
                self.cache_manager.get_cached_song("https://www.youtube.com/watch?v=test123")
            )
            self.assertIsNone(result)
    
    def test_get_cached_song_found(self):
        """Test getting cached song that exists"""
        cached_info = {
            'youtube_id': 'test123456',
            'title': 'Test Song',
            'duration': 180,
            'filename': 'test.mp3',
            'normalized_filename': 'test_normalized.mp3'
        }
        
        # Create the actual file
        test_file = os.path.join(self.audio_dir, 'test.mp3')
        with open(test_file, 'w') as f:
            f.write('test')
        
        with patch('utils.cache_manager.db') as mock_db:
            mock_db.get_cached_song = AsyncMock(return_value=cached_info)
            mock_db.update_cache_access = AsyncMock()
            
            result = self._run_async(
                self.cache_manager.get_cached_song("https://www.youtube.com/watch?v=test123456")
            )
            
            self.assertIsNotNone(result)
            self.assertEqual(result['title'], 'Test Song')
    
    def test_get_cached_song_file_missing(self):
        """Test getting cached song when file is missing"""
        cached_info = {
            'youtube_id': 'test123456',
            'title': 'Test Song',
            'duration': 180,
            'filename': 'missing.mp3',
            'normalized_filename': None
        }
        
        with patch('utils.cache_manager.db') as mock_db:
            mock_db.get_cached_song = AsyncMock(return_value=cached_info)
            mock_db.remove_cached_song = AsyncMock()
            
            result = self._run_async(
                self.cache_manager.get_cached_song("https://www.youtube.com/watch?v=test123456")
            )
            
            self.assertIsNone(result)
            mock_db.remove_cached_song.assert_called_once_with('test123456')
    
    def test_add_to_cache_disabled(self):
        """Test adding to cache when cache is disabled"""
        with patch('utils.cache_manager.config') as mock_config:
            mock_config.cache_enabled = False
            
            result = self._run_async(
                self.cache_manager.add_to_cache("test123", "Test Song", 180, "test.mp3")
            )
            
            self.assertEqual(result, {'success': False})
    
    def test_cleanup_cache_disabled(self):
        """Test cleanup when cache is disabled"""
        with patch('utils.cache_manager.config') as mock_config:
            mock_config.cache_enabled = False
            
            result = self._run_async(self.cache_manager.cleanup_cache())
            
            self.assertEqual(result, {'cleaned': 0, 'freed_mb': 0})
    
    def test_get_cache_stats_disabled(self):
        """Test getting stats when cache is disabled"""
        with patch('utils.cache_manager.config') as mock_config:
            mock_config.cache_enabled = False
            
            result = self._run_async(self.cache_manager.get_cache_stats())
            
            self.assertEqual(result, {'enabled': False})


if __name__ == '__main__':
    unittest.main()
