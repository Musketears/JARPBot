import logging
import traceback
from functools import wraps
from typing import Callable, Any
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in bot commands"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except discord.Forbidden:
            # For class methods, ctx is the second argument (after self)
            ctx = args[1] if len(args) > 1 else (args[0] if args else None)
            if ctx and hasattr(ctx, 'send'):
                await ctx.send("❌ I don't have permission to do that!")
            logger.warning(f"Forbidden error in {func.__name__}")
        except discord.HTTPException as e:
            # For class methods, ctx is the second argument (after self)
            ctx = args[1] if len(args) > 1 else (args[0] if args else None)
            if ctx and hasattr(ctx, 'send'):
                await ctx.send("❌ An error occurred with Discord.")
            logger.error(f"Discord API error in {func.__name__}: {e}")
        except discord.ext.commands.CommandError as e:
            # For class methods, ctx is the second argument (after self)
            ctx = args[1] if len(args) > 1 else (args[0] if args else None)
            if ctx and hasattr(ctx, 'send'):
                await ctx.send(f"❌ Command error: {str(e)}")
            logger.error(f"Command error in {func.__name__}: {e}")
        except Exception as e:
            # For class methods, ctx is the second argument (after self)
            ctx = args[1] if len(args) > 1 else (args[0] if args else None)
            if ctx and hasattr(ctx, 'send'):
                await ctx.send("❌ An unexpected error occurred.")
            logger.error(f"Unexpected error in {func.__name__}: {e}\n{traceback.format_exc()}")
    return wrapper

def log_command(func: Callable) -> Callable:
    """Decorator to log command usage"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # For class methods, ctx is the second argument (after self)
        ctx = args[1] if len(args) > 1 else (args[0] if args else None)
        if ctx and hasattr(ctx, 'author') and hasattr(ctx, 'guild'):
            logger.info(f"Command executed: {func.__name__} by {ctx.author} in {ctx.guild}")
        return await func(*args, **kwargs)
    return wrapper

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param}")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided.")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        # Log the error
        logger.error(f"Unhandled command error: {error}")
        await ctx.send("❌ An unexpected error occurred while processing your command.")

def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log"):
    """Setup logging configuration"""
    import os
    from datetime import datetime
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('youtube_dl').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING)

async def setup(bot):
    """Setup function for the error handler extension"""
    await bot.add_cog(ErrorHandler(bot)) 