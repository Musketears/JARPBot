import discord
from discord.ext import commands
import logging
import os
import asyncio
from datetime import datetime, timedelta
import re
from typing import Optional, List
import json

from utils.error_handler import handle_errors, log_command
from utils.helpers import create_status_embed

logger = logging.getLogger(__name__)

class LoggingCommands(commands.Cog):
    """Commands for managing bot logging and viewing logs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logs_dir = "logs"
        self.log_file = "logs/bot.log"
        self.max_log_lines = 1000
        self.log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
    
    @commands.command(name='logs', help='View recent bot logs')
    @handle_errors
    @log_command
    async def view_logs(self, ctx, lines: int = 50, level: str = None):
        """View recent bot logs with optional filtering"""
        if not await self._check_permissions(ctx):
            return
        
        if lines > self.max_log_lines:
            await ctx.send(f"❌ Maximum lines allowed is {self.max_log_lines}")
            return
        
        if not os.path.exists(self.log_file):
            await ctx.send("❌ No log file found")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Filter by level if specified
            if level and level.upper() in self.log_levels:
                filtered_lines = []
                for line in log_lines:
                    if f" - {level.upper()} - " in line:
                        filtered_lines.append(line)
                log_lines = filtered_lines
            
            # Get the last N lines
            recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
            
            if not recent_logs:
                await ctx.send("❌ No logs found matching the criteria")
                return
            
            # Format logs for display
            formatted_logs = self._format_logs(recent_logs)
            
            # Split into chunks if too long
            chunks = self._split_logs(formatted_logs)
            
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"Bot Logs ({len(recent_logs)} lines)",
                    description=f"```{chunk}```",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"Page {i+1}/{len(chunks)}")
                await ctx.send(embed=embed)
                
                # Add delay between messages to avoid rate limiting
                if len(chunks) > 1 and i < len(chunks) - 1:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            await ctx.send("❌ Error reading log file")
    
    @commands.command(name='loglevel', help='Set bot log level')
    @handle_errors
    @log_command
    async def set_log_level(self, ctx, level: str):
        """Set the bot's logging level"""
        if not await self._check_permissions(ctx):
            return
        
        level = level.upper()
        if level not in self.log_levels:
            valid_levels = ", ".join(self.log_levels.keys())
            await ctx.send(f"❌ Invalid log level. Valid levels: {valid_levels}")
            return
        
        try:
            # Update root logger level
            logging.getLogger().setLevel(self.log_levels[level])
            
            # Update all existing loggers
            for logger_name in logging.root.manager.loggerDict:
                logger_obj = logging.getLogger(logger_name)
                logger_obj.setLevel(self.log_levels[level])
            
            embed = discord.Embed(
                title="Log Level Updated",
                description=f"✅ Log level set to **{level}**",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await ctx.send(embed=embed)
            
            logger.info(f"Log level changed to {level} by {ctx.author}")
            
        except Exception as e:
            logger.error(f"Error setting log level: {e}")
            await ctx.send("❌ Error setting log level")
    
    @commands.command(name='logstats', help='Show logging statistics')
    @handle_errors
    @log_command
    async def log_stats(self, ctx, hours: int = 24):
        """Show logging statistics for the specified time period"""
        if not await self._check_permissions(ctx):
            return
        
        if not os.path.exists(self.log_file):
            await ctx.send("❌ No log file found")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Filter logs by time
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_logs = []
            
            for line in log_lines:
                try:
                    # Extract timestamp from log line
                    timestamp_str = line.split(' - ')[0]
                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    if log_time >= cutoff_time:
                        recent_logs.append(line)
                except (ValueError, IndexError):
                    continue
            
            # Count by level
            level_counts = {}
            for level in self.log_levels.keys():
                level_counts[level] = len([line for line in recent_logs if f" - {level} - " in line])
            
            # Create statistics embed
            embed = discord.Embed(
                title="Logging Statistics",
                description=f"Statistics for the last {hours} hours",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            total_logs = len(recent_logs)
            embed.add_field(
                name="Total Logs",
                value=f"{total_logs:,}",
                inline=True
            )
            
            for level, count in level_counts.items():
                if count > 0:
                    percentage = (count / total_logs * 100) if total_logs > 0 else 0
                    embed.add_field(
                        name=f"{level}",
                        value=f"{count:,} ({percentage:.1f}%)",
                        inline=True
                    )
            
            # File size info
            file_size = os.path.getsize(self.log_file)
            embed.add_field(
                name="Log File Size",
                value=f"{file_size / 1024 / 1024:.2f} MB",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error generating log stats: {e}")
            await ctx.send("❌ Error generating log statistics")
    
    @commands.command(name='searchlogs', help='Search logs for specific text')
    @handle_errors
    @log_command
    async def search_logs(self, ctx, search_term: str, lines: int = 100):
        """Search logs for specific text"""
        if not await self._check_permissions(ctx):
            return
        
        if lines > self.max_log_lines:
            await ctx.send(f"❌ Maximum lines allowed is {self.max_log_lines}")
            return
        
        if not os.path.exists(self.log_file):
            await ctx.send("❌ No log file found")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Search for matching lines
            matching_lines = []
            for line in log_lines:
                if search_term.lower() in line.lower():
                    matching_lines.append(line)
            
            if not matching_lines:
                await ctx.send(f"❌ No logs found containing '{search_term}'")
                return
            
            # Limit results
            if len(matching_lines) > lines:
                matching_lines = matching_lines[-lines:]
            
            # Format and display results
            formatted_logs = self._format_logs(matching_lines)
            chunks = self._split_logs(formatted_logs)
            
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"Log Search Results",
                    description=f"Search term: `{search_term}`\n```{chunk}```",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"Found {len(matching_lines)} matches | Page {i+1}/{len(chunks)}")
                await ctx.send(embed=embed)
                
                if len(chunks) > 1 and i < len(chunks) - 1:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            await ctx.send("❌ Error searching logs")
    
    @commands.command(name='clearlogs', help='Clear log file')
    @handle_errors
    @log_command
    async def clear_logs(self, ctx):
        """Clear the log file"""
        if not await self._check_permissions(ctx):
            return
        
        try:
            # Backup current log file
            if os.path.exists(self.log_file):
                backup_name = f"{self.log_file}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.log_file, backup_name)
            
            # Create new empty log file
            with open(self.log_file, 'w') as f:
                pass
            
            embed = discord.Embed(
                title="Logs Cleared",
                description="✅ Log file has been cleared",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await ctx.send(embed=embed)
            
            logger.info(f"Logs cleared by {ctx.author}")
            
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            await ctx.send("❌ Error clearing logs")
    
    @commands.command(name='logbackup', help='Create a backup of the log file')
    @handle_errors
    @log_command
    async def backup_logs(self, ctx):
        """Create a backup of the current log file"""
        if not await self._check_permissions(ctx):
            return
        
        if not os.path.exists(self.log_file):
            await ctx.send("❌ No log file found to backup")
            return
        
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{self.log_file}.backup.{timestamp}"
            
            # Copy log file
            with open(self.log_file, 'r', encoding='utf-8') as source:
                with open(backup_name, 'w', encoding='utf-8') as dest:
                    dest.write(source.read())
            
            file_size = os.path.getsize(backup_name)
            
            embed = discord.Embed(
                title="Log Backup Created",
                description=f"✅ Log backup created: `{os.path.basename(backup_name)}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Size", value=f"{file_size / 1024:.2f} KB", inline=True)
            await ctx.send(embed=embed)
            
            logger.info(f"Log backup created by {ctx.author}: {backup_name}")
            
        except Exception as e:
            logger.error(f"Error creating log backup: {e}")
            await ctx.send("❌ Error creating log backup")
    
    @commands.command(name='exportlogs', help='Export logs to a downloadable file')
    @handle_errors
    @log_command
    async def export_logs(self, ctx, lines: int = 1000, level: str = None):
        """Export logs to a downloadable file"""
        if not await self._check_permissions(ctx):
            return
        
        if lines > self.max_log_lines:
            await ctx.send(f"❌ Maximum lines allowed is {self.max_log_lines}")
            return
        
        if not os.path.exists(self.log_file):
            await ctx.send("❌ No log file found")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Filter by level if specified
            if level and level.upper() in self.log_levels:
                filtered_lines = []
                for line in log_lines:
                    if f" - {level.upper()} - " in line:
                        filtered_lines.append(line)
                log_lines = filtered_lines
            
            # Get the last N lines
            export_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
            
            if not export_logs:
                await ctx.send("❌ No logs found matching the criteria")
                return
            
            # Create export file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            export_filename = f"logs_export_{timestamp}.txt"
            export_path = os.path.join(self.logs_dir, export_filename)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(f"Bot Logs Export - {datetime.utcnow()}\n")
                f.write(f"Filter: {level if level else 'All levels'}\n")
                f.write(f"Lines: {len(export_logs)}\n")
                f.write("=" * 50 + "\n\n")
                f.writelines(export_logs)
            
            # Create file object for Discord
            file = discord.File(export_path, filename=export_filename)
            
            embed = discord.Embed(
                title="📁 Logs Exported",
                description=f"✅ Exported {len(export_logs)} log lines to file",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="File", value=export_filename, inline=True)
            embed.add_field(name="Size", value=f"{os.path.getsize(export_path) / 1024:.2f} KB", inline=True)
            if level:
                embed.add_field(name="Level Filter", value=level.upper(), inline=True)
            
            await ctx.send(embed=embed, file=file)
            
            # Clean up the file after sending
            await asyncio.sleep(5)  # Give time for download
            try:
                os.remove(export_path)
            except:
                pass  # Ignore cleanup errors
            
            logger.info(f"Logs exported by {ctx.author}: {len(export_logs)} lines")
            
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            await ctx.send("❌ Error exporting logs")
    
    @commands.command(name='loginfo', help='Show logging configuration information')
    @handle_errors
    @log_command
    async def log_info(self, ctx):
        """Show current logging configuration"""
        if not await self._check_permissions(ctx):
            return
        
        try:
            root_logger = logging.getLogger()
            current_level = logging.getLevelName(root_logger.level)
            
            embed = discord.Embed(
                title="Logging Configuration",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Current Log Level",
                value=current_level,
                inline=True
            )
            
            embed.add_field(
                name="Log File",
                value=self.log_file,
                inline=True
            )
            
            embed.add_field(
                name="Logs Directory",
                value=self.logs_dir,
                inline=True
            )
            
            # Check if log file exists and get its size
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                embed.add_field(
                    name="Log File Size",
                    value=f"{file_size / 1024 / 1024:.2f} MB",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Log File Size",
                    value="File not found",
                    inline=True
                )
            
            # Count active handlers
            handler_count = len(root_logger.handlers)
            embed.add_field(
                name="Active Handlers",
                value=str(handler_count),
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting log info: {e}")
            await ctx.send("❌ Error getting logging information")
    
    @commands.command(name='loghelp', help='Show help for logging commands')
    @handle_errors
    @log_command
    async def log_help(self, ctx):
        """Show detailed help for logging commands"""
        if not await self._check_permissions(ctx):
            return
        
        embed = discord.Embed(
            title="📋 Logging Commands Help",
            description="Commands for managing and viewing bot logs",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        commands_info = [
            ("`!logs [lines] [level]`", "View recent bot logs (default: 50 lines)"),
            ("`!loglevel <level>`", "Set bot log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
            ("`!logstats [hours]`", "Show logging statistics (default: 24 hours)"),
            ("`!searchlogs <term> [lines]`", "Search logs for specific text"),
            ("`!clearlogs`", "Clear the log file (creates backup)"),
            ("`!logbackup`", "Create a backup of the current log file"),
            ("`!exportlogs [lines] [level]`", "Export logs to downloadable file"),
            ("`!loginfo`", "Show current logging configuration"),
            ("`!loghelp`", "Show this help message")
        ]
        
        for cmd, desc in commands_info:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.add_field(
            name="📝 Examples",
            value=(
                "`!logs 100` - View last 100 log lines\n"
                "`!logs 50 ERROR` - View last 50 ERROR level logs\n"
                "`!loglevel DEBUG` - Set log level to DEBUG\n"
                "`!searchlogs error 200` - Search for 'error' in last 200 lines\n"
                "`!logstats 48` - Show stats for last 48 hours\n"
                "`!exportlogs 500 ERROR` - Export last 500 ERROR logs"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔐 Permissions",
            value="Requires 'Manage Server' permission or bot owner",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _check_permissions(self, ctx) -> bool:
        """Check if user has permission to use logging commands"""
        # Check if user has manage server permission or is bot owner
        if ctx.guild and ctx.author.guild_permissions.manage_guild:
            return True
        
        # Check if user is bot owner
        if ctx.author.id == self.bot.owner_id:
            return True
        
        await ctx.send("❌ You need 'Manage Server' permission to use logging commands")
        return False
    
    def _format_logs(self, log_lines: List[str]) -> str:
        """Format log lines for display"""
        formatted = []
        for line in log_lines:
            # Clean up the line and limit length
            cleaned = line.strip()
            if len(cleaned) > 200:
                cleaned = cleaned[:197] + "..."
            formatted.append(cleaned)
        return "\n".join(formatted)
    
    def _split_logs(self, log_text: str, max_length: int = 1900) -> List[str]:
        """Split log text into chunks that fit in Discord embeds"""
        if len(log_text) <= max_length:
            return [log_text]
        
        chunks = []
        lines = log_text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            if current_length + line_length > max_length and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

async def setup(bot):
    """Setup function for the logging commands cog"""
    await bot.add_cog(LoggingCommands(bot)) 