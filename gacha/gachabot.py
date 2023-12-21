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
bot = commands.Bot(command_prefix='~',intents=intents)

is_stop = False
is_processing = False
current_file = ''
balances_file = 'user_balances.json'
#TODO create dict that includes "balance" and "persons"
user_balances = {}
#user_balances format:
#{unique user id: {"balance":100, "person":["default person"]}, unique user id: {"balance":100, "person":["default person"]}, ...}
person_pool = ["Alex","Ryan","Priscilla","Jackson","Holli","Nathan"]
#adjective additional sell value will be equal to index of this list
adjectives_pool = ["Default", "Homeless", "Dumb", "Boring", "Sleepy", "Hungry", "Hairy", "Stinky", "Silly", "Emo", "K/DA", "Edgelord", "Roided", "Zombie", "Smoll", "Tilted", "Large", "Biblically Accurate", "Skibidi", "Goated"]


def update_balance(id, amount, person_in):
    global user_balances
    if id in user_balances:
        prev_amount = amount
        user_balances[id]["balance"] += amount
        user_balances[id]["person"].append(person_in)
    else:
        user_balances[id] = {"balance": 100 + amount, "person": [person_in]}
    with open(balances_file, 'w') as file:
        json.dump(user_balances, file)

def load_balances():
    global user_balances
    try:
        file = open(balances_file, 'r')
        user_balances = json.load(file)
    except FileNotFoundError:
        user_balances = {}


@bot.command(name='pull', help='Pulls 1 person. Cost = 10')
async def pull(ctx):
    global person_pool
    global adjectives_pool
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        update_balance(user_id, 0, '3 ★ Default Person')

    bet = 10

    if bet > user_balances[user_id]["balance"]:
        await ctx.send("You're too poor to play.")
        return
    
   #detemines rarity
    new_person = ""
    result = random.randint(1,100)
    if result == 1:
        new_person = '5 ★ '

    if result >= 2 and result <= 15:
        new_person = '4 ★ '

    if result >= 15 and result <= 50:
        new_person = '3 ★ '
    else:
        new_person = '2 ★ '
    
    #pick random adjective
    new_person = new_person + random.choice(adjectives_pool) + " "
    #pick random person
    new_person = new_person + random.choice(person_pool)
    

    update_balance(user_id, -bet, new_person)
    temp_balance = user_balances[user_id]["balance"]
    await ctx.send(f"Congratulations! You got a {new_person}!\nYour new balance is: {temp_balance}.")

#TODO add a sell command

@bot.command(name='balance', help='Check your balance')
async def balance(ctx):
    global user_balances
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. Your balance is 100 to start.")
    else:
        temp_balance = user_balances[user_id]["balance"]
        await ctx.send(f"Your current balance is {temp_balance}.")

@bot.command(name='gacha_inv', help='Check your gacha inventory')
async def gacha_inv(ctx):
    global user_balances
    output_str = ""
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. You have a 3 ★ Default Person to start.")
    else:
        for person in user_balances[user_id]["person"]:
            output_str = output_str + person + "\n"
        await ctx.send(output_str)
        

if __name__ == "__main__" :
    load_balances()
    bot.run(TOKEN)
