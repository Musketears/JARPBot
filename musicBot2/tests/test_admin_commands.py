import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import discord
from discord.ext import commands

# Import the admin commands cog
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands.admin_commands import AdminCommands

class TestAdminCommands(unittest.TestCase):
    """Test cases for admin commands"""
    
    def setUp(self):
        """Set up test environment"""
        self.bot = Mock()
        self.bot.owner_id = 123456789
        self.cog = AdminCommands(self.bot)
        
        # Mock context
        self.ctx = Mock()
        self.ctx.author = Mock()
        self.ctx.author.id = 123456789
        self.ctx.guild = Mock()
        self.ctx.author.guild_permissions = Mock()
        self.ctx.send = AsyncMock()
        self.ctx.message.edit = AsyncMock()
    
    def test_check_admin_permissions_with_admin(self):
        """Test permission check with administrator permission"""
        self.ctx.author.guild_permissions.administrator = True
        result = asyncio.run(self.cog._check_admin_permissions(self.ctx))
        self.assertTrue(result)
    
    def test_check_admin_permissions_without_admin(self):
        """Test permission check without administrator permission"""
        self.ctx.author.guild_permissions.administrator = False
        self.ctx.author.id = 987654321  # Different from owner_id
        result = asyncio.run(self.cog._check_admin_permissions(self.ctx))
        self.assertFalse(result)
    
    def test_check_admin_permissions_bot_owner(self):
        """Test permission check for bot owner"""
        self.ctx.author.guild_permissions.administrator = False
        self.ctx.author.id = self.bot.owner_id
        result = asyncio.run(self.cog._check_admin_permissions(self.ctx))
        self.assertTrue(result)
    
    @patch('commands.admin_commands.subprocess.run')
    @patch('commands.admin_commands.os.path.exists')
    def test_update_bot_success(self, mock_exists, mock_run):
        """Test successful bot update"""
        # Mock permissions
        self.ctx.author.guild_permissions.administrator = True
        
        # Mock script exists
        mock_exists.return_value = True
        
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Update successful"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Test the command
        asyncio.run(self.cog.update_bot(self.ctx))
        
        # Verify send was called
        self.ctx.send.assert_called()
    
    @patch('commands.admin_commands.subprocess.run')
    @patch('commands.admin_commands.os.path.exists')
    def test_update_bot_script_not_found(self, mock_exists, mock_run):
        """Test update when script is not found"""
        # Mock permissions
        self.ctx.author.guild_permissions.administrator = True
        
        # Mock script doesn't exist
        mock_exists.return_value = False
        
        # Test the command
        asyncio.run(self.cog.update_bot(self.ctx))
        
        # Verify send was called with error
        self.ctx.send.assert_called()
        call_args = self.ctx.send.call_args[0][0]
        self.assertIn("Update script not found", call_args.description)
    
    def test_update_bot_no_permissions(self):
        """Test update command without permissions"""
        # Mock no permissions
        self.ctx.author.guild_permissions.administrator = False
        self.ctx.author.id = 987654321
        
        # Test the command
        asyncio.run(self.cog.update_bot(self.ctx))
        
        # Verify send was called with permission denied
        self.ctx.send.assert_called()
        call_args = self.ctx.send.call_args[0][0]
        self.assertIn("Permission Denied", call_args.title)
    
    def test_system_status_permissions(self):
        """Test system_status command permissions"""
        # Mock no permissions
        self.ctx.author.guild_permissions.administrator = False
        self.ctx.author.id = 987654321
        
        # Test the command
        asyncio.run(self.cog.system_status(self.ctx))
        
        # Verify send was called with permission denied
        self.ctx.send.assert_called()
        call_args = self.ctx.send.call_args[0][0]
        self.assertIn("Permission Denied", call_args.title)

if __name__ == '__main__':
    unittest.main() 