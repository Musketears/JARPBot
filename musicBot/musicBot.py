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
import subprocess
import platform
import requests
import base64
import csv
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET') 

ffmpeg_path = 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg'

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)

queue = []
is_stop = False
is_processing = False
current_file = ''
balances_file = 'user_balances.json'
griddies_file = 'griddy_balances.json'
gachas_file = 'gacha_balances.json'
user_balances = {}
user_griddy = {}
user_gachas = {}

#{unique user id: {"balance":100, "person":["default person"]}, unique user id: {"balance":100, "person":["default person"]}, ...}
person_pool = ["Alex","Ryan","Priscilla","Jackson","Holli","Nathan"]
#adjective additional sell value will be equal to index of this list
adjectives_pool = ["Default", "Homeless", "Dumb", "Boring", "Sleepy", "Hungry", "Hairy", "Stinky", "Silly", "Emo", "K/DA", "Edgelord", "Roided", "Zombie", "Smoll", "Tilted", "Large", "Biblically Accurate", "Skibidi", "Goated"]

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
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
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

@bot.event
async def on_ready():
    await refresh(None)
    
@bot.command(name='refresh_status')
async def refresh(ctx):
    members = []
    for guild in bot.guilds:
        if guild.id == 1166433978681667614:
            for member in guild.members:
                if not member.bot:
                    members.append(member.name)
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"%s shower" % members[random.randint(0,len(members)-1)]))


@bot.command(name='griddy')
async def griddy(ctx, msg=None):
    data = []
    with open('griddyurls.csv', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            for item in row:
                data.append(item)
    await ctx.send(data[random.randint(0,len(data)-1)], reference=msg)
    
@bot.command(name='griddyon')
async def griddyon(ctx, name):
    addgriddy(name)
    msg = await ctx.send(name + ' has been griddied on ' + str(user_griddy[name]) + ' times')
    await griddy(ctx, msg)

@bot.command(name='addgriddyimg')
async def addgriddyimg(ctx, url):
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

        await ctx.send(url)
        

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
        
def load_griddies():
    global user_griddy
    try:
        file = open(griddies_file, 'r')
        user_griddy = json.load(file)
    except FileNotFoundError:
        user_griddy = {}
        
def addgriddy(name):
    global user_griddy
    if name in user_griddy:
        user_griddy[name] += 1
    else:
        user_griddy[name] = 1
    with open(griddies_file, 'w') as file:
        json.dump(user_griddy, file)

def load_gachas():
    global user_gachas
    try:
        file = open(gachas_file, 'r')
        user_gachas = json.load(file)
    except FileNotFoundError:
        user_gachas = {}

def add_gacha(id, person_in):
    global user_gachas
    if id in user_gachas:
        user_gachas[id].append(person_in)
    else:
        user_gachas[id] = [person_in]
    with open(gachas_file, 'w') as file:
        json.dump(user_gachas, file)

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
            voice_channel.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=filename), after=lambda ex: bot.loop.create_task(play_next(ctx)))
            is_processing = False
        await ctx.send('**Now playing:** {}'.format(filename))
    except Exception as e:
        await ctx.send(f"There was an error playing the song: {url} \n {e}")

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
            voice_channel.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=queue[0]), after=lambda ex: bot.loop.create_task(play_next(ctx)))
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
    formatted_queue = []
    for f in queue:
        formatted_title = re.sub(r'\[.*', '', f).replace('_', ' ').strip()
        formatted_title = re.sub(r'\.\w+$', '', formatted_title)
        formatted_queue.append(formatted_title)
    await ctx.send(limit_to_4000_chars(formatted_queue))

def limit_to_4000_chars(strings, limit=4000):
    result = ""
    for string in strings:
        # Check if adding the next string would exceed the limit
        if len(result) + len(string) + 1 > limit:  # +1 for the newline or separator
            break
        # Add the string and a newline separator
        result += string + "\n"
    return result.strip() if len(result) > 0 else "There is nothing in queue"  # Strip trailing newline if present

def remove_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
        else:
            print("The file does not exist" + str(file))

@bot.command(name='shuffle', help='Shuffule the current queue')
async def shuffle(ctx):
    random.shuffle(queue)
    await print_queue(ctx)

@bot.command(name='alex_roulette', help='ggs')
async def alex_roulette(ctx):
    user_id = str(ctx.author.id)
    
    if user_balances[user_id] < 10:
        await ctx.send("You're poor. No roulette for you")
    
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
async def gamble(ctx, bet: str = None):
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        update_balance(user_id, 0)

    if bet is None:
        await ctx.send("Use your brain and enter a bet too.")
        return
    
    if bet == "all":
        bet = user_balances[user_id]
    else:
        try:
            bet = int(bet)
        except ValueError:
            await ctx.send("Make sure your bet is an integer.")
            return
    
    if bet is None or bet <= 0:
        await ctx.send("Use your brain and enter a bet too.")
        return

    if bet > user_balances[user_id]:
        await ctx.send("You're too poor to bet.")
        return
    elif bet <= 0:
        await ctx.send("Enter your bet.")
        return

    current_number = random.randint(1, 10)
    await ctx.send(f'The current number is {current_number}. Will the next be higher or lower?')

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['higher', 'lower']

    try:
        guess_msg = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send('You took too long.')
        return

    possible_numbers = [num for num in range(1, 11) if num != current_number]
    next_number = random.choice(possible_numbers)
    player_guess = guess_msg.content.lower()

    win = (player_guess == 'higher' and next_number > current_number) or (player_guess == 'lower' and next_number < current_number)

    if win:
        await ctx.send(f"Congrats, you were correct! The next number was {next_number}.")
        update_balance(user_id, bet)
    else:
        await ctx.send(f"You lost. The number was {next_number}.")
        update_balance(user_id, bet * -1)

    await ctx.send(f"Your new balance is: {user_balances[user_id]}")

@bot.command(name='balance', help='Check your balance')
async def balance(ctx):
    global user_balances
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. Your balance is 100 to start.")
    else:
        await ctx.send(f"Your current balance is {user_balances[user_id]}.")
        
@bot.command(name='i_have_a_problem', help='You have an issue if you use this')
async def problem(ctx):
    global user_balances
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        await ctx.send("You are a new player. Your balance is 100 to start.")
    else:
        msg = 'I have a problem, I need to stop gambling, I need to call 1-800-662-4357'
        await ctx.send("type: " + msg)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        guess_msg = await bot.wait_for('message', check=check, timeout=30.0)
        if guess_msg.content == msg:
            update_balance(user_id, 10)
            await ctx.send(f"Your current balance is {user_balances[user_id]}.")
        else:
            await ctx.send("you are a degenerate, get some help")
            
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
    
@bot.command(name='update_bot', help='updates the bot')
async def update_bot(ctx):
    subprocess.run(['bash','../pull_and_restart.sh'])

@bot.command(name='vpn', help='updates the vpn')
async def update_vpn(ctx):
    result = subprocess.run(['nordvpn','connect','united_states'])
    while True:
        try:
            await ctx.send(result.stdout)
        except:
            pass

@bot.command(name='test_embed', help='test embed')
async def test_embed(ctx):
    embed=discord.Embed(title="Slots", description="")
    embed.add_field(name="", value="7️⃣ | 7️⃣ | 🍋 \n 🍋 | 🔔 | 🍋 \n 🔔 | 7️⃣ | 💎", inline=False)
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(.5)
    embed=discord.Embed(title="Slots", description="")
    embed.add_field(name="", value="💎 | 💎 | 💎 \n 💎 | 💎 | 💎 \n 💎 | 💎 | 💎", inline=False)
    await msg.edit(embed=embed)
    await asyncio.sleep(.5)
    embed=discord.Embed(title="Slots", description="")
    embed.add_field(name="", value="🍋 | 🍋 | 🍋 \n 🍋 | 🍋 | 🍋 \n 🍋 | 🍋 | 🍋", inline=False)
    await msg.edit(embed=embed)
    
@bot.command(name='get_log', help="print log file out for errors enter a number after to print that many lines (default 20)")
async def get_log(ctx, n = 20):
    with open('musicBot.log', 'r') as f:
        output = "".join(f.readlines()[n * -1::])
        await ctx.send(output[-4000::])

@bot.command(name='8ball', help='Ask a yes/no question and get a response with the best course of action.')
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

@bot.command(name='test_button', help='test button')
async def test_button(ctx):
    view = ButtonView()
    await ctx.send(embed=getBlackjackEmbed(ctx), view=view)\

def getBlackjackEmbed(ctx):
    result_embed = discord.Embed(color=0xBEBEFE)
    result_embed.title = "Blackjack"
    result_embed.set_author(
        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
    )
    return result_embed
    
class ButtonView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(ButtonTest('hit', hitCallback))
        self.add_item(ButtonTest('stay', stayCallback))
        
class ButtonTest(discord.ui.Button):
    def __init__(self, name, cb) -> None:
        self.cb = cb
        super().__init__(
            label=name
        )
        
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.cb(interaction)
        
async def hitCallback(interaction):
    result_embed = interaction.message.embeds[0]
    # result_embed = discord.Embed(color=0xBEBEFE)
    result_embed.description = "You clicked hit!"
    await interaction.response.edit_message(embed=result_embed)
    
async def stayCallback(interaction):
    result_embed = interaction.message.embeds[0]
    # result_embed = discord.Embed(color=0xBEBEFE)
    result_embed.description = "You clicked stay!"
    await interaction.response.edit_message(embed=result_embed)
    
@bot.command(name='rps', help='Play rock paper scissors')
async def rps(ctx):
    view = RockPaperScissorsView(ctx)
    await ctx.send("Please make your choice", view=view)

class RockPaperScissorsView(discord.ui.View):
    def __init__(self, ctx) -> None:
        super().__init__()
        self.add_item(RockPaperScissors())
        self.ctx = ctx
        
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id
        
class RockPaperScissors(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Scissors", description="You choose scissors.", emoji="✂"
            ),
            discord.SelectOption(
                label="Rock", description="You choose rock.", emoji="🪨"
            ),
            discord.SelectOption(
                label="Paper", description="You choose paper.", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="Choose...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        global user_balances
        choices = {
            "rock": 0,
            "paper": 1,
            "scissors": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0xBEBEFE)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.display_avatar.url
        )

        user_id = str(interaction.user.id)
        winner = (3 + user_choice_index - bot_choice_index) % 3
        if winner == 0:
            update_balance(user_id, -1)
            result_embed.description = f"**That's a draw!**\nYou've chosen {user_choice} and I've chosen {bot_choice}.\nYour new balance is: {user_balances[user_id]}."
            result_embed.colour = 0xF59E42
        elif winner == 1:
            update_balance(user_id, 5)
            result_embed.description = f"**You won!**\nYou've chosen {user_choice} and I've chosen {bot_choice}.\nYour new balance is: {user_balances[user_id]}."
            result_embed.colour = 0x57F287
        else:
            update_balance(user_id, -5)
            result_embed.description = f"**You lost!**\nYou've chosen {user_choice} and I've chosen {bot_choice}.\nYour new balance is: {user_balances[user_id]}."
            result_embed.colour = 0xE02B2B

        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )
        

@bot.command(name='playlist', help='Play a splotify playlist, paste the share link after')
async def rps(ctx, link):
    playlist_URI = link.split("/")[-1].split("?")[0]
    SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/api/token'
    SPOTIFY_AUTH_HEADERS = {'Authorization' : 'Basic ' + (base64.b64encode((SPOTIFY_CLIENT_ID + ":" + SPOTIFY_CLIENT_SECRET).encode())).decode("ascii")}
    SPOTIFY_AUTH_BODY = {'grant_type' : 'client_credentials'}
    SPOTIFY_AUTH_TOKEN = requests.post(SPOTIFY_AUTH_URL, data=SPOTIFY_AUTH_BODY, headers=SPOTIFY_AUTH_HEADERS).json()['access_token']

    SPOTIFY_PLAYLIST_URL = 'https://api.spotify.com/v1/playlists/%s/tracks?fields=items(track(name,artists(name),href,album(name,href)))'
    SPOTIFY_PLAYLIST_HEADERS = {'Authorization' : 'Bearer ' + SPOTIFY_AUTH_TOKEN}
    SPOTIFY_PLAYLIST = [(item['track']['name'] + ' by ' + ', '.join([artist['name'] for artist in item['track']['artists']])) for item in requests.get(SPOTIFY_PLAYLIST_URL % playlist_URI, headers=SPOTIFY_PLAYLIST_HEADERS).json()['items']]
    for item in SPOTIFY_PLAYLIST:
        await play(ctx, item)

@bot.command(name='pull', help='Pulls 1 person. Cost = 10')
async def pull(ctx):
    global person_pool
    global adjectives_pool
    user_id = str(ctx.author.id)
    if user_id not in user_balances:
        update_balance(user_id, 0)

    bet = 10

    if bet > user_balances[user_id]:
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
    

    update_balance(user_id, -bet)
    add_gacha(user_id, new_person)
    temp_balance = user_balances[user_id]
    await ctx.send(f"Congratulations! You got a {new_person}!\nYour new balance is: {temp_balance}.")

@bot.command(name='gacha_inv', help='Check your gacha inventory')
async def gacha_inv(ctx):
    global user_gachas
    output_str = ""
    user_id = str(ctx.author.id)
    if user_id not in user_gachas:
        await ctx.send("You are a new player. You have no gachas.")
    else:
        for person in user_gachas[user_id]:
            output_str = output_str + person + "\n"
        await ctx.send(output_str)

if __name__ == "__main__" :
    load_balances()
    load_griddies()
    load_gachas()
    bot.run(TOKEN)
