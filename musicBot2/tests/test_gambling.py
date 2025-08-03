#!/usr/bin/env python3
"""
Unit tests for gambling system
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
import sys
sys.path.append('..')

from games.gambling import GamblingManager, HigherLowerGame, SlotMachine, AlexRoulette
from utils.database import DatabaseManager
from config import config

class TestGamblingManager(unittest.TestCase):
    """Test GamblingManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.gambling_manager = GamblingManager()
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_check_gambling_limits_new_user(self):
        """Test gambling limits for new user"""
        user_id = "test_user"
        bet_amount = 50
        
        # Mock database calls
        with patch.object(self.db_manager, 'get_daily_bet_total', return_value=0):
            with patch.object(self.db_manager, 'get_balance', return_value=100):
                can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, bet_amount)
                self.assertTrue(can_gamble)
                self.assertEqual(error, "")
    
    async def test_check_gambling_limits_insufficient_balance(self):
        """Test gambling limits with insufficient balance"""
        user_id = "test_user"
        bet_amount = 150
        
        with patch.object(self.db_manager, 'get_balance', return_value=100):
            can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, bet_amount)
            self.assertFalse(can_gamble)
            self.assertIn("don't have enough money", error)
    
    async def test_check_gambling_limits_daily_limit_exceeded(self):
        """Test gambling limits with daily limit exceeded"""
        user_id = "test_user"
        bet_amount = 100
        
        with patch.object(self.db_manager, 'get_daily_bet_total', return_value=950):
            with patch.object(self.db_manager, 'get_balance', return_value=200):
                can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, bet_amount)
                self.assertFalse(can_gamble)
                self.assertIn("Daily betting limit exceeded", error)
    
    async def test_check_gambling_limits_cooldown(self):
        """Test gambling limits with cooldown"""
        user_id = "test_user"
        bet_amount = 50
        
        # Set cooldown
        self.gambling_manager.cooldowns[user_id] = MagicMock()
        
        with patch.object(self.db_manager, 'get_daily_bet_total', return_value=0):
            with patch.object(self.db_manager, 'get_balance', return_value=100):
                can_gamble, error = await self.gambling_manager.check_gambling_limits(user_id, bet_amount)
                self.assertFalse(can_gamble)
                self.assertIn("Please wait", error)
    
    async def test_apply_gambling_cooldown(self):
        """Test applying gambling cooldown"""
        user_id = "test_user"
        
        await self.gambling_manager.apply_gambling_cooldown(user_id)
        
        self.assertIn(user_id, self.gambling_manager.cooldowns)
        self.assertIsNotNone(self.gambling_manager.cooldowns[user_id])

class TestHigherLowerGame(unittest.TestCase):
    """Test HigherLowerGame class"""
    
    def setUp(self):
        """Set up test environment"""
        self.game = HigherLowerGame()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    async def test_start_game(self):
        """Test starting a higher/lower game"""
        user_id = "test_user"
        bet_amount = 50
        
        result = await self.game.start_game(user_id, bet_amount)
        
        self.assertIn('current_number', result)
        self.assertIn('message', result)
        self.assertIsInstance(result['current_number'], int)
        self.assertGreaterEqual(result['current_number'], 1)
        self.assertLessEqual(result['current_number'], 10)
        
        # Check game is stored
        self.assertIn(user_id, self.game.active_games)
        self.assertEqual(self.game.active_games[user_id]['bet_amount'], bet_amount)
    
    async def test_process_guess_win_higher(self):
        """Test processing a winning higher guess"""
        user_id = "test_user"
        bet_amount = 50
        
        # Start game with current number 3
        self.game.active_games[user_id] = {
            'current_number': 3,
            'bet_amount': bet_amount,
            'started_at': MagicMock()
        }
        
        with patch.object(self.db_manager, 'update_balance', return_value=150):
            with patch.object(self.db_manager, 'record_gambling'):
                result = await self.game.process_guess(user_id, "higher")
                
                self.assertTrue(result['win'])
                self.assertGreater(result['next_number'], 3)
                self.assertEqual(result['win_amount'], bet_amount)
                self.assertEqual(result['new_balance'], 150)
    
    async def test_process_guess_win_lower(self):
        """Test processing a winning lower guess"""
        user_id = "test_user"
        bet_amount = 50
        
        # Start game with current number 8
        self.game.active_games[user_id] = {
            'current_number': 8,
            'bet_amount': bet_amount,
            'started_at': MagicMock()
        }
        
        with patch.object(self.db_manager, 'update_balance', return_value=150):
            with patch.object(self.db_manager, 'record_gambling'):
                result = await self.game.process_guess(user_id, "lower")
                
                self.assertTrue(result['win'])
                self.assertLess(result['next_number'], 8)
                self.assertEqual(result['win_amount'], bet_amount)
    
    async def test_process_guess_lose(self):
        """Test processing a losing guess"""
        user_id = "test_user"
        bet_amount = 50
        
        # Start game with current number 5
        self.game.active_games[user_id] = {
            'current_number': 5,
            'bet_amount': bet_amount,
            'started_at': MagicMock()
        }
        
        with patch.object(self.db_manager, 'update_balance', return_value=50):
            with patch.object(self.db_manager, 'record_gambling'):
                result = await self.game.process_guess(user_id, "higher")
                
                # This might win or lose depending on random number
                # Just check the structure
                self.assertIn('win', result)
                self.assertIn('next_number', result)
                self.assertIn('new_balance', result)
    
    async def test_process_guess_no_active_game(self):
        """Test processing guess with no active game"""
        user_id = "test_user"
        
        result = await self.game.process_guess(user_id, "higher")
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No active game found.')

class TestSlotMachine(unittest.TestCase):
    """Test SlotMachine class"""
    
    def setUp(self):
        """Set up test environment"""
        self.slot_machine = SlotMachine()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_slot_machine_initialization(self):
        """Test slot machine initialization"""
        self.assertIsInstance(self.slot_machine.symbols, list)
        self.assertIsInstance(self.slot_machine.payouts, dict)
        
        # Check symbols
        expected_symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
        self.assertEqual(self.slot_machine.symbols, expected_symbols)
        
        # Check payouts
        expected_payouts = {
            "🍒": 5, "🍋": 10, "🔔": 20, "💎": 100, "7️⃣": 15
        }
        self.assertEqual(self.slot_machine.payouts, expected_payouts)
    
    async def test_spin_basic(self):
        """Test basic slot machine spin"""
        user_id = "test_user"
        bet_amount = 5
        
        with patch.object(self.db_manager, 'update_balance', return_value=95):
            with patch.object(self.db_manager, 'record_gambling'):
                result = await self.slot_machine.spin(user_id, bet_amount)
                
                self.assertIn('grid', result)
                self.assertIn('win_amount', result)
                self.assertIn('new_balance', result)
                self.assertIn('message', result)
                
                # Check grid structure
                self.assertEqual(len(result['grid']), 3)
                for row in result['grid']:
                    self.assertEqual(len(row), 3)
                    for symbol in row:
                        self.assertIn(symbol, self.slot_machine.symbols)
    
    async def test_spin_winning_combination(self):
        """Test slot machine with winning combination"""
        user_id = "test_user"
        bet_amount = 5
        
        # Mock random to get a winning combination
        with patch('random.choices', side_effect=[
            ["🍒", "🍒", "🍒"],  # First row
            ["🍋", "🔔", "7️⃣"],  # Second row
            ["💎", "🍒", "🔔"]   # Third row
        ]):
            with patch.object(self.db_manager, 'update_balance', return_value=110):
                with patch.object(self.db_manager, 'record_gambling'):
                    result = await self.slot_machine.spin(user_id, bet_amount)
                    
                    # Should win 5 from first row (all cherries)
                    self.assertEqual(result['win_amount'], 5)
                    self.assertIn("You won", result['message'])
    
    async def test_spin_jackpot(self):
        """Test slot machine jackpot"""
        user_id = "test_user"
        bet_amount = 5
        
        # Mock random to get all diamonds
        with patch('random.choices', side_effect=[
            ["💎", "💎", "💎"],  # First row
            ["💎", "💎", "💎"],  # Second row
            ["💎", "💎", "💎"]   # Third row
        ]):
            with patch.object(self.db_manager, 'update_balance', return_value=10000005):
                with patch.object(self.db_manager, 'record_gambling'):
                    result = await self.slot_machine.spin(user_id, bet_amount)
                    
                    # Should win jackpot
                    self.assertEqual(result['win_amount'], 10000000)
                    self.assertIn("You won", result['message'])

class TestAlexRoulette(unittest.TestCase):
    """Test AlexRoulette class"""
    
    def setUp(self):
        """Set up test environment"""
        self.roulette = AlexRoulette()
    
    def test_roulette_initialization(self):
        """Test roulette initialization"""
        self.assertIsInstance(self.roulette.special_outcomes, dict)
        
        # Check special outcomes
        expected_outcomes = {
            90: {"message": "ggs", "url": "https://www.youtube.com/watch?v=1EUoIhob8t8"},
            10: {"message": "ff", "url": "https://www.youtube.com/watch?v=d3h1I3QDEHU"},
            20: {"message": "My favorite song", "url": "https://www.youtube.com/watch?v=VZZCXP_rFKk"}
        }
        self.assertEqual(self.roulette.special_outcomes, expected_outcomes)
    
    async def test_spin_normal_outcome(self):
        """Test roulette spin with normal outcome"""
        user_id = "test_user"
        
        # Mock random to get normal outcome
        with patch('random.randint', return_value=50):
            result = await self.roulette.spin(user_id)
            
            self.assertEqual(result['number'], 50)
            self.assertFalse(result['special'])
            self.assertEqual(result['message'], "Thanks for the $10 xD, try again?")
    
    async def test_spin_special_outcome(self):
        """Test roulette spin with special outcome"""
        user_id = "test_user"
        
        # Mock random to get special outcome
        with patch('random.randint', return_value=90):
            result = await self.roulette.spin(user_id)
            
            self.assertEqual(result['number'], 90)
            self.assertTrue(result['special'])
            self.assertEqual(result['message'], "ggs")
            self.assertIn('url', result)
    
    async def test_spin_all_special_outcomes(self):
        """Test all special outcomes"""
        user_id = "test_user"
        
        for number in [10, 20, 90]:
            with patch('random.randint', return_value=number):
                result = await self.roulette.spin(user_id)
                
                self.assertEqual(result['number'], number)
                self.assertTrue(result['special'])
                self.assertIn('url', result)
                self.assertIn('message', result)

if __name__ == '__main__':
    unittest.main() 