import discord
from discord.ext import commands
import asyncio
import re
from typing import Optional
import logging
from youtubesearchpython import VideosSearch
import requests
import base64
import os

from music.player import music_player, YTDLSource
from utils.database import db
from utils.error_handler import handle_errors, log_command
from utils.helpers import validate_youtube_url, format_duration, create_success_embed, create_error_embed, create_info_embed
from config import config

logger = logging.getLogger(__name__)

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
        
        # Clean up queue and files
        music_player.clear_queue()
        if self.current_file and os.path.exists(self.current_file):
            os.remove(self.current_file)
        
        # Clean up normalized files
        if music_player.current_track and music_player.current_track.normalized_filename:
            if os.path.exists(music_player.current_track.normalized_filename):
                os.remove(music_player.current_track.normalized_filename)
        
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
                
                if voice_client.is_playing() or self.is_processing:
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
    
    @commands.command(name='playlist', help='Play a Spotify playlist')
    @handle_errors
    @log_command
    async def playlist(self, ctx, playlist_url: str):
        """Play a Spotify playlist"""
        if not ctx.author.voice:
            embed = create_error_embed("You are not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        # Extract playlist ID
        playlist_uri = playlist_url.split("/")[-1].split("?")[0]
        
        try:
            # Get Spotify access token
            auth_url = 'https://accounts.spotify.com/api/token'
            auth_headers = {
                'Authorization': 'Basic ' + base64.b64encode(
                    (config.spotify_client_id + ":" + config.spotify_client_secret).encode()
                ).decode("ascii")
            }
            auth_body = {'grant_type': 'client_credentials'}
            
            auth_response = requests.post(auth_url, data=auth_body, headers=auth_headers)
            access_token = auth_response.json()['access_token']
            
            # Get playlist tracks
            playlist_url = f'https://api.spotify.com/v1/playlists/{playlist_uri}/tracks?fields=items(track(name,artists(name)))'
            playlist_headers = {'Authorization': f'Bearer {access_token}'}
            
            playlist_response = requests.get(playlist_url, headers=playlist_headers)
            tracks = playlist_response.json()['items']
            
            # Convert to search queries
            search_queries = []
            for item in tracks:
                track_name = item['track']['name']
                artists = ', '.join([artist['name'] for artist in item['track']['artists']])
                search_queries.append(f"{track_name} by {artists}")
            
            # Shuffle and add to queue
            import random
            random.shuffle(search_queries)
            
            embed = create_success_embed(f"Adding {len(search_queries)} tracks from Spotify playlist to queue...")
            await ctx.send(embed=embed)
            
            # Add tracks to queue
            for query in search_queries[:20]:  # Limit to 20 tracks
                try:
                    search_results = VideosSearch(query, limit=1).result()
                    if search_results and search_results.get('result'):
                        url = search_results['result'][0]['link']
                        track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                        music_player.add_track(track)
                except Exception as e:
                    logger.error(f"Error adding track from playlist: {e}")
                    continue
            
            embed = create_success_embed(f"Added {len(search_queries[:20])} tracks to the queue!")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error processing Spotify playlist: {e}")
            embed = create_error_embed(f"Error processing Spotify playlist: {str(e)}")
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
            # Clean up the problematic file
            if os.path.exists(track.filename):
                try:
                    os.remove(track.filename)
                except:
                    pass
            if track.normalized_filename and os.path.exists(track.normalized_filename):
                try:
                    os.remove(track.normalized_filename)
                except:
                    pass
            
            embed = create_error_embed(f"Error playing track: {str(e)}")
            await ctx.send(embed=embed)
        finally:
            self.is_processing = False
    
    async def _play_next(self, ctx):
        """Play the next track in queue"""
        # Clean up current file
        if self.current_file and os.path.exists(self.current_file):
            os.remove(self.current_file)
        
        if music_player.queue:
            next_track = music_player.queue.pop(0)
            await self._play_track(ctx, next_track)
        else:
            music_player.is_playing = False
            music_player.current_track = None
            embed = create_info_embed("Queue Empty", "No more tracks in the queue.")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCommands(bot)) 