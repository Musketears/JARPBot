# bot.py
import os
import discord
import random
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='?',intents=intents)

@bot.command(name='8ball', help='Ask a yes/no question and I will respond with the best course of action.')
async def ball(ctx, msg=None):

    if msg is None:
        await ctx.send("You have to ask a question.")
        return

    ask1 = "Yes."
    ask2 = "No."
    ask3 = "I would get Sticky's instead."
    ask4 = "Probably..."
    ask5 = "Probably not..."
    ask6 = "I would ask Jackson for his opinion."
    ask7 = "I'd go with whatever Alex says."
    ask8 = "If Ryan says yes, then it's definitely a no."
    ask9 = "Only if Priscilla approves."
    ask10 = "You should gamble instead..."
    ask11 = "Maybe..."
    ask12 = "Ask me again"
    ask13 = "ERROR: QUESTION TOO STUPID TO RESPOND TO"
    ask14 = "What does your gut say? Go with that."
    ask15 = "Definitely a no."

    responses = [ask1, ask2, ask3, ask4, ask5, ask6, ask7, ask8, ask9, ask10, ask11, ask12, ask13, ask14, ask15]

    selectedStatement = random.choice(responses)
    await ctx.send(selectedStatement)

if __name__ == "__main__" :
    bot.run(TOKEN)