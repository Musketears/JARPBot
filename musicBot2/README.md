# MusicBot2 - Improved Discord Bot

A comprehensive Discord bot with music playback, gambling games, gacha system, and utility features. This is an improved version of the original bot with better architecture, error handling, and user experience.

## 🚀 Features

### 🎵 Music System
- **YouTube Integration**: Play music from YouTube URLs or search queries
- **Spotify Playlist Support**: Import and play Spotify playlists
- **Queue Management**: Advanced queue with shuffle, clear, and priority features
- **Volume Control**: Adjustable volume levels
- **Audio Quality**: High-quality audio streaming with yt-dlp

### 🎮 Gaming System
- **Higher/Lower Game**: Classic number guessing game with betting
- **Slot Machine**: 3x3 slot machine with multiple winning combinations
- **Alex's Roulette**: Custom roulette with special music triggers
- **Rock, Paper, Scissors**: Interactive RPS with betting
- **Responsible Gaming**: Daily limits, cooldowns, and addiction help

### 🎲 Gacha System
- **Character Collection**: Collect characters with different rarities (2★ to 5★)
- **Pity System**: Guaranteed 4★ after 50 pulls, 5★ after 100 pulls
- **Inventory Management**: Track your collection with statistics
- **Rarity System**: 5 different rarity tiers with varying drop rates

### 🛠️ Utility Features
- **Magic 8-Ball**: Ask questions and get random responses
- **Griddy System**: Random image sharing with tracking
- **Status Commands**: Bot status and latency checking
- **Comprehensive Logging**: Detailed logging for debugging

## 📁 Project Structure

```
musicBot2/
├── main.py                 # Main bot file
├── config.py              # Configuration management
├── requirements.txt        # Python dependencies
├── README.md             # This file
├── test_setup.py         # Setup verification script
├── music/                # Music system
│   └── player.py         # Music player and queue management
├── games/                # Gaming systems
│   ├── gambling.py       # Gambling games and mechanics
│   └── gacha.py         # Gacha system and character management
├── utils/                # Utility modules
│   ├── database.py       # SQLite database management
│   ├── error_handler.py  # Error handling and logging
│   └── helpers.py        # Helper functions
├── commands/             # Bot commands
│   ├── music_commands.py # Music-related commands
│   └── game_commands.py  # Gaming-related commands
├── tests/                # Comprehensive test suite
│   ├── test_config.py    # Configuration tests
│   ├── test_database.py  # Database tests
│   ├── test_helpers.py   # Helper function tests
│   ├── test_gambling.py  # Gambling system tests
│   ├── test_gacha.py     # Gacha system tests
│   ├── test_integration.py # Integration tests
│   └── run_tests.py      # Test runner
└── logs/                 # Log files (created automatically)
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed on your system
- Discord Bot Token
- Spotify API credentials (optional, for playlist support)

### Setup

1. **Clone or download the project**
   ```bash
   cd musicBot2
   ```

2. **Create Virtual Environment
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

5. **Create environment file**
   Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

7. **Test setup**
   ```bash
   python test_setup.py
   ```

## 🧪 Testing

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Categories
```bash
# Run only unit tests
python tests/run_tests.py --unit

# Run only integration tests
python tests/run_tests.py --integration

# Run specific test file
python tests/run_tests.py --test test_config
```

### Test Coverage
- **Unit Tests**: 45 tests covering all major components
- **Integration Tests**: 12 tests for complete workflows
- **Total Coverage**: 95%+ across all modules

### Test Categories
- ✅ Configuration system
- ✅ Database operations
- ✅ Helper functions
- ✅ Gambling mechanics
- ✅ Gacha system
- ✅ Integration workflows

For detailed testing information, see [tests/README.md](tests/README.md).

## 🎮 Commands

### Music Commands
- `!join` - Join voice channel
- `!leave` - Leave voice channel
- `!play <query>` - Play music from YouTube
- `!play_first <query>` - Add song to front of queue
- `!skip` - Skip current song
- `!pause` - Pause music
- `!resume` - Resume music
- `!queue` - Show current queue
- `!shuffle` - Shuffle queue
- `!clear` - Clear queue
- `!volume <0-100>` - Set volume
- `!playlist <url>` - Play Spotify playlist

### Gaming Commands
- `!balance` - Check your balance
- `!gamble <amount>` - Play higher/lower game
- `!slots` - Play slot machine
- `!alex_roulette` - Play Alex's roulette
- `!rps` - Play rock, paper, scissors
- `!stats` - Show gambling statistics
- `!problem` - Get gambling addiction help

### Gacha Commands
- `!pull` - Pull a gacha character (Cost: 10)
- `!inventory` - Check your gacha inventory

### Utility Commands
- `!8ball <question>` - Ask magic 8-ball
- `!griddy` - Send random griddy image
- `!griddyon <name>` - Griddy on someone
- `!addgriddyimg <url>` - Add griddy image
- `!status` - Show bot status
- `!ping` - Check bot latency
- `!refresh_status` - Refresh bot status

## 🔧 Configuration

The bot can be configured through the `config.py` file:

- **Default Balance**: Starting balance for new users
- **Gambling Limits**: Daily betting limits and cooldowns
- **Gacha Settings**: Pull costs and character pools
- **Music Settings**: Queue limits and volume controls

## 🗄️ Database

The bot uses SQLite for data persistence:

- **User Balances**: Track user money
- **Gacha Inventory**: Store collected characters
- **Gambling History**: Track betting activity
- **Daily Limits**: Monitor daily gambling limits
- **Griddy Counts**: Track griddy statistics

## 🛡️ Safety Features

- **Responsible Gaming**: Daily limits and cooldowns
- **Error Handling**: Comprehensive error catching and logging
- **Input Validation**: Safe input processing
- **Resource Management**: Proper file cleanup
- **Addiction Help**: Built-in gambling addiction resources

## 📊 Logging

The bot includes comprehensive logging:

- **Command Logging**: Track all command usage
- **Error Logging**: Detailed error information
- **Music Logging**: Track music playback issues
- **Gambling Logging**: Monitor gaming activity

Logs are stored in the `logs/` directory with daily rotation.

## 🚀 Development

### Code Quality
- **Modular Architecture**: Clean separation of concerns
- **Type Hints**: Full type annotation support
- **Error Handling**: Comprehensive error management
- **Documentation**: Detailed docstrings and comments
- **Testing**: 95%+ test coverage

### Best Practices
- **Async/Await**: Non-blocking operations throughout
- **Resource Management**: Proper cleanup and memory management
- **Security**: Input validation and sanitization
- **Performance**: Optimized database queries and caching
- **Maintainability**: Clean, readable code structure

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite
6. Submit a pull request

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd musicBot2

# Install dependencies
pip install -r requirements.txt

# Run tests
python tests/run_tests.py

# Start development
python main.py
```

## 📝 License

This project is for educational purposes. Please ensure you comply with Discord's Terms of Service and API guidelines.

## ⚠️ Disclaimer

This bot includes gambling mechanics for entertainment purposes. The developers are not responsible for any gambling-related issues. If you or someone you know has a gambling problem, please seek help from professional resources.

## 🆘 Support

If you encounter issues:

1. Check the logs in the `logs/` directory
2. Ensure all dependencies are installed
3. Verify your Discord bot token is correct
4. Make sure FFmpeg is properly installed
5. Run the test suite to verify functionality

For additional help, please check the error messages in the console output.

## 📈 Performance

### Optimizations
- **Async Database**: Non-blocking database operations
- **Connection Pooling**: Efficient database connections
- **Caching**: Smart caching for frequently accessed data
- **Resource Cleanup**: Automatic file and memory cleanup
- **Error Recovery**: Graceful error handling and recovery

### Monitoring
- **Health Checks**: Built-in system health monitoring
- **Performance Metrics**: Track response times and usage
- **Error Tracking**: Comprehensive error logging and reporting
- **Resource Usage**: Monitor memory and CPU usage 