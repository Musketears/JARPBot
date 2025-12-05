import discord
from discord.ext import commands
import asyncio
import re
from typing import Optional
import logging
from youtubesearchpython import VideosSearch
import os

from music.player import music_player, YTDLSource
from utils.database import db
from utils.cache_manager import cache_manager
from utils.error_handler import handle_errors, log_command
from utils.helpers import validate_youtube_url, format_duration, create_success_embed, create_error_embed, create_info_embed
from utils.wrapped_generator import generate_wrapped_image_async
from config import config
import io

logger = logging.getLogger(__name__)

# Global lock to prevent multiple commands from processing simultaneously
_global_processing_lock = asyncio.Lock()

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_file = ''
        self.is_processing = False
    
    @commands.command(name='join', help='Join the voice channel')
    @handle_errors
    @log_command
    async def join(self, ctx):
        """Join the user's voice channel"""
        if not ctx.author.voice:
            embed = create_error_embed("You are not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client
        
        if voice_client and voice_client.is_connected():
            if voice_client.channel == channel:
                embed = create_info_embed("Already Connected", f"I'm already in {channel.name}")
                await ctx.send(embed=embed)
                return
            else:
                await voice_client.move_to(channel)
        else:
            await channel.connect()
        
        embed = create_success_embed(f"Joined {channel.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='leave', help='Leave the voice channel')
    @handle_errors
    @log_command
    async def leave(self, ctx):
        """Leave the voice channel and clear queue"""
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = create_error_embed("I'm not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        # Clean up current track files
        music_player.cleanup_current_track()
        
        # Clean up queue and files
        music_player.clear_queue()
        
        # Clean up any remaining files
        if self.current_file and os.path.exists(self.current_file):
            try:
                os.remove(self.current_file)
                logger.debug(f"Cleaned up file: {self.current_file}")
            except Exception as e:
                logger.error(f"Error cleaning up file {self.current_file}: {e}")
        
        await voice_client.disconnect()
        embed = create_success_embed("Left the voice channel")
        await ctx.send(embed=embed)
    
    @commands.command(name='play', help='Play a song from YouTube search')
    @handle_errors
    @log_command
    async def play(self, ctx, *, query: str):
        """Play a song from YouTube search"""
        if not ctx.author.voice:
            embed = create_error_embed("You are not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        # Join voice channel if not connected
        voice_client = ctx.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await ctx.author.voice.channel.connect()
            voice_client = ctx.guild.voice_client
        
        async with ctx.typing():
            async with _global_processing_lock:
                try:
                    # Search for the song
                    if validate_youtube_url(query):
                        url = query
                    else:
                        search_results = VideosSearch(query, limit=1).result()
                        if not search_results or not search_results.get('result'):
                            embed = create_error_embed("No results found for your search.")
                            await ctx.send(embed=embed)
                            return
                        url = search_results['result'][0]['link']
                    
                    # Download and add to queue
                    track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                    
                    if voice_client.is_playing() or music_player.is_playing:
                        music_player.add_track(track)
                        embed = create_success_embed(f"Added **{track.title}** to the queue")
                        await ctx.send(embed=embed)
                    else:
                        # Play immediately
                        await self._play_track(ctx, track)
                
                except Exception as e:
                    logger.error(f"Error playing track: {e}")
                    embed = create_error_embed(f"Error playing the song: {str(e)}")
                    await ctx.send(embed=embed)
    
    @commands.command(name='play_first', help='Add a song to the front of the queue')
    @handle_errors
    @log_command
    async def play_first(self, ctx, *, query: str):
        """Add a song to the front of the queue"""
        if not ctx.author.voice:
            embed = create_error_embed("You are not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        async with ctx.typing():
            async with _global_processing_lock:
                try:
                    # Search for the song
                    if validate_youtube_url(query):
                        url = query
                    else:
                        search_results = VideosSearch(query, limit=1).result()
                        if not search_results or not search_results.get('result'):
                            embed = create_error_embed("No results found for your search.")
                            await ctx.send(embed=embed)
                            return
                        url = search_results['result'][0]['link']
                    
                    # Download and add to front of queue
                    track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                    music_player.add_track(track, position=0)
                    
                    embed = create_success_embed(f"Added **{track.title}** to the front of the queue")
                    await ctx.send(embed=embed)
                
                except Exception as e:
                    logger.error(f"Error adding track to front: {e}")
                    embed = create_error_embed(f"Error adding the song: {str(e)}")
                    await ctx.send(embed=embed)
    
    @commands.command(name='skip', help='Skip the current song')
    @handle_errors
    @log_command
    async def skip(self, ctx):
        """Skip the current song"""
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_playing():
            embed = create_error_embed("I'm not playing anything right now.")
            await ctx.send(embed=embed)
            return
        
        # Clean up current track files before stopping
        music_player.cleanup_current_track()
        
        voice_client.stop()
        embed = create_success_embed("Skipped the current song")
        await ctx.send(embed=embed)
    
    @commands.command(name='pause', help='Pause the current song')
    @handle_errors
    @log_command
    async def pause(self, ctx):
        """Pause the current song"""
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_playing():
            embed = create_error_embed("I'm not playing anything right now.")
            await ctx.send(embed=embed)
            return
        
        voice_client.pause()
        embed = create_success_embed("Paused the music")
        await ctx.send(embed=embed)
    
    @commands.command(name='resume', help='Resume the current song')
    @handle_errors
    @log_command
    async def resume(self, ctx):
        """Resume the current song"""
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_paused():
            embed = create_error_embed("I'm not paused right now.")
            await ctx.send(embed=embed)
            return
        
        voice_client.resume()
        embed = create_success_embed("Resumed the music")
        await ctx.send(embed=embed)
    
    @commands.command(name='queue', help='Show the current queue')
    @handle_errors
    @log_command
    async def queue(self, ctx):
        """Show the current music queue"""
        queue_info = music_player.get_queue_info()
        queue_tracks = music_player.get_queue_tracks()
        
        embed = discord.Embed(title="🎵 Music Queue", color=0x1DB954)
        
        # Current track
        if queue_info['current_track']:
            embed.add_field(
                name="🎶 Now Playing",
                value=f"**{queue_info['current_track']}**",
                inline=False
            )
        
        # Queue
        if queue_tracks:
            queue_text = ""
            for track in queue_tracks[:10]:  # Show first 10 tracks
                queue_text += f"**{track['position']}.** {track['title']} ({track['duration']}) - {track['requester']}\n"
            
            if len(queue_tracks) > 10:
                queue_text += f"\n... and {len(queue_tracks) - 10} more tracks"
            
            embed.add_field(
                name=f"📋 Queue ({len(queue_tracks)} tracks)",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Queue",
                value="The queue is empty",
                inline=False
            )
        
        # Queue info
        embed.add_field(
            name="ℹ️ Info",
            value=f"**Volume:** {int(queue_info['volume'] * 100)}%\n**Loop:** {'On' if queue_info['loop'] else 'Off'}\n**Normalization:** {'On' if music_player.normalize_audio else 'Off'}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='shuffle', help='Shuffle the queue')
    @handle_errors
    @log_command
    async def shuffle(self, ctx):
        """Shuffle the music queue"""
        if len(music_player.queue) < 2:
            embed = create_error_embed("Need at least 2 tracks to shuffle.")
            await ctx.send(embed=embed)
            return
        
        music_player.shuffle_queue()
        embed = create_success_embed("Shuffled the queue")
        await ctx.send(embed=embed)
    
    @commands.command(name='clear', help='Clear the queue')
    @handle_errors
    @log_command
    async def clear(self, ctx):
        """Clear the music queue"""
        # Clean up current track files
        music_player.cleanup_current_track()
        
        # Clear queue and clean up files
        music_player.clear_queue()
        
        embed = create_success_embed("Cleared the queue")
        await ctx.send(embed=embed)
    
    @commands.command(name='volume', help='Set the volume (0-100) or show current volume')
    @handle_errors
    @log_command
    async def volume(self, ctx, volume: Optional[int] = None):
        """Set the music volume or show current volume"""
        if volume is None:
            # Show current volume
            current_volume = int(music_player.volume * 100)
            embed = create_info_embed("Current Volume", f"The current volume is **{current_volume}%**")
            await ctx.send(embed=embed)
            return
        
        if not 0 <= volume <= 100:
            embed = create_error_embed("Volume must be between 0 and 100.")
            await ctx.send(embed=embed)
            return
        
        music_player.volume = volume / 100
        voice_client = ctx.guild.voice_client
        
        # Update volume on current source if it's a PCMVolumeTransformer
        if voice_client and voice_client.source:
            if isinstance(voice_client.source, discord.PCMVolumeTransformer):
                voice_client.source.volume = music_player.volume
            elif hasattr(voice_client.source, 'volume'):
                voice_client.source.volume = music_player.volume
        
        embed = create_success_embed(f"Volume set to {volume}%")
        await ctx.send(embed=embed)
    
    @commands.command(name='normalize', help='Toggle audio normalization (makes all songs same volume)')
    @handle_errors
    @log_command
    async def normalize(self, ctx):
        """Toggle audio normalization on/off"""
        music_player.normalize_audio = not music_player.normalize_audio
        status = "enabled" if music_player.normalize_audio else "disabled"
        embed = create_success_embed(f"Audio normalization {status}")
        await ctx.send(embed=embed)
    
    @commands.command(name='normalize_info', help='Show audio normalization settings')
    @handle_errors
    @log_command
    async def normalize_info(self, ctx):
        """Show current audio normalization settings"""
        embed = discord.Embed(title="🎵 Audio Normalization Settings", color=0x1DB954)
        
        embed.add_field(
            name="Status",
            value="✅ Enabled" if music_player.normalize_audio else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="Target Loudness",
            value="-16 LUFS",
            inline=True
        )
        
        embed.add_field(
            name="True Peak",
            value="-1 dB",
            inline=True
        )
        
        embed.add_field(
            name="Description",
            value="Audio normalization ensures all songs have consistent volume levels for better listening experience.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='cleanup', help='Clean up orphaned audio files')
    @handle_errors
    @log_command
    async def cleanup(self, ctx):
        """Clean up orphaned audio files"""
        embed = create_info_embed("Cleaning Up", "Cleaning up orphaned audio files...")
        await ctx.send(embed=embed)
        
        try:
            music_player.cleanup_orphaned_files()
            embed = create_success_embed("Orphaned audio files have been cleaned up.")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            embed = create_error_embed(f"Error during cleanup: {str(e)}")
            await ctx.send(embed=embed)
    

    
    async def _play_track(self, ctx, track):
        """Play a track"""
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            return
        
        self.is_processing = True
        self.current_file = track.filename
        
        try:
            # Use normalized file if available, otherwise use original
            audio_file = track.normalized_filename if track.normalized_filename and os.path.exists(track.normalized_filename) else track.filename
            
            # Check if the file exists and is a valid audio file
            if not os.path.exists(audio_file):
                raise Exception(f"Audio file not found: {audio_file}")
            
            # Check file size to ensure it's not empty
            if os.path.getsize(audio_file) == 0:
                raise Exception("Downloaded audio file is empty")
            
            # Check if file has a valid audio extension
            valid_extensions = ('.mp3', '.m4a', '.webm', '.ogg', '.wav', '.flac')
            if not audio_file.lower().endswith(valid_extensions):
                raise Exception(f"Invalid audio file format: {audio_file}")
            
            # Record the song play in the database
            try:
                await db.record_song_play(
                    user_id=str(track.requester_id),
                    song_title=track.title,
                    song_artist="YouTube",  # Default since we don't have artist info from YouTube
                    song_url=track.url
                )
            except Exception as e:
                logger.error(f"Failed to record song play: {e}")
            
            # Create FFmpegPCMAudio source and wrap it with PCMVolumeTransformer for volume control
            ffmpeg_source = discord.FFmpegPCMAudio(
                executable=config.ffmpeg_path,
                source=audio_file
            )
            
            # Wrap with volume transformer
            volume_source = discord.PCMVolumeTransformer(ffmpeg_source)
            volume_source.volume = music_player.volume
            
            voice_client.play(
                volume_source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._play_next(ctx), self.bot.loop
                )
            )
            
            music_player.current_track = track
            music_player.is_playing = True
            
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{track.title}**",
                color=0x1DB954
            )
            embed.add_field(name="Duration", value=format_duration(track.duration))
            embed.add_field(name="Requested by", value=track.requester_name)
            
            # Add normalization status
            if track.normalized_filename and os.path.exists(track.normalized_filename):
                embed.add_field(name="Audio", value="✅ Normalized", inline=True)
            else:
                embed.add_field(name="Audio", value="📊 Original", inline=True)
            
            if track.thumbnail:
                embed.set_thumbnail(url=track.thumbnail)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            # Clean up the problematic file (only if not cached)
            if os.path.exists(track.filename):
                # Check if this is a cached file
                cache_audio_dir = os.path.join("cache", "audio")
                is_cached = track.filename.startswith(cache_audio_dir)
                
                if not is_cached:
                    try:
                        os.remove(track.filename)
                        logger.debug(f"Cleaned up file: {track.filename}")
                    except Exception as cleanup_error:
                        logger.error(f"Error cleaning up file {track.filename}: {cleanup_error}")
                else:
                    logger.debug(f"Skipped cleanup of cached file: {track.filename}")
                    
            if track.normalized_filename and os.path.exists(track.normalized_filename):
                # Check if this is a cached normalized file
                cache_normalized_dir = os.path.join("cache", "normalized")
                is_cached_normalized = track.normalized_filename.startswith(cache_normalized_dir)
                
                if not is_cached_normalized:
                    try:
                        os.remove(track.normalized_filename)
                        logger.debug(f"Cleaned up normalized file: {track.normalized_filename}")
                    except Exception as cleanup_error:
                        logger.error(f"Error cleaning up normalized file {track.normalized_filename}: {cleanup_error}")
                else:
                    logger.debug(f"Skipped cleanup of cached normalized file: {track.normalized_filename}")
            
            embed = create_error_embed(f"Error playing track: {str(e)}")
            await ctx.send(embed=embed)
        finally:
            self.is_processing = False
    
    async def _play_next(self, ctx):
        """Play the next track in queue"""
        # Clean up current track files
        music_player.cleanup_current_track()
        
        # Clean up any remaining files (only if they're not cached)
        if self.current_file and os.path.exists(self.current_file):
            # Check if this is a cached file
            cache_audio_dir = os.path.join("cache", "audio")
            cache_normalized_dir = os.path.join("cache", "normalized")
            
            is_cached = (self.current_file.startswith(cache_audio_dir) or 
                        self.current_file.startswith(cache_normalized_dir))
            
            if not is_cached:
                try:
                    os.remove(self.current_file)
                    logger.debug(f"Cleaned up file: {self.current_file}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {self.current_file}: {e}")
            else:
                logger.debug(f"Skipped cleanup of cached file: {self.current_file}")
        
        if music_player.queue:
            next_track = music_player.queue.pop(0)
            await self._play_track(ctx, next_track)
        else:
            music_player.is_playing = False
            music_player.current_track = None
            embed = create_info_embed("Queue Empty", "No more tracks in the queue.")
            await ctx.send(embed=embed)
    
    @commands.command(name='mystats', help='Show your music listening statistics')
    @handle_errors
    @log_command
    async def mystats(self, ctx):
        """Show user's music listening statistics"""
        user_id = str(ctx.author.id)
        
        try:
            # Get user's song statistics
            user_stats = await db.get_user_song_stats(user_id)
            favorites = await db.get_user_favorite_songs(user_id, limit=5)
            recent_history = await db.get_user_song_history(user_id, limit=5)
            
            embed = discord.Embed(
                title="🎵 Your Music Stats",
                description=f"Statistics for {ctx.author.display_name}",
                color=0x1DB954
            )
            
            # Add statistics fields
            embed.add_field(
                name="📊 Total Plays", 
                value=f"{user_stats['total_plays']} songs", 
                inline=True
            )
            embed.add_field(
                name="🎼 Unique Songs", 
                value=f"{user_stats['unique_songs']} different tracks", 
                inline=True
            )
            embed.add_field(
                name="📅 Today's Plays", 
                value=f"{user_stats['today_plays']} songs", 
                inline=True
            )
            
            # Add favorite songs
            if favorites:
                favorites_text = "\n".join([
                    f"**{i+1}.** {song['song_title']} ({song['play_count']} plays)"
                    for i, song in enumerate(favorites)
                ])
                embed.add_field(
                    name="❤️ Your Favorites",
                    value=favorites_text,
                    inline=False
                )
            
            # Add recent plays
            if recent_history:
                recent_text = "\n".join([
                    f"**{i+1}.** {song['song_title']}"
                    for i, song in enumerate(recent_history)
                ])
                embed.add_field(
                    name="🕒 Recent Plays",
                    value=recent_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            embed = create_error_embed("Error retrieving your music statistics.")
            await ctx.send(embed=embed)
    
    @commands.command(name='userstats', help='Show another user\'s music listening statistics')
    @handle_errors
    @log_command
    async def userstats(self, ctx, member: discord.Member):
        """Show another user's music listening statistics"""
        user_id = str(member.id)
        
        try:
            # Get user's song statistics
            user_stats = await db.get_user_song_stats(user_id)
            favorites = await db.get_user_favorite_songs(user_id, limit=5)
            recent_history = await db.get_user_song_history(user_id, limit=5)
            
            embed = discord.Embed(
                title="🎵 User Music Stats",
                description=f"Statistics for {member.display_name}",
                color=0x1DB954
            )
            
            # Add statistics fields
            embed.add_field(
                name="📊 Total Plays", 
                value=f"{user_stats['total_plays']} songs", 
                inline=True
            )
            embed.add_field(
                name="🎼 Unique Songs", 
                value=f"{user_stats['unique_songs']} different tracks", 
                inline=True
            )
            embed.add_field(
                name="📅 Today's Plays", 
                value=f"{user_stats['today_plays']} songs", 
                inline=True
            )
            
            # Add favorite songs
            if favorites:
                favorites_text = "\n".join([
                    f"**{i+1}.** {song['song_title']} ({song['play_count']} plays)"
                    for i, song in enumerate(favorites)
                ])
                embed.add_field(
                    name="❤️ Their Favorites",
                    value=favorites_text,
                    inline=False
                )
            
            # Add recent plays
            if recent_history:
                recent_text = "\n".join([
                    f"**{i+1}.** {song['song_title']}"
                    for i, song in enumerate(recent_history)
                ])
                embed.add_field(
                    name="🕒 Recent Plays",
                    value=recent_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            embed = create_error_embed("Error retrieving user music statistics.")
            await ctx.send(embed=embed)
    
    @commands.command(name='usertopsongs', help='Show another user\'s top songs')
    @handle_errors
    @log_command
    async def usertopsongs(self, ctx, member: discord.Member, limit: int = 10):
        """Show another user's top songs"""
        if limit > 20:
            limit = 20  # Cap at 20 to prevent spam
        
        user_id = str(member.id)
        
        try:
            # Get user's favorite songs
            favorites = await db.get_user_favorite_songs(user_id, limit=limit)
            
            if not favorites:
                embed = create_info_embed(
                    "No Songs Found", 
                    f"{member.display_name} hasn't played any songs yet!"
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"🎵 {member.display_name}'s Top Songs",
                description=f"Most played songs by {member.display_name} (Top {len(favorites)})",
                color=0x1DB954
            )
            
            for i, song in enumerate(favorites):
                embed.add_field(
                    name=f"#{i+1} {song['song_title']}",
                    value=f"🎵 {song['play_count']} plays\n👤 {song['song_artist']}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user top songs: {e}")
            embed = create_error_embed("Error retrieving user's top songs.")
            await ctx.send(embed=embed)
    
    @commands.command(name='topcharts', help='Show the most played songs')
    @handle_errors
    @log_command
    async def topcharts(self, ctx, limit: int = 10):
        """Show the most played songs"""
        if limit > 20:
            limit = 20  # Cap at 20 to prevent spam
        
        try:
            top_songs = await db.get_song_stats(limit=limit)
            
            if not top_songs:
                embed = create_info_embed("No Songs Played", "No songs have been played yet!")
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🏆 Top Charts",
                description=f"Most played songs (Top {len(top_songs)})",
                color=0x1DB954
            )
            
            for i, song in enumerate(top_songs):
                embed.add_field(
                    name=f"#{i+1} {song['song_title']}",
                    value=f"🎵 {song['play_count']} plays\n👤 {song['song_artist']}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting top charts: {e}")
            embed = create_error_embed("Error retrieving top charts.")
            await ctx.send(embed=embed)
    
    @commands.command(name='recentplays', help='Show recent song plays')
    @handle_errors
    @log_command
    async def recentplays(self, ctx, hours: int = 24):
        """Show recent song plays within the specified hours"""
        if hours > 168:  # Cap at 1 week
            hours = 168
        
        try:
            recent_plays = await db.get_recent_song_plays(hours=hours, limit=15)
            
            if not recent_plays:
                embed = create_info_embed("No Recent Plays", f"No songs played in the last {hours} hours.")
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🕒 Recent Plays",
                description=f"Songs played in the last {hours} hours",
                color=0x1DB954
            )
            
            for i, play in enumerate(recent_plays):
                embed.add_field(
                    name=f"{i+1}. {play['song_title']}",
                    value=f"👤 {play['song_artist']}\n🎵 Requested by <@{play['user_id']}>",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting recent plays: {e}")
            embed = create_error_embed("Error retrieving recent plays.")
            await ctx.send(embed=embed)
    
    @commands.command(name='songstats', help='Show overall music statistics')
    @handle_errors
    @log_command
    async def songstats(self, ctx):
        """Show overall music statistics"""
        try:
            total_plays = await db.get_total_songs_played()
            unique_songs = await db.get_unique_songs_count()
            
            embed = discord.Embed(
                title="📊 Music Statistics",
                description="Overall music bot usage statistics",
                color=0x1DB954
            )
            
            embed.add_field(
                name="🎵 Total Plays",
                value=f"{total_plays} songs played",
                inline=True
            )
            embed.add_field(
                name="🎼 Unique Songs",
                value=f"{unique_songs} different tracks",
                inline=True
            )
            
            if total_plays > 0:
                avg_plays_per_song = total_plays / unique_songs
                embed.add_field(
                    name="📈 Average Plays per Song",
                    value=f"{avg_plays_per_song:.1f} plays",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting song stats: {e}")
            embed = create_error_embed("Error retrieving music statistics.")
            await ctx.send(embed=embed)
    
    @commands.command(name='cache', help='Show cache statistics')
    @handle_errors
    @log_command
    async def cache_stats(self, ctx):
        """Show cache statistics"""
        try:
            stats = await cache_manager.get_cache_stats()
            
            if not stats['enabled']:
                embed = create_info_embed("Cache Disabled", "Audio cache is currently disabled.")
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="💾 Cache Statistics",
                description="Audio cache performance and usage",
                color=0x1DB954
            )
            
            embed.add_field(
                name="📊 Usage",
                value=f"**Songs:** {stats['total_songs']}\n**Size:** {stats['actual_disk_size_mb']}MB / {stats['max_size_mb']}MB\n**Files:** {stats['audio_files']} audio, {stats['normalized_files']} normalized",
                inline=True
            )
            
            embed.add_field(
                name="⚙️ Settings",
                value=f"**Max Age:** {stats['max_age_days']} days\n**Status:** {'✅ Enabled' if stats['enabled'] else '❌ Disabled'}",
                inline=True
            )
            
            # Add top songs if available
            if stats.get('top_songs'):
                top_songs_text = "\n".join([
                    f"**{i+1}.** {song['title']} ({song['access_count']} plays)"
                    for i, song in enumerate(stats['top_songs'][:3])
                ])
                embed.add_field(
                    name="🔥 Most Cached",
                    value=top_songs_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            embed = create_error_embed("Error retrieving cache statistics.")
            await ctx.send(embed=embed)
    
    @commands.command(name='cache_cleanup', help='Clean up old cache entries')
    @handle_errors
    @log_command
    async def cache_cleanup(self, ctx):
        """Clean up old cache entries"""
        try:
            embed = create_info_embed("Cleaning Cache", "Cleaning up old cache entries...")
            await ctx.send(embed=embed)
            
            result = await cache_manager.cleanup_cache()
            
            if result['cleaned'] > 0:
                embed = create_success_embed(
                    f"Cache Cleanup Complete",
                    f"Removed **{result['cleaned']}** entries and freed **{result['freed_mb']}MB** of space."
                )
            else:
                embed = create_info_embed(
                    "Cache Cleanup Complete",
                    "No cache entries needed cleanup."
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            embed = create_error_embed(f"Error during cache cleanup: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='cache_clear', help='Clear all cache entries (admin only)')
    @handle_errors
    @log_command
    async def cache_clear(self, ctx):
        """Clear all cache entries"""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            embed = create_error_embed("Permission Denied", "You need administrator permissions to clear the cache.")
            await ctx.send(embed=embed)
            return
        
        try:
            embed = discord.Embed(
                title="⚠️ Clear Cache",
                description="Are you sure you want to clear all cache entries? This will remove all cached songs.",
                color=0xFFA500
            )
            embed.add_field(
                name="This will:",
                value="• Remove all cached audio files\n• Clear cache database entries\n• Free up disk space",
                inline=False
            )
            
            # Add confirmation buttons
            from discord.ui import View, Button
            from discord import ButtonStyle
            
            class CacheClearView(View):
                def __init__(self, ctx):
                    super().__init__(timeout=30.0)
                    self.ctx = ctx
                
                async def interaction_check(self, interaction):
                    return interaction.user.id == self.ctx.author.id
                
                @discord.ui.button(label="Clear Cache", style=ButtonStyle.danger)
                async def clear_cache(self, interaction, button):
                    try:
                        # Get cache stats before clearing
                        stats = await cache_manager.get_cache_stats()
                        total_songs = stats.get('total_songs', 0)
                        total_size = stats.get('actual_disk_size_mb', 0)
                        
                        # Clear cache database
                        await db.cleanup_old_cache(0)  # Remove all entries
                        
                        # Clear cache files
                        import shutil
                        if os.path.exists(cache_manager.audio_dir):
                            shutil.rmtree(cache_manager.audio_dir)
                            os.makedirs(cache_manager.audio_dir)
                        if os.path.exists(cache_manager.normalized_dir):
                            shutil.rmtree(cache_manager.normalized_dir)
                            os.makedirs(cache_manager.normalized_dir)
                        
                        embed = create_success_embed(
                            "Cache Cleared",
                            f"Successfully cleared **{total_songs}** cached songs and freed **{total_size}MB** of space."
                        )
                        await interaction.response.edit_message(embed=embed, view=None)
                        
                    except Exception as e:
                        logger.error(f"Error clearing cache: {e}")
                        embed = create_error_embed(f"Error clearing cache: {str(e)}")
                        await interaction.response.edit_message(embed=embed, view=None)
                
                @discord.ui.button(label="Cancel", style=ButtonStyle.secondary)
                async def cancel(self, interaction, button):
                    embed = create_info_embed("Cancelled", "Cache clear operation cancelled.")
                    await interaction.response.edit_message(embed=embed, view=None)
            
            view = CacheClearView(ctx)
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error setting up cache clear: {e}")
            embed = create_error_embed(f"Error setting up cache clear: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='wrapped', help='Generate a Spotify Wrapped-style image for a user')
    @handle_errors
    @log_command
    async def wrapped(self, ctx, member: discord.Member = None):
        """Generate a Spotify Wrapped-style image showing user's music stats"""
        # Default to command author if no member specified
        if member is None:
            member = ctx.author
        
        user_id = str(member.id)
        
        # Send initial loading message
        loading_embed = discord.Embed(
            title="🎵 Generating Your Wrapped...",
            description=f"Creating a personalized music summary for **{member.display_name}**...\n\n✨ *Crunching the numbers...*",
            color=0x1DB954
        )
        loading_msg = await ctx.send(embed=loading_embed)
        
        try:
            # Get wrapped stats from database
            stats = await db.get_user_wrapped_stats(user_id)
            
            # Check if user has any data
            if stats['total_plays'] == 0:
                embed = create_info_embed(
                    "No Music Data",
                    f"**{member.display_name}** hasn't played any songs yet!\n\n"
                    "Start playing some music with `!play` to build up your wrapped stats! 🎵"
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Generate the wrapped image
            image_buffer = await generate_wrapped_image_async(
                user_name=member.display_name,
                user_id=user_id,
                avatar_url=str(member.display_avatar.url) if member.display_avatar else None,
                stats=stats
            )
            
            # Create Discord file from buffer
            file = discord.File(image_buffer, filename=f"wrapped_{member.id}.png")
            
            # Create embed with the image
            embed = discord.Embed(
                title=f"🎵 {member.display_name}'s Music Wrapped",
                description=f"**{stats['total_plays']:,}** songs played • **{stats['unique_songs']:,}** unique tracks",
                color=0x1DB954
            )
            
            # Add some text stats as fields
            if stats['top_songs']:
                top_song = stats['top_songs'][0]
                embed.add_field(
                    name="🏆 #1 Song",
                    value=f"**{top_song['song_title'][:40]}**\n{top_song['play_count']} plays",
                    inline=True
                )
            
            if stats['favorite_hour'] is not None:
                hour = stats['favorite_hour']
                time_str = f"{hour}:00" if hour >= 10 else f"0{hour}:00"
                period = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                embed.add_field(
                    name="⏰ Peak Hour",
                    value=f"**{display_hour}:00 {period}**\nYour most active time",
                    inline=True
                )
            
            if stats['days_with_music']:
                embed.add_field(
                    name="📅 Active Days",
                    value=f"**{stats['days_with_music']}** days\nwith music",
                    inline=True
                )
            
            embed.set_image(url=f"attachment://wrapped_{member.id}.png")
            embed.set_footer(text="Your personalized music journey • Powered by JARPbot")
            
            # Delete loading message and send the wrapped image
            await loading_msg.delete()
            await ctx.send(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error generating wrapped for {member.display_name}: {e}")
            embed = create_error_embed(
                f"Error generating wrapped image.\n\n"
                f"**Details:** {str(e)[:200]}\n\n"
                f"Try again later or contact an admin if this persists."
            )
            await loading_msg.edit(embed=embed)
    
    @commands.command(name='mywrapped', help='Generate your personal Spotify Wrapped-style image')
    @handle_errors
    @log_command
    async def mywrapped(self, ctx):
        """Shortcut to generate your own wrapped image"""
        await self.wrapped(ctx, ctx.author)

async def setup(bot):
    await bot.add_cog(MusicCommands(bot)) 