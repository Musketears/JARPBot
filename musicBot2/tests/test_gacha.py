#!/usr/bin/env python3
"""
Unit tests for gacha system
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

from games.gacha import GachaSystem, GachaCharacter
from utils.database import DatabaseManager
from config import config

class TestGachaCharacter(unittest.TestCase):
    """Test GachaCharacter class"""
    
    def test_character_initialization(self):
        """Test character initialization"""
        character = GachaCharacter(
            name="TestChar",
            rarity=4,
            adjective="TestAdj",
            drop_rate=0.13,
            sell_value=50
        )
        
        self.assertEqual(character.name, "TestChar")
        self.assertEqual(character.rarity, 4)
        self.assertEqual(character.adjective, "TestAdj")
        self.assertEqual(character.drop_rate, 0.13)
        self.assertEqual(character.sell_value, 50)
    
    def test_character_string_representation(self):
        """Test character string representation"""
        character = GachaCharacter(
            name="TestChar",
            rarity=3,
            adjective="TestAdj",
            drop_rate=0.35,
            sell_value=15
        )
        
        expected = "3★ TestAdj TestChar"
        self.assertEqual(str(character), expected)

class TestGachaSystem(unittest.TestCase):
    """Test GachaSystem class"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.gacha_system = GachaSystem()
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_gacha_system_initialization(self):
        """Test gacha system initialization"""
        self.assertIsInstance(self.gacha_system.characters, list)
        self.assertIsInstance(self.gacha_system.rates, dict)
        self.assertIsInstance(self.gacha_system.pity_system, dict)
        
        # Check rates
        expected_rates = {2: 0.5, 3: 0.35, 4: 0.13, 5: 0.02}
        self.assertEqual(self.gacha_system.rates, expected_rates)
    
    def test_load_characters(self):
        """Test character loading"""
        characters = self.gacha_system._load_characters()
        
        self.assertIsInstance(characters, list)
        self.assertGreater(len(characters), 0)
        
        # Check character structure
        for character in characters:
            self.assertIsInstance(character, GachaCharacter)
            self.assertIn(character.name, config.person_pool)
            self.assertIn(character.adjective, config.adjectives_pool)
            self.assertIn(character.rarity, [2, 3, 4, 5])
            self.assertGreater(character.sell_value, 0)
    
    def test_get_pity_info_new_user(self):
        """Test pity info for new user"""
        user_id = "new_user"
        
        pity_info = self.gacha_system._get_pity_info(user_id)
        
        self.assertEqual(pity_info['pulls'], 0)
        self.assertEqual(pity_info['last_4_star'], 0)
        self.assertEqual(pity_info['last_5_star'], 0)
    
    def test_get_pity_info_existing_user(self):
        """Test pity info for existing user"""
        user_id = "existing_user"
        
        # Set up existing pity info
        self.gacha_system.pity_system[user_id] = {
            'pulls': 25,
            'last_4_star': 20,
            'last_5_star': 0
        }
        
        pity_info = self.gacha_system._get_pity_info(user_id)
        
        self.assertEqual(pity_info['pulls'], 25)
        self.assertEqual(pity_info['last_4_star'], 20)
        self.assertEqual(pity_info['last_5_star'], 0)
    
    def test_update_pity(self):
        """Test pity update"""
        user_id = "test_user"
        
        # Initial pity info
        self.gacha_system.pity_system[user_id] = {
            'pulls': 10,
            'last_4_star': 0,
            'last_5_star': 0
        }
        
        # Update pity for 3-star pull
        self.gacha_system._update_pity(user_id, 3)
        
        pity_info = self.gacha_system._get_pity_info(user_id)
        self.assertEqual(pity_info['pulls'], 11)
        self.assertEqual(pity_info['last_4_star'], 0)
        self.assertEqual(pity_info['last_5_star'], 0)
        
        # Update pity for 4-star pull
        self.gacha_system._update_pity(user_id, 4)
        
        pity_info = self.gacha_system._get_pity_info(user_id)
        self.assertEqual(pity_info['pulls'], 12)
        self.assertEqual(pity_info['last_4_star'], 12)
        self.assertEqual(pity_info['last_5_star'], 0)
        
        # Update pity for 5-star pull
        self.gacha_system._update_pity(user_id, 5)
        
        pity_info = self.gacha_system._get_pity_info(user_id)
        self.assertEqual(pity_info['pulls'], 13)
        self.assertEqual(pity_info['last_4_star'], 12)
        self.assertEqual(pity_info['last_5_star'], 13)
    
    def test_apply_pity_no_guarantee(self):
        """Test pity system with no guarantee"""
        user_id = "test_user"
        
        # Set up pity info with no guarantees
        self.gacha_system.pity_system[user_id] = {
            'pulls': 25,
            'last_4_star': 20,
            'last_5_star': 0
        }
        
        guaranteed_rarity = self.gacha_system._apply_pity(user_id)
        self.assertIsNone(guaranteed_rarity)
    
    def test_apply_pity_guaranteed_4_star(self):
        """Test pity system with guaranteed 4-star"""
        user_id = "test_user"
        
        # Set up pity info with guaranteed 4-star
        self.gacha_system.pity_system[user_id] = {
            'pulls': 70,
            'last_4_star': 20,  # 50 pulls without 4-star
            'last_5_star': 0
        }
        
        guaranteed_rarity = self.gacha_system._apply_pity(user_id)
        self.assertEqual(guaranteed_rarity, 4)
    
    def test_apply_pity_guaranteed_5_star(self):
        """Test pity system with guaranteed 5-star"""
        user_id = "test_user"
        
        # Set up pity info with guaranteed 5-star
        self.gacha_system.pity_system[user_id] = {
            'pulls': 120,
            'last_4_star': 70,
            'last_5_star': 20  # 100 pulls without 5-star
        }
        
        guaranteed_rarity = self.gacha_system._apply_pity(user_id)
        self.assertEqual(guaranteed_rarity, 5)
    
    async def test_pull_normal(self):
        """Test normal gacha pull"""
        user_id = "test_user"
        
        with patch.object(self.db_manager, 'add_gacha_item'):
            result = await self.gacha_system.pull(user_id)
            
            self.assertIn('character', result)
            self.assertIn('rarity', result)
            self.assertIn('pity_pulls', result)
            self.assertIn('next_guaranteed_4', result)
            self.assertIn('next_guaranteed_5', result)
            
            # Check character is valid
            character = result['character']
            self.assertIsInstance(character, GachaCharacter)
            self.assertIn(character.name, config.person_pool)
            self.assertIn(character.adjective, config.adjectives_pool)
            self.assertIn(character.rarity, [2, 3, 4, 5])
    
    async def test_pull_with_guarantee(self):
        """Test gacha pull with pity guarantee"""
        user_id = "test_user"
        
        # Set up pity for guaranteed 4-star
        self.gacha_system.pity_system[user_id] = {
            'pulls': 70,
            'last_4_star': 20,
            'last_5_star': 0
        }
        
        with patch.object(self.db_manager, 'add_gacha_item'):
            result = await self.gacha_system.pull(user_id)
            
            # Should get 4-star due to pity
            self.assertEqual(result['rarity'], 4)
            character = result['character']
            self.assertEqual(character.rarity, 4)
    
    async def test_pull_pity_counters(self):
        """Test pity counters after pull"""
        user_id = "test_user"
        
        with patch.object(self.db_manager, 'add_gacha_item'):
            result = await self.gacha_system.pull(user_id)
            
            # Check pity was updated
            pity_info = self.gacha_system._get_pity_info(user_id)
            self.assertEqual(pity_info['pulls'], 1)
            
            # Check next guaranteed calculations
            self.assertIsInstance(result['next_guaranteed_4'], int)
            self.assertIsInstance(result['next_guaranteed_5'], int)
            self.assertGreaterEqual(result['next_guaranteed_4'], 0)
            self.assertGreaterEqual(result['next_guaranteed_5'], 0)
    
    async def test_get_inventory_stats_empty(self):
        """Test inventory stats for empty inventory"""
        user_id = "new_user"
        
        with patch.object(self.db_manager, 'get_gacha_inventory', return_value=[]):
            stats = await self.gacha_system.get_inventory_stats(user_id)
            
            expected_stats = {
                'total_characters': 0,
                'rarity_counts': {2: 0, 3: 0, 4: 0, 5: 0},
                'total_value': 0,
                'rarest_character': None
            }
            
            self.assertEqual(stats, expected_stats)
    
    async def test_get_inventory_stats_with_items(self):
        """Test inventory stats with items"""
        user_id = "test_user"
        
        mock_inventory = [
            {'character_name': 'Char1', 'rarity': 2, 'adjective': 'Adj1'},
            {'character_name': 'Char2', 'rarity': 4, 'adjective': 'Adj2'},
            {'character_name': 'Char3', 'rarity': 2, 'adjective': 'Adj3'},
            {'character_name': 'Char4', 'rarity': 5, 'adjective': 'Adj4'}
        ]
        
        with patch.object(self.db_manager, 'get_gacha_inventory', return_value=mock_inventory):
            stats = await self.gacha_system.get_inventory_stats(user_id)
            
            self.assertEqual(stats['total_characters'], 4)
            self.assertEqual(stats['rarity_counts'], {2: 2, 3: 0, 4: 1, 5: 1})
            self.assertEqual(stats['total_value'], 230)  # 2*5 + 1*50 + 1*200
            self.assertEqual(stats['rarest_character']['rarity'], 5)
    
    def test_get_rarity_color(self):
        """Test rarity color function"""
        test_cases = [
            (2, 0x808080),  # Gray
            (3, 0x00FF00),  # Green
            (4, 0x0000FF),  # Blue
            (5, 0xFFD700),  # Gold
            (1, 0x808080),  # Default for invalid
            (6, 0x808080)   # Default for invalid
        ]
        
        for rarity, expected_color in test_cases:
            with self.subTest(rarity=rarity):
                color = self.gacha_system.get_rarity_color(rarity)
                self.assertEqual(color, expected_color)
    
    def test_get_rarity_emoji(self):
        """Test rarity emoji function"""
        test_cases = [
            (2, "⚪"),
            (3, "🟢"),
            (4, "🔵"),
            (5, "🟡"),
            (1, "⚪"),  # Default for invalid
            (6, "⚪")   # Default for invalid
        ]
        
        for rarity, expected_emoji in test_cases:
            with self.subTest(rarity=rarity):
                emoji = self.gacha_system.get_rarity_emoji(rarity)
                self.assertEqual(emoji, expected_emoji)
    
    def test_character_distribution(self):
        """Test character distribution across rarities"""
        characters = self.gacha_system._load_characters()
        
        # Count characters by rarity
        rarity_counts = {}
        for character in characters:
            rarity_counts[character.rarity] = rarity_counts.get(character.rarity, 0) + 1
        
        # Check that we have characters for each rarity
        for rarity in [2, 3, 4, 5]:
            self.assertIn(rarity, rarity_counts)
            self.assertGreater(rarity_counts[rarity], 0)
        
        # Check that higher rarities have fewer characters (more valuable)
        self.assertGreater(rarity_counts[2], rarity_counts[3])
        self.assertGreater(rarity_counts[3], rarity_counts[4])
        self.assertGreater(rarity_counts[4], rarity_counts[5])
    
    def test_character_uniqueness(self):
        """Test that characters are unique combinations"""
        characters = self.gacha_system._load_characters()
        
        # Create unique identifiers
        unique_combinations = set()
        for character in characters:
            combo = f"{character.rarity}_{character.adjective}_{character.name}"
            unique_combinations.add(combo)
        
        # All combinations should be unique
        self.assertEqual(len(unique_combinations), len(characters))

if __name__ == '__main__':
    unittest.main() 