import sqlite3
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_balances (
                    user_id TEXT PRIMARY KEY,
                    balance INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gacha_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    character_name TEXT,
                    rarity INTEGER,
                    adjective TEXT,
                    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gambling_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    game_type TEXT,
                    bet_amount INTEGER,
                    win_amount INTEGER,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_limits (
                    user_id TEXT,
                    date TEXT,
                    total_bet INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS griddy_counts (
                    name TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # New tables for song tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS song_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    song_title TEXT,
                    song_artist TEXT,
                    song_url TEXT,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_balances (user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS song_stats (
                    song_title TEXT,
                    song_artist TEXT,
                    song_url TEXT,
                    play_count INTEGER DEFAULT 0,
                    first_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (song_title, song_artist)
                )
            """)
            
            # Cache tracking table
            conn.execute("""
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
                )
            """)
            
            # Cache settings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Custom playlist tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    name TEXT,
                    description TEXT,
                    is_public BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """)
            
            conn.execute("""
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
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gacha_user_id ON gacha_inventory(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gambling_user_id ON gambling_history(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gambling_date ON gambling_history(played_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_user_id ON song_plays(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_song ON song_plays(song_title, song_artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_date ON song_plays(played_at)")
            
            # Playlist indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON playlists(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playlists_public ON playlists(is_public)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playlist_songs_playlist_id ON playlist_songs(playlist_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playlist_songs_position ON playlist_songs(playlist_id, position)")
    
    async def get_balance(self, user_id: str) -> int:
        """Get user balance asynchronously"""
        def _get_balance():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT balance FROM user_balances WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    # Create new user with default balance
                    conn.execute(
                        "INSERT INTO user_balances (user_id, balance) VALUES (?, ?)",
                        (user_id, config.default_balance)
                    )
                    return config.default_balance
        
        return await asyncio.to_thread(_get_balance)
    
    async def update_balance(self, user_id: str, amount: int) -> int:
        """Update user balance asynchronously"""
        def _update_balance():
            with sqlite3.connect(self.db_path) as conn:
                # Get current balance
                cursor = conn.execute(
                    "SELECT balance FROM user_balances WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    new_balance = result[0] + amount
                    conn.execute(
                        "UPDATE user_balances SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (new_balance, user_id)
                    )
                else:
                    new_balance = config.default_balance + amount
                    conn.execute(
                        "INSERT INTO user_balances (user_id, balance) VALUES (?, ?)",
                        (user_id, new_balance)
                    )
                
                return new_balance
        
        return await asyncio.to_thread(_update_balance)
    
    async def add_gacha_item(self, user_id: str, character_name: str, rarity: int, adjective: str):
        """Add gacha item to user inventory"""
        def _add_gacha():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO gacha_inventory (user_id, character_name, rarity, adjective) VALUES (?, ?, ?, ?)",
                    (user_id, character_name, rarity, adjective)
                )
        
        await asyncio.to_thread(_add_gacha)
    
    async def get_gacha_inventory(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's gacha inventory"""
        def _get_inventory():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT character_name, rarity, adjective, obtained_at FROM gacha_inventory WHERE user_id = ? ORDER BY obtained_at DESC",
                    (user_id,)
                )
                return [
                    {
                        'character_name': row[0],
                        'rarity': row[1],
                        'adjective': row[2],
                        'obtained_at': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_inventory)
    
    async def record_gambling(self, user_id: str, game_type: str, bet_amount: int, win_amount: int):
        """Record gambling activity"""
        def _record_gambling():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO gambling_history (user_id, game_type, bet_amount, win_amount) VALUES (?, ?, ?, ?)",
                    (user_id, game_type, bet_amount, win_amount)
                )
        
        await asyncio.to_thread(_record_gambling)
    
    async def get_daily_bet_total(self, user_id: str) -> int:
        """Get user's total bets for today"""
        def _get_daily_total():
            today = datetime.now().strftime('%Y-%m-%d')
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT total_bet FROM daily_limits WHERE user_id = ? AND date = ?",
                    (user_id, today)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        
        return await asyncio.to_thread(_get_daily_total)
    
    async def update_daily_bet_total(self, user_id: str, bet_amount: int):
        """Update user's daily bet total"""
        def _update_daily_total():
            today = datetime.now().strftime('%Y-%m-%d')
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO daily_limits (user_id, date, total_bet) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(user_id, date) 
                    DO UPDATE SET total_bet = total_bet + ?
                    """,
                    (user_id, today, bet_amount, bet_amount)
                )
        
        await asyncio.to_thread(_update_daily_total)
    
    async def get_griddy_count(self, name: str) -> int:
        """Get griddy count for a name"""
        def _get_griddy_count():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT count FROM griddy_counts WHERE name = ?",
                    (name,)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        
        return await asyncio.to_thread(_get_griddy_count)
    
    async def increment_griddy_count(self, name: str):
        """Increment griddy count for a name"""
        def _increment_griddy():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO griddy_counts (name, count) VALUES (?, 1)
                    ON CONFLICT(name) DO UPDATE SET 
                    count = count + 1,
                    last_updated = CURRENT_TIMESTAMP
                    """,
                    (name,)
                )
        
        await asyncio.to_thread(_increment_griddy)
    
    async def get_gambling_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive gambling statistics for a user"""
        def _get_stats():
            with sqlite3.connect(self.db_path) as conn:
                # Total stats
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_games,
                        SUM(bet_amount) as total_bet,
                        SUM(win_amount) as total_won,
                        SUM(win_amount - bet_amount) as net_profit
                    FROM gambling_history 
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )
                total_stats = cursor.fetchone()
                
                # Today's stats
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as today_games,
                        SUM(bet_amount) as today_bet,
                        SUM(win_amount) as today_won
                    FROM gambling_history 
                    WHERE user_id = ? AND DATE(played_at) = ?
                    """,
                    (user_id, today)
                )
                today_stats = cursor.fetchone()
                
                return {
                    'total_games': total_stats[0] or 0,
                    'total_bet': total_stats[1] or 0,
                    'total_won': total_stats[2] or 0,
                    'net_profit': total_stats[3] or 0,
                    'today_games': today_stats[0] or 0,
                    'today_bet': today_stats[1] or 0,
                    'today_won': today_stats[2] or 0
                }
        
        return await asyncio.to_thread(_get_stats)
    
    async def record_song_play(self, user_id: str, song_title: str, song_artist: str, song_url: str = None):
        """Record a song play by a user"""
        def _record_song_play():
            with sqlite3.connect(self.db_path) as conn:
                # Record the individual play
                conn.execute(
                    "INSERT INTO song_plays (user_id, song_title, song_artist, song_url) VALUES (?, ?, ?, ?)",
                    (user_id, song_title, song_artist, song_url)
                )
                
                # Update song statistics
                conn.execute(
                    """
                    INSERT INTO song_stats (song_title, song_artist, song_url, play_count, first_played, last_played) 
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(song_title, song_artist) DO UPDATE SET 
                    play_count = play_count + 1,
                    last_played = CURRENT_TIMESTAMP
                    """,
                    (song_title, song_artist, song_url)
                )
        
        await asyncio.to_thread(_record_song_play)
    
    async def get_user_song_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get a user's song play history"""
        def _get_user_history():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT song_title, song_artist, song_url, played_at 
                    FROM song_plays 
                    WHERE user_id = ? 
                    ORDER BY played_at DESC 
                    LIMIT ?
                    """,
                    (user_id, limit)
                )
                return [
                    {
                        'song_title': row[0],
                        'song_artist': row[1],
                        'song_url': row[2],
                        'played_at': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_user_history)
    
    async def get_song_stats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get overall song statistics, ordered by play count"""
        def _get_song_stats():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT song_title, song_artist, song_url, play_count, first_played, last_played
                    FROM song_stats 
                    ORDER BY play_count DESC 
                    LIMIT ?
                    """,
                    (limit,)
                )
                return [
                    {
                        'song_title': row[0],
                        'song_artist': row[1],
                        'song_url': row[2],
                        'play_count': row[3],
                        'first_played': row[4],
                        'last_played': row[5]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_song_stats)
    
    async def get_user_favorite_songs(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a user's most played songs"""
        def _get_favorites():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT song_title, song_artist, song_url, COUNT(*) as play_count
                    FROM song_plays 
                    WHERE user_id = ? 
                    GROUP BY song_title, song_artist 
                    ORDER BY play_count DESC 
                    LIMIT ?
                    """,
                    (user_id, limit)
                )
                return [
                    {
                        'song_title': row[0],
                        'song_artist': row[1],
                        'song_url': row[2],
                        'play_count': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_favorites)
    
    async def get_recent_song_plays(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent song plays within the specified hours"""
        def _get_recent_plays():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT sp.song_title, sp.song_artist, sp.song_url, sp.user_id, sp.played_at
                    FROM song_plays sp
                    WHERE sp.played_at >= datetime('now', '-{} hours')
                    ORDER BY sp.played_at DESC 
                    LIMIT ?
                    """.format(hours),
                    (limit,)
                )
                return [
                    {
                        'song_title': row[0],
                        'song_artist': row[1],
                        'song_url': row[2],
                        'user_id': row[3],
                        'played_at': row[4]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_recent_plays)
    
    async def get_song_play_count(self, song_title: str, song_artist: str) -> int:
        """Get the total play count for a specific song"""
        def _get_play_count():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT play_count FROM song_stats WHERE song_title = ? AND song_artist = ?",
                    (song_title, song_artist)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        
        return await asyncio.to_thread(_get_play_count)
    
    async def get_user_play_count(self, user_id: str) -> int:
        """Get total number of songs played by a user"""
        def _get_user_play_count():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM song_plays WHERE user_id = ?",
                    (user_id,)
                )
                return cursor.fetchone()[0]
        
        return await asyncio.to_thread(_get_user_play_count)
    
    async def get_total_songs_played(self) -> int:
        """Get total number of songs played across all users"""
        def _get_total_plays():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM song_plays")
                return cursor.fetchone()[0]
        
        return await asyncio.to_thread(_get_total_plays)
    
    async def get_unique_songs_count(self) -> int:
        """Get total number of unique songs played"""
        def _get_unique_songs():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM song_stats")
                return cursor.fetchone()[0]
        
        return await asyncio.to_thread(_get_unique_songs)
    
    async def get_user_song_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive song statistics for a user"""
        def _get_user_song_stats():
            with sqlite3.connect(self.db_path) as conn:
                # Total plays
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM song_plays WHERE user_id = ?",
                    (user_id,)
                )
                total_plays = cursor.fetchone()[0]
                
                # Unique songs played
                cursor = conn.execute(
                    "SELECT COUNT(DISTINCT song_title || ' - ' || song_artist) FROM song_plays WHERE user_id = ?",
                    (user_id,)
                )
                unique_songs = cursor.fetchone()[0]
                
                # Today's plays
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM song_plays WHERE user_id = ? AND DATE(played_at) = ?",
                    (user_id, today)
                )
                today_plays = cursor.fetchone()[0]
                
                return {
                    'total_plays': total_plays,
                    'unique_songs': unique_songs,
                    'today_plays': today_plays
                }
        
        return await asyncio.to_thread(_get_user_song_stats)
    
    async def get_cached_song(self, youtube_id: str) -> Optional[Dict[str, Any]]:
        """Get cached song information"""
        def _get_cached_song():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT youtube_id, title, duration, filename, normalized_filename, 
                           file_size, download_date, last_accessed, access_count
                    FROM audio_cache WHERE youtube_id = ?
                    """,
                    (youtube_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'youtube_id': result[0],
                        'title': result[1],
                        'duration': result[2],
                        'filename': result[3],
                        'normalized_filename': result[4],
                        'file_size': result[5],
                        'download_date': result[6],
                        'last_accessed': result[7],
                        'access_count': result[8]
                    }
                return None
        
        return await asyncio.to_thread(_get_cached_song)
    
    async def add_cached_song(self, youtube_id: str, title: str, duration: int, 
                             filename: str, normalized_filename: str = None, file_size: int = 0):
        """Add a song to the cache"""
        def _add_cached_song():
            with sqlite3.connect(self.db_path) as conn:
                # Use a transaction to ensure atomicity
                conn.execute("BEGIN TRANSACTION")
                try:
                    # Check if entry already exists to avoid race conditions
                    cursor = conn.execute("SELECT youtube_id FROM audio_cache WHERE youtube_id = ?", (youtube_id,))
                    if cursor.fetchone():
                        # Entry already exists, update it instead
                        conn.execute(
                            """
                            UPDATE audio_cache 
                            SET title = ?, duration = ?, filename = ?, normalized_filename = ?, 
                                file_size = ?, download_date = CURRENT_TIMESTAMP, 
                                last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                            WHERE youtube_id = ?
                            """,
                            (title, duration, filename, normalized_filename, file_size, youtube_id)
                        )
                    else:
                        # Insert new entry
                        conn.execute(
                            """
                            INSERT INTO audio_cache 
                            (youtube_id, title, duration, filename, normalized_filename, file_size, 
                             download_date, last_accessed, access_count)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                            """,
                            (youtube_id, title, duration, filename, normalized_filename, file_size)
                        )
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise e
        
        await asyncio.to_thread(_add_cached_song)
    
    async def update_cache_access(self, youtube_id: str):
        """Update cache access time and count"""
        def _update_cache_access():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE audio_cache 
                    SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                    WHERE youtube_id = ?
                    """,
                    (youtube_id,)
                )
        
        await asyncio.to_thread(_update_cache_access)
    
    async def remove_cached_song(self, youtube_id: str):
        """Remove a song from cache"""
        def _remove_cached_song():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM audio_cache WHERE youtube_id = ?", (youtube_id,))
        
        await asyncio.to_thread(_remove_cached_song)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        def _get_cache_stats():
            with sqlite3.connect(self.db_path) as conn:
                # Total cached songs
                cursor = conn.execute("SELECT COUNT(*) FROM audio_cache")
                total_songs = cursor.fetchone()[0]
                
                # Total cache size
                cursor = conn.execute("SELECT SUM(file_size) FROM audio_cache")
                total_size = cursor.fetchone()[0] or 0
                
                # Most accessed songs
                cursor = conn.execute(
                    "SELECT title, access_count FROM audio_cache ORDER BY access_count DESC LIMIT 5"
                )
                top_songs = [{'title': row[0], 'access_count': row[1]} for row in cursor.fetchall()]
                
                # Oldest cached songs
                cursor = conn.execute(
                    "SELECT title, download_date FROM audio_cache ORDER BY download_date ASC LIMIT 5"
                )
                oldest_songs = [{'title': row[0], 'download_date': row[1]} for row in cursor.fetchall()]
                
                return {
                    'total_songs': total_songs,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'top_songs': top_songs,
                    'oldest_songs': oldest_songs
                }
        
        return await asyncio.to_thread(_get_cache_stats)
    
    async def cleanup_old_cache(self, max_age_days: int = 30):
        """Remove old cache entries"""
        def _cleanup_old_cache():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM audio_cache 
                    WHERE julianday('now') - julianday(download_date) > ?
                    """,
                    (max_age_days,)
                )
        
        await asyncio.to_thread(_cleanup_old_cache)
    
    async def get_cache_entries_to_cleanup(self, max_size_mb: int) -> List[Dict[str, Any]]:
        """Get cache entries that should be cleaned up based on size"""
        def _get_cleanup_entries():
            with sqlite3.connect(self.db_path) as conn:
                # Get total current size
                cursor = conn.execute("SELECT SUM(file_size) FROM audio_cache")
                total_size = cursor.fetchone()[0] or 0
                max_size_bytes = max_size_mb * 1024 * 1024
                
                if total_size <= max_size_bytes:
                    return []
                
                # Get entries to remove (oldest and least accessed first)
                cursor = conn.execute(
                    """
                    SELECT youtube_id, title, file_size, access_count, download_date
                    FROM audio_cache 
                    ORDER BY access_count ASC, download_date ASC
                    """
                )
                entries = []
                current_size = total_size
                
                for row in cursor.fetchall():
                    if current_size <= max_size_bytes:
                        break
                    entries.append({
                        'youtube_id': row[0],
                        'title': row[1],
                        'file_size': row[2],
                        'access_count': row[3],
                        'download_date': row[4]
                    })
                    current_size -= row[2]
                
                return entries
        
        return await asyncio.to_thread(_get_cleanup_entries)
    
    # Playlist management methods
    async def create_playlist(self, user_id: str, name: str, description: str = "", is_public: bool = False) -> int:
        """Create a new playlist"""
        def _create_playlist():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO playlists (user_id, name, description, is_public) VALUES (?, ?, ?, ?)",
                    (user_id, name, description, is_public)
                )
                return cursor.lastrowid
        
        return await asyncio.to_thread(_create_playlist)
    
    async def get_user_playlists(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all playlists for a user"""
        def _get_user_playlists():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, name, description, is_public, created_at, updated_at,
                           (SELECT COUNT(*) FROM playlist_songs WHERE playlist_id = playlists.id) as song_count
                    FROM playlists 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC
                    """,
                    (user_id,)
                )
                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'is_public': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5],
                        'song_count': row[6]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_user_playlists)
    
    async def get_public_playlists(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get public playlists"""
        def _get_public_playlists():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT p.id, p.user_id, p.name, p.description, p.created_at, p.updated_at,
                           (SELECT COUNT(*) FROM playlist_songs WHERE playlist_id = p.id) as song_count
                    FROM playlists p
                    WHERE p.is_public = 1 
                    ORDER BY p.updated_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                return [
                    {
                        'id': row[0],
                        'user_id': row[1],
                        'name': row[2],
                        'description': row[3],
                        'created_at': row[4],
                        'updated_at': row[5],
                        'song_count': row[6]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_public_playlists)
    
    async def get_playlist(self, playlist_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific playlist by ID"""
        def _get_playlist():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, user_id, name, description, is_public, created_at, updated_at,
                           (SELECT COUNT(*) FROM playlist_songs WHERE playlist_id = playlists.id) as song_count
                    FROM playlists 
                    WHERE id = ?
                    """,
                    (playlist_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'user_id': result[1],
                        'name': result[2],
                        'description': result[3],
                        'is_public': bool(result[4]),
                        'created_at': result[5],
                        'updated_at': result[6],
                        'song_count': result[7]
                    }
                return None
        
        return await asyncio.to_thread(_get_playlist)
    
    async def get_playlist_songs(self, playlist_id: int) -> List[Dict[str, Any]]:
        """Get all songs in a playlist"""
        def _get_playlist_songs():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, song_title, song_artist, song_url, youtube_id, position, added_at
                    FROM playlist_songs 
                    WHERE playlist_id = ? 
                    ORDER BY position
                    """,
                    (playlist_id,)
                )
                return [
                    {
                        'id': row[0],
                        'song_title': row[1],
                        'song_artist': row[2],
                        'song_url': row[3],
                        'youtube_id': row[4],
                        'position': row[5],
                        'added_at': row[6]
                    }
                    for row in cursor.fetchall()
                ]
        
        return await asyncio.to_thread(_get_playlist_songs)
    
    async def add_song_to_playlist(self, playlist_id: int, song_title: str, song_artist: str, 
                                  song_url: str, youtube_id: str = None) -> bool:
        """Add a song to a playlist"""
        def _add_song_to_playlist():
            with sqlite3.connect(self.db_path) as conn:
                # Get the next position
                cursor = conn.execute(
                    "SELECT MAX(position) FROM playlist_songs WHERE playlist_id = ?",
                    (playlist_id,)
                )
                result = cursor.fetchone()
                next_position = (result[0] or 0) + 1
                
                # Add the song
                conn.execute(
                    """
                    INSERT INTO playlist_songs (playlist_id, song_title, song_artist, song_url, youtube_id, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (playlist_id, song_title, song_artist, song_url, youtube_id, next_position)
                )
                
                # Update playlist timestamp
                conn.execute(
                    "UPDATE playlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (playlist_id,)
                )
                
                return True
        
        return await asyncio.to_thread(_add_song_to_playlist)
    
    async def remove_song_from_playlist(self, playlist_id: int, song_id: int) -> bool:
        """Remove a song from a playlist"""
        def _remove_song_from_playlist():
            with sqlite3.connect(self.db_path) as conn:
                # Get the position of the song to remove
                cursor = conn.execute(
                    "SELECT position FROM playlist_songs WHERE id = ? AND playlist_id = ?",
                    (song_id, playlist_id)
                )
                result = cursor.fetchone()
                if not result:
                    return False
                
                removed_position = result[0]
                
                # Remove the song
                conn.execute(
                    "DELETE FROM playlist_songs WHERE id = ? AND playlist_id = ?",
                    (song_id, playlist_id)
                )
                
                # Update positions of songs after the removed one
                conn.execute(
                    """
                    UPDATE playlist_songs 
                    SET position = position - 1 
                    WHERE playlist_id = ? AND position > ?
                    """,
                    (playlist_id, removed_position)
                )
                
                # Update playlist timestamp
                conn.execute(
                    "UPDATE playlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (playlist_id,)
                )
                
                return True
        
        return await asyncio.to_thread(_remove_song_from_playlist)
    
    async def delete_playlist(self, playlist_id: int, user_id: str) -> bool:
        """Delete a playlist (only by owner)"""
        def _delete_playlist():
            with sqlite3.connect(self.db_path) as conn:
                # Check if user owns the playlist
                cursor = conn.execute(
                    "SELECT id FROM playlists WHERE id = ? AND user_id = ?",
                    (playlist_id, user_id)
                )
                if not cursor.fetchone():
                    return False
                
                # Delete the playlist (songs will be deleted due to CASCADE)
                conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
                return True
        
        return await asyncio.to_thread(_delete_playlist)
    
    async def update_playlist(self, playlist_id: int, user_id: str, name: str = None, 
                            description: str = None, is_public: bool = None) -> bool:
        """Update playlist details (only by owner)"""
        def _update_playlist():
            with sqlite3.connect(self.db_path) as conn:
                # Check if user owns the playlist
                cursor = conn.execute(
                    "SELECT id FROM playlists WHERE id = ? AND user_id = ?",
                    (playlist_id, user_id)
                )
                if not cursor.fetchone():
                    return False
                
                # Build update query
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if is_public is not None:
                    updates.append("is_public = ?")
                    params.append(is_public)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(playlist_id)
                    
                    query = f"UPDATE playlists SET {', '.join(updates)} WHERE id = ?"
                    conn.execute(query, params)
                
                return True
        
        return await asyncio.to_thread(_update_playlist)

# Global database instance
db = DatabaseManager() 