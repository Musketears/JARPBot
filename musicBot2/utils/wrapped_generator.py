"""
Wrapped Image Generator - Creates Spotify Wrapped-style images
"""
import io
import random
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os

# Vibrant color palettes - each user gets a unique combination based on their ID
COLOR_PALETTES = [
    # Sunset Vibes
    {"primary": (255, 95, 109), "secondary": (255, 195, 113), "accent": (255, 154, 158), "dark": (45, 20, 44)},
    # Ocean Dream
    {"primary": (67, 206, 162), "secondary": (24, 90, 157), "accent": (116, 235, 213), "dark": (15, 32, 39)},
    # Purple Haze
    {"primary": (131, 58, 180), "secondary": (253, 29, 29), "accent": (252, 176, 69), "dark": (25, 15, 35)},
    # Electric Blue
    {"primary": (0, 198, 255), "secondary": (0, 114, 255), "accent": (139, 233, 253), "dark": (10, 25, 47)},
    # Neon Pink
    {"primary": (255, 0, 128), "secondary": (255, 128, 171), "accent": (255, 77, 148), "dark": (40, 10, 25)},
    # Tropical Paradise
    {"primary": (255, 183, 77), "secondary": (255, 87, 87), "accent": (255, 214, 138), "dark": (35, 25, 20)},
    # Aurora Borealis
    {"primary": (0, 255, 157), "secondary": (0, 162, 255), "accent": (127, 255, 212), "dark": (10, 30, 35)},
    # Fire Storm
    {"primary": (255, 69, 0), "secondary": (255, 165, 0), "accent": (255, 215, 0), "dark": (35, 15, 10)},
    # Cyberpunk
    {"primary": (255, 0, 255), "secondary": (0, 255, 255), "accent": (255, 105, 180), "dark": (20, 10, 30)},
    # Forest Glow
    {"primary": (34, 197, 94), "secondary": (74, 222, 128), "accent": (187, 247, 208), "dark": (15, 35, 20)},
    # Cosmic Purple
    {"primary": (167, 139, 250), "secondary": (139, 92, 246), "accent": (196, 181, 253), "dark": (30, 20, 45)},
    # Cherry Blossom
    {"primary": (255, 182, 193), "secondary": (255, 105, 180), "accent": (255, 218, 233), "dark": (45, 20, 30)},
    # Midnight Jazz
    {"primary": (59, 130, 246), "secondary": (37, 99, 235), "accent": (147, 197, 253), "dark": (15, 23, 42)},
    # Lava Flow
    {"primary": (239, 68, 68), "secondary": (234, 179, 8), "accent": (251, 146, 60), "dark": (40, 15, 15)},
    # Arctic Frost
    {"primary": (56, 189, 248), "secondary": (125, 211, 252), "accent": (186, 230, 253), "dark": (15, 30, 40)},
]

# Fun titles for different listening amounts
LISTENING_TITLES = [
    (0, "🎵 Silent Soul"),
    (10, "🎶 Casual Listener"),
    (50, "🎧 Music Enthusiast"),
    (100, "🔥 Dedicated Fan"),
    (200, "⭐ Music Connoisseur"),
    (500, "💎 Audiophile Elite"),
    (1000, "👑 Music Royalty"),
    (2000, "🌟 Legendary Listener"),
]

def get_listening_title(play_count: int) -> str:
    """Get a fun title based on play count"""
    title = LISTENING_TITLES[0][1]
    for threshold, label in LISTENING_TITLES:
        if play_count >= threshold:
            title = label
    return title

def get_user_palette(user_id: str) -> Dict[str, Tuple[int, int, int]]:
    """Get a unique color palette based on user ID"""
    # Use user ID to generate a consistent palette selection
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    palette_index = hash_val % len(COLOR_PALETTES)
    return COLOR_PALETTES[palette_index]

def create_gradient_background(width: int, height: int, colors: List[Tuple[int, int, int]], angle: float = 45) -> Image.Image:
    """Create a gradient background with multiple colors"""
    import math
    
    base = Image.new('RGB', (width, height), colors[0])
    draw = ImageDraw.Draw(base)
    
    # Create diagonal gradient
    angle_rad = math.radians(angle)
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    
    for y in range(height):
        for x in range(width):
            # Calculate position along gradient line
            pos = (x * cos_angle + y * sin_angle) / (width * cos_angle + height * sin_angle)
            
            # Interpolate between colors
            if len(colors) == 2:
                r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * pos)
                g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * pos)
                b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * pos)
            else:
                # Multiple color stops
                segment = pos * (len(colors) - 1)
                idx = min(int(segment), len(colors) - 2)
                local_pos = segment - idx
                r = int(colors[idx][0] + (colors[idx + 1][0] - colors[idx][0]) * local_pos)
                g = int(colors[idx][1] + (colors[idx + 1][1] - colors[idx][1]) * local_pos)
                b = int(colors[idx][2] + (colors[idx + 1][2] - colors[idx][2]) * local_pos)
            
            draw.point((x, y), fill=(r, g, b))
    
    return base

def create_simple_gradient(width: int, height: int, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> Image.Image:
    """Create a simple vertical gradient - faster than diagonal"""
    base = Image.new('RGB', (width, height), color1)
    draw = ImageDraw.Draw(base)
    
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return base

def add_noise_texture(image: Image.Image, intensity: int = 15) -> Image.Image:
    """Add subtle noise texture to image"""
    import random
    
    pixels = image.load()
    width, height = image.size
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            noise = random.randint(-intensity, intensity)
            r = max(0, min(255, r + noise))
            g = max(0, min(255, g + noise))
            b = max(0, min(255, b + noise))
            pixels[x, y] = (r, g, b)
    
    return image

def add_decorative_shapes(draw: ImageDraw.Draw, width: int, height: int, colors: Dict[str, Tuple[int, int, int]], user_id: str):
    """Add decorative shapes based on user ID for uniqueness"""
    random.seed(int(hashlib.md5(user_id.encode()).hexdigest(), 16))
    
    # Add floating circles
    for _ in range(random.randint(5, 10)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(20, 100)
        opacity = random.randint(20, 50)
        color = (*colors["accent"], opacity)
        
        # Draw circle with PIL (create overlay)
        for i in range(r, 0, -3):
            alpha = int(opacity * (1 - i / r))
            circle_color = (*colors["accent"][:3],)
            draw.ellipse([x - i, y - i, x + i, y + i], outline=circle_color, width=1)
    
    # Add some line decorations
    for _ in range(random.randint(3, 6)):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        length = random.randint(50, 150)
        angle = random.uniform(0, 6.28)
        import math
        x2 = int(x1 + length * math.cos(angle))
        y2 = int(y1 + length * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=(*colors["primary"], 40), width=2)

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if custom font not available"""
    # Try to use system fonts
    font_paths = [
        # Windows fonts
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        # Linux fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Mac fonts
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    
    bold_paths = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    
    paths_to_try = bold_paths if bold else font_paths
    
    for path in paths_to_try:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    
    # Fallback to default
    return ImageFont.load_default()

def truncate_text(text: str, max_length: int = 35) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def generate_wrapped_image(
    user_name: str,
    user_id: str,
    avatar_url: Optional[str],
    stats: Dict[str, Any]
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
    - favorite_hour: int (optional, 0-23)
    """
    # Image dimensions (portrait for mobile-friendly)
    width = 800
    height = 1200
    
    # Get user-specific color palette
    palette = get_user_palette(user_id)
    
    # Create gradient background
    bg = create_simple_gradient(
        width, height,
        palette["dark"],
        (
            int(palette["dark"][0] * 0.6 + palette["secondary"][0] * 0.4),
            int(palette["dark"][1] * 0.6 + palette["secondary"][1] * 0.4),
            int(palette["dark"][2] * 0.6 + palette["secondary"][2] * 0.4)
        )
    )
    
    draw = ImageDraw.Draw(bg)
    
    # Add decorative elements
    add_decorative_shapes(draw, width, height, palette, user_id)
    
    # Fonts
    title_font = get_font(48, bold=True)
    heading_font = get_font(36, bold=True)
    stat_font = get_font(72, bold=True)
    label_font = get_font(24)
    song_font = get_font(28, bold=True)
    small_font = get_font(20)
    
    y_pos = 60
    
    # Header - Year and Wrapped title
    current_year = datetime.now().year
    header_text = f"🎵 {current_year} WRAPPED"
    bbox = draw.textbbox((0, 0), header_text, font=title_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos), header_text, fill=palette["primary"], font=title_font)
    
    y_pos += 80
    
    # Username with listening title
    title = get_listening_title(stats.get("total_plays", 0))
    user_text = f"{user_name}'s Year in Music"
    bbox = draw.textbbox((0, 0), user_text, font=heading_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos), user_text, fill=(255, 255, 255), font=heading_font)
    
    y_pos += 50
    
    # Listening title badge
    bbox = draw.textbbox((0, 0), title, font=label_font)
    text_width = bbox[2] - bbox[0]
    badge_padding = 15
    badge_width = text_width + badge_padding * 2
    badge_height = 40
    badge_x = (width - badge_width) // 2
    
    # Draw badge background
    draw.rounded_rectangle(
        [badge_x, y_pos, badge_x + badge_width, y_pos + badge_height],
        radius=20,
        fill=palette["primary"]
    )
    draw.text((badge_x + badge_padding, y_pos + 8), title, fill=(255, 255, 255), font=label_font)
    
    y_pos += 80
    
    # Main stats section - Total plays
    total_plays = stats.get("total_plays", 0)
    plays_text = f"{total_plays:,}"
    bbox = draw.textbbox((0, 0), plays_text, font=stat_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos), plays_text, fill=palette["accent"], font=stat_font)
    
    y_pos += 80
    
    label = "songs played"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_pos), label, fill=(200, 200, 200), font=label_font)
    
    y_pos += 60
    
    # Secondary stats row
    unique_songs = stats.get("unique_songs", 0)
    
    # Draw stat boxes
    box_width = 350
    box_height = 100
    box_spacing = 50
    start_x = (width - (box_width * 2 + box_spacing)) // 2
    
    # Unique songs box
    draw.rounded_rectangle(
        [start_x, y_pos, start_x + box_width, y_pos + box_height],
        radius=15,
        fill=(255, 255, 255, 20),
        outline=palette["primary"],
        width=2
    )
    
    unique_text = f"{unique_songs:,}"
    bbox = draw.textbbox((0, 0), unique_text, font=heading_font)
    text_width = bbox[2] - bbox[0]
    draw.text((start_x + (box_width - text_width) // 2, y_pos + 15), unique_text, fill=palette["accent"], font=heading_font)
    
    unique_label = "unique tracks"
    bbox = draw.textbbox((0, 0), unique_label, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text((start_x + (box_width - text_width) // 2, y_pos + 60), unique_label, fill=(180, 180, 180), font=small_font)
    
    # Variety ratio box
    variety_x = start_x + box_width + box_spacing
    draw.rounded_rectangle(
        [variety_x, y_pos, variety_x + box_width, y_pos + box_height],
        radius=15,
        fill=(255, 255, 255, 20),
        outline=palette["secondary"],
        width=2
    )
    
    # Calculate variety percentage
    variety = (unique_songs / total_plays * 100) if total_plays > 0 else 0
    variety_text = f"{variety:.0f}%"
    bbox = draw.textbbox((0, 0), variety_text, font=heading_font)
    text_width = bbox[2] - bbox[0]
    draw.text((variety_x + (box_width - text_width) // 2, y_pos + 15), variety_text, fill=palette["accent"], font=heading_font)
    
    variety_label = "variety score"
    bbox = draw.textbbox((0, 0), variety_label, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text((variety_x + (box_width - text_width) // 2, y_pos + 60), variety_label, fill=(180, 180, 180), font=small_font)
    
    y_pos += box_height + 50
    
    # Top Songs Section
    top_songs = stats.get("top_songs", [])
    if top_songs:
        section_title = "🏆 YOUR TOP SONGS"
        bbox = draw.textbbox((0, 0), section_title, font=heading_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, y_pos), section_title, fill=palette["primary"], font=heading_font)
        
        y_pos += 60
        
        # Display top 5 songs
        for i, song in enumerate(top_songs[:5]):
            song_y = y_pos + i * 70
            
            # Rank circle
            rank_x = 60
            rank_size = 40
            rank_color = palette["primary"] if i == 0 else palette["secondary"] if i < 3 else (100, 100, 100)
            draw.ellipse([rank_x, song_y, rank_x + rank_size, song_y + rank_size], fill=rank_color)
            
            # Rank number
            rank_text = str(i + 1)
            bbox = draw.textbbox((0, 0), rank_text, font=label_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(
                (rank_x + (rank_size - text_width) // 2, song_y + (rank_size - text_height) // 2 - 2),
                rank_text,
                fill=(255, 255, 255),
                font=label_font
            )
            
            # Song title
            song_title = truncate_text(song.get("song_title", "Unknown Song"))
            draw.text((120, song_y + 5), song_title, fill=(255, 255, 255), font=song_font)
            
            # Play count
            play_count = song.get("play_count", 0)
            plays_label = f"{play_count} plays"
            draw.text((120, song_y + 38), plays_label, fill=(150, 150, 150), font=small_font)
            
            # Play count bar
            bar_x = 500
            bar_width = 250
            bar_height = 20
            max_plays = top_songs[0].get("play_count", 1) if top_songs else 1
            fill_width = int((play_count / max_plays) * bar_width)
            
            draw.rounded_rectangle(
                [bar_x, song_y + 15, bar_x + bar_width, song_y + 15 + bar_height],
                radius=10,
                fill=(60, 60, 60)
            )
            
            if fill_width > 0:
                draw.rounded_rectangle(
                    [bar_x, song_y + 15, bar_x + fill_width, song_y + 15 + bar_height],
                    radius=10,
                    fill=palette["primary"]
                )
        
        y_pos += len(top_songs[:5]) * 70 + 30
    
    # Fun fact at the bottom
    y_pos = height - 120
    
    # Generate a fun fact
    fun_facts = []
    if total_plays > 0:
        if variety > 70:
            fun_facts.append("You're an explorer! Always finding new music 🔍")
        elif variety < 30:
            fun_facts.append("You know what you like and stick to it! 💪")
        
        if total_plays > 500:
            fun_facts.append("You're basically a DJ at this point! 🎧")
        elif total_plays > 200:
            fun_facts.append("Music is clearly a big part of your life! 🎶")
        
        if unique_songs > 100:
            fun_facts.append(f"You've discovered {unique_songs} unique tracks! 🌟")
    
    if fun_facts:
        random.seed(int(user_id) if user_id.isdigit() else hash(user_id))
        fact = random.choice(fun_facts)
        bbox = draw.textbbox((0, 0), fact, font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, y_pos), fact, fill=(200, 200, 200), font=small_font)
    
    # Footer
    footer_text = "Generated by JARPbot 🤖"
    bbox = draw.textbbox((0, 0), footer_text, font=small_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, height - 50), footer_text, fill=(120, 120, 120), font=small_font)
    
    # Convert to bytes
    buffer = io.BytesIO()
    bg.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    return buffer

async def generate_wrapped_image_async(
    user_name: str,
    user_id: str,
    avatar_url: Optional[str],
    stats: Dict[str, Any]
) -> io.BytesIO:
    """Async wrapper for generate_wrapped_image"""
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generate_wrapped_image,
        user_name,
        user_id,
        avatar_url,
        stats
    )

