#!/usr/bin/env python3
"""
Integration tests for the complete bot system
"""

import unittest
import asyncio
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.append('..')

from config import config
from utils.database import DatabaseManager
from games.gambling import GamblingManager, HigherLowerGame, SlotMachine, AlexRoulette
from games.gacha import GachaSystem
from music.player import MusicPlayer, Track
from utils.helpers import validate_youtube_url, validate_bet_amount, format_balance

class TestBotIntegration(unittest.TestCase):
    """Integration tests for the complete bot system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        
        # Initialize all systems
        self.gambling_manager = GamblingManager()
        self.higher_lower_game = HigherLowerGame()
        self.slot_machine = SlotMachine()
        self.alex_roulette = AlexRoulette()
        self.gacha_system = GachaSystem()
        self.music_player = MusicPlayer()
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_complete_user_workflow(self):
        """Test a complete user workflow"""
        user_id = "test_user_123"
        
        # 1. Check initial balance
        balance = await self.db_manager.get_balance(user_id)
        self.assertEqual(balance, config.default_balance)
        
        # 2. Play slots
        with patch.object(self.db_manager, 'update_balance', return_value=95):
            with patch.object(self.db_manager, 'record_gambling'):
                slot_result = await self.slot_machine.spin(user_id, 5)
                self.assertIn('grid', slot_result)
                self.assertIn('win_amount', slot_result)
                self.assertIn('new_balance', slot_result)
        
        # 3. Play higher/lower game
        game_result = await self.higher_lower_game.start_game(user_id, 10)
        self.assertIn('current_number', game_result)
        
        # Process the game
        with patch.object(self.db_manager, 'update_balance', return_value=85):
            with patch.object(self.db_manager, 'record_gambling'):
                guess_result = await self.higher_lower_game.process_guess(user_id, "higher")
                self.assertIn('win', guess_result)
                self.assertIn('next_number', guess_result)
        
        # 4. Pull gacha
        with patch.object(self.db_manager, 'add_gacha_item'):
            gacha_result = await self.gacha_system.pull(user_id)
            self.assertIn('character', gacha_result)
            self.assertIn('rarity', gacha_result)
        
        # 5. Check gambling stats
        stats = await self.db_manager.get_gambling_stats(user_id)
        self.assertIsInstance(stats, dict)
        self.assertIn('total_games', stats)
        self.assertIn('total_bet', stats)
        self.assertIn('total_won', stats)
    
    async def test_music_system_integration(self):
        """Test music system integration"""
        # Test track creation
        track = Track(
            title="Test Song",
            url="https://youtube.com/watch?v=test",
            duration=180,
            requester_id=123456,
            requester_name="TestUser",
            filename="test_song.mp3"
        )
        
        self.assertEqual(track.title, "Test Song")
        self.assertEqual(track.duration, 180)
        self.assertEqual(track.requester_name, "TestUser")
        
        # Test queue management
        self.music_player.add_track(track)
        self.assertEqual(len(self.music_player.queue), 1)
        
        # Test queue info
        queue_info = self.music_player.get_queue_info()
        self.assertIn('queue_length', queue_info)
        self.assertEqual(queue_info['queue_length'], 1)
        
        # Test queue tracks
        queue_tracks = self.music_player.get_queue_tracks()
        self.assertEqual(len(queue_tracks), 1)
        self.assertEqual(queue_tracks[0]['title'], "Test Song")
        
        # Test queue operations
        self.music_player.shuffle_queue()
        self.assertEqual(len(self.music_player.queue), 1)
        
        self.music_player.clear_queue()
        self.assertEqual(len(self.music_player.queue), 0)
    
    async def test_gambling_system_integration(self):
        """Test gambling system integration"""
        user_id = "gambling_test_user"
        
        # Test gambling limits
        can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, 50)
        self.assertTrue(can_gamble)
        self.assertEqual(error, "")
        
        # Test insufficient balance
        can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, 200)
        self.assertFalse(can_gamble)
        self.assertIn("don't have enough money", error)
        
        # Test daily limit
        with patch.object(self.db_manager, 'get_daily_bet_total', return_value=950):
            can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, 100)
            self.assertFalse(can_gamble)
            self.assertIn("Daily betting limit exceeded", error)
    
    async def test_gacha_system_integration(self):
        """Test gacha system integration"""
        user_id = "gacha_test_user"
        
        # Test multiple pulls
        for i in range(5):
            with patch.object(self.db_manager, 'add_gacha_item'):
                result = await self.gacha_system.pull(user_id)
                
                # Check result structure
                self.assertIn('character', result)
                self.assertIn('rarity', result)
                self.assertIn('pity_pulls', result)
                
                # Check character validity
                character = result['character']
                self.assertIn(character.name, config.person_pool)
                self.assertIn(character.adjective, config.adjectives_pool)
                self.assertIn(character.rarity, [2, 3, 4, 5])
        
        # Test pity system
        pity_info = self.gacha_system._get_pity_info(user_id)
        self.assertEqual(pity_info['pulls'], 5)
    
    async def test_database_integration(self):
        """Test database integration with all systems"""
        user_id = "db_test_user"
        
        # Test balance operations
        initial_balance = await self.db_manager.get_balance(user_id)
        self.assertEqual(initial_balance, config.default_balance)
        
        new_balance = await self.db_manager.update_balance(user_id, 50)
        self.assertEqual(new_balance, config.default_balance + 50)
        
        # Test gambling recording
        await self.db_manager.record_gambling(user_id, "slots", 10, 25)
        await self.db_manager.record_gambling(user_id, "gamble", 20, 0)
        
        # Test gambling stats
        stats = await self.db_manager.get_gambling_stats(user_id)
        self.assertEqual(stats['total_games'], 2)
        self.assertEqual(stats['total_bet'], 30)
        self.assertEqual(stats['total_won'], 25)
        self.assertEqual(stats['net_profit'], -5)
        
        # Test gacha inventory
        await self.db_manager.add_gacha_item(user_id, "TestChar", 3, "TestAdj")
        inventory = await self.db_manager.get_gacha_inventory(user_id)
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]['character_name'], "TestChar")
        self.assertEqual(inventory[0]['rarity'], 3)
        
        # Test daily limits
        daily_total = await self.db_manager.get_daily_bet_total(user_id)
        self.assertEqual(daily_total, 30)
        
        # Test griddy counts
        await self.db_manager.increment_griddy_count("TestName")
        count = await self.db_manager.get_griddy_count("TestName")
        self.assertEqual(count, 1)
    
    async def test_error_handling_integration(self):
        """Test error handling integration"""
        user_id = "error_test_user"
        
        # Test invalid bet amount
        bet_amount = validate_bet_amount("invalid", 100)
        self.assertIsNone(bet_amount)
        
        # Test valid bet amount
        bet_amount = validate_bet_amount("50", 100)
        self.assertEqual(bet_amount, 50)
        
        # Test "all" bet
        bet_amount = validate_bet_amount("all", 100)
        self.assertEqual(bet_amount, 100)
        
        # Test URL validation
        valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(valid_url))
        
        invalid_url = "https://www.google.com"
        self.assertFalse(validate_youtube_url(invalid_url))
    
    async def test_configuration_integration(self):
        """Test configuration integration"""
        # Test config values
        self.assertIsInstance(config.command_prefix, str)
        self.assertIsInstance(config.default_balance, int)
        self.assertIsInstance(config.gacha_cost, int)
        self.assertIsInstance(config.max_daily_bet, int)
        self.assertIsInstance(config.gambling_cooldown, int)
        
        # Test person pool
        self.assertIsInstance(config.person_pool, list)
        self.assertGreater(len(config.person_pool), 0)
        
        # Test adjectives pool
        self.assertIsInstance(config.adjectives_pool, list)
        self.assertGreater(len(config.adjectives_pool), 0)
        
        # Test music settings
        self.assertIsInstance(config.max_queue_size, int)
        self.assertIsInstance(config.max_volume, float)
        self.assertIsInstance(config.default_volume, float)
    
    async def test_helper_functions_integration(self):
        """Test helper functions integration"""
        # Test balance formatting
        formatted = format_balance(1234567)
        self.assertEqual(formatted, "$1,234,567")
        
        # Test duration formatting
        duration = "3:05"
        # This would be tested with actual duration formatting function
        
        # Test validation functions
        self.assertTrue(validate_youtube_url("https://www.youtube.com/watch?v=test"))
        self.assertFalse(validate_youtube_url("https://google.com"))
        
        # Test bet validation
        self.assertEqual(validate_bet_amount("50", 100), 50)
        self.assertIsNone(validate_bet_amount("150", 100))
        self.assertEqual(validate_bet_amount("all", 100), 100)

class TestSystemCompatibility(unittest.TestCase):
    """Test system compatibility and edge cases"""
    
    def test_config_compatibility(self):
        """Test configuration compatibility"""
        # Test that all required config values exist
        required_attrs = [
            'token', 'command_prefix', 'default_balance', 'gacha_cost',
            'max_daily_bet', 'gambling_cooldown', 'max_queue_size',
            'max_volume', 'default_volume', 'person_pool', 'adjectives_pool'
        ]
        
        for attr in required_attrs:
            self.assertTrue(hasattr(config, attr), f"Missing config attribute: {attr}")
    
    def test_database_schema_compatibility(self):
        """Test database schema compatibility"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            db_manager = DatabaseManager(temp_db.name)
            
            # Test that all required tables exist
            import sqlite3
            with sqlite3.connect(temp_db.name) as conn:
                cursor = conn.cursor()
                
                required_tables = [
                    'user_balances', 'gacha_inventory', 'gambling_history',
                    'daily_limits', 'griddy_counts'
                ]
                
                for table in required_tables:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    self.assertIsNotNone(cursor.fetchone(), f"Missing table: {table}")
        
        finally:
            if os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
    
    def test_gacha_character_compatibility(self):
        """Test gacha character compatibility"""
        gacha_system = GachaSystem()
        
        # Test that all characters are valid
        for character in gacha_system.characters:
            self.assertIn(character.name, config.person_pool)
            self.assertIn(character.adjective, config.adjectives_pool)
            self.assertIn(character.rarity, [2, 3, 4, 5])
            self.assertGreater(character.sell_value, 0)
            self.assertGreater(character.drop_rate, 0)
            self.assertLessEqual(character.drop_rate, 1)

if __name__ == '__main__':
    unittest.main() 