"""
Fun commands for the bot (8ball, griddy, rps, etc.)
"""

import discord
from discord.ext import commands
from discord.ui import View, Select
from discord import SelectOption
import random
import csv
import os
import logging
from typing import Optional

from utils.database import db
from utils.error_handler import handle_errors, log_command

logger = logging.getLogger(__name__)


class FunCommands(commands.Cog):
    """Fun and miscellaneous commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.griddy_file = 'griddyurls.csv'
    
    @commands.command(name='8ball', help='Ask the magic 8-ball a question')
    @handle_errors
    @log_command
    async def eight_ball(self, ctx: commands.Context, *, question: Optional[str] = None):
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
    
    def _load_griddy_urls(self) -> list[str]:
        """Load griddy URLs from CSV file"""
        data = []
        try:
            with open(self.griddy_file, newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    for item in row:
                        if item.strip():
                            data.append(item.strip())
        except FileNotFoundError:
            logger.warning(f"Griddy file not found: {self.griddy_file}")
        return data
    
    def _save_griddy_urls(self, urls: list[str]) -> None:
        """Save griddy URLs to CSV file"""
        with open(self.griddy_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(urls)
    
    @commands.command(name='griddy', help='Send a random griddy image')
    @handle_errors
    @log_command
    async def griddy(self, ctx: commands.Context, msg: Optional[str] = None):
        """Send a random griddy image"""
        data = self._load_griddy_urls()
        
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
    
    @commands.command(name='griddyon', help='Griddy on someone')
    @handle_errors
    @log_command
    async def griddyon(self, ctx: commands.Context, name: str):
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
        await self.griddy(ctx)
    
    @commands.command(name='addgriddyimg', help='Add a griddy image URL')
    @handle_errors
    @log_command
    async def addgriddyimg(self, ctx: commands.Context, url: str):
        """Add a griddy image URL"""
        data = self._load_griddy_urls()
        data.append(url)
        self._save_griddy_urls(data)
        
        embed = discord.Embed(
            title="✅ Success",
            description=f"Added griddy image: {url}",
            color=0x57F287
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='rps', help='Play rock, paper, scissors')
    @handle_errors
    @log_command
    async def rps(self, ctx: commands.Context):
        """Play rock, paper, scissors"""
        
        class RPSView(View):
            def __init__(self, ctx: commands.Context):
                super().__init__(timeout=30.0)
                self.ctx = ctx
                self.add_item(RPSSelect())
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
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
            
            async def callback(self, interaction: discord.Interaction):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))
