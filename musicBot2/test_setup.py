#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the bot setup and configuration
"""

import os
import sys
import logging
import subprocess

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import config
        print("OK Config imported successfully")
    except Exception as e:
        print(f"ERROR Config import failed: {e}")
        return False
    
    try:
        from utils.database import db
        print("OK Database imported successfully")
    except Exception as e:
        print(f"ERROR Database import failed: {e}")
        return False
    
    try:
        from music.player import music_player
        print("OK Music player imported successfully")
    except Exception as e:
        print(f"ERROR Music player import failed: {e}")
        return False
    
    try:
        from games.gambling import gambling_manager
        print("OK Gambling manager imported successfully")
    except Exception as e:
        print(f"ERROR Gambling manager import failed: {e}")
        return False
    
    try:
        from games.gacha import gacha_system
        print("OK Gacha system imported successfully")
    except Exception as e:
        print(f"ERROR Gacha system import failed: {e}")
        return False
    
    return True

def test_ffmpeg():
    """Test if FFmpeg is properly installed and accessible"""
    print("\nTesting FFmpeg...")
    
    try:
        from config import config
        ffmpeg_path = config.ffmpeg_path
        
        # Test if FFmpeg can be executed
        result = subprocess.run([ffmpeg_path, '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode == 0:
            print(f"OK FFmpeg found at: {ffmpeg_path}")
            # Extract version info
            version_line = result.stdout.split('\n')[0]
            print(f"OK FFmpeg version: {version_line}")
            return True
        else:
            print(f"ERROR FFmpeg test failed with return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR FFmpeg test timed out")
        return False
    except FileNotFoundError:
        print(f"ERROR FFmpeg not found at: {ffmpeg_path}")
        print("Please install FFmpeg:")
        print("   - Windows: Download from https://ffmpeg.org/download.html")
        print("   - macOS: brew install ffmpeg")
        print("   - Linux: sudo apt install ffmpeg")
        return False
    except Exception as e:
        print(f"ERROR FFmpeg test failed: {e}")
        return False

def test_config():
    """Test configuration values"""
    print("\nTesting configuration...")
    
    from config import config
    
    required_fields = ['token']
    for field in required_fields:
        if hasattr(config, field) and getattr(config, field):
            print(f"OK {field} is configured")
        else:
            print(f"WARNING {field} is not configured (this is normal if you haven't set up .env)")
    
    print(f"OK Default balance: {config.default_balance}")
    print(f"OK Command prefix: {config.command_prefix}")
    print(f"OK Gacha cost: {config.gacha_cost}")
    print(f"OK FFmpeg path: {config.ffmpeg_path}")

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    
    try:
        from utils.database import db
        print("OK Database manager created successfully")
        print(f"OK Database path: {db.db_path}")
    except Exception as e:
        print(f"ERROR Database test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Testing MusicBot2 setup...\n")
    
    # Test imports
    if not test_imports():
        print("\nERROR Import tests failed!")
        return False
    
    # Test FFmpeg
    if not test_ffmpeg():
        print("\nERROR FFmpeg test failed!")
        return False
    
    # Test config
    test_config()
    
    # Test database
    if not test_database():
        print("\nERROR Database test failed!")
        return False
    
    print("\nOK All tests passed! The bot should be ready to run.")
    print("\nNext steps:")
    print("1. Create a .env file with your Discord token")
    print("2. Run: python main.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 