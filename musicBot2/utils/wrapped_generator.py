"""
Wrapped Image Generator - Creates Spotify Wrapped-style images
"""
import io
import random
import hashlib
import math
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

# Default timezone (EST)
DEFAULT_TIMEZONE = "America/New_York"

# Vibrant color palettes - each user gets a unique combination based on their ID
COLOR_PALETTES = [
    # Sunset Vibes
    {"primary": (255, 95, 109), "secondary": (255, 195, 113), "accent": (255, 154, 158), "dark": (45, 20, 44), "glow": (255, 120, 130)},
    # Ocean Dream
    {"primary": (67, 206, 162), "secondary": (24, 90, 157), "accent": (116, 235, 213), "dark": (15, 32, 39), "glow": (80, 220, 180)},
    # Purple Haze
    {"primary": (131, 58, 180), "secondary": (253, 29, 29), "accent": (252, 176, 69), "dark": (25, 15, 35), "glow": (160, 80, 200)},
    # Electric Blue
    {"primary": (0, 198, 255), "secondary": (0, 114, 255), "accent": (139, 233, 253), "dark": (10, 25, 47), "glow": (50, 180, 255)},
    # Neon Pink
    {"primary": (255, 0, 128), "secondary": (255, 128, 171), "accent": (255, 77, 148), "dark": (40, 10, 25), "glow": (255, 50, 150)},
    # Tropical Paradise
    {"primary": (255, 183, 77), "secondary": (255, 87, 87), "accent": (255, 214, 138), "dark": (35, 25, 20), "glow": (255, 200, 100)},
    # Aurora Borealis
    {"primary": (0, 255, 157), "secondary": (0, 162, 255), "accent": (127, 255, 212), "dark": (10, 30, 35), "glow": (50, 255, 180)},
    # Fire Storm
    {"primary": (255, 69, 0), "secondary": (255, 165, 0), "accent": (255, 215, 0), "dark": (35, 15, 10), "glow": (255, 100, 30)},
    # Cyberpunk
    {"primary": (255, 0, 255), "secondary": (0, 255, 255), "accent": (255, 105, 180), "dark": (20, 10, 30), "glow": (255, 50, 255)},
    # Forest Glow
    {"primary": (34, 197, 94), "secondary": (74, 222, 128), "accent": (187, 247, 208), "dark": (15, 35, 20), "glow": (60, 220, 120)},
    # Cosmic Purple
    {"primary": (167, 139, 250), "secondary": (139, 92, 246), "accent": (196, 181, 253), "dark": (30, 20, 45), "glow": (180, 150, 255)},
    # Cherry Blossom
    {"primary": (255, 182, 193), "secondary": (255, 105, 180), "accent": (255, 218, 233), "dark": (45, 20, 30), "glow": (255, 200, 210)},
    # Midnight Jazz
    {"primary": (59, 130, 246), "secondary": (37, 99, 235), "accent": (147, 197, 253), "dark": (15, 23, 42), "glow": (80, 150, 255)},
    # Lava Flow
    {"primary": (239, 68, 68), "secondary": (234, 179, 8), "accent": (251, 146, 60), "dark": (40, 15, 15), "glow": (255, 100, 80)},
    # Arctic Frost
    {"primary": (56, 189, 248), "secondary": (125, 211, 252), "accent": (186, 230, 253), "dark": (15, 30, 40), "glow": (80, 200, 255)},
]

# Fun titles for different listening amounts
LISTENING_TITLES = [
    (0, "Silent Soul"),
    (10, "Casual Listener"),
    (50, "Music Enthusiast"),
    (100, "Dedicated Fan"),
    (200, "Music Connoisseur"),
    (500, "Audiophile Elite"),
    (1000, "Music Royalty"),
    (2000, "Legendary Listener"),
]

def convert_utc_hour_to_timezone(utc_hour: int, timezone_str: str = DEFAULT_TIMEZONE) -> int:
    """Convert a UTC hour (0-23) to local timezone hour"""
    if not HAS_PYTZ:
        # Fallback: EST is UTC-5 (or UTC-4 during DST, but we'll use -5 as default)
        return (utc_hour - 5) % 24
    
    try:
        tz = pytz.timezone(timezone_str)
        # Create a dummy datetime in UTC for today
        utc = pytz.UTC
        now = datetime.now(utc)
        utc_dt = now.replace(hour=utc_hour, minute=0, second=0, microsecond=0)
        # Convert to target timezone
        local_dt = utc_dt.astimezone(tz)
        return local_dt.hour
    except Exception:
        # Fallback to EST offset
        return (utc_hour - 5) % 24

def get_listening_title(play_count: int) -> str:
    """Get a fun title based on play count"""
    title = LISTENING_TITLES[0][1]
    for threshold, label in LISTENING_TITLES:
        if play_count >= threshold:
            title = label
    return title

def get_user_palette(user_id: str) -> Dict[str, Tuple[int, int, int]]:
    """Get a unique color palette based on user ID"""
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    palette_index = hash_val % len(COLOR_PALETTES)
    return COLOR_PALETTES[palette_index]

def create_radial_gradient(width: int, height: int, center: Tuple[int, int], 
                           color1: Tuple[int, int, int], color2: Tuple[int, int, int],
                           radius: float = 1.0) -> Image.Image:
    """Create a radial gradient from center"""
    base = Image.new('RGB', (width, height), color2)
    pixels = base.load()
    
    max_dist = math.sqrt(center[0]**2 + center[1]**2) * radius
    
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - center[0])**2 + (y - center[1])**2)
            ratio = min(1.0, dist / max_dist)
            
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            pixels[x, y] = (r, g, b)
    
    return base

def create_mesh_gradient(width: int, height: int, palette: Dict[str, Tuple[int, int, int]]) -> Image.Image:
    """Create a modern mesh-style gradient background"""
    base = Image.new('RGBA', (width, height), (*palette["dark"], 255))
    
    # Create multiple overlapping radial gradients for mesh effect
    overlay1 = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw1 = ImageDraw.Draw(overlay1)
    
    # Top-left glow
    for r in range(400, 0, -10):
        alpha = int(30 * (1 - r / 400))
        color = (*palette["primary"], alpha)
        draw1.ellipse([-100, -100, r * 2 - 100, r * 2 - 100], fill=color)
    
    # Bottom-right glow
    for r in range(500, 0, -10):
        alpha = int(25 * (1 - r / 500))
        color = (*palette["secondary"], alpha)
        draw1.ellipse([width - r * 2 + 150, height - r * 2 + 200, 
                       width + 150, height + 200], fill=color)
    
    # Center subtle glow
    for r in range(300, 0, -10):
        alpha = int(15 * (1 - r / 300))
        color = (*palette["accent"], alpha)
        draw1.ellipse([width//2 - r, height//2 - r, 
                       width//2 + r, height//2 + r], fill=color)
    
    base = Image.alpha_composite(base, overlay1)
    return base.convert('RGB')

def draw_glass_card(draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int], 
                    palette: Dict[str, Tuple[int, int, int]], 
                    filled: bool = False, glow: bool = False) -> None:
    """Draw a frosted glass-style card"""
    x1, y1, x2, y2 = bbox
    
    # Main card with subtle fill
    fill_color = (255, 255, 255, 12) if not filled else (*palette["dark"], 180)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=fill_color)
    
    # Subtle border
    draw.rounded_rectangle([x1, y1, x2, y2], radius=20, outline=(255, 255, 255, 30), width=1)

def draw_glow_text(image: Image.Image, pos: Tuple[int, int], text: str, 
                   font: ImageFont.FreeTypeFont, color: Tuple[int, int, int],
                   glow_color: Tuple[int, int, int] = None, glow_radius: int = 10) -> None:
    """Draw text with a subtle glow effect"""
    if glow_color is None:
        glow_color = color
    
    # Create glow layer
    glow_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    # Draw glow (multiple passes with decreasing opacity)
    for offset in range(glow_radius, 0, -2):
        alpha = int(60 * (1 - offset / glow_radius))
        glow_draw.text((pos[0] - offset//2, pos[1] - offset//2), text, 
                       fill=(*glow_color, alpha), font=font)
        glow_draw.text((pos[0] + offset//2, pos[1] - offset//2), text, 
                       fill=(*glow_color, alpha), font=font)
        glow_draw.text((pos[0] - offset//2, pos[1] + offset//2), text, 
                       fill=(*glow_color, alpha), font=font)
        glow_draw.text((pos[0] + offset//2, pos[1] + offset//2), text, 
                       fill=(*glow_color, alpha), font=font)
    
    # Blur the glow slightly
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    
    # Composite glow onto image
    image.paste(Image.alpha_composite(Image.new('RGBA', image.size, (0, 0, 0, 0)), glow_layer), (0, 0), glow_layer)
    
    # Draw main text with RGBA mode
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.text(pos, text, fill=color, font=font)

def add_corner_decorations(draw: ImageDraw.Draw, width: int, height: int, 
                           palette: Dict[str, Tuple[int, int, int]], user_id: str):
    """Add subtle decorative elements in corners that don't interfere with content"""
    random.seed(int(hashlib.md5(user_id.encode()).hexdigest(), 16))
    
    # Top-left corner decoration
    for i in range(3):
        x = -20 + i * 30
        y = -20 + i * 30
        size = 60 - i * 15
        draw.rounded_rectangle([x, y, x + size, y + size], radius=10, 
                               outline=(*palette["primary"], 40 - i * 10), width=2)
    
    # Bottom-right corner decoration
    for i in range(3):
        x = width - 40 - i * 30
        y = height - 40 - i * 30
        size = 60 - i * 15
        draw.rounded_rectangle([x, y, x + size, y + size], radius=10,
                               outline=(*palette["secondary"], 40 - i * 10), width=2)
    
    # Decorative lines
    line_color = (*palette["accent"], 15)
    draw.line([(0, 150), (80, 150)], fill=line_color, width=2)
    draw.line([(width - 80, height - 150), (width, height - 150)], fill=line_color, width=2)

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if custom font not available"""
    font_paths = [
        # Linux fonts (prioritize good-looking fonts)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # Windows fonts
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        # Mac fonts
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    
    return ImageFont.load_default()

def truncate_text(text: str, max_length: int = 40) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def draw_progress_bar(draw: ImageDraw.Draw, x: int, y: int, width: int, height: int,
                      progress: float, bg_color: Tuple[int, int, int],
                      fill_color: Tuple[int, int, int], glow: bool = False) -> None:
    """Draw a stylish progress bar"""
    # Background
    draw.rounded_rectangle([x, y, x + width, y + height], radius=height // 2, fill=bg_color)
    
    # Fill
    if progress > 0:
        fill_width = max(height, int(width * progress))  # Minimum width for rounded corners
        draw.rounded_rectangle([x, y, x + fill_width, y + height], radius=height // 2, fill=fill_color)

def generate_wrapped_image(
    user_name: str,
    user_id: str,
    avatar_url: Optional[str],
    stats: Dict[str, Any],
    timezone: str = DEFAULT_TIMEZONE
) -> io.BytesIO:
    """
    Generate a Spotify Wrapped-style image
    
    stats should contain:
    - total_plays: int
    - unique_songs: int
    - top_songs: List[Dict] with song_title, play_count
    - top_artists: List[Dict] with artist, play_count (optional)
    - first_song: Dict with song_title, played_at (optional)
    - listening_streak: int (optional)
    - favorite_hour: int (optional, 0-23, in UTC)
    
    timezone: IANA timezone string (e.g., "America/New_York")
    """
    # Image dimensions (portrait for mobile-friendly)
    width = 800
    height = 1400  # Taller for better layout
    
    # Get user-specific color palette
    palette = get_user_palette(user_id)
    
    # Create mesh gradient background
    bg = create_mesh_gradient(width, height, palette)
    bg = bg.convert('RGBA')
    
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    # Add subtle corner decorations
    add_corner_decorations(draw, width, height, palette, user_id)
    
    # Fonts
    title_font = get_font(52, bold=True)
    heading_font = get_font(38, bold=True)
    stat_font = get_font(80, bold=True)
    medium_stat_font = get_font(48, bold=True)
    label_font = get_font(22)
    song_font = get_font(24, bold=True)
    small_font = get_font(18)
    tiny_font = get_font(16)
    
    y_pos = 50
    
    # ===== HEADER SECTION =====
    current_year = datetime.now().year
    header_text = f"~ {current_year} WRAPPED ~"
    bbox = draw.textbbox((0, 0), header_text, font=title_font)
    text_width = bbox[2] - bbox[0]
    
    # Draw header with glow effect
    header_x = (width - text_width) // 2
    draw_glow_text(bg, (header_x, y_pos), header_text, title_font, 
                   palette["primary"], palette["glow"], glow_radius=15)
    # Recreate draw object after glow text
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    y_pos += 90
    
    # Username
    user_text = f"{user_name}'s Year in Music"
    bbox = draw.textbbox((0, 0), user_text, font=heading_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos), user_text, fill=(255, 255, 255), font=heading_font)
    
    y_pos += 55
    
    # Listening title badge
    title = get_listening_title(stats.get("total_plays", 0))
    bbox = draw.textbbox((0, 0), title, font=label_font)
    text_width = bbox[2] - bbox[0]
    badge_padding = 20
    badge_width = text_width + badge_padding * 2
    badge_height = 44
    badge_x = (width - badge_width) // 2
    
    # Draw badge with gradient feel
    draw.rounded_rectangle(
        [badge_x, y_pos, badge_x + badge_width, y_pos + badge_height],
        radius=22,
        fill=palette["primary"]
    )
    # Add subtle highlight
    draw.rounded_rectangle(
        [badge_x + 2, y_pos + 2, badge_x + badge_width - 2, y_pos + badge_height // 2],
        radius=20,
        fill=(*palette["accent"], 40)
    )
    draw.text((badge_x + badge_padding, y_pos + 10), title, fill=(255, 255, 255), font=label_font)
    
    y_pos += 80
    
    # ===== MAIN STATS CARD =====
    card_margin = 50
    card_height = 200
    draw_glass_card(draw, (card_margin, y_pos, width - card_margin, y_pos + card_height), palette)
    
    # Total plays - big centered number
    total_plays = stats.get("total_plays", 0)
    plays_text = f"{total_plays:,}"
    bbox = draw.textbbox((0, 0), plays_text, font=stat_font)
    text_width = bbox[2] - bbox[0]
    draw_glow_text(bg, ((width - text_width) // 2, y_pos + 30), plays_text, stat_font,
                   palette["accent"], palette["glow"], glow_radius=12)
    # Recreate draw object after glow text
    draw = ImageDraw.Draw(bg, 'RGBA')
    
    label = "songs played this year"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos + 125), label, fill=(180, 180, 180), font=label_font)
    
    y_pos += card_height + 25
    
    # ===== SECONDARY STATS ROW =====
    unique_songs = stats.get("unique_songs", 0)
    variety = (unique_songs / total_plays * 100) if total_plays > 0 else 0
    
    box_width = (width - card_margin * 2 - 20) // 2
    box_height = 110
    
    # Unique tracks box
    box1_x = card_margin
    draw_glass_card(draw, (box1_x, y_pos, box1_x + box_width, y_pos + box_height), palette)
    
    unique_text = f"{unique_songs:,}"
    bbox = draw.textbbox((0, 0), unique_text, font=medium_stat_font)
    text_width = bbox[2] - bbox[0]
    draw.text((box1_x + (box_width - text_width) // 2, y_pos + 18), unique_text, 
              fill=palette["accent"], font=medium_stat_font)
    
    unique_label = "unique tracks"
    bbox = draw.textbbox((0, 0), unique_label, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text((box1_x + (box_width - text_width) // 2, y_pos + 75), unique_label, 
              fill=(160, 160, 160), font=small_font)
    
    # Variety score box
    box2_x = card_margin + box_width + 20
    draw_glass_card(draw, (box2_x, y_pos, box2_x + box_width, y_pos + box_height), palette)
    
    variety_text = f"{variety:.0f}%"
    bbox = draw.textbbox((0, 0), variety_text, font=medium_stat_font)
    text_width = bbox[2] - bbox[0]
    draw.text((box2_x + (box_width - text_width) // 2, y_pos + 18), variety_text,
              fill=palette["accent"], font=medium_stat_font)
    
    variety_label = "variety score"
    bbox = draw.textbbox((0, 0), variety_label, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text((box2_x + (box_width - text_width) // 2, y_pos + 75), variety_label,
              fill=(160, 160, 160), font=small_font)
    
    y_pos += box_height + 30
    
    # ===== ADDITIONAL STATS ROW (if available) =====
    favorite_hour_utc = stats.get("favorite_hour")
    days_with_music = stats.get("days_with_music", 0)
    
    if favorite_hour_utc is not None or days_with_music > 0:
        small_box_width = (width - card_margin * 2 - 20) // 2
        small_box_height = 90
        
        if favorite_hour_utc is not None:
            draw_glass_card(draw, (card_margin, y_pos, card_margin + small_box_width, y_pos + small_box_height), palette)
            
            # Convert UTC hour to user's timezone
            hour = convert_utc_hour_to_timezone(favorite_hour_utc, timezone)
            period = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            time_text = f"{display_hour} {period}"
            
            bbox = draw.textbbox((0, 0), time_text, font=heading_font)
            text_width = bbox[2] - bbox[0]
            draw.text((card_margin + (small_box_width - text_width) // 2, y_pos + 15), 
                      time_text, fill=palette["primary"], font=heading_font)
            
            peak_label = "peak listening hour"
            bbox = draw.textbbox((0, 0), peak_label, font=tiny_font)
            text_width = bbox[2] - bbox[0]
            draw.text((card_margin + (small_box_width - text_width) // 2, y_pos + 58),
                      peak_label, fill=(140, 140, 140), font=tiny_font)
        
        if days_with_music > 0:
            box_x = card_margin + small_box_width + 20 if favorite_hour_utc is not None else card_margin
            draw_glass_card(draw, (box_x, y_pos, box_x + small_box_width, y_pos + small_box_height), palette)
            
            days_text = f"{days_with_music}"
            bbox = draw.textbbox((0, 0), days_text, font=heading_font)
            text_width = bbox[2] - bbox[0]
            draw.text((box_x + (small_box_width - text_width) // 2, y_pos + 15),
                      days_text, fill=palette["primary"], font=heading_font)
            
            days_label = "days with music"
            bbox = draw.textbbox((0, 0), days_label, font=tiny_font)
            text_width = bbox[2] - bbox[0]
            draw.text((box_x + (small_box_width - text_width) // 2, y_pos + 58),
                      days_label, fill=(140, 140, 140), font=tiny_font)
        
        y_pos += small_box_height + 30
    
    # ===== TOP SONGS SECTION =====
    top_songs = stats.get("top_songs", [])
    if top_songs:
        section_title = "YOUR TOP SONGS"
        bbox = draw.textbbox((0, 0), section_title, font=heading_font)
        text_width = bbox[2] - bbox[0]
        draw_glow_text(bg, ((width - text_width) // 2, y_pos), section_title, heading_font,
                       palette["primary"], palette["glow"], glow_radius=8)
        
        # Recreate draw object after glow text to ensure it's in sync
        draw = ImageDraw.Draw(bg, 'RGBA')
        
        y_pos += 55
        
        # Songs card
        songs_to_show = min(5, len(top_songs))
        songs_card_height = songs_to_show * 65 + 30
        draw_glass_card(draw, (card_margin, y_pos, width - card_margin, y_pos + songs_card_height), palette)
        
        y_pos += 20
        
        max_plays = top_songs[0].get("play_count", 1) if top_songs else 1
        
        for i, song in enumerate(top_songs[:5]):
            song_y = y_pos + i * 65
            
            # Rank indicator
            rank_x = card_margin + 20
            rank_colors = [
                palette["primary"],  # #1 - primary color
                palette["secondary"],  # #2 - secondary
                palette["accent"],  # #3 - accent
                (120, 120, 120),  # #4 - gray
                (100, 100, 100),  # #5 - darker gray
            ]
            rank_color = rank_colors[min(i, 4)]
            
            # Rank badge
            draw.rounded_rectangle([rank_x, song_y, rank_x + 35, song_y + 35], 
                                   radius=8, fill=rank_color)
            
            rank_text = str(i + 1)
            bbox = draw.textbbox((0, 0), rank_text, font=label_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text((rank_x + (35 - text_w) // 2, song_y + (35 - text_h) // 2 - 2),
                      rank_text, fill=(255, 255, 255), font=label_font)
            
            # Song info - get title with robust fallback
            # Try multiple possible keys for the song title
            raw_title = None
            for key in ["song_title", "title", "name"]:
                if key in song and song[key]:
                    raw_title = str(song[key])
                    break
            
            if not raw_title or not raw_title.strip():
                raw_title = f"Song #{i + 1}"
            
            song_title = truncate_text(raw_title.strip(), 28)
            play_count = song.get("play_count", 0)
            
            # Draw song title and play count
            song_draw = ImageDraw.Draw(bg)
            # Use dark color for song title since it's on a light glass card
            song_draw.text((rank_x + 50, song_y + 4), song_title, fill=(30, 30, 30), font=label_font)
            song_draw.text((rank_x + 50, song_y + 26), f"{play_count} plays", fill=(100, 100, 100), font=tiny_font)
            
            # Progress bar on the right
            bar_x = width - card_margin - 150
            bar_width = 120
            bar_height = 12
            progress = play_count / max_plays if max_plays > 0 else 0
            
            draw_progress_bar(draw, bar_x, song_y + 12, bar_width, bar_height,
                              progress, (50, 50, 50), rank_color)
        
        y_pos += songs_card_height + 20
    
    # ===== FUN FACT SECTION =====
    fun_facts = []
    if total_plays > 0:
        if variety > 80:
            fun_facts.append("You're an explorer! Always discovering new music!")
        elif variety > 50:
            fun_facts.append("Great mix of favorites and new discoveries!")
        elif variety < 30:
            fun_facts.append("You know what you like and stick to it!")
        
        if total_plays > 500:
            fun_facts.append("You're basically a DJ at this point!")
        elif total_plays > 200:
            fun_facts.append("Music is clearly a big part of your life!")
        elif total_plays > 50:
            fun_facts.append("Building up a great listening history!")
        
        if unique_songs > 100:
            fun_facts.append(f"You've explored {unique_songs} different tracks!")
        elif unique_songs > 50:
            fun_facts.append(f"{unique_songs} unique tracks in your rotation!")
    
    if fun_facts:
        random.seed(int(user_id) if user_id.isdigit() else hash(user_id))
        fact = random.choice(fun_facts)
        
        # Draw fun fact in a subtle card
        fact_card_y = height - 140
        draw_glass_card(draw, (card_margin + 40, fact_card_y, width - card_margin - 40, fact_card_y + 50), palette)
        
        bbox = draw.textbbox((0, 0), fact, font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, fact_card_y + 15), fact, fill=(220, 220, 220), font=small_font)
    
    # ===== FOOTER =====
    footer_text = "Generated by JARPbot"
    bbox = draw.textbbox((0, 0), footer_text, font=tiny_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, height - 45), footer_text, fill=(100, 100, 100), font=tiny_font)
    
    # Year indicator in corner
    year_text = str(current_year)
    bbox = draw.textbbox((0, 0), year_text, font=medium_stat_font)
    draw.text((width - 100, height - 80), year_text, fill=(40, 40, 40, 80), font=medium_stat_font)
    
    # Convert to RGB for saving
    final_image = bg.convert('RGB')
    
    # Save to buffer
    buffer = io.BytesIO()
    final_image.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    return buffer

async def generate_wrapped_image_async(
    user_name: str,
    user_id: str,
    avatar_url: Optional[str],
    stats: Dict[str, Any],
    timezone: str = DEFAULT_TIMEZONE
) -> io.BytesIO:
    """Async wrapper for generate_wrapped_image"""
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: generate_wrapped_image(user_name, user_id, avatar_url, stats, timezone)
    )
