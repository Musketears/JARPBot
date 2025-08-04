# JARP Music Bot v2

A Discord music bot with advanced features including audio normalization, caching, and custom playlists.

## Features

### Music System
- YouTube music playback
- Audio normalization for consistent volume levels
- Intelligent caching system for faster playback
- Queue management with shuffle and skip functionality
- Volume control and audio quality settings

### Custom Playlist System
- Create and manage your own playlists
- Public and private playlist support
- Add songs by search or YouTube URL
- Play entire playlists with one command
- Browse and play public playlists from other users

### Game System
- Gacha system with character collection
- Gambling games (dice, coin flip, rock-paper-scissors)
- Daily limits and balance management
- Statistics tracking

### Utility Features
- Magic 8-ball command
- Griddy image system
- Comprehensive logging and error handling
- Database-driven statistics and tracking

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Discord bot token:
```
DISCORD_TOKEN=your_discord_bot_token_here
```

3. Run the bot:
```bash
python main.py
```

## Music Commands

### Basic Music Commands
- `?play <song>` - Play a song from YouTube
- `?play_first <song>` - Add song to front of queue
- `?skip` - Skip current song
- `?pause` / `?resume` - Control playback
- `?queue` - Show current queue
- `?shuffle` - Shuffle the queue
- `?clear` - Clear the queue
- `?volume [0-100]` - Set or show volume
- `?leave` - Leave voice channel

### Audio Settings
- `?normalize` - Toggle audio normalization
- `?normalize_info` - Show normalization settings
- `?cleanup` - Clean up orphaned audio files

### Statistics
- `?mystats` - Show your music statistics
- `?topcharts [limit]` - Show most played songs
- `?recentplays [hours]` - Show recent plays
- `?songstats` - Show overall statistics

### Cache Management
- `?cache` - Show cache statistics
- `?cache_cleanup` - Clean up old cache entries
- `?cache_clear` - Clear all cache (admin only)

## Playlist Commands

### Creating and Managing Playlists
- `?playlist_create <name> [description]` - Create a new playlist
- `?playlist_add <playlist_id> <song>` - Add song to playlist
- `?playlist_remove <playlist_id> <song_id>` - Remove song from playlist
- `?playlist_edit <playlist_id> [name] [description]` - Edit playlist details
- `?playlist_visibility <playlist_id>` - Toggle public/private
- `?playlist_delete <playlist_id>` - Delete playlist

### Playing and Browsing Playlists
- `?playlist_play <playlist_id>` - Play a playlist
- `?playlist_list` - List your playlists
- `?playlist_show <playlist_id>` - Show playlist details
- `?playlist_public` - Browse public playlists
- `?playlist_help` - Show playlist system help

## Game Commands

### Gacha System
- `?gacha` - Pull a character (costs $10)
- `?inventory` - Show your character collection
- `?balance` - Check your balance

### Gambling Games
- `?dice <bet>` - Roll dice (1-6)
- `?coinflip <bet>` - Flip a coin
- `?rps` - Rock, paper, scissors

## Configuration

The bot uses a configuration system that automatically detects your system's FFmpeg installation. Key settings can be modified in `config.py`:

- Command prefix (default: `?`)
- Default balance for new users
- Gacha and gambling settings
- Music queue limits
- Cache settings

## Database

The bot uses SQLite for data persistence, storing:
- User balances and statistics
- Gacha inventory and gambling history
- Song play history and statistics
- Playlist data and song collections
- Audio cache metadata

## Audio Processing

The bot includes advanced audio processing features:
- Automatic audio normalization to -16 LUFS
- Intelligent caching system for frequently played songs
- Support for multiple audio formats
- Volume control and quality settings

## Error Handling

Comprehensive error handling and logging system:
- Graceful handling of network issues
- Audio file validation and cleanup
- Database error recovery
- User-friendly error messages

## Contributing

Feel free to submit issues and enhancement requests! 