# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Active Project

The active project is `musicBot2/`. The legacy directories (`musicBot/`, `musicBotDB/`, `8ball/`, `gacha/`, `JARPSlots/`) are older implementations and generally should not be modified.

## Commands

All commands are run from within `musicBot2/`:

```bash
# Run the bot
python main.py

# Run all tests
python -m unittest discover tests/
python tests/run_tests.py

# Run setup (creates .env, directories, checks dependencies)
python setup.py
```

The bot is deployed via systemd as `musicbot2`. The `!update` Discord command triggers `update_and_restart.sh`, which pulls from `main` branch and restarts the service.

## Architecture

**Entry point:** `main.py` — initializes the bot, loads 7 cogs/extensions, registers signal handlers for graceful shutdown, and schedules cache cleanup every 12 hours.

**Configuration:** `config.py` — module-level singletons `config` (BotConfig) and `youtube_config` (YouTubeConfig). Bot token loaded from `.env`. FFmpeg auto-detected across 8 platform paths.

**Cog structure** (`commands/`):
- `music_commands.py` — playback, queue, shuffle, volume, normalization
- `playlist_commands.py` — per-user playlist CRUD and playback
- `game_commands.py` — gacha, inventory, balance, dice, slots
- `logging_commands.py` — log inspection and management
- `admin_commands.py` — `!update`, `!restart`, `!system_status`
- `fun_commands.py` / `health_commands.py` — misc features

**Game systems** (`games/`):
- `gacha.py` — GachaSystem with pity mechanics; 6 characters × 20 adjectives; rarities 2★–5★
- `gambling.py` — GamblingManager enforcing 30-second cooldowns and $1000/day limits

**Music pipeline** (`music/player.py`):
- Downloads via yt-dlp with custom User-Agent headers
- FFmpeg audio normalization using `loudnorm` filter (-16 LUFS, -1 dBTP, 48kHz, 192kbps MP3)
- Race condition protection via per-track-ID `_download_locks`

**Database** (`utils/database.py`): SQLite with 9 tables — `user_balances`, `gacha_inventory`, `gambling_history`, `daily_limits`, `griddy_counts`, `song_plays`, `song_stats`, `audio_cache`. Async wrapper methods throughout.

**Utilities** (`utils/`):
- `cache_manager.py` — audio file caching (up to 1024MB, 30-day retention)
- `helpers.py` — URL validation, bet parsing, embed creation, progress bars
- `wrapped_generator.py` — Spotify Wrapped-style image generation with Pillow
- `error_handler.py` — logging setup and error decorators
- `migrations.py` — SQLite schema migrations

## Environment

Requires a `.env` file in `musicBot2/` with `DISCORD_TOKEN`. The setup script creates this interactively. FFmpeg must be installed system-wide (`sudo apt install ffmpeg` on Linux).
