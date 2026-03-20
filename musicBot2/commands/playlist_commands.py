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
    
    @commands.command(name='playlist_add', help='Add one or more songs to a playlist (comma-separated)')
    @handle_errors
    @log_command
    async def playlist_add(self, ctx, playlist_id: int, *, query: str):
        """Add one or more songs to a playlist (comma-separated queries or URLs)"""
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

        queries = [q.strip() for q in query.split(',') if q.strip()]

        async with ctx.typing():
            from utils.helpers import validate_youtube_url

            added = []
            failed = []

            for q in queries:
                try:
                    if validate_youtube_url(q):
                        url = q
                    else:
                        search_results = VideosSearch(q, limit=1).result()
                        if not search_results or not search_results.get('result'):
                            failed.append(q)
                            continue
                        url = search_results['result'][0]['link']

                    # Fetch metadata only — no audio download needed
                    info = await music_player.extract_info_only(url)

                    success = await db.add_song_to_playlist(
                        playlist_id,
                        info['title'],
                        "YouTube",
                        info['url'],
                        info['youtube_id']
                    )

                    if success:
                        added.append(info['title'])
                    else:
                        failed.append(q)

                except Exception as e:
                    logger.error(f"Error adding song to playlist: {e}")
                    failed.append(q)

            if added:
                desc = '\n'.join(f"• {t}" for t in added)
                embed = create_success_embed(
                    f"Added **{len(added)}** song(s) to **{playlist['name']}**"
                )
                embed.add_field(name="Added", value=desc, inline=False)
                if failed:
                    embed.add_field(name="Failed", value='\n'.join(f"• {q}" for q in failed), inline=False)
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed("Failed to add any songs to the playlist.")
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
            try:
                await ctx.author.voice.channel.connect()
            except asyncio.TimeoutError:
                embed = create_error_embed("Timed out connecting to the voice channel. Discord's voice servers may be slow — please try again.")
                await ctx.send(embed=embed)
                return
            voice_client = ctx.guild.voice_client

        async with ctx.typing():
            try:
                currently_playing = voice_client.is_playing() or music_player.is_playing

                embed = create_info_embed(
                    "Adding Playlist to Queue",
                    f"Loading **{playlist['name']}** ({len(songs)} songs) — first few will download now, rest queue in background..."
                )
                await ctx.send(embed=embed)

                # Resolve all URLs first (search only for songs without a stored URL)
                resolved_urls = []
                for song in songs:
                    if song['song_url']:
                        resolved_urls.append(song['song_url'])
                    else:
                        search_query = f"{song['song_title']} {song['song_artist']}"
                        search_results = VideosSearch(search_query, limit=1).result()
                        if search_results and search_results.get('result'):
                            resolved_urls.append(search_results['result'][0]['link'])
                        # Skip songs we can't resolve

                if not resolved_urls:
                    embed = create_error_embed("Could not resolve any songs in this playlist.")
                    await ctx.send(embed=embed)
                    return

                # Determine how many to download eagerly
                # We need: 1 for immediate play (if nothing playing) + up to DOWNLOAD_AHEAD in buffer
                buffer_slots = music_player._DOWNLOAD_AHEAD - len(music_player.queue)
                if not currently_playing:
                    buffer_slots += 1  # One extra for the track we'll play immediately
                eager_count = max(0, min(buffer_slots, len(resolved_urls)))

                first_track = None
                added_count = 0

                # Download the eager batch
                for i, url in enumerate(resolved_urls[:eager_count]):
                    try:
                        track = await music_player.download_track(url, ctx.author.id, ctx.author.name)
                        if i == 0 and not currently_playing:
                            first_track = track  # Play this one immediately
                        else:
                            music_player.add_track(track)
                        added_count += 1
                    except Exception as e:
                        logger.error(f"Error downloading playlist track {i}: {e}")

                # Add remaining URLs to pending queue for lazy download
                for url in resolved_urls[eager_count:]:
                    music_player.add_pending(url, ctx.author.id, ctx.author.name)
                    added_count += 1

                # Kick off background buffer fill for pending songs
                music_player.trigger_buffer_fill()

                # Start playback or add first track to queue
                music_cog = self.bot.get_cog('MusicCommands')
                if first_track and not currently_playing and music_cog:
                    await music_cog._play_track(ctx, first_track)
                elif first_track:
                    music_player.add_track(first_track)

                embed = create_success_embed(
                    f"Queued **{playlist['name']}** — {eager_count} song(s) ready, "
                    f"{len(resolved_urls[eager_count:])} downloading in background"
                )
                embed.add_field(name="Playlist", value=playlist['name'], inline=True)
                embed.add_field(name="Total Songs", value=len(resolved_urls), inline=True)

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
            value="`?playlist_add <playlist_id> <song_name_or_url>` - Add a song to your playlist (separate multiple with commas)",
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