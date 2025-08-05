#!/usr/bin/env python3
"""
Unit tests for configuration system
"""

import unittest
import os
import tempfile
from unittest.mock import patch
import sys
sys.path.append('..')

from config import BotConfig, YouTubeConfig, config, youtube_config

class TestBotConfig(unittest.TestCase):
    """Test BotConfig class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_config = BotConfig(
            token="test_token"
        )
    
    def test_config_initialization(self):
        """Test config initialization with default values"""
        self.assertEqual(self.test_config.token, "test_token")
        self.assertEqual(self.test_config.command_prefix, "?")
        self.assertEqual(self.test_config.default_balance, 100)
        self.assertEqual(self.test_config.gacha_cost, 10)
        self.assertEqual(self.test_config.max_daily_bet, 1000)
        self.assertEqual(self.test_config.gambling_cooldown, 30)
        self.assertEqual(self.test_config.max_queue_size, 50)
        self.assertEqual(self.test_config.max_volume, 1.0)
        self.assertEqual(self.test_config.default_volume, 0.5)
    
    def test_person_pool_default(self):
        """Test default person pool"""
        expected_pool = ["Alex", "Ryan", "Priscilla", "Jackson", "Holli", "Nathan"]
        self.assertEqual(self.test_config.person_pool, expected_pool)
    
    def test_adjectives_pool_default(self):
        """Test default adjectives pool"""
        expected_adjectives = [
            "Default", "Homeless", "Dumb", "Boring", "Sleepy", "Hungry", 
            "Hairy", "Stinky", "Silly", "Emo", "K/DA", "Edgelord", 
            "Roided", "Zombie", "Smoll", "Tilted", "Large", 
            "Biblically Accurate", "Skibidi", "Goated"
        ]
        self.assertEqual(self.test_config.adjectives_pool, expected_adjectives)
    
    def test_custom_person_pool(self):
        """Test custom person pool"""
        custom_pool = ["Test1", "Test2"]
        config_with_custom = BotConfig(
            token="test",
            person_pool=custom_pool
        )
        self.assertEqual(config_with_custom.person_pool, custom_pool)
    
    def test_custom_adjectives_pool(self):
        """Test custom adjectives pool"""
        custom_adjectives = ["Test1", "Test2"]
        config_with_custom = BotConfig(
            token="test",
            adjectives_pool=custom_adjectives
        )
        self.assertEqual(config_with_custom.adjectives_pool, custom_adjectives)
    
    @patch.dict(os.environ, {
        'DISCORD_TOKEN': 'env_test_token'
    })
    def test_from_env(self):
        """Test creating config from environment variables"""
        env_config = BotConfig.from_env()
        self.assertEqual(env_config.token, 'env_test_token')

class TestYouTubeConfig(unittest.TestCase):
    """Test YouTubeConfig class"""
    
    def setUp(self):
        """Set up test environment"""
        self.yt_config = YouTubeConfig()
    
    def test_default_values(self):
        """Test default YouTube config values"""
        self.assertEqual(self.yt_config.format, 'bestaudio/best')
        self.assertTrue(self.yt_config.restrictfilenames)
        self.assertTrue(self.yt_config.noplaylist)
        self.assertTrue(self.yt_config.nocheckcertificate)
        self.assertFalse(self.yt_config.ignoreerrors)
        self.assertFalse(self.yt_config.logtostderr)
        self.assertTrue(self.yt_config.quiet)
        self.assertTrue(self.yt_config.no_warnings)
        self.assertEqual(self.yt_config.default_search, 'auto')
        self.assertEqual(self.yt_config.source_address, '0.0.0.0')
    
    def test_to_dict(self):
        """Test to_dict property"""
        config_dict = self.yt_config.to_dict
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict['format'], 'bestaudio/best')
        self.assertTrue(config_dict['restrictfilenames'])
        self.assertIn('http_headers', config_dict)
        self.assertIn('User-Agent', config_dict['http_headers'])

class TestGlobalConfig(unittest.TestCase):
    """Test global config instances"""
    
    def test_config_instance(self):
        """Test global config instance exists"""
        self.assertIsInstance(config, BotConfig)
        self.assertIsInstance(youtube_config, YouTubeConfig)
    
    def test_config_attributes(self):
        """Test global config has required attributes"""
        required_attrs = [
            'token', 'spotify_client_id', 'spotify_client_secret',
            'command_prefix', 'default_balance', 'gacha_cost',
            'max_daily_bet', 'gambling_cooldown', 'max_queue_size',
            'max_volume', 'default_volume', 'person_pool', 'adjectives_pool'
        ]
        
        for attr in required_attrs:
            self.assertTrue(hasattr(config, attr), f"Config missing attribute: {attr}")

if __name__ == '__main__':
    unittest.main() 