import os
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

def get_ffmpeg_path():
    """Get the correct FFmpeg path for the current system"""
    # Common FFmpeg paths
    possible_paths = [
        'ffmpeg',  # Default system path
        'ffmpeg.exe',  # Windows
        '/usr/bin/ffmpeg',  # Linux
        '/usr/local/bin/ffmpeg',  # macOS with Homebrew
        '/opt/homebrew/bin/ffmpeg',  # macOS with Homebrew (Apple Silicon)
        'C:\\ffmpeg\\bin\\ffmpeg.exe',  # Windows custom install
    ]
    
    # Check if ffmpeg is available in PATH
    for path in possible_paths:
        try:
            result = subprocess.run([path, '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # If not found, return the default based on OS
    return 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'

@dataclass
class BotConfig:
    token: str
    spotify_client_id: str
    spotify_client_secret: str
    command_prefix: str = "?"
    default_balance: int = 100
    ffmpeg_path: str = None
    
    # Gacha settings
    gacha_cost: int = 10
    person_pool: List[str] = None
    adjectives_pool: List[str] = None
    
    # Gambling settings
    max_daily_bet: int = 1000
    gambling_cooldown: int = 30  # seconds
    
    # Music settings
    max_queue_size: int = 50
    max_volume: float = 1.0
    default_volume: float = 0.5
    
    # Cache settings
    cache_enabled: bool = True
    cache_max_size: int = 1024  # MB
    cache_max_age: int = 30  # days
    cache_directory: str = "cache"
    
    def __post_init__(self):
        if self.ffmpeg_path is None:
            self.ffmpeg_path = get_ffmpeg_path()
        if self.person_pool is None:
            self.person_pool = ["Alex", "Ryan", "Priscilla", "Jackson", "Holli", "Nathan"]
        if self.adjectives_pool is None:
            self.adjectives_pool = [
                "Default", "Homeless", "Dumb", "Boring", "Sleepy", "Hungry", 
                "Hairy", "Stinky", "Silly", "Emo", "K/DA", "Edgelord", 
                "Roided", "Zombie", "Smoll", "Tilted", "Large", 
                "Biblically Accurate", "Skibidi", "Goated"
            ]
    
    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv('DISCORD_TOKEN'),
            spotify_client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            spotify_client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
        )

@dataclass
class YouTubeConfig:
    format: str = 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best'
    restrictfilenames: bool = True
    noplaylist: bool = True
    nocheckcertificate: bool = True
    ignoreerrors: bool = False
    logtostderr: bool = False
    quiet: bool = True
    no_warnings: bool = True
    default_search: str = 'auto'
    source_address: str = '0.0.0.0'
    outtmpl: str = '%(title)s-%(id)s.%(ext)s'
    extractaudio: bool = True
    audioformat: str = 'mp3'
    audioquality: str = '192K'
    
    @property
    def to_dict(self) -> Dict[str, Any]:
        return {
            'format': self.format,
            'restrictfilenames': self.restrictfilenames,
            'noplaylist': self.noplaylist,
            'nocheckcertificate': self.nocheckcertificate,
            'ignoreerrors': self.ignoreerrors,
            'logtostderr': self.logtostderr,
            'quiet': self.quiet,
            'no_warnings': self.no_warnings,
            'default_search': self.default_search,
            'source_address': self.source_address,
            'outtmpl': self.outtmpl,
            'extractaudio': self.extractaudio,
            'audioformat': self.audioformat,
            'audioquality': self.audioquality,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

# Global config instance
config = BotConfig.from_env()
youtube_config = YouTubeConfig() 