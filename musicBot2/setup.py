#!/usr/bin/env python3
"""
Setup script for JARP Music Bot v2
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    print("\n🎵 Checking FFmpeg installation...")
    
    # Common FFmpeg paths
    possible_paths = [
        'ffmpeg',
        'ffmpeg.exe',
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                print(f"✅ FFmpeg found at: {path}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    print("❌ FFmpeg not found")
    print("\n📥 Please install FFmpeg:")
    system = platform.system().lower()
    if system == "darwin":  # macOS
        print("   brew install ffmpeg")
    elif system == "linux":
        print("   sudo apt install ffmpeg  # Ubuntu/Debian")
        print("   sudo yum install ffmpeg  # CentOS/RHEL")
    elif system == "windows":
        print("   Download from: https://ffmpeg.org/download.html")
    return False

def create_env_file():
    """Create .env file template"""
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ .env file already exists")
        return True
    
    print("\n🔧 Creating .env file...")
    try:
        with open(env_file, "w") as f:
            f.write("# Discord Bot Configuration\n")
            f.write("# Replace 'your_discord_bot_token_here' with your actual bot token\n")
            f.write("DISCORD_TOKEN=your_discord_bot_token_here\n")
        
        print("✅ .env file created")
        print("⚠️  Please edit .env file and add your Discord bot token")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    directories = ["cache/audio", "cache/normalized", "logs"]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"❌ Failed to create directory {directory}: {e}")
            return False
    
    return True

def run_tests():
    """Run basic tests"""
    print("\n🧪 Running basic tests...")
    try:
        result = subprocess.run([sys.executable, "test_setup.py"], 
                              capture_output=True, 
                              text=True, 
                              timeout=30)
        if result.returncode == 0:
            print("✅ Basic tests passed")
            return True
        else:
            print("⚠️  Some tests failed, but bot may still work")
            print(result.stdout)
            return True
    except Exception as e:
        print(f"⚠️  Could not run tests: {e}")
        return True

def main():
    """Main setup function"""
    print("🎵 JARP Music Bot v2 Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Check FFmpeg
    if not check_ffmpeg():
        print("\n⚠️  FFmpeg is required for audio processing")
        print("   You can continue setup, but audio features won't work")
    
    # Create directories
    if not create_directories():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Run tests
    run_tests()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your Discord bot token")
    print("2. Create a Discord application at https://discord.com/developers/applications")
    print("3. Add your bot to your server")
    print("4. Run the bot: python main.py")
    print("\n📚 For more information, see README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 