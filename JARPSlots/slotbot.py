import os
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='?',intents=intents)

queue = []
is_stop = False
is_processing = False
current_file = ''
balances_file = 'user_balances.json'
user_balances = {}

def update_balance(id, amount):
    global user_balances
    if id in user_balances:
        user_balances[id] += amount
    else:
        user_balances[id] = 100 + amount
    with open(balances_file, 'w') as file:
        json.dump(user_balances, file)

def load_balances():
    global user_balances
    try:
        file = open(balances_file, 'r')
        user_balances = json.load(file)
    except FileNotFoundError:
        user_balances = {}

@bot.command(name='slots', help='Play the slot machine')
async def slots(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        update_balance(user_id, 0)

    bet = 5

    if bet > user_balances[user_id]:
        await ctx.send("You're too poor to play.")
        return

    update_balance(user_id, -bet)

    slots_symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
    grid = [random.choices(slots_symbols, k=3) for _ in range(3)]
    for row in grid:
        result = " | ".join(row)
        msg = await ctx.send(result)
        await asyncio.sleep(0.5)

    win_amount = 0
    for row in grid:
        if len(set(row)) == 1:
            symbol = row[0]
            if symbol == "🍒":
                win_amount += 5
            elif symbol == "🍋":
                win_amount += 10
            elif symbol == "7️⃣":
                win_amount += 15
            elif symbol == "🔔":
                win_amount += 20
            elif symbol == "💎":
                win_amount += 100


    if grid[0][0] == grid[1][1] == grid[2][2] or grid[0][2] == grid[1][1] == grid[2][0]:
        symbol = grid[1][1]
        if symbol == "🍒":
            win_amount += 2
        elif symbol == "🍋":
            win_amount += 4
        elif symbol == "🔔":
            win_amount += 8

    if all(symbol == "💎" for row in grid for symbol in row):
        win_amount = 10000000

    if win_amount > 0:
        await ctx.send(f"🎉 You won ${win_amount}!")
        update_balance(user_id, win_amount)
    else:
        await ctx.send("Sorry, you didn't win anything. Better luck next time.")

    await ctx.send(f"Your new balance is: {user_balances[user_id]}.")

@bot.command(name='balance', help='Check your balance')
async def balance(ctx):
    global user_balances
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. Your balance is 100 to start.")
    else:
        await ctx.send(f"Your current balance is {user_balances[user_id]}.")

if __name__ == "__main__" :
    load_balances()
    bot.run(TOKEN)
