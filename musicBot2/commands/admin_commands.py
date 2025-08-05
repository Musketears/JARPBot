import discord
from discord.ext import commands
import asyncio
import subprocess
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Admin commands for bot management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def _check_admin_permissions(self, ctx) -> bool:
        """Check if user has admin permissions"""
        # Check if user has administrator permission
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        
        # Check if user is bot owner
        if ctx.author.id == self.bot.owner_id:
            return True
        
        return False
    
    @commands.command(name='update', help='Update and restart the bot (admin only)')
    async def update_bot(self, ctx):
        """Update and restart the bot by pulling from GitHub"""
        # Check permissions
        if not await self._check_admin_permissions(ctx):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions or be the bot owner to use this command.",
                color=0xE02B2B
            )
            await ctx.send(embed=embed)
            return
        
        # Send initial response
        embed = discord.Embed(
            title="🔄 Bot Update",
            description="Starting bot update and restart process...",
            color=0x57F287
        )
        message = await ctx.send(embed=embed)
        
        try:
            # Get the script path
            script_path = 'update_and_restart.sh'
            
            # Check if script exists
            if not os.path.exists(script_path):
                embed = discord.Embed(
                    title="❌ Error",
                    description="Update script not found. Please check the installation.",
                    color=0xE02B2B
                )
                await message.edit(embed=embed)
                return
            
            # Update embed
            embed.description = "🔄 Pulling latest changes from GitHub..."
            await message.edit(embed=embed)
            
            # Run the update script
            subprocess.run(
                ['bash',script_path],
            )
            
        except subprocess.TimeoutExpired:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="Update process timed out. The bot may still be updating in the background.",
                color=0xFFA500
            )
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error during bot update: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred during the update: {str(e)}",
                color=0xE02B2B
            )
            await message.edit(embed=embed)
    
    @commands.command(name='system_status', help='Show bot system status (admin only)')
    async def system_status(self, ctx):
        """Show detailed bot system status"""
        # Check permissions
        if not await self._check_admin_permissions(ctx):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions or be the bot owner to use this command.",
                color=0xE02B2B
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Get system information
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Bot process info
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cmdline'] and any('main.py' in cmd for cmd in proc.info['cmdline'] if cmd):
                        bot_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            embed = discord.Embed(
                title="📊 Bot System Status",
                color=0x57F287
            )
            
            embed.add_field(
                name="🖥️ System",
                value=f"CPU: {cpu_percent}%\nMemory: {memory.percent}%\nDisk: {disk.percent}%",
                inline=True
            )
            
            if bot_processes:
                process_info = []
                for proc in bot_processes:
                    process_info.append(f"PID: {proc['pid']}\nCPU: {proc['cpu_percent']}%\nMemory: {proc['memory_percent']:.1f}%")
                
                embed.add_field(
                    name="🤖 Bot Processes",
                    value="\n\n".join(process_info),
                    inline=True
                )
            else:
                embed.add_field(
                    name="🤖 Bot Processes",
                    value="No bot processes found",
                    inline=True
                )
            
            embed.add_field(
                name="📈 Memory Details",
                value=f"Total: {memory.total // (1024**3)}GB\nUsed: {memory.used // (1024**3)}GB\nAvailable: {memory.available // (1024**3)}GB",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except ImportError:
            embed = discord.Embed(
                title="❌ Error",
                description="psutil library not available. Install it with: `pip install psutil`",
                color=0xE02B2B
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while getting status: {str(e)}",
                color=0xE02B2B
            )
            await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(AdminCommands(bot)) 