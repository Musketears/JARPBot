import discord
from discord.ext import commands
import asyncio
import random
import logging
from typing import Optional

from games.gambling import gambling_manager, higher_lower_game, slot_machine, alex_roulette
from games.gacha import gacha_system
from utils.database import db
from utils.error_handler import handle_errors, log_command
from utils.helpers import validate_bet_amount, format_balance, create_success_embed, create_error_embed, create_info_embed
from config import config

logger = logging.getLogger(__name__)

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='balance', help='Check your balance')
    @handle_errors
    @log_command
    async def balance(self, ctx):
        """Check user's balance"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        
        embed = discord.Embed(title="💰 Balance", color=0x57F287)
        embed.add_field(name="Current Balance", value=format_balance(balance))
        
        # Get gambling stats
        stats = await db.get_gambling_stats(user_id)
        if stats['total_games'] > 0:
            embed.add_field(
                name="📊 Gambling Stats",
                value=f"**Total Games:** {stats['total_games']}\n"
                      f"**Net Profit:** {format_balance(stats['net_profit'])}\n"
                      f"**Today's Games:** {stats['today_games']}",
                inline=False
            )
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='gamble', help='Play higher/lower game')
    @handle_errors
    @log_command
    async def gamble(self, ctx, bet: str):
        """Play higher/lower gambling game"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        
        # Validate bet amount
        bet_amount = validate_bet_amount(bet, balance)
        if bet_amount is None:
            embed = create_error_embed("Invalid bet amount. Use a number or 'all'.")
            await ctx.send(embed=embed)
            return
        
        # Check gambling limits
        can_gamble, error_message = await gambling_manager.check_gambling_limits(user_id, bet_amount)
        if not can_gamble:
            embed = create_error_embed(error_message)
            await ctx.send(embed=embed)
            return
        
        # Start the game
        game_result = await higher_lower_game.start_game(user_id, bet_amount)
        
        embed = discord.Embed(title="🎲 Higher/Lower", color=0xBEBEFE)
        embed.add_field(name="Current Number", value=f"**{game_result['current_number']}**", inline=True)
        embed.add_field(name="Your Bet", value=format_balance(bet_amount), inline=True)
        embed.add_field(name="Instructions", value="Reply with `higher` or `lower`", inline=False)
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        
        # Wait for user response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['higher', 'lower']
        
        try:
            guess_msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            result = await higher_lower_game.process_guess(user_id, guess_msg.content.lower())
            
            if 'error' in result:
                embed = create_error_embed(result['error'])
                await ctx.send(embed=embed)
                return
            
            # Create result embed
            color = 0x57F287 if result['win'] else 0xE02B2B
            embed = discord.Embed(title="🎲 Game Result", color=color)
            
            embed.add_field(name="Result", value=result['message'], inline=False)
            embed.add_field(name="Next Number", value=f"**{result['next_number']}**", inline=True)
            embed.add_field(name="New Balance", value=format_balance(result['new_balance']), inline=True)
            
            if result['win']:
                embed.add_field(name="💰 Winnings", value=format_balance(result['win_amount']), inline=True)
            
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = create_error_embed("Game timed out. You took too long to respond.")
            await ctx.send(embed=embed)
    
    @commands.command(name='slots', help='Play the slot machine')
    @handle_errors
    @log_command
    async def slots(self, ctx):
        """Play the slot machine"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        bet_amount = 5  # Fixed bet for slots
        
        # Check gambling limits
        can_gamble, error_message = await gambling_manager.check_gambling_limits(user_id, bet_amount)
        if not can_gamble:
            embed = create_error_embed(error_message)
            await ctx.send(embed=embed)
            return
        
        # Spin the slots
        result = await slot_machine.spin(user_id, bet_amount)
        
        # Create slots display
        embed = discord.Embed(title="🎰 Slot Machine", color=0xFFD700)
        
        # Display the grid
        grid_text = ""
        for i, row in enumerate(result['grid']):
            grid_text += " | ".join(row) + "\n"
            if i < 2:  # Add separator between rows
                grid_text += "─" * 15 + "\n"
        
        embed.add_field(name="🎰 Reels", value=f"```\n{grid_text}```", inline=False)
        
        # Add result info
        embed.add_field(name="Bet Amount", value=format_balance(bet_amount), inline=True)
        embed.add_field(name="New Balance", value=format_balance(result['new_balance']), inline=True)
        
        if result['win_amount'] > 0:
            embed.add_field(name="💰 Winnings", value=format_balance(result['win_amount']), inline=True)
            embed.color = 0x57F287
        else:
            embed.color = 0xE02B2B
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='alex_roulette', help='Play Alex\'s roulette')
    @handle_errors
    @log_command
    async def alex_roulette(self, ctx):
        """Play Alex's roulette"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        bet_amount = 10  # Fixed bet for roulette
        
        if balance < bet_amount:
            embed = create_error_embed("You're poor. No roulette for you.")
            await ctx.send(embed=embed)
            return
        
        # Update balance
        new_balance = await db.update_balance(user_id, -bet_amount)
        
        # Spin the roulette
        result = await alex_roulette.spin(user_id)
        
        embed = discord.Embed(title="🎲 Alex's Roulette", color=0xBEBEFE)
        embed.add_field(name="Number", value=f"**{result['number']}**", inline=True)
        embed.add_field(name="New Balance", value=format_balance(new_balance), inline=True)
        embed.add_field(name="Result", value=result['message'], inline=False)
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        
        # Play special music if triggered
        if result['special'] and 'url' in result:
            try:
                # Import here to avoid circular imports
                from commands.music_commands import MusicCommands
                music_cog = self.bot.get_cog('MusicCommands')
                if music_cog:
                    await music_cog.play(ctx, query=result['url'])
            except Exception as e:
                logger.error(f"Error playing roulette music: {e}")
    
    @commands.command(name='pull', help='Pull a gacha character (Cost: 10)')
    @handle_errors
    @log_command
    async def pull(self, ctx):
        """Pull a gacha character"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        
        if balance < config.gacha_cost:
            embed = create_error_embed("You don't have enough money for a pull.")
            await ctx.send(embed=embed)
            return
        
        # Update balance
        new_balance = await db.update_balance(user_id, -config.gacha_cost)
        
        # Perform gacha pull
        result = await gacha_system.pull(user_id)
        character = result['character']
        
        # Create embed
        color = gacha_system.get_rarity_color(character.rarity)
        embed = discord.Embed(title="🎉 Gacha Pull!", color=color)
        
        embed.add_field(
            name="Character",
            value=f"**{character.rarity}★ {character.adjective} {character.name}**",
            inline=False
        )
        
        embed.add_field(name="Rarity", value="★" * character.rarity, inline=True)
        embed.add_field(name="Sell Value", value=format_balance(character.sell_value), inline=True)
        embed.add_field(name="New Balance", value=format_balance(new_balance), inline=True)
        
        # Add pity info
        embed.add_field(
            name="Pity Info",
            value=f"**Total Pulls:** {result['pity_pulls']}\n"
                  f"**Next 4★:** {result['next_guaranteed_4']} pulls\n"
                  f"**Next 5★:** {result['next_guaranteed_5']} pulls",
            inline=False
        )
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='inventory', help='Check your gacha inventory')
    @handle_errors
    @log_command
    async def inventory(self, ctx):
        """Show user's gacha inventory"""
        user_id = str(ctx.author.id)
        inventory = await db.get_gacha_inventory(user_id)
        stats = await gacha_system.get_inventory_stats(user_id)
        
        embed = discord.Embed(title="📦 Gacha Inventory", color=0xBEBEFE)
        
        if not inventory:
            embed.description = "You don't have any characters yet. Try `!pull` to get some!"
        else:
            # Show inventory summary
            embed.add_field(
                name="📊 Summary",
                value=f"**Total Characters:** {stats['total_characters']}\n"
                      f"**Total Value:** {format_balance(stats['total_value'])}",
                inline=False
            )
            
            # Show rarity breakdown
            rarity_text = ""
            for rarity, count in stats['rarity_counts'].items():
                if count > 0:
                    rarity_text += f"{'★' * rarity}: {count}\n"
            
            if rarity_text:
                embed.add_field(name="🎯 Rarity Breakdown", value=rarity_text, inline=True)
            
            # Show rarest character
            if stats['rarest_character']:
                rarest = stats['rarest_character']
                embed.add_field(
                    name="🏆 Rarest Character",
                    value=f"**{rarest['rarity']}★ {rarest['adjective']} {rarest['character_name']}**",
                    inline=True
                )
            
            # Show recent characters (last 5)
            recent_text = ""
            for item in inventory[:5]:
                recent_text += f"{item['rarity']}★ {item['adjective']} {item['character_name']}\n"
            
            if recent_text:
                embed.add_field(name="🆕 Recent Pulls", value=recent_text, inline=False)
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='stats', help='Show your gambling statistics')
    @handle_errors
    @log_command
    async def stats(self, ctx):
        """Show comprehensive gambling statistics"""
        user_id = str(ctx.author.id)
        stats = await db.get_gambling_stats(user_id)
        
        embed = discord.Embed(title="📊 Gambling Statistics", color=0xBEBEFE)
        
        if stats['total_games'] == 0:
            embed.description = "You haven't played any games yet!"
        else:
            # Overall stats
            embed.add_field(
                name="📈 Overall Stats",
                value=f"**Total Games:** {stats['total_games']}\n"
                      f"**Total Bet:** {format_balance(stats['total_bet'])}\n"
                      f"**Total Won:** {format_balance(stats['total_won'])}\n"
                      f"**Net Profit:** {format_balance(stats['net_profit'])}",
                inline=False
            )
            
            # Today's stats
            embed.add_field(
                name="📅 Today's Stats",
                value=f"**Games Played:** {stats['today_games']}\n"
                      f"**Amount Bet:** {format_balance(stats['today_bet'])}\n"
                      f"**Amount Won:** {format_balance(stats['today_won'])}",
                inline=True
            )
            
            # Win rate
            win_rate = (stats['total_won'] / stats['total_bet'] * 100) if stats['total_bet'] > 0 else 0
            embed.add_field(
                name="🎯 Win Rate",
                value=f"**{win_rate:.1f}%**",
                inline=True
            )
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='problem', help='Get help for gambling addiction')
    @handle_errors
    @log_command
    async def problem(self, ctx):
        """Gambling addiction help command"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        
        embed = discord.Embed(
            title="🆘 Gambling Addiction Help",
            description="If you're struggling with gambling, help is available.",
            color=0xE02B2B
        )
        
        embed.add_field(
            name="📞 National Problem Gambling Helpline",
            value="**1-800-662-4357**\nAvailable 24/7, free and confidential",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Online Resources",
            value="• [Gamblers Anonymous](https://www.gamblersanonymous.org/)\n"
                  "• [National Council on Problem Gambling](https://www.ncpgambling.org/)",
            inline=False
        )
        
        embed.add_field(
            name="💡 Self-Exclusion",
            value="Consider using Discord's self-exclusion features or taking a break from gambling activities.",
            inline=False
        )
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GameCommands(bot)) 