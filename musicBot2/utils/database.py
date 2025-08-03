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
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gacha_user_id ON gacha_inventory(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gambling_user_id ON gambling_history(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gambling_date ON gambling_history(played_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_user_id ON song_plays(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_song ON song_plays(song_title, song_artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_song_plays_date ON song_plays(played_at)")
    
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

# Global database instance
db = DatabaseManager() 