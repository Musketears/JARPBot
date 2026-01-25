-- Migration 001: Initial Schema
-- Created at: 2026-01-25
-- This migration documents the initial schema that was created by init_database()
-- It uses CREATE TABLE IF NOT EXISTS to be idempotent

-- User balances
CREATE TABLE IF NOT EXISTS user_balances (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gacha inventory
CREATE TABLE IF NOT EXISTS gacha_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    character_name TEXT,
    rarity INTEGER,
    adjective TEXT,
    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
);

-- Gacha pity tracking
CREATE TABLE IF NOT EXISTS gacha_pity (
    user_id TEXT PRIMARY KEY,
    total_pulls INTEGER DEFAULT 0,
    pulls_since_4star INTEGER DEFAULT 0,
    pulls_since_5star INTEGER DEFAULT 0,
    last_pull_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gambling history
CREATE TABLE IF NOT EXISTS gambling_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    game_type TEXT,
    bet_amount INTEGER,
    win_amount INTEGER,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
);

-- Daily limits
CREATE TABLE IF NOT EXISTS daily_limits (
    user_id TEXT,
    date TEXT,
    total_bet INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- Griddy counts
CREATE TABLE IF NOT EXISTS griddy_counts (
    name TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Song plays
CREATE TABLE IF NOT EXISTS song_plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    song_title TEXT,
    song_artist TEXT,
    song_url TEXT,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
);

-- Song stats
CREATE TABLE IF NOT EXISTS song_stats (
    song_title TEXT,
    song_artist TEXT,
    song_url TEXT,
    play_count INTEGER DEFAULT 0,
    first_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (song_title, song_artist)
);

-- Audio cache
CREATE TABLE IF NOT EXISTS audio_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_id TEXT UNIQUE,
    title TEXT,
    duration INTEGER,
    filename TEXT,
    normalized_filename TEXT,
    file_size INTEGER,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Cache settings
CREATE TABLE IF NOT EXISTS cache_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Playlists
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    name TEXT,
    description TEXT,
    is_public BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

-- Playlist songs
CREATE TABLE IF NOT EXISTS playlist_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER,
    song_title TEXT,
    song_artist TEXT,
    song_url TEXT,
    youtube_id TEXT,
    position INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gacha_user_id ON gacha_inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_gambling_user_id ON gambling_history(user_id);
CREATE INDEX IF NOT EXISTS idx_gambling_date ON gambling_history(played_at);
CREATE INDEX IF NOT EXISTS idx_song_plays_user_id ON song_plays(user_id);
CREATE INDEX IF NOT EXISTS idx_song_plays_song ON song_plays(song_title, song_artist);
CREATE INDEX IF NOT EXISTS idx_song_plays_date ON song_plays(played_at);
CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_playlists_public ON playlists(is_public);
CREATE INDEX IF NOT EXISTS idx_playlist_songs_playlist_id ON playlist_songs(playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_songs_position ON playlist_songs(playlist_id, position);
