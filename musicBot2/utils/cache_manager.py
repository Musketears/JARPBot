import os
import re
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from config import config
from utils.database import db

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.cache_dir = config.cache_directory
        self.audio_dir = os.path.join(self.cache_dir, "audio")
        self.normalized_dir = os.path.join(self.cache_dir, "normalized")
        
        # Ensure cache directories exist
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.normalized_dir, exist_ok=True)
    
    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats"""
        if not url:
            return None
        
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_cached_song(self, url: str) -> Optional[Dict[str, Any]]:
        """Check if a song is cached and return its information"""
        if not config.cache_enabled:
            return None
        
        youtube_id = self.extract_youtube_id(url)
        if not youtube_id:
            return None
        
        try:
            cached_info = await db.get_cached_song(youtube_id)
            if not cached_info:
                return None
            
            # Check if files actually exist
            audio_file = os.path.join(self.audio_dir, cached_info['filename'])
            normalized_file = None
            if cached_info['normalized_filename']:
                normalized_file = os.path.join(self.normalized_dir, cached_info['normalized_filename'])
            
            if not os.path.exists(audio_file):
                # File doesn't exist, remove from cache
                await db.remove_cached_song(youtube_id)
                return None
            
            # Update access time and count
            await db.update_cache_access(youtube_id)
            
            # Update file paths to be relative to cache directories
            cached_info['audio_file'] = audio_file
            cached_info['normalized_file'] = normalized_file
            
            logger.info(f"Cache hit for YouTube ID: {youtube_id}")
            return cached_info
            
        except Exception as e:
            logger.error(f"Error checking cache for {url}: {e}")
            return None
    
    async def add_to_cache(self, youtube_id: str, title: str, duration: int, 
                          original_file: str, normalized_file: str = None) -> Dict[str, str]:
        """Add a song to the cache and return the cached file paths"""
        if not config.cache_enabled:
            return {'success': False}
        
        try:
            # Check if already cached to avoid race conditions
            existing_cache = await db.get_cached_song(youtube_id)
            if existing_cache:
                logger.info(f"Song already cached: {title}")
                return {
                    'success': True,
                    'audio_file': os.path.join(self.audio_dir, existing_cache['filename']),
                    'normalized_file': os.path.join(self.normalized_dir, existing_cache['normalized_filename']) if existing_cache['normalized_filename'] else None
                }
            
            # Move files to cache directories with atomic operations
            filename = os.path.basename(original_file)
            cached_audio_file = os.path.join(self.audio_dir, filename)
            
            # Use atomic move operation
            if os.path.exists(original_file):
                # Create a temporary file first to avoid race conditions
                temp_audio_file = f"{cached_audio_file}.tmp"
                os.rename(original_file, temp_audio_file)
                
                # Now move to final location
                if os.path.exists(cached_audio_file):
                    # If file already exists, remove the temp file
                    os.remove(temp_audio_file)
                    logger.warning(f"Cache file already exists: {cached_audio_file}")
                else:
                    os.rename(temp_audio_file, cached_audio_file)
                
                file_size = os.path.getsize(cached_audio_file)
            else:
                logger.error(f"Original file not found: {original_file}")
                return {'success': False}
            
            # Handle normalized file with atomic operations
            cached_normalized_file = None
            normalized_filename = None
            if normalized_file and os.path.exists(normalized_file):
                normalized_filename = os.path.basename(normalized_file)
                cached_normalized_file = os.path.join(self.normalized_dir, normalized_filename)
                
                # Use atomic move for normalized file too
                temp_normalized_file = f"{cached_normalized_file}.tmp"
                os.rename(normalized_file, temp_normalized_file)
                
                if os.path.exists(cached_normalized_file):
                    os.remove(temp_normalized_file)
                    logger.warning(f"Normalized cache file already exists: {cached_normalized_file}")
                else:
                    os.rename(temp_normalized_file, cached_normalized_file)
                
                file_size += os.path.getsize(cached_normalized_file)
            
            # Add to database with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await db.add_cached_song(
                        youtube_id=youtube_id,
                        title=title,
                        duration=duration,
                        filename=filename,
                        normalized_filename=normalized_filename,
                        file_size=file_size
                    )
                    break
                except Exception as db_error:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to add to database after {max_retries} attempts: {db_error}")
                        # Clean up files if database operation fails
                        if os.path.exists(cached_audio_file):
                            os.remove(cached_audio_file)
                        if cached_normalized_file and os.path.exists(cached_normalized_file):
                            os.remove(cached_normalized_file)
                        return {'success': False}
                    else:
                        logger.warning(f"Database operation failed, retrying... ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            
            logger.info(f"Added to cache: {title} (ID: {youtube_id})")
            return {
                'success': True,
                'audio_file': cached_audio_file,
                'normalized_file': cached_normalized_file
            }
            
        except Exception as e:
            logger.error(f"Error adding to cache: {e}")
            # Clean up any partially created files
            try:
                if 'cached_audio_file' in locals() and os.path.exists(cached_audio_file):
                    os.remove(cached_audio_file)
                if 'cached_normalized_file' in locals() and cached_normalized_file and os.path.exists(cached_normalized_file):
                    os.remove(cached_normalized_file)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up cache files: {cleanup_error}")
            return {'success': False}
    
    async def cleanup_cache(self) -> Dict[str, Any]:
        """Clean up cache based on size and age limits"""
        if not config.cache_enabled:
            return {'cleaned': 0, 'freed_mb': 0}
        
        try:
            cleaned_count = 0
            freed_bytes = 0
            
            # Clean up old entries (based on age)
            await db.cleanup_old_cache(config.cache_max_age)
            
            # Clean up based on size
            entries_to_remove = await db.get_cache_entries_to_cleanup(config.cache_max_size)
            
            for entry in entries_to_remove:
                try:
                    # Remove audio file
                    audio_file = os.path.join(self.audio_dir, f"{entry['youtube_id']}.mp3")
                    if os.path.exists(audio_file):
                        freed_bytes += os.path.getsize(audio_file)
                        os.remove(audio_file)
                    
                    # Remove normalized file if it exists
                    normalized_file = os.path.join(self.normalized_dir, f"{entry['youtube_id']}_normalized.mp3")
                    if os.path.exists(normalized_file):
                        freed_bytes += os.path.getsize(normalized_file)
                        os.remove(normalized_file)
                    
                    # Remove from database
                    await db.remove_cached_song(entry['youtube_id'])
                    cleaned_count += 1
                    
                    logger.info(f"Cleaned up cached song: {entry['title']}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up cache entry {entry['youtube_id']}: {e}")
            
            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            logger.info(f"Cache cleanup completed: {cleaned_count} entries removed, {freed_mb}MB freed")
            
            return {
                'cleaned': cleaned_count,
                'freed_mb': freed_mb
            }
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            return {'cleaned': 0, 'freed_mb': 0}
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not config.cache_enabled:
            return {'enabled': False}
        
        try:
            db_stats = await db.get_cache_stats()
            
            # Calculate actual disk usage
            total_disk_size = 0
            audio_files = 0
            normalized_files = 0
            
            if os.path.exists(self.audio_dir):
                for file in os.listdir(self.audio_dir):
                    file_path = os.path.join(self.audio_dir, file)
                    if os.path.isfile(file_path):
                        total_disk_size += os.path.getsize(file_path)
                        audio_files += 1
            
            if os.path.exists(self.normalized_dir):
                for file in os.listdir(self.normalized_dir):
                    file_path = os.path.join(self.normalized_dir, file)
                    if os.path.isfile(file_path):
                        total_disk_size += os.path.getsize(file_path)
                        normalized_files += 1
            
            return {
                'enabled': True,
                'total_songs': db_stats['total_songs'],
                'total_size_mb': db_stats['total_size_mb'],
                'actual_disk_size_mb': round(total_disk_size / (1024 * 1024), 2),
                'audio_files': audio_files,
                'normalized_files': normalized_files,
                'max_size_mb': config.cache_max_size,
                'max_age_days': config.cache_max_age,
                'top_songs': db_stats['top_songs'],
                'oldest_songs': db_stats['oldest_songs']
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'enabled': False, 'error': str(e)}
    
    def get_cache_file_path(self, youtube_id: str, is_normalized: bool = False) -> str:
        """Get the expected cache file path for a YouTube ID"""
        if is_normalized:
            return os.path.join(self.normalized_dir, f"{youtube_id}_normalized.mp3")
        else:
            return os.path.join(self.audio_dir, f"{youtube_id}.mp3")

# Global cache manager instance
cache_manager = CacheManager() 