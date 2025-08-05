import discord
from discord.ext import commands
import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime

from config import config
from utils.error_handler import setup_logging, ErrorHandler
from utils.database import db
from utils.cache_manager import cache_manager
from utils.helpers import create_status_embed

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f'Received signal {signum}, shutting down gracefully...')
    
    # Schedule bot shutdown
    asyncio.create_task(bot.close())

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)

# Set up signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    
    # Set initial status
    await update_status()
    
    # Load all cogs
    await load_extensions()
    
    # Start periodic cache cleanup task
    asyncio.create_task(periodic_cache_cleanup())
    
    logger.info('Bot is ready!')

@bot.event
async def on_disconnect():
    """Called when the bot disconnects"""
    logger.info('Bot disconnected from Discord')

@bot.event
async def on_close():
    """Called when the bot is closing"""
    logger.info('Bot is shutting down, cleaning up files...')
    
    # Clean up music files
    try:
        from music.player import music_player
        if music_player.current_track:
            music_player.cleanup_current_track()
        if music_player.queue:
            await music_player.cleanup_files(music_player.queue)
        
        # Clean up orphaned files
        music_player.cleanup_orphaned_files()
        
        logger.info('Music files cleaned up successfully')
    except Exception as e:
        logger.error(f'Error cleaning up music files: {e}')
    
    # Close database connection
    try:
        await db.close()
        logger.info('Database connection closed')
    except Exception as e:
        logger.error(f'Error closing database connection: {e}')
    
    logger.info('Bot shutdown complete')

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    logger.error(f'Command error in {ctx.command}: {error}')
    
    # Let the error handler cog handle it
    pass

async def load_extensions():
    """Load all bot extensions/cogs"""
    extensions = [
        'utils.error_handler',  # Load error handler first
        'commands.music_commands',
        'commands.playlist_commands',
        'commands.game_commands',
        'commands.logging_commands',
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f'Loaded extension: {extension}')
        except Exception as e:
            logger.error(f'Failed to load extension {extension}: {e}')

async def update_status():
    """Update bot status"""
    try:
        # Get a random guild member for status
        if bot.guilds:
            guild = bot.guilds[0]  # Use first guild
            members = [member for member in guild.members if not member.bot]
            if members:
                random_member = random.choice(members)
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{random_member.name} shower"
                )
                await bot.change_presence(activity=activity)
    except Exception as e:
        logger.error(f'Error updating status: {e}')

async def periodic_cache_cleanup():
    """Periodic cache cleanup task"""
    while True:
        try:
            # Wait for 6 hours before first cleanup
            await asyncio.sleep(6 * 60 * 60)  # 6 hours
            
            logger.info("Starting periodic cache cleanup...")
            result = await cache_manager.cleanup_cache()
            
            if result['cleaned'] > 0:
                logger.info(f"Periodic cache cleanup: {result['cleaned']} entries removed, {result['freed_mb']}MB freed")
            else:
                logger.info("Periodic cache cleanup: No entries needed cleanup")
                
        except Exception as e:
            logger.error(f"Error during periodic cache cleanup: {e}")
        
        # Run cleanup every 12 hours
        await asyncio.sleep(12 * 60 * 60)  # 12 hours

@bot.command(name='status', help='Show bot status')
async def status(ctx):
    """Show bot status information"""
    embed = create_status_embed(bot, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name='ping', help='Check bot latency')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{latency}ms**",
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command(name='refresh_status', help='Refresh bot status')
async def refresh_status(ctx):
    """Refresh bot status"""
    await update_status()
    embed = discord.Embed(
        title="✅ Status Updated",
        description="Bot status has been refreshed!",
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command(name='8ball', help='Ask the magic 8-ball a question')
async def eight_ball(ctx, *, question: str = None):
    """Magic 8-ball command"""
    if not question:
        embed = discord.Embed(
            title="❌ Error",
            description="You need to ask a question!",
            color=0xE02B2B
        )
        await ctx.send(embed=embed)
        return
    
    responses = [
        "Yes.",
        "No.",
        "I would get Sticky's instead.",
        "Probably...",
        "Probably not...",
        "I would ask Jackson for his opinion.",
        "I'd go with whatever Alex says.",
        "If Ryan says yes, then it's definitely a no.",
        "Only if Priscilla approves.",
        "You should gamble instead...",
        "Maybe...",
        "Ask me again",
        "ERROR: QUESTION TOO STUPID TO RESPOND TO",
        "What does your gut say? Go with that.",
        "Definitely a no."
    ]
    
    response = random.choice(responses)
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}\n\n**Answer:** {response}",
        color=0xBEBEFE
    )
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='griddy', help='Send a random griddy image')
async def griddy(ctx, msg=None):
    """Send a random griddy image"""
    try:
        import csv
        data = []
        with open('griddyurls.csv', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                for item in row:
                    data.append(item)
        
        if data:
            random_url = random.choice(data)
            await ctx.send(random_url, reference=msg)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No griddy images available.",
                color=0xE02B2B
            )
            await ctx.send(embed=embed)
    except FileNotFoundError:
        embed = discord.Embed(
            title="❌ Error",
            description="Griddy images file not found.",
            color=0xE02B2B
        )
        await ctx.send(embed=embed)

@bot.command(name='griddyon', help='Griddy on someone')
async def griddyon(ctx, name: str):
    """Griddy on someone"""
    await db.increment_griddy_count(name)
    count = await db.get_griddy_count(name)
    
    embed = discord.Embed(
        title="🕺 Griddy",
        description=f"{name} has been griddied on **{count}** times!",
        color=0x57F287
    )
    await ctx.send(embed=embed)
    
    # Send a griddy image
    await griddy(ctx)

@bot.command(name='addgriddyimg', help='Add a griddy image URL')
async def addgriddyimg(ctx, url: str):
    """Add a griddy image URL"""
    try:
        import csv
        data = []
        with open('griddyurls.csv', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                for item in row:
                    data.append(item)
        
        data.append(url)
        
        with open('griddyurls.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data)
        
        embed = discord.Embed(
            title="✅ Success",
            description=f"Added griddy image: {url}",
            color=0x57F287
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to add griddy image: {str(e)}",
            color=0xE02B2B
        )
        await ctx.send(embed=embed)

@bot.command(name='rps', help='Play rock, paper, scissors')
async def rps(ctx):
    """Play rock, paper, scissors"""
    from discord.ui import View, Select
    from discord import SelectOption
    
    class RPSView(View):
        def __init__(self, ctx):
            super().__init__(timeout=30.0)
            self.ctx = ctx
            self.add_item(RPSSelect())
        
        async def interaction_check(self, interaction):
            return interaction.user.id == self.ctx.author.id
    
    class RPSSelect(Select):
        def __init__(self):
            options = [
                SelectOption(label="Rock", description="You choose rock", emoji="🪨"),
                SelectOption(label="Paper", description="You choose paper", emoji="🧻"),
                SelectOption(label="Scissors", description="You choose scissors", emoji="✂️"),
            ]
            super().__init__(
                placeholder="Choose your weapon...",
                min_values=1,
                max_values=1,
                options=options
            )
        
        async def callback(self, interaction):
            user_choice = self.values[0].lower()
            bot_choice = random.choice(['rock', 'paper', 'scissors'])
            
            # Determine winner
            choices = {'rock': 0, 'paper': 1, 'scissors': 2}
            user_idx = choices[user_choice]
            bot_idx = choices[bot_choice]
            
            winner = (3 + user_idx - bot_idx) % 3
            
            # Update balance
            user_id = str(interaction.user.id)
            if winner == 0:  # Draw
                balance_change = -1
                result_msg = "**It's a draw!**"
                color = 0xF59E42
            elif winner == 1:  # User wins
                balance_change = 5
                result_msg = "**You won!**"
                color = 0x57F287
            else:  # Bot wins
                balance_change = -5
                result_msg = "**You lost!**"
                color = 0xE02B2B
            
            new_balance = await db.update_balance(user_id, balance_change)
            
            embed = discord.Embed(
                title="🪨 Rock, Paper, Scissors",
                description=f"{result_msg}\nYou chose **{user_choice}** and I chose **{bot_choice}**.",
                color=color
            )
            embed.add_field(name="New Balance", value=f"${new_balance:,}")
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            
            await interaction.response.edit_message(embed=embed, view=None)
    
    view = RPSView(ctx)
    embed = discord.Embed(
        title="🪨 Rock, Paper, Scissors",
        description="Choose your weapon!",
        color=0xBEBEFE
    )
    await ctx.send(embed=embed, view=view)

async def main():
    """Main function to run the bot"""
    try:
        logger.info('Starting bot...')
        await bot.start(config.token)
    except Exception as e:
        logger.error(f'Error starting bot: {e}')
        raise

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main()) 