#!/usr/bin/env python3
"""
Unit tests for database system
"""

import unittest
import asyncio
import tempfile
import os
import sqlite3
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

from utils.database import DatabaseManager
from config import config

class TestDatabaseManager(unittest.TestCase):
    """Test DatabaseManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization creates tables"""
        # Check if tables exist
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Check user_balances table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user_balances'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check gacha_inventory table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='gacha_inventory'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check gambling_history table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='gambling_history'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check daily_limits table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='daily_limits'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check griddy_counts table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='griddy_counts'
            """)
            self.assertIsNotNone(cursor.fetchone())
    
    def test_get_balance_new_user(self):
        """Test getting balance for new user"""
        async def test():
            balance = await self.db_manager.get_balance("test_user_123")
            self.assertEqual(balance, config.default_balance)
        
        asyncio.run(test())
    
    def test_get_balance_existing_user(self):
        """Test getting balance for existing user"""
        async def test():
            # First, create a user with a specific balance
            await self.db_manager.update_balance("test_user_456", 200)
            
            # Then get their balance
            balance = await self.db_manager.get_balance("test_user_456")
            self.assertEqual(balance, 200)
        
        asyncio.run(test())
    
    def test_update_balance_new_user(self):
        """Test updating balance for new user"""
        async def test():
            new_balance = await self.db_manager.update_balance("test_user_789", 50)
            self.assertEqual(new_balance, config.default_balance + 50)
        
        asyncio.run(test())
    
    def test_update_balance_existing_user(self):
        """Test updating balance for existing user"""
        async def test():
            # First, create a user
            await self.db_manager.update_balance("test_user_101", 100)
            
            # Then update their balance
            new_balance = await self.db_manager.update_balance("test_user_101", 25)
            self.assertEqual(new_balance, 125)
        
        asyncio.run(test())
    
    def test_add_gacha_item(self):
        """Test adding gacha item"""
        async def test():
            await self.db_manager.add_gacha_item("test_user", "TestChar", 3, "TestAdj")
            
            # Verify item was added
            inventory = await self.db_manager.get_gacha_inventory("test_user")
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]['character_name'], "TestChar")
            self.assertEqual(inventory[0]['rarity'], 3)
            self.assertEqual(inventory[0]['adjective'], "TestAdj")
        
        asyncio.run(test())
    
    def test_get_gacha_inventory_empty(self):
        """Test getting empty gacha inventory"""
        async def test():
            inventory = await self.db_manager.get_gacha_inventory("new_user")
            self.assertEqual(len(inventory), 0)
        
        asyncio.run(test())
    
    def test_get_gacha_inventory_with_items(self):
        """Test getting gacha inventory with items"""
        async def test():
            # Add multiple items
            await self.db_manager.add_gacha_item("test_user", "Char1", 2, "Adj1")
            await self.db_manager.add_gacha_item("test_user", "Char2", 4, "Adj2")
            
            inventory = await self.db_manager.get_gacha_inventory("test_user")
            self.assertEqual(len(inventory), 2)
            
            # Check items are ordered by obtained_at DESC
            self.assertEqual(inventory[0]['character_name'], "Char2")
            self.assertEqual(inventory[1]['character_name'], "Char1")
        
        asyncio.run(test())
    
    def test_record_gambling(self):
        """Test recording gambling activity"""
        async def test():
            await self.db_manager.record_gambling("test_user", "slots", 10, 25)
            
            # Verify record was created
            with sqlite3.connect(self.temp_db.name) as conn:
                cursor = conn.execute(
                    "SELECT * FROM gambling_history WHERE user_id = ?",
                    ("test_user",)
                )
                result = cursor.fetchone()
                self.assertIsNotNone(result)
                self.assertEqual(result[2], "slots")  # game_type
                self.assertEqual(result[3], 10)       # bet_amount
                self.assertEqual(result[4], 25)       # win_amount
        
        asyncio.run(test())
    
    def test_get_daily_bet_total_empty(self):
        """Test getting daily bet total for new user"""
        async def test():
            total = await self.db_manager.get_daily_bet_total("new_user")
            self.assertEqual(total, 0)
        
        asyncio.run(test())
    
    def test_get_daily_bet_total_with_bets(self):
        """Test getting daily bet total with existing bets"""
        async def test():
            # Record some gambling activity
            await self.db_manager.record_gambling("test_user", "slots", 10, 25)
            await self.db_manager.record_gambling("test_user", "gamble", 20, 0)
            
            total = await self.db_manager.get_daily_bet_total("test_user")
            self.assertEqual(total, 30)  # 10 + 20
        
        asyncio.run(test())
    
    def test_get_griddy_count_new(self):
        """Test getting griddy count for new name"""
        async def test():
            count = await self.db_manager.get_griddy_count("new_name")
            self.assertEqual(count, 0)
        
        asyncio.run(test())
    
    def test_increment_griddy_count(self):
        """Test incrementing griddy count"""
        async def test():
            # Increment count
            await self.db_manager.increment_griddy_count("test_name")
            
            # Check count
            count = await self.db_manager.get_griddy_count("test_name")
            self.assertEqual(count, 1)
            
            # Increment again
            await self.db_manager.increment_griddy_count("test_name")
            count = await self.db_manager.get_griddy_count("test_name")
            self.assertEqual(count, 2)
        
        asyncio.run(test())
    
    def test_get_gambling_stats_empty(self):
        """Test getting gambling stats for user with no history"""
        async def test():
            stats = await self.db_manager.get_gambling_stats("new_user")
            
            expected_stats = {
                'total_games': 0,
                'total_bet': 0,
                'total_won': 0,
                'net_profit': 0,
                'today_games': 0,
                'today_bet': 0,
                'today_won': 0
            }
            
            self.assertEqual(stats, expected_stats)
        
        asyncio.run(test())
    
    def test_get_gambling_stats_with_history(self):
        """Test getting gambling stats with history"""
        async def test():
            # Record some gambling activity
            await self.db_manager.record_gambling("test_user", "slots", 10, 25)
            await self.db_manager.record_gambling("test_user", "gamble", 20, 0)
            await self.db_manager.record_gambling("test_user", "slots", 5, 15)
            
            stats = await self.db_manager.get_gambling_stats("test_user")
            
            self.assertEqual(stats['total_games'], 3)
            self.assertEqual(stats['total_bet'], 35)  # 10 + 20 + 5
            self.assertEqual(stats['total_won'], 40)  # 25 + 0 + 15
            self.assertEqual(stats['net_profit'], 5)  # 40 - 35
            self.assertEqual(stats['today_games'], 3)
            self.assertEqual(stats['today_bet'], 35)
            self.assertEqual(stats['today_won'], 40)
        
        asyncio.run(test())

if __name__ == '__main__':
    unittest.main() 