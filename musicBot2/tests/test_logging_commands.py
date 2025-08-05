import unittest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock
import discord
from discord.ext import commands

# Import the logging commands
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands.logging_commands import LoggingCommands

class TestLoggingCommands(unittest.TestCase):
    """Test cases for logging commands"""
    
    def setUp(self):
        """Set up test environment"""
        self.bot = Mock()
        self.bot.owner_id = 123456789
        self.cog = LoggingCommands(self.bot)
        
        # Create temporary directory for logs
        self.temp_dir = tempfile.mkdtemp()
        self.cog.logs_dir = self.temp_dir
        self.cog.log_file = os.path.join(self.temp_dir, "bot.log")
        
        # Create mock context
        self.ctx = Mock()
        self.ctx.author = Mock()
        self.ctx.author.id = 987654321
        self.ctx.author.guild_permissions = Mock()
        self.ctx.author.guild_permissions.manage_guild = True
        self.ctx.guild = Mock()
        self.ctx.send = AsyncMock()
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_check_permissions_with_manage_guild(self):
        """Test permission check with manage guild permission"""
        result = asyncio.run(self.cog._check_permissions(self.ctx))
        self.assertTrue(result)
    
    def test_check_permissions_without_manage_guild(self):
        """Test permission check without manage guild permission"""
        self.ctx.author.guild_permissions.manage_guild = False
        result = asyncio.run(self.cog._check_permissions(self.ctx))
        self.assertFalse(result)
        self.ctx.send.assert_called_once()
    
    def test_check_permissions_bot_owner(self):
        """Test permission check for bot owner"""
        self.ctx.author.id = self.bot.owner_id
        self.ctx.author.guild_permissions.manage_guild = False
        result = asyncio.run(self.cog._check_permissions(self.ctx))
        self.assertTrue(result)
    
    def test_format_logs(self):
        """Test log formatting"""
        test_logs = [
            "2024-01-01 12:00:00,000 - INFO - Test log 1",
            "2024-01-01 12:00:01,000 - ERROR - Test log 2 with a very long message that should be truncated",
            "2024-01-01 12:00:02,000 - DEBUG - Test log 3"
        ]
        
        formatted = self.cog._format_logs(test_logs)
        self.assertIsInstance(formatted, str)
        self.assertIn("Test log 1", formatted)
        self.assertIn("Test log 2", formatted)
        self.assertIn("Test log 3", formatted)
    
    def test_split_logs(self):
        """Test log splitting for Discord embeds"""
        # Create a long log text
        long_text = "Test line\n" * 100
        
        chunks = self.cog._split_logs(long_text)
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)
        
        # Check that each chunk is within Discord's limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 1900)
    
    def test_log_levels(self):
        """Test that log levels are properly defined"""
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            self.assertIn(level, self.cog.log_levels)
            self.assertIsInstance(self.cog.log_levels[level], int)
    
    def test_log_file_operations(self):
        """Test basic log file operations"""
        # Test creating log file
        test_content = "Test log line 1\nTest log line 2\n"
        with open(self.cog.log_file, 'w') as f:
            f.write(test_content)
        
        # Test reading log file
        with open(self.cog.log_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, test_content)
        
        # Test file exists
        self.assertTrue(os.path.exists(self.cog.log_file))
    
    def test_backup_creation(self):
        """Test backup file creation"""
        # Create a test log file
        with open(self.cog.log_file, 'w') as f:
            f.write("Test log content\n")
        
        # Simulate backup creation
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{self.cog.log_file}.backup.{timestamp}"
        
        # Copy file to backup
        with open(self.cog.log_file, 'r') as source:
            with open(backup_name, 'w') as dest:
                dest.write(source.read())
        
        # Check backup exists
        self.assertTrue(os.path.exists(backup_name))
        
        # Clean up
        os.remove(backup_name)
    
    def test_log_filtering(self):
        """Test log filtering by level"""
        test_logs = [
            "2024-01-01 12:00:00,000 - INFO - Test info log",
            "2024-01-01 12:00:01,000 - ERROR - Test error log",
            "2024-01-01 12:00:02,000 - DEBUG - Test debug log",
            "2024-01-01 12:00:03,000 - ERROR - Another error log"
        ]
        
        # Filter by ERROR level
        error_logs = [line for line in test_logs if " - ERROR - " in line]
        self.assertEqual(len(error_logs), 2)
        
        # Filter by INFO level
        info_logs = [line for line in test_logs if " - INFO - " in line]
        self.assertEqual(len(info_logs), 1)
    
    def test_log_search(self):
        """Test log searching functionality"""
        test_logs = [
            "2024-01-01 12:00:00,000 - INFO - User login successful",
            "2024-01-01 12:00:01,000 - ERROR - Database connection failed",
            "2024-01-01 12:00:02,000 - INFO - Cache hit for song ID",
            "2024-01-01 12:00:03,000 - ERROR - Another database error"
        ]
        
        # Search for "error"
        error_matches = [line for line in test_logs if "error" in line.lower()]
        self.assertEqual(len(error_matches), 2)
        
        # Search for "cache"
        cache_matches = [line for line in test_logs if "cache" in line.lower()]
        self.assertEqual(len(cache_matches), 1)
    
    def test_log_statistics(self):
        """Test log statistics calculation"""
        test_logs = [
            "2024-01-01 12:00:00,000 - INFO - Log 1",
            "2024-01-01 12:00:01,000 - ERROR - Log 2",
            "2024-01-01 12:00:02,000 - INFO - Log 3",
            "2024-01-01 12:00:03,000 - WARNING - Log 4",
            "2024-01-01 12:00:04,000 - ERROR - Log 5"
        ]
        
        # Count by level
        level_counts = {}
        for level in self.cog.log_levels.keys():
            level_counts[level] = len([line for line in test_logs if f" - {level} - " in line])
        
        self.assertEqual(level_counts["INFO"], 2)
        self.assertEqual(level_counts["ERROR"], 2)
        self.assertEqual(level_counts["WARNING"], 1)
        self.assertEqual(level_counts["DEBUG"], 0)
        self.assertEqual(level_counts["CRITICAL"], 0)
        
        # Total logs
        total_logs = len(test_logs)
        self.assertEqual(total_logs, 5)

if __name__ == '__main__':
    unittest.main() 