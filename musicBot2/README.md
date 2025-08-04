# JARP Music Bot v2

A feature-rich Discord music bot with advanced audio processing, intelligent caching, custom playlists, and gaming features.

## 🎵 Features

### Music System
- **YouTube Integration**: Play any song from YouTube with search or direct URL
- **Audio Normalization**: Automatic volume normalization to -16 LUFS for consistent listening
- **Intelligent Caching**: Smart caching system for faster playback and reduced bandwidth
- **Queue Management**: Advanced queue with shuffle, skip, and volume control
- **High-Quality Audio**: 192kbps MP3 with 48kHz sample rate optimized for Discord

### Custom Playlist System
- **Create & Manage**: Build your own playlists with public/private options
- **Easy Sharing**: Browse and play public playlists from other users
- **Flexible Adding**: Add songs by search or direct YouTube URL
- **Bulk Operations**: Play entire playlists with one command

### Gaming Features
- **Gacha System**: Collect characters with daily pulls and balance management
- **Gambling Games**: Dice, coin flip, and rock-paper-scissors with daily limits
- **Statistics Tracking**: Comprehensive stats for all gaming activities

### Utility Features
- **Magic 8-Ball**: Classic fortune-telling command
- **Griddy System**: Custom image generation
- **Comprehensive Logging**: Detailed error handling and performance monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FFmpeg installed on your system
- Discord bot token

### Installation

#### Option 1: Automated Setup (Recommended)
```bash
git clone <repository-url>
cd musicBot2
python setup.py
```

#### Option 2: Manual Setup
1. **Clone the repository**
```bash
git clone <repository-url>
cd musicBot2
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment**
```bash
# Create .env file
echo "DISCORD_TOKEN=your_discord_bot_token_here" > .env
```

4. **Run the bot**
```bash
python main.py
```

## 📋 Commands

### Music Commands

#### Basic Playback
- `?play <song>` - Play a song from YouTube
- `?play_first <song>` - Add song to front of queue
- `?skip` - Skip current song
- `?pause` / `?resume` - Control playback
- `?queue` - Show current queue
- `?shuffle` - Shuffle the queue
- `?clear` - Clear the queue
- `?volume [0-100]` - Set or show volume
- `?leave` - Leave voice channel

#### Audio Settings
- `?normalize` - Toggle audio normalization
- `?normalize_info` - Show normalization settings
- `?cleanup` - Clean up orphaned audio files

#### Statistics
- `?mystats` - Show your music statistics
- `?topcharts [limit]` - Show most played songs
- `?recentplays [hours]` - Show recent plays
- `?songstats` - Show overall statistics

### Playlist Commands

#### Creating and Managing
- `?playlist_create <name> [description]` - Create a new playlist
- `?playlist_add <playlist_id> <song>` - Add song to playlist
- `?playlist_remove <playlist_id> <song_id>` - Remove song from playlist
- `?playlist_edit <playlist_id> [name] [description]` - Edit playlist details
- `?playlist_visibility <playlist_id>` - Toggle public/private
- `?playlist_delete <playlist_id>` - Delete playlist

#### Playing and Browsing
- `?playlist_play <playlist_id>` - Play a playlist
- `?playlist_list` - List your playlists
- `?playlist_show <playlist_id>` - Show playlist details
- `?playlist_public` - Browse public playlists
- `?playlist_help` - Show playlist system help

### Gaming Commands

#### Gacha System
- `?gacha` - Pull a character (costs $10)
- `?inventory` - Show your character collection
- `?balance` - Check your balance

#### Gambling Games
- `?dice <bet>` - Roll dice (1-6)
- `?coinflip <bet>` - Flip a coin
- `?rps` - Rock, paper, scissors

### Cache Management
- `?cache` - Show cache statistics
- `?cache_cleanup` - Clean up old cache entries
- `?cache_clear` - Clear all cache (admin only)

## ⚙️ Configuration

The bot automatically detects your system's FFmpeg installation. Key settings can be modified in `config.py`:

```python
# Core settings
command_prefix = "?"
default_balance = 100

# Cache settings
cache_enabled = True
cache_max_size = 1024  # MB
cache_max_age = 30     # days

# Music settings
max_queue_size = 50
max_volume = 1.0
default_volume = 0.5

# Gaming settings
gacha_cost = 10
max_daily_bet = 1000
gambling_cooldown = 30  # seconds
```

## 🎛️ Advanced Features

### Audio Normalization

The bot includes automatic audio normalization to ensure consistent volume levels across all songs:

- **Target**: -16 LUFS (industry standard)
- **True Peak**: -1 dB
- **Quality**: 192kbps MP3, 48kHz sample rate
- **Toggle**: Use `?normalize` to enable/disable

### Intelligent Caching System

The cache system provides significant performance improvements:

- **~80-90% faster** song loading for cached tracks
- **Reduced bandwidth** usage and YouTube API calls
- **Automatic management** with configurable size and age limits
- **Smart prioritization** keeps popular songs longer

#### Cache Benefits
- **Performance**: Instant playback for cached songs
- **Efficiency**: No duplicate downloads of the same song
- **Reliability**: Race condition protection for concurrent requests
- **Storage**: Automatic cleanup prevents disk space issues

### Database System

SQLite database stores:
- User balances and gaming statistics
- Song play history and metadata
- Playlist data and song collections
- Cache metadata and access tracking

## 🔧 Technical Details

### Race Condition Protection

The bot includes comprehensive race condition fixes:

- **Download Locks**: YouTube ID-specific locks prevent duplicate downloads
- **Atomic Operations**: File system operations use temporary files
- **Database Transactions**: Proper transaction handling prevents conflicts
- **Global Processing Locks**: Prevents concurrent command conflicts

### Error Handling

- **Graceful Recovery**: Network issues and audio problems handled automatically
- **File Validation**: Audio file integrity checks
- **Database Recovery**: Automatic error recovery and rollback
- **User-Friendly Messages**: Clear error messages for users

### Performance Optimizations

- **Async Processing**: Non-blocking audio operations
- **Memory Management**: Efficient file handling and cleanup
- **Cache Intelligence**: Smart cache hit detection and management
- **Resource Monitoring**: Automatic cleanup of temporary files

## 📁 Project Structure

```
musicBot2/
├── main.py                 # Bot entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── bot_data.db           # SQLite database
├── commands/             # Command modules
│   ├── music_commands.py
│   ├── playlist_commands.py
│   └── game_commands.py
├── music/               # Music system
│   └── player.py
├── games/               # Gaming features
│   ├── gacha.py
│   └── gambling.py
├── utils/               # Utility modules
│   ├── cache_manager.py
│   ├── database.py
│   └── helpers.py
├── cache/               # Cache directories
│   ├── audio/
│   └── normalized/
└── tests/               # Test suite
```

## 🧪 Testing

### Quick Setup Test
Run the automated setup test to verify your installation:

```bash
python test_setup.py
```

### Full Test Suite
Run the complete test suite:

```bash
python -m unittest discover tests/
```

## 📊 Monitoring

### Log Messages to Watch
- `Cache hit for YouTube ID: {id}` - Successful cache retrieval
- `Added to cache: {title} (ID: {id})` - New cache entry
- `Audio normalization enabled/disabled` - Normalization status
- `Periodic cache cleanup: {count} entries removed` - Cleanup results

### Performance Metrics
- Cache hit rate
- Total cache size and efficiency
- Most accessed songs
- Error rates and recovery success

## 🛠️ Troubleshooting

### Common Issues

**FFmpeg not found**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

**Cache not working**
- Check `cache_enabled` in config
- Verify cache directories exist
- Check database permissions

**Audio normalization fails**
- Ensure FFmpeg is properly installed
- Check system resources
- Use `?normalize` to disable if needed

**Performance issues**
- Monitor cache hit rate with `?cache`
- Increase cache size in config if needed
- Check disk space and I/O performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **discord.py** - Discord API wrapper
- **yt-dlp** - YouTube download functionality
- **FFmpeg** - Audio processing and normalization
- **SQLite** - Database management

---

**Note**: This bot is designed for personal use and educational purposes. Please respect YouTube's terms of service and Discord's API guidelines when using this bot. 