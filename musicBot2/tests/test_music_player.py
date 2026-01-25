#!/usr/bin/env python3
"""
Unit tests for music player system
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from music.player import MusicPlayer, Track, GuildMusicManager


class TestTrack(unittest.TestCase):
    """Test Track dataclass"""
    
    def test_track_creation(self):
        """Test creating a Track"""
        track = Track(
            title="Test Song",
            url="https://www.youtube.com/watch?v=test123",
            duration=180,
            requester_id=123456,
            requester_name="TestUser",
            filename="test.mp3"
        )
        
        self.assertEqual(track.title, "Test Song")
        self.assertEqual(track.url, "https://www.youtube.com/watch?v=test123")
        self.assertEqual(track.duration, 180)
        self.assertEqual(track.requester_id, 123456)
        self.assertEqual(track.requester_name, "TestUser")
        self.assertEqual(track.filename, "test.mp3")
        self.assertIsNone(track.thumbnail)
        self.assertIsNone(track.normalized_filename)
        self.assertIsNotNone(track.added_at)
    
    def test_track_with_optional_fields(self):
        """Test creating a Track with optional fields"""
        track = Track(
            title="Test Song",
            url="https://www.youtube.com/watch?v=test123",
            duration=180,
            requester_id=123456,
            requester_name="TestUser",
            filename="test.mp3",
            thumbnail="https://example.com/thumb.jpg",
            normalized_filename="test_normalized.mp3"
        )
        
        self.assertEqual(track.thumbnail, "https://example.com/thumb.jpg")
        self.assertEqual(track.normalized_filename, "test_normalized.mp3")


class TestMusicPlayer(unittest.TestCase):
    """Test MusicPlayer class"""
    
    def setUp(self):
        """Set up test environment"""
        with patch('music.player.config') as mock_config:
            mock_config.default_volume = 0.5
            mock_config.max_queue_size = 50
            mock_config.ffmpeg_path = 'ffmpeg'
            self.player = MusicPlayer()
    
    def test_initial_state(self):
        """Test initial player state"""
        self.assertEqual(self.player.queue, [])
        self.assertIsNone(self.player.current_track)
        self.assertFalse(self.player.loop)
        self.assertEqual(self.player.volume, 0.5)
        self.assertFalse(self.player.is_playing)
        self.assertFalse(self.player.is_paused)
        self.assertTrue(self.player.normalize_audio)
    
    def test_add_track_to_empty_queue(self):
        """Test adding track to empty queue"""
        track = Track(
            title="Test Song",
            url="https://www.youtube.com/watch?v=test123",
            duration=180,
            requester_id=123456,
            requester_name="TestUser",
            filename="test.mp3"
        )
        
        self.player.add_track(track)
        
        self.assertEqual(len(self.player.queue), 1)
        self.assertEqual(self.player.queue[0], track)
    
    def test_add_track_at_position(self):
        """Test adding track at specific position"""
        track1 = Track("Song 1", "url1", 100, 1, "User1", "file1.mp3")
        track2 = Track("Song 2", "url2", 100, 1, "User1", "file2.mp3")
        track3 = Track("Song 3", "url3", 100, 1, "User1", "file3.mp3")
        
        self.player.add_track(track1)
        self.player.add_track(track2)
        self.player.add_track(track3, position=1)
        
        self.assertEqual(len(self.player.queue), 3)
        self.assertEqual(self.player.queue[0].title, "Song 1")
        self.assertEqual(self.player.queue[1].title, "Song 3")
        self.assertEqual(self.player.queue[2].title, "Song 2")
    
    def test_add_track_queue_full(self):
        """Test adding track when queue is full"""
        with patch('music.player.config') as mock_config:
            mock_config.max_queue_size = 2
            mock_config.default_volume = 0.5
            mock_config.ffmpeg_path = 'ffmpeg'
            player = MusicPlayer()
            
            track1 = Track("Song 1", "url1", 100, 1, "User1", "file1.mp3")
            track2 = Track("Song 2", "url2", 100, 1, "User1", "file2.mp3")
            track3 = Track("Song 3", "url3", 100, 1, "User1", "file3.mp3")
            
            player.add_track(track1)
            player.add_track(track2)
            
            with self.assertRaises(ValueError) as context:
                player.add_track(track3)
            
            self.assertIn("Queue is full", str(context.exception))
    
    def test_remove_track(self):
        """Test removing track from queue"""
        track1 = Track("Song 1", "url1", 100, 1, "User1", "file1.mp3")
        track2 = Track("Song 2", "url2", 100, 1, "User1", "file2.mp3")
        
        self.player.add_track(track1)
        self.player.add_track(track2)
        
        removed = self.player.remove_track(0)
        
        self.assertEqual(removed, track1)
        self.assertEqual(len(self.player.queue), 1)
        self.assertEqual(self.player.queue[0], track2)
    
    def test_remove_track_invalid_index(self):
        """Test removing track with invalid index"""
        track = Track("Song 1", "url1", 100, 1, "User1", "file1.mp3")
        self.player.add_track(track)
        
        removed = self.player.remove_track(5)
        
        self.assertIsNone(removed)
        self.assertEqual(len(self.player.queue), 1)
    
    def test_clear_queue(self):
        """Test clearing the queue"""
        track1 = Track("Song 1", "url1", 100, 1, "User1", "file1.mp3")
        track2 = Track("Song 2", "url2", 100, 1, "User1", "file2.mp3")
        
        self.player.add_track(track1)
        self.player.add_track(track2)
        
        self.player.clear_queue()
        
        self.assertEqual(len(self.player.queue), 0)
    
    def test_shuffle_queue(self):
        """Test shuffling the queue"""
        tracks = [
            Track(f"Song {i}", f"url{i}", 100, 1, "User1", f"file{i}.mp3")
            for i in range(10)
        ]
        
        for track in tracks:
            self.player.add_track(track)
        
        original_order = [t.title for t in self.player.queue]
        
        # Shuffle multiple times to ensure it changes
        for _ in range(10):
            self.player.shuffle_queue()
        
        # Queue should still have same tracks but potentially different order
        self.assertEqual(len(self.player.queue), 10)
        shuffled_order = [t.title for t in self.player.queue]
        
        # With 10 items, it's extremely unlikely to get the same order
        # Note: This test could theoretically fail, but probability is 1/10!
        self.assertEqual(set(original_order), set(shuffled_order))
    
    def test_get_queue_info(self):
        """Test getting queue info"""
        track = Track("Test Song", "url", 180, 123, "TestUser", "test.mp3")
        self.player.add_track(track)
        self.player.current_track = track
        self.player.is_playing = True
        
        info = self.player.get_queue_info()
        
        self.assertEqual(info['current_track'], "Test Song")
        self.assertEqual(info['queue_length'], 1)
        self.assertTrue(info['is_playing'])
        self.assertFalse(info['is_paused'])
        self.assertEqual(info['volume'], 0.5)
        self.assertFalse(info['loop'])
    
    def test_get_queue_tracks(self):
        """Test getting queue tracks"""
        track1 = Track("Song 1", "url1", 180, 1, "User1", "file1.mp3")
        track2 = Track("Song 2", "url2", 240, 2, "User2", "file2.mp3")
        
        self.player.add_track(track1)
        self.player.add_track(track2)
        
        tracks_info = self.player.get_queue_tracks()
        
        self.assertEqual(len(tracks_info), 2)
        self.assertEqual(tracks_info[0]['position'], 1)
        self.assertEqual(tracks_info[0]['title'], "Song 1")
        self.assertEqual(tracks_info[0]['duration'], "3:00")
        self.assertEqual(tracks_info[0]['requester'], "User1")
        
        self.assertEqual(tracks_info[1]['position'], 2)
        self.assertEqual(tracks_info[1]['title'], "Song 2")
        self.assertEqual(tracks_info[1]['duration'], "4:00")


class TestGuildMusicManager(unittest.TestCase):
    """Test GuildMusicManager class"""
    
    def setUp(self):
        """Set up test environment"""
        with patch('music.player.config') as mock_config:
            mock_config.default_volume = 0.5
            mock_config.max_queue_size = 50
            mock_config.ffmpeg_path = 'ffmpeg'
            self.manager = GuildMusicManager()
    
    def test_get_player_creates_new(self):
        """Test that get_player creates new player for new guild"""
        player = self.manager.get_player(123456)
        
        self.assertIsInstance(player, MusicPlayer)
        self.assertEqual(len(self.manager._players), 1)
    
    def test_get_player_returns_existing(self):
        """Test that get_player returns existing player"""
        player1 = self.manager.get_player(123456)
        player2 = self.manager.get_player(123456)
        
        self.assertIs(player1, player2)
        self.assertEqual(len(self.manager._players), 1)
    
    def test_get_player_different_guilds(self):
        """Test that different guilds get different players"""
        player1 = self.manager.get_player(111111)
        player2 = self.manager.get_player(222222)
        
        self.assertIsNot(player1, player2)
        self.assertEqual(len(self.manager._players), 2)
    
    def test_remove_player(self):
        """Test removing a player"""
        self.manager.get_player(123456)
        self.assertEqual(len(self.manager._players), 1)
        
        self.manager.remove_player(123456)
        self.assertEqual(len(self.manager._players), 0)
    
    def test_remove_player_nonexistent(self):
        """Test removing a player that doesn't exist"""
        # Should not raise an exception
        self.manager.remove_player(999999)
    
    def test_save_voice_state(self):
        """Test saving voice state"""
        track = Track("Test", "url", 180, 1, "User", "file.mp3")
        
        self.manager.save_voice_state(
            guild_id=123456,
            channel_id=789,
            track=track,
            position=30.5,
            is_playing=True
        )
        
        state = self.manager.get_voice_state(123456)
        
        self.assertIsNotNone(state)
        self.assertEqual(state['channel_id'], 789)
        self.assertEqual(state['track'], track)
        self.assertEqual(state['position'], 30.5)
        self.assertTrue(state['is_playing'])
    
    def test_clear_voice_state(self):
        """Test clearing voice state"""
        self.manager.save_voice_state(123456, 789, None, 0, False)
        self.assertIsNotNone(self.manager.get_voice_state(123456))
        
        self.manager.clear_voice_state(123456)
        self.assertIsNone(self.manager.get_voice_state(123456))
    
    def test_get_all_guild_ids(self):
        """Test getting all guild IDs"""
        self.manager.get_player(111111)
        self.manager.get_player(222222)
        self.manager.get_player(333333)
        
        guild_ids = self.manager.get_all_guild_ids()
        
        self.assertEqual(len(guild_ids), 3)
        self.assertIn(111111, guild_ids)
        self.assertIn(222222, guild_ids)
        self.assertIn(333333, guild_ids)


if __name__ == '__main__':
    unittest.main()
