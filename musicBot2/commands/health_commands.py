"""
Health check commands for monitoring bot status.
"""

import discord
from discord.ext import commands
import asyncio
import psutil
import os
import logging
from datetime import datetime

from utils.error_handler import handle_errors, log_command
from utils.database import db
from utils.cache_manager import cache_manager
from music.player import guild_music_manager

logger = logging.getLogger(__name__)


class HealthCommands(commands.Cog):
    """Health check and monitoring commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
    
    @commands.command(name='health', help='Show bot health status')
    @handle_errors
    @log_command
    async def health(self, ctx):
        """Show comprehensive bot health status"""
        embed = discord.Embed(
            title="🏥 Bot Health Status",
            color=0x00FF00,
            timestamp=datetime.now()
        )
        
        # Basic status
        latency = round(self.bot.latency * 1000)
        uptime = datetime.now() - self.start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
        
        status_emoji = "🟢" if latency < 200 else ("🟡" if latency < 500 else "🔴")
        
        embed.add_field(
            name=f"{status_emoji} Connection",
            value=f"**Latency:** {latency}ms\n**Uptime:** {uptime_str}\n**Guilds:** {len(self.bot.guilds)}",
            inline=True
        )
        
        # Database status
        try:
            # Quick database check
            balance = await db.get_balance("health_check_test")
            db_status = "🟢 Connected"
        except Exception as e:
            db_status = f"🔴 Error: {str(e)[:30]}"
            logger.error(f"Database health check failed: {e}")
        
        embed.add_field(
            name="💾 Database",
            value=db_status,
            inline=True
        )
        
        # Cache status
        try:
            cache_stats = await cache_manager.get_cache_stats()
            if cache_stats.get('enabled'):
                cache_status = f"🟢 {cache_stats['total_songs']} songs\n{cache_stats['actual_disk_size_mb']}MB used"
            else:
                cache_status = "⚪ Disabled"
        except Exception as e:
            cache_status = f"🔴 Error: {str(e)[:30]}"
        
        embed.add_field(
            name="📦 Cache",
            value=cache_status,
            inline=True
        )
        
        # Voice connections
        voice_connections = []
        for guild_id in guild_music_manager.get_all_guild_ids():
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client and guild.voice_client.is_connected():
                player = guild_music_manager.get_player(guild_id)
                status = "🎵" if player.is_playing else "⏸️"
                voice_connections.append(f"{status} {guild.name[:20]}")
        
        if voice_connections:
            embed.add_field(
                name=f"🔊 Voice ({len(voice_connections)})",
                value="\n".join(voice_connections[:5]) + ("\n..." if len(voice_connections) > 5 else ""),
                inline=True
            )
        else:
            embed.add_field(
                name="🔊 Voice",
                value="No active connections",
                inline=True
            )
        
        # System resources
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Disk space for cache directory
            if os.path.exists("cache"):
                disk_usage = psutil.disk_usage(".")
                disk_free_gb = disk_usage.free / (1024 * 1024 * 1024)
                disk_status = f"**Free:** {disk_free_gb:.1f}GB"
            else:
                disk_status = "N/A"
            
            embed.add_field(
                name="🖥️ System",
                value=f"**Memory:** {memory_mb:.1f}MB\n**CPU:** {cpu_percent:.1f}%\n{disk_status}",
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="🖥️ System",
                value=f"Unable to get stats",
                inline=True
            )
        
        # Overall status
        all_good = (
            latency < 500 and 
            "🟢" in db_status and 
            ("🟢" in cache_status or "⚪" in cache_status)
        )
        
        embed.description = "✅ All systems operational" if all_good else "⚠️ Some issues detected"
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='dbstatus', help='Show detailed database status')
    @handle_errors
    @log_command
    async def dbstatus(self, ctx):
        """Show detailed database status"""
        embed = discord.Embed(
            title="💾 Database Status",
            color=0x1DB954,
            timestamp=datetime.now()
        )
        
        try:
            # Get various counts
            total_songs = await db.get_total_songs_played()
            unique_songs = await db.get_unique_songs_count()
            
            # Get database file size
            db_path = "bot_data.db"
            if os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            else:
                db_size_mb = 0
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Total Plays:** {total_songs:,}\n**Unique Songs:** {unique_songs:,}\n**DB Size:** {db_size_mb:.2f}MB",
                inline=True
            )
            
            # Get cache stats
            cache_stats = await cache_manager.get_cache_stats()
            if cache_stats.get('enabled'):
                embed.add_field(
                    name="📦 Cache",
                    value=f"**Cached Songs:** {cache_stats['total_songs']}\n**Cache Size:** {cache_stats['actual_disk_size_mb']}MB",
                    inline=True
                )
            
            embed.description = "✅ Database is healthy"
            
        except Exception as e:
            embed.description = f"❌ Error checking database: {str(e)}"
            logger.error(f"Database status check failed: {e}")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HealthCommands(bot))
