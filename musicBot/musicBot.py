# bot.py
import os
import random
import youtube_dl
import discord
from discord.ext import commands
from dotenv import load_dotenv
from youtube_search import YoutubeSearch
import yt_dlp as youtube_dl
import asyncio
import string
import time
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)

queue = []
is_stop = False
is_processing = False
current_file = ''
balances_file = 'user_balances.json'
user_balances = {}

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        og_filename = data['title'] if stream else ytdl.prepare_filename(data)
        filename, file_extension = os.path.splitext(og_filename)
        filename = f"{filename}_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}{file_extension}"
        os.rename(og_filename, filename)
        return filename


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

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    global queue
    remove_files(queue)
    queue = []
    global is_stop
    is_stop = True
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        time.sleep(5)
        remove_files([current_file])
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='play_link', help='To play song from youtube link')
async def play_url(ctx,url):
    global is_processing
    try :
        voice_client = ctx.message.guild.voice_client
        if voice_client == None:
            voice_client = ctx.message.author.voice.channel
            await voice_client.connect()
            await play_url(ctx, url)
            return
        if is_processing or voice_client.is_playing():
            filename = await YTDLSource.from_url(url, loop=bot.loop)
            queue.append(filename)
            return
        server = ctx.message.guild
        voice_channel = server.voice_client
        async with ctx.typing():
            is_processing = True
            filename = await YTDLSource.from_url(url, loop=bot.loop)
            global current_file
            current_file = filename
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename), after=lambda ex: bot.loop.create_task(play_next(ctx)))
            is_processing = False
        await ctx.send('**Now playing:** {}'.format(filename))
    except:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='play', help='To play song from youtube search')
async def play(ctx,*args):
    try :
        delimiter = ' '
        url = "https://www.youtube.com" + YoutubeSearch(delimiter.join(args), max_results=1).to_dict()[0]['url_suffix']
        await play_url(ctx, url)
    except:
        await ctx.send("The bot is not connected to a voice channel.")

async def play_next(ctx):
    global current_file
    remove_files([current_file])
    if not len(queue) == 0 and not is_stop:
        server = ctx.message.guild
        voice_channel = server.voice_client
        async with ctx.typing():
            current_file = queue[0]
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=queue[0]), after=lambda ex: bot.loop.create_task(play_next(ctx)))
        await ctx.send('**Now playing:** {}'.format(queue.pop(0)))
    elif not is_stop:
        await ctx.send('There is nothing in queue')

@bot.command(name='skip', help='This command skip the current song and plays the next in queue (if there is one)')
async def skip(ctx):
    global is_stop
    is_stop = False
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play command")

@bot.command(name='queue', help='See whats in queue')
async def print_queue(ctx):
    await ctx.send(queue)

def remove_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
        else:
            print("The file does not exist" + str(file))

@bot.command(name='alex_roulette', help='ggs')
async def alex_roulette(ctx):
    user_id = str(ctx.author.id)
    
    if user_balances[user_id] < 10:
        await ctx.send("You're poor as fuck. No roulette for you")
    
    else:
        update_balance(user_id, -10)
        await ctx.send(f"Your new balance is: {user_balances[user_id]}")
        roulette_num = random.randint(1,100)
        if roulette_num >= 90:
            try:
                await ctx.send("ggs")
                url = "https://www.youtube.com/watch?v=1EUoIhob8t8"
                await play_url(ctx, url)
            except:
                await ctx.send("The bot is not connected to a voice channel.")
        if roulette_num <= 10:
            try:
                await ctx.send("ff")
                url = "https://www.youtube.com/watch?v=d3h1I3QDEHU"
                await play_url(ctx, url)
            except:
                await ctx.send("The bot is not connected to a voice channel.")
        if roulette_num == 20:
            try:
                await ctx.send("My favorite song")
                url = "https://www.youtube.com/watch?v=VZZCXP_rFKk"
                await play_url(ctx, url)
            except:
                await ctx.send("The bot is not connected to a voice channel.")
        else:
            try:
                await ctx.send("Thanks for the $10 xD, try again?")
            except:
                await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='gamble', help='Gamble your life savings')
async def gamble(ctx, bet: int = None):
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        update_balance(user_id, 0)

    if bet is None or bet <= 0:
        await ctx.send("Use your fucking brain and enter a bet idiot")
        return

    if bet > user_balances[user_id]:
        await ctx.send("You're too poor to bet. Get lost loser")
        return
    elif bet <= 0:
        await ctx.send("Enter your bet pussy")
        return

    current_number = random.randint(1, 10)
    await ctx.send(f'The current number is {current_number}. Will the next be higher or lower?')

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['higher', 'lower']

    try:
        guess_msg = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send('You took too long, loser. Get fucked and fuck off')
        return

    next_number = random.randint(1,10)
    player_guess = guess_msg.content.lower()

    win = (player_guess == 'higher' and next_number > current_number) or (player_guess == 'lower' and next_number < current_number)

    if win:
        await ctx.send(f"Congrats, you were correct! This means you're not a loser, as the next number was {next_number}.")
        update_balance(user_id, bet)
    else:
        await ctx.send(f"Damn, what a loser. You lost. The number was {next_number}. Get fucked and fuck off. Be poor.")
        update_balance(user_id, bet * -1)

    await ctx.send(f"Your new balance is: {user_balances[user_id]}")

@bot.command(name='balance', help='Check your balance you fucking addict')
async def balance(ctx):
    global user_balances
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. Welcome to hell. Your balance is 100 to start.")
    else:
        await ctx.send(f"Your current balance is {user_balances[user_id]}.")

if __name__ == "__main__" :
    load_balances()
    bot.run(TOKEN)