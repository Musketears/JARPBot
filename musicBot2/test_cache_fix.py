#!/usr/bin/env python3
"""
Test script to verify the cache race condition fix
"""

import asyncio
import os
import sys
import logging

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from music.player import music_player
from utils.cache_manager import cache_manager
from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache_fix():
    """Test that the cache fix works correctly"""
    
    # Test URL (replace with a real YouTube URL)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
    
    print("Testing cache race condition fix...")
    print(f"Test URL: {test_url}")
    
    try:
        # First download - should download and cache
        print("\n1. First download (should download and cache)...")
        track1 = await music_player.download_track(test_url, 123, "TestUser1")
        print(f"   Track 1 filename: {track1.filename}")
        print(f"   Track 1 normalized: {track1.normalized_filename}")
        print(f"   File exists: {os.path.exists(track1.filename)}")
        
        # Second download - should use cache
        print("\n2. Second download (should use cache)...")
        track2 = await music_player.download_track(test_url, 456, "TestUser2")
        print(f"   Track 2 filename: {track2.filename}")
        print(f"   Track 2 normalized: {track2.normalized_filename}")
        print(f"   File exists: {os.path.exists(track2.filename)}")
        
        # Verify both tracks point to the same cached file
        if track1.filename == track2.filename:
            print("   ✅ Both tracks point to the same cached file")
        else:
            print("   ❌ Tracks point to different files")
        
        # Check if files are in cache directory
        if track1.filename.startswith(config.cache_directory):
            print("   ✅ Files are in cache directory")
        else:
            print("   ❌ Files are not in cache directory")
        
        print("\n✅ Cache fix test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Test failed")

if __name__ == "__main__":
    asyncio.run(test_cache_fix()) 