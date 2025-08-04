import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional
import re

from utils.database import db
from utils.error_handler import handle_errors, log_command
from utils.helpers import create_success_embed, create_error_embed, create_info_embed
from music.player import music_player
from youtubesearchpython import VideosSearch

logger = logging.getLogger(__name__)

class PlaylistCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='playlist_create', help='Create a new playlist')
    @handle_errors
    @log_command
    async def playlist_create(self, ctx, name: str, *, description: str = ""):
        """Create a new playlist"""
        user_id = str(ctx.author.id)
        
        try:
            playlist_id = await db.create_playlist(user_id, name, description)
            embed = create_success_embed(
                f"**{name}** has been created successfully!\n\n**Description:** {description or 'No description'}"
            )
            embed.add_field(name="Playlist ID", value=str(playlist_id), inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                embed = create_error_embed("You already have a playlist with that name.")
            else:
                embed = create_error_embed(f"Error creating playlist: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_add', help='Add a song to a playlist')
    @handle_errors
    @log_command
    async def playlist_add(self, ctx, playlist_id: int, *, query: str):
        """Add a song to a playlist"""
        user_id = str(ctx.author.id)
        
        # Check if user owns the playlist
        playlist = await db.get_playlist(playlist_id)
        if not playlist:
            embed = create_error_embed("Playlist not found.")
            await ctx.send(embed=embed)
            return
        
        if playlist['user_id'] != user_id:
            embed = create_error_embed("You can only add songs to your own playlists.")
            await ctx.send(embed=embed)
            return
        
        async with ctx.typing():
            try:
                # Search for the song
                from utils.helpers import validate_youtube_url
                if validate_youtube_url(query):
                    url = query
                else:
                    search_results = VideosSearch(query, limit=1).result()
                    if not search_results or not search_results.get('result'):
                        embed = create_error_embed("No results found for your search.")
                        await ctx.send(embed=embed)
                        return
                    url = search_results['result'][0]['link']
                
                # Get song info
                track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                
                # Extract YouTube ID from URL
                from utils.cache_manager import cache_manager
                youtube_id = cache_manager.extract_youtube_id(track.url)
                
                # Add to playlist
                success = await db.add_song_to_playlist(
                    playlist_id, 
                    track.title, 
                    "YouTube", 
                    track.url, 
                    youtube_id
                )
                
                if success:
                    embed = create_success_embed(
                        f"**{track.title}** has been added to **{playlist['name']}**"
                    )
                    embed.add_field(name="Playlist", value=playlist['name'], inline=True)
                    embed.add_field(name="Song Count", value=playlist['song_count'] + 1, inline=True)
                    await ctx.send(embed=embed)
                else:
                    embed = create_error_embed("Failed to add song to playlist.")
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"Error adding song to playlist: {e}")
                embed = create_error_embed(f"Error adding song to playlist: {str(e)}")
                await ctx.send(embed=embed)
    
    @commands.command(name='playlist_remove', help='Remove a song from a playlist')
    @handle_errors
    @log_command
    async def playlist_remove(self, ctx, playlist_id: int, song_id: int):
        """Remove a song from a playlist"""
        user_id = str(ctx.author.id)
        
        # Check if user owns the playlist
        playlist = await db.get_playlist(playlist_id)
        if not playlist:
            embed = create_error_embed("Playlist not found.")
            await ctx.send(embed=embed)
            return
        
        if playlist['user_id'] != user_id:
            embed = create_error_embed("You can only remove songs from your own playlists.")
            await ctx.send(embed=embed)
            return
        
        try:
            success = await db.remove_song_from_playlist(playlist_id, song_id)
            if success:
                embed = create_success_embed(
                    f"Song has been removed from **{playlist['name']}**"
                )
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed("Song not found in playlist.")
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error removing song from playlist: {e}")
            embed = create_error_embed(f"Error removing song from playlist: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_play', help='Play a playlist')
    @handle_errors
    @log_command
    async def playlist_play(self, ctx, playlist_id: int):
        """Play a playlist"""
        if not ctx.author.voice:
            embed = create_error_embed("You are not connected to a voice channel.")
            await ctx.send(embed=embed)
            return
        
        # Get playlist info
        playlist = await db.get_playlist(playlist_id)
        if not playlist:
            embed = create_error_embed("Playlist not found.")
            await ctx.send(embed=embed)
            return
        
        # Check if playlist is public or user owns it
        user_id = str(ctx.author.id)
        if not playlist['is_public'] and playlist['user_id'] != user_id:
            embed = create_error_embed("This playlist is private.")
            await ctx.send(embed=embed)
            return
        
        # Get playlist songs
        songs = await db.get_playlist_songs(playlist_id)
        if not songs:
            embed = create_error_embed("This playlist is empty.")
            await ctx.send(embed=embed)
            return
        
        # Join voice channel if not connected
        voice_client = ctx.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await ctx.author.voice.channel.connect()
            voice_client = ctx.guild.voice_client
        
        async with ctx.typing():
            try:
                embed = create_info_embed(
                    "Adding Playlist to Queue",
                    f"Adding **{len(songs)}** songs from **{playlist['name']}** to the queue..."
                )
                await ctx.send(embed=embed)
                
                added_count = 0
                first_track = None
                
                for i, song in enumerate(songs):
                    try:
                        # Use the stored URL if available, otherwise search
                        if song['song_url']:
                            url = song['song_url']
                        else:
                            # Search for the song
                            search_query = f"{song['song_title']} {song['song_artist']}"
                            search_results = VideosSearch(search_query, limit=1).result()
                            if not search_results or not search_results.get('result'):
                                continue
                            url = search_results['result'][0]['link']
                        
                        # Download track
                        track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                        
                        # Store the first track to play immediately if nothing is playing
                        if i == 0:
                            first_track = track
                        
                        # Add to queue (skip first track if we'll play it immediately)
                        if i > 0 or voice_client.is_playing() or music_player.is_playing:
                            music_player.add_track(track)
                        
                        added_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error adding song from playlist: {e}")
                        continue
                
                # Start playing the first track if nothing is currently playing
                if first_track and not voice_client.is_playing() and not music_player.is_playing:
                    # Import the music commands to access _play_track method
                    from commands.music_commands import MusicCommands
                    music_cog = MusicCommands(self.bot)
                    await music_cog._play_track(ctx, first_track)
                
                embed = create_success_embed(
                    f"Added **{added_count}** songs from **{playlist['name']}** to the queue!"
                )
                embed.add_field(name="Playlist", value=playlist['name'], inline=True)
                embed.add_field(name="Songs Added", value=added_count, inline=True)
                embed.add_field(name="Total Songs", value=len(songs), inline=True)
                
                if added_count < len(songs):
                    embed.add_field(
                        name="Note", 
                        value=f"{len(songs) - added_count} songs could not be added due to errors.",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error playing playlist: {e}")
                embed = create_error_embed(f"Error playing playlist: {str(e)}")
                await ctx.send(embed=embed)
    
    @commands.command(name='playlist_list', help='List your playlists')
    @handle_errors
    @log_command
    async def playlist_list(self, ctx):
        """List user's playlists"""
        user_id = str(ctx.author.id)
        
        try:
            playlists = await db.get_user_playlists(user_id)
            
            if not playlists:
                embed = create_info_embed("No Playlists", "You don't have any playlists yet.")
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Your Playlists",
                description=f"Playlists for {ctx.author.display_name}",
                color=0x1DB954
            )
            
            for playlist in playlists:
                status = "🌐 Public" if playlist['is_public'] else "🔒 Private"
                embed.add_field(
                    name=f"🎵 {playlist['name']} (ID: {playlist['id']})",
                    value=f"**Songs:** {playlist['song_count']}\n**Status:** {status}\n**Description:** {playlist['description'] or 'No description'}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            embed = create_error_embed("Error retrieving playlists.")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_show', help='Show a specific playlist')
    @handle_errors
    @log_command
    async def playlist_show(self, ctx, playlist_id: int):
        """Show a specific playlist"""
        try:
            playlist = await db.get_playlist(playlist_id)
            if not playlist:
                embed = create_error_embed("Playlist not found.")
                await ctx.send(embed=embed)
                return
            
            # Check if user can view the playlist
            user_id = str(ctx.author.id)
            if not playlist['is_public'] and playlist['user_id'] != user_id:
                embed = create_error_embed("This playlist is private.")
                await ctx.send(embed=embed)
                return
            
            songs = await db.get_playlist_songs(playlist_id)
            
            embed = discord.Embed(
                title=f"📋 {playlist['name']}",
                description=playlist['description'] or "No description",
                color=0x1DB954
            )
            
            embed.add_field(name="Owner", value=f"<@{playlist['user_id']}>", inline=True)
            embed.add_field(name="Status", value="🌐 Public" if playlist['is_public'] else "🔒 Private", inline=True)
            embed.add_field(name="Songs", value=str(len(songs)), inline=True)
            
            if songs:
                songs_text = ""
                for i, song in enumerate(songs[:10], 1):
                    songs_text += f"**{i}.** {song['song_title']} - {song['song_artist']}\n"
                
                if len(songs) > 10:
                    songs_text += f"\n... and {len(songs) - 10} more songs"
                
                embed.add_field(name="Songs", value=songs_text, inline=False)
            else:
                embed.add_field(name="Songs", value="This playlist is empty.", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing playlist: {e}")
            embed = create_error_embed("Error retrieving playlist.")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_public', help='List public playlists')
    @handle_errors
    @log_command
    async def playlist_public(self, ctx):
        """List public playlists"""
        try:
            playlists = await db.get_public_playlists(limit=10)
            
            if not playlists:
                embed = create_info_embed("No Public Playlists", "No public playlists available.")
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🌐 Public Playlists",
                description="Public playlists you can listen to",
                color=0x1DB954
            )
            
            for playlist in playlists:
                embed.add_field(
                    name=f"🎵 {playlist['name']} (ID: {playlist['id']})",
                    value=f"**Owner:** <@{playlist['user_id']}>\n**Songs:** {playlist['song_count']}\n**Description:** {playlist['description'] or 'No description'}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing public playlists: {e}")
            embed = create_error_embed("Error retrieving public playlists.")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_delete', help='Delete a playlist')
    @handle_errors
    @log_command
    async def playlist_delete(self, ctx, playlist_id: int):
        """Delete a playlist"""
        user_id = str(ctx.author.id)
        
        try:
            success = await db.delete_playlist(playlist_id, user_id)
            if success:
                embed = create_success_embed("Your playlist has been deleted successfully.")
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed("You can only delete your own playlists, or the playlist doesn't exist.")
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            embed = create_error_embed(f"Error deleting playlist: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_edit', help='Edit playlist details')
    @handle_errors
    @log_command
    async def playlist_edit(self, ctx, playlist_id: int, name: str = None, *, description: str = None):
        """Edit playlist details"""
        user_id = str(ctx.author.id)
        
        try:
            success = await db.update_playlist(playlist_id, user_id, name, description)
            if success:
                embed = create_success_embed("Your playlist has been updated successfully.")
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed("You can only edit your own playlists, or the playlist doesn't exist.")
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            embed = create_error_embed(f"Error updating playlist: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_visibility', help='Toggle playlist visibility (public/private)')
    @handle_errors
    @log_command
    async def playlist_visibility(self, ctx, playlist_id: int):
        """Toggle playlist visibility"""
        user_id = str(ctx.author.id)
        
        try:
            playlist = await db.get_playlist(playlist_id)
            if not playlist:
                embed = create_error_embed("Playlist not found.")
                await ctx.send(embed=embed)
                return
            
            if playlist['user_id'] != user_id:
                embed = create_error_embed("You can only change visibility of your own playlists.")
                await ctx.send(embed=embed)
                return
            
            new_visibility = not playlist['is_public']
            success = await db.update_playlist(playlist_id, user_id, is_public=new_visibility)
            
            if success:
                status = "public" if new_visibility else "private"
                embed = create_success_embed(
                    f"**{playlist['name']}** is now **{status}**"
                )
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed("Failed to update playlist visibility.")
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error updating playlist visibility: {e}")
            embed = create_error_embed(f"Error updating playlist visibility: {str(e)}")
            await ctx.send(embed=embed)
    
    @commands.command(name='playlist_help', help='Show playlist system help')
    @handle_errors
    @log_command
    async def playlist_help(self, ctx):
        """Show help for the playlist system"""
        embed = discord.Embed(
            title="📋 Playlist System Help",
            description="Create and manage your own custom playlists!",
            color=0x1DB954
        )
        
        embed.add_field(
            name="🎵 Creating Playlists",
            value="`?playlist_create <name> [description]` - Create a new playlist",
            inline=False
        )
        
        embed.add_field(
            name="➕ Adding Songs",
            value="`?playlist_add <playlist_id> <song_name_or_url>` - Add a song to your playlist",
            inline=False
        )
        
        embed.add_field(
            name="🎵 Playing Playlists",
            value="`?playlist_play <playlist_id>` - Play a playlist (public or your own)",
            inline=False
        )
        
        embed.add_field(
            name="📋 Managing Playlists",
            value="""`?playlist_list` - List your playlists
`?playlist_show <playlist_id>` - Show playlist details
`?playlist_public` - Browse public playlists
`?playlist_edit <playlist_id> [name] [description]` - Edit playlist details
`?playlist_visibility <playlist_id>` - Toggle public/private
`?playlist_remove <playlist_id> <song_id>` - Remove a song
`?playlist_delete <playlist_id>` - Delete a playlist""",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="""• Playlists can be public or private
• You can only edit your own playlists
• Use `?playlist_show` to see song IDs for removal
• Public playlists can be played by anyone
• Songs are added to the current music queue""",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PlaylistCommands(bot)) 