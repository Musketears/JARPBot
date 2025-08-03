import discord
import asyncio
import random
import string
import os
import yt_dlp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from config import youtube_config, config

logger = logging.getLogger(__name__)

@dataclass
class Track:
    title: str
    url: str
    duration: int
    requester_id: int
    requester_name: str
    filename: str
    thumbnail: Optional[str] = None
    added_at: datetime = None
    
    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now()

class MusicPlayer:
    def __init__(self):
        self.queue: List[Track] = []
        self.current_track: Optional[Track] = None
        self.loop = False
        self.volume = config.default_volume
        self.is_playing = False
        self.is_paused = False
        
        # Updated yt-dlp configuration for better compatibility
        ytdl_options = {
            'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'outtmpl': '%(title)s-%(id)s.%(ext)s',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        self.ytdl = yt_dlp.YoutubeDL(ytdl_options)
    
    async def download_track(self, url: str, requester_id: int, requester_name: str) -> Track:
        """Download a track from URL"""
        try:
            # Extract info first
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
            
            if 'entries' in data:
                # Take first item from a playlist
                data = data['entries'][0]
            
            # Download the audio
            download_data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=True))
            
            if 'entries' in download_data:
                download_data = download_data['entries'][0]
            
            # Generate expected filename
            expected_filename = self.ytdl.prepare_filename(download_data)
            
            # Handle different file extensions
            if not expected_filename.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                expected_filename = expected_filename.rsplit('.', 1)[0] + '.mp3'
            
            # Generate unique filename
            filename, file_extension = os.path.splitext(expected_filename)
            unique_filename = f"{filename}_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}{file_extension}"
            
            # Look for the downloaded file with better detection
            downloaded_file = None
            
            # First check if the expected file exists
            if os.path.exists(expected_filename):
                downloaded_file = expected_filename
            else:
                # Search for files with similar names in current directory
                base_name = expected_filename.rsplit('.', 1)[0]
                for file in os.listdir('.'):
                    if (file.startswith(base_name) and 
                        file.endswith(('.mp3', '.m4a', '.webm', '.ogg')) and
                        os.path.isfile(file)):
                        downloaded_file = file
                        break
                
                # If still not found, look for any recently created audio files
                if downloaded_file is None:
                    current_time = datetime.now()
                    for file in os.listdir('.'):
                        if (file.endswith(('.mp3', '.m4a', '.webm', '.ogg')) and 
                            os.path.isfile(file)):
                            try:
                                file_time = datetime.fromtimestamp(os.path.getctime(file))
                                if (current_time - file_time).total_seconds() < 60:  # File created in last minute
                                    downloaded_file = file
                                    break
                            except:
                                continue
            
            if downloaded_file is None:
                raise Exception("Downloaded audio file not found")
            
            # Rename to unique filename
            if downloaded_file != unique_filename:
                os.rename(downloaded_file, unique_filename)
            
            return Track(
                title=data.get('title', 'Unknown Title'),
                url=url,
                duration=data.get('duration', 0),
                requester_id=requester_id,
                requester_name=requester_name,
                filename=unique_filename,
                thumbnail=data.get('thumbnail')
            )
        
        except Exception as e:
            logger.error(f"Error downloading track {url}: {e}")
            raise
    
    def add_track(self, track: Track, position: Optional[int] = None):
        """Add track to queue"""
        if len(self.queue) >= config.max_queue_size:
            raise ValueError(f"Queue is full (max {config.max_queue_size} tracks)")
        
        if position is None:
            self.queue.append(track)
        else:
            self.queue.insert(position, track)
        
        logger.info(f"Added track '{track.title}' to queue by {track.requester_name}")
    
    def remove_track(self, index: int) -> Optional[Track]:
        """Remove track from queue by index"""
        if 0 <= index < len(self.queue):
            track = self.queue.pop(index)
            logger.info(f"Removed track '{track.title}' from queue")
            return track
        return None
    
    def clear_queue(self):
        """Clear the queue"""
        self.queue.clear()
        logger.info("Queue cleared")
    
    def shuffle_queue(self):
        """Shuffle the queue"""
        random.shuffle(self.queue)
        logger.info("Queue shuffled")
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information"""
        return {
            'current_track': self.current_track.title if self.current_track else None,
            'queue_length': len(self.queue),
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'volume': self.volume,
            'loop': self.loop
        }
    
    def get_queue_tracks(self) -> List[Dict[str, Any]]:
        """Get list of tracks in queue with formatted info"""
        tracks = []
        for i, track in enumerate(self.queue):
            duration_str = f"{track.duration//60}:{track.duration%60:02d}" if track.duration else "Unknown"
            tracks.append({
                'position': i + 1,
                'title': track.title,
                'duration': duration_str,
                'requester': track.requester_name,
                'added_at': track.added_at.strftime("%H:%M")
            })
        return tracks
    
    async def cleanup_files(self, tracks: List[Track]):
        """Clean up downloaded files"""
        for track in tracks:
            try:
                if os.path.exists(track.filename):
                    os.remove(track.filename)
                    logger.debug(f"Cleaned up file: {track.filename}")
            except Exception as e:
                logger.error(f"Error cleaning up file {track.filename}: {e}")

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url', '')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        # Use improved yt-dlp options for better audio extraction
        ytdl_options = {
            'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'outtmpl': '%(title)s-%(id)s.%(ext)s',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        ytdl = yt_dlp.YoutubeDL(ytdl_options)
        
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        
        og_filename = data['title'] if stream else ytdl.prepare_filename(data)
        
        # Ensure we have a proper audio file extension
        if not og_filename.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
            og_filename = og_filename.rsplit('.', 1)[0] + '.mp3'
        
        filename, file_extension = os.path.splitext(og_filename)
        filename = f"{filename}_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}{file_extension}"
        
        if not stream:
            # Handle file renaming with better error handling
            if os.path.exists(og_filename):
                os.rename(og_filename, filename)
            else:
                # If the original file doesn't exist, check for files with similar names
                base_name = og_filename.rsplit('.', 1)[0]
                for file in os.listdir('.'):
                    if file.startswith(base_name) and file.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                        os.rename(file, filename)
                        break
                else:
                    raise Exception("Downloaded audio file not found")
        
        return filename

# Global music player instance
music_player = MusicPlayer() 