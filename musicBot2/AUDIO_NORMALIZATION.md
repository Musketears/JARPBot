# Audio Normalization Feature

## Overview

The music bot now includes automatic audio normalization to ensure all songs have consistent volume levels. This feature uses FFmpeg's `loudnorm` filter to normalize audio to a standard loudness level, providing a better listening experience.

## How It Works

### Target Settings
- **Target Loudness**: -16 LUFS (Loudness Units relative to Full Scale)
- **True Peak**: -1 dB
- **Loudness Range**: 11 LU
- **Sample Rate**: 48kHz (optimized for Discord)
- **Bitrate**: 192kbps

### Why -16 LUFS?
-16 LUFS is the standard loudness level used by streaming platforms like Spotify, Apple Music, and YouTube
- Provides optimal listening experience for headphones
- Prevents sudden volume changes between songs
- Maintains audio quality while ensuring consistency

## Commands

### `?normalize`
Toggle audio normalization on/off.

**Usage:**
```
?normalize
```

**Response:**
- "Audio normalization enabled" or "Audio normalization disabled"

### `?normalize_info`
Show current audio normalization settings and information.

**Usage:**
```
?normalize_info
```

**Response:**
- Status (enabled/disabled)
- Target loudness (-16 LUFS)
- True peak (-1 dB)
- Description of the feature

## Technical Details

### FFmpeg Command
The normalization uses this FFmpeg filter:
```bash
loudnorm=I=-16:TP=-1:LRA=11:measured_I=-23:measured_LRA=7:measured_TP=-1:measured_thresh=-70:offset=0:linear=true
```

### File Management
- Original audio files are preserved
- Normalized files are created with `_normalized` suffix
- Both files are automatically cleaned up after playback
- If normalization fails, the original file is used

### Performance
- Normalization adds ~5-10 seconds to download time per song
- Uses async processing to avoid blocking
- 5-minute timeout per normalization operation
- Falls back to original file if normalization fails

## Benefits

1. **Consistent Volume**: All songs play at the same perceived loudness
2. **Better Experience**: No need to adjust volume between songs
3. **Professional Quality**: Matches industry standards
4. **Headphone Optimized**: Perfect for personal listening

## Troubleshooting

### FFmpeg Not Found
If you get errors about FFmpeg not being found:
1. Install FFmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Ubuntu)
2. Ensure FFmpeg is in your system PATH
3. Restart the bot

### Normalization Fails
If normalization fails for a specific song:
1. The bot will use the original file
2. Check the logs for specific error messages
3. The song will still play normally

### Performance Issues
If normalization is too slow:
1. Use `?normalize` to disable the feature
2. Consider upgrading your system's processing power
3. Check if other processes are using CPU resources

## Configuration

The normalization settings can be modified in `music/player.py`:

```python
# Audio normalization settings
AUDIO_NORMALIZATION_TARGET = -16.0  # LUFS target
AUDIO_NORMALIZATION_TRUE_PEAK = -1.0  # True peak target
AUDIO_NORMALIZATION_OFFSET = 0.0  # Offset to apply
```

## Default Behavior

- Audio normalization is **enabled by default**
- Can be toggled on/off with `?normalize`
- Status is shown in queue info (`?queue`)
- Normalized files are indicated in "Now Playing" messages 