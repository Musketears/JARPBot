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
import sqlite3

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)

def init_db():
    conn = sqlite3.connect('user_balances.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, balance INTEGER)''')
    conn.commit()
    conn.close()

queue = []
is_stop = False
is_processing = False
current_file = ''
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


def update_balance(user_id, amount):
    global user_balances
    conn = sqlite3.connect('user_balances.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        new_balance = row[0] + amount
        c.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    else:
        new_balance = 100 + amount
        c.execute('INSERT INTO balances (user_id, balance) VALUES (?, ?)', (user_id, new_balance))
    conn.commit()
    conn.close()
    user_balances[user_id] = new_balance

def load_balances():
    conn = sqlite3.connect('user_balances.db')
    c = conn.cursor()
    c.execute('SELECT * FROM balances')
    rows = c.fetchall()
    conn.close()
    return {str(row[0]): row[1] for row in rows}


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
    
@bot.command(name='test_embed', help='test embed')
async def test_embed(ctx):
    embed=discord.Embed(title="Slots", description="")
    embed.add_field(name="", value="7️⃣ | 7️⃣ | 🍋 \n 🍋 | 🔔 | 🍋 \n 🔔 | 7️⃣ | 💎", inline=False)
    await ctx.send(embed=embed)
    
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
    
@bot.command(name='rps', help='Play rock paper scissors')
async def rps(ctx):
    view = RockPaperScissorsView()
    await ctx.send("Please make your choice", view=view)

class RockPaperScissorsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(RockPaperScissors())
        
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


if __name__ == "__main__" :
    init_db()
    user_balances = load_balances()
    bot.run(TOKEN)