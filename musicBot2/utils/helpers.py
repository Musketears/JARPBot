import re
import asyncio
import os
from typing import List, Optional, Dict, Any
import discord
from datetime import datetime

def validate_youtube_url(url: str) -> bool:
    """Validate if URL is a valid YouTube URL"""
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    return bool(re.match(youtube_regex, url))

def validate_bet_amount(amount: str, user_balance: int) -> Optional[int]:
    """Validate and parse bet amount"""
    try:
        if amount.lower() == "all":
            return user_balance
        
        bet = int(amount)
        if bet <= 0:
            return None
        if bet > user_balance:
            return None
        return bet
    except ValueError:
        return None

def limit_to_4000_chars(strings: List[str], limit: int = 4000) -> str:
    """Limit a list of strings to Discord's character limit"""
    result = ""
    for string in strings:
        if len(result) + len(string) + 1 > limit:
            break
        result += string + "\n"
    return result.strip() if result else "No items to display"

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS format"""
    if seconds <= 0:
        return "Unknown"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"

def format_balance(amount: int) -> str:
    """Format balance with commas"""
    return f"${amount:,}"

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Create a text-based progress bar"""
    if total == 0:
        return "█" * length
    
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    return bar

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

async def cleanup_files(files: List[str]):
    """Clean up files asynchronously"""
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Error cleaning up file {file}: {e}")

def get_user_mention(user_id: int) -> str:
    """Get user mention string"""
    return f"<@{user_id}>"

def create_paginated_embed(title: str, items: List[str], page: int = 0, items_per_page: int = 10) -> discord.Embed:
    """Create a paginated embed"""
    embed = discord.Embed(title=title, color=0x1DB954)
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = items[start_idx:end_idx]
    
    if not page_items:
        embed.description = "No items to display."
        return embed
    
    content = "\n".join(f"{i+start_idx+1}. {item}" for i, item in enumerate(page_items))
    embed.description = content
    
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    embed.set_footer(text=f"Page {page + 1}/{total_pages} • {len(items)} total items")
    
    return embed

def create_status_embed(bot, guild) -> discord.Embed:
    """Create a status embed for the bot"""
    embed = discord.Embed(title="🤖 Bot Status", color=0x1DB954)
    
    # Bot info
    embed.add_field(
        name="Bot Info",
        value=f"**Name:** {bot.user.name}\n**ID:** {bot.user.id}\n**Created:** {bot.user.created_at.strftime('%Y-%m-%d')}",
        inline=True
    )
    
    # Server info
    if guild:
        embed.add_field(
            name="Server Info",
            value=f"**Name:** {guild.name}\n**Members:** {guild.member_count}\n**Channels:** {len(guild.channels)}",
            inline=True
        )
    
    # Voice info
    voice_client = guild.voice_client if guild else None
    if voice_client and voice_client.is_connected():
        embed.add_field(
            name="Voice Status",
            value=f"**Connected:** ✅\n**Channel:** {voice_client.channel.name}\n**Playing:** {'Yes' if voice_client.is_playing() else 'No'}",
            inline=True
        )
    else:
        embed.add_field(
            name="Voice Status",
            value="**Connected:** ❌\n**Channel:** None\n**Playing:** No",
            inline=True
        )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.timestamp = datetime.now()
    
    return embed

def parse_time_string(time_str: str) -> Optional[int]:
    """Parse time string (e.g., '1m30s', '2h15m') to seconds"""
    if not time_str:
        return None
    
    total_seconds = 0
    current_num = ""
    
    for char in time_str.lower():
        if char.isdigit():
            current_num += char
        elif char == 'h':
            if current_num:
                total_seconds += int(current_num) * 3600
                current_num = ""
        elif char == 'm':
            if current_num:
                total_seconds += int(current_num) * 60
                current_num = ""
        elif char == 's':
            if current_num:
                total_seconds += int(current_num)
                current_num = ""
    
    return total_seconds if total_seconds > 0 else None

def format_time_string(seconds: int) -> str:
    """Format seconds to human readable time string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m{remaining_seconds}s" if remaining_seconds > 0 else f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h{remaining_minutes}m" if remaining_minutes > 0 else f"{hours}h"

def create_error_embed(error_message: str) -> discord.Embed:
    """Create an error embed"""
    embed = discord.Embed(
        title="❌ Error",
        description=error_message,
        color=0xE02B2B
    )
    return embed

def create_success_embed(message: str) -> discord.Embed:
    """Create a success embed"""
    embed = discord.Embed(
        title="✅ Success",
        description=message,
        color=0x57F287
    )
    return embed

def create_info_embed(title: str, message: str) -> discord.Embed:
    """Create an info embed"""
    embed = discord.Embed(
        title=title,
        description=message,
        color=0xBEBEFE
    )
    return embed 