import json
import os
from bs4 import BeautifulSoup
course_name = "Medical"
year=2025
audio_url = "https://www.youtube.com/watch?v=RgAxhZTcDWQs"

# Define the file paths
html_file_path = os.path.join(
    "00_data_processing", "pages", "2025", f"{course_name}.html"
)

# Updated to match your exact output directory structure
output_json_path = os.path.join(
    "00_data_processing", "data", "nrif_ranking", f"{year}", f"{course_name}.json"
)

def extract_table_to_json(html_path, json_path):
    # 1. Read the local HTML file
    if not os.path.exists(html_path):
        print(f"Error: The file {html_path} does not exist.")
        return

    with open(html_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    # 2. Find the target table
    table = soup.find("table")
    if not table:
        print("Error: No table found in the HTML file.")
        return

    # Normalized keys matching your visual layout
    normalized_headers = ["Institute ID", "Name", "City", "State", "Score", "Rank"]

    # 4. Extract Row Data
    data_list = []
    
    # Target rows directly inside tbody to maintain structure integrity
    tbody = table.find("tbody")
    rows = tbody.find_all("tr", recursive=False) if tbody else table.find_all("tr", recursive=False)

    for row in rows:
        # CRITICAL FIX: recursive=False ensures we only get the 6 primary columns.
        # It completely ignores any <td> elements hiding inside the parameter sub-tables.
        cells = row.find_all("td", recursive=False)
        if not cells or len(cells) < 6:
            continue  

        row_data = {}
        
        # Parse each target column deliberately to handle custom element structures
        # Column 0: Institute ID
        row_data[normalized_headers[0]] = cells[0].get_text(strip=True)
        
        # Column 1: Name 
        # CRITICAL FIX: find(text=True) target-extracts just the raw text node 
        # ("All India Institute of Medical Sciences...") before any button/div elements.
        name_text = cells[1].find(text=True)
        row_data[normalized_headers[1]] = name_text.strip() if name_text else cells[1].get_text(strip=True)
        
        # Column 2: City
        row_data[normalized_headers[2]] = cells[2].get_text(strip=True)
        
        # Column 3: State
        row_data[normalized_headers[3]] = cells[3].get_text(strip=True)
        
        # Column 4: Score
        row_data[normalized_headers[4]] = cells[4].get_text(strip=True)
        
        # Column 5: Rank
        row_data[normalized_headers[5]] = cells[5].get_text(strip=True)

        data_list.append(row_data)

    # 5. Ensure the target directory path exists before writing
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    # Write data out to a clean structured JSON file
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(data_list, json_file, indent=4, ensure_ascii=False)

    print(f"Successfully extracted {len(data_list)} records to {json_path}")


extract_table_to_json(html_file_path, output_json_path)

# =========================================================
# PREMIUM VIDEO GENERATION ENGINE (MOVIEPY v2.0+)
# - Modern Left-Accent Blade Layout for Maximum Visibility
# - Side-by-Side Dual Random Gradients (LIGHT/PASTEL OVERHAUL)
# - Intelligent High-Contrast Dark Typography For Light Layouts
# - Streamed Frame-by-Frame Upward Marquee Engine
# - Auto Workspace Directory Cleanup
# =========================================================

import json
import os
import random
import textwrap
import shutil
import time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips

# =========================================================
# CONFIG
# =========================================================
year=2025
JSON_FILE = (
    "00_data_processing/"
    f"data/nrif_ranking/{year}/"
    f"{course_name}/institute_ranking.json"
)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 540

MOBILE_WIDTH = 1080
MOBILE_HEIGHT = 1920

FPS = 30
SLIDE_DURATION = 3  

TEMP_FOLDER = "slides"
MOBILE_FOLDER = "slides_mobile"

os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(MOBILE_FOLDER, exist_ok=True)

OUTPUT_MOBILE_VIDEO = (
    "00_data_processing/"
    "outputs/videos/"
    f"{course_name}.mp4"
)

os.makedirs(os.path.dirname(OUTPUT_MOBILE_VIDEO), exist_ok=True)

# =========================================================
# BRAND NEW PREMIUM LIGHT & VIBRANT PASTEL THEMES
# (No dark/black backgrounds, explicitly tailored for dark text)
# =========================================================
THEMES = [
    {"bg1": (255, 236, 210), "bg2": (252, 182, 159)},  # Peach Blossom Cream
    {"bg1": (212, 252, 242), "bg2": (150, 230, 210)},  # Fresh Mint Sorbet
    {"bg1": (230, 242, 255), "bg2": (180, 210, 255)},  # Clean Sky Blue
    {"bg1": (254, 211, 252), "bg2": (253, 161, 234)},  # Bubblegum Pink
    {"bg1": (255, 243, 195), "bg2": (255, 213, 115)},  # Soft Lemon Honey
    {"bg1": (224, 255, 210), "bg2": (163, 235, 140)},  # Lime Pistachio
    {"bg1": (243, 231, 255), "bg2": (211, 181, 255)},  # Lavender Mist
    {"bg1": (255, 222, 222), "bg2": (255, 164, 164)},  # Light Rose Petal
    {"bg1": (206, 246, 253), "bg2": (132, 220, 238)},  # Electric Ice
    {"bg1": (255, 237, 188), "bg2": (253, 202, 131)},  # Summer Apricot
    {"bg1": (225, 253, 200), "bg2": (175, 235, 210)},  # Matcha Melon Slim
    {"bg1": (240, 240, 245), "bg2": (200, 205, 220)},  # Platinum Silk Grid
    {"bg1": (255, 225, 240), "bg2": (255, 170, 210)},  # Cotton Candy Dream
    {"bg1": (215, 255, 225), "bg2": (160, 230, 190)}   # Aqua Marine Mint
]

# =========================================================
# LOAD DATA
# =========================================================
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Loaded {len(data)} records")

# =========================================================
# LOAD FONTS
# =========================================================
FONT_PATHS = [
    "arialbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "arial.ttf",
    "C:/Windows/Fonts/arial.ttf"
]

font_path = None
for path in FONT_PATHS:
    if os.path.exists(path):
        font_path = path
        break

try:
    rank_font = ImageFont.truetype(font_path, 80)
    institute_font = ImageFont.truetype(font_path, 40)
    score_font = ImageFont.truetype(font_path, 44)
    label_font = ImageFont.truetype(font_path, 20)
    address_font = ImageFont.truetype(font_path, 30)
    intro_font = ImageFont.truetype(font_path, 80)
    sub_font = ImageFont.truetype(font_path, 40)
except:
    rank_font = institute_font = score_font = label_font = address_font = intro_font = sub_font = ImageFont.load_default()

# =========================================================
# HELPERS
# =========================================================
def wrap_text(text, width=18):
    return textwrap.fill(str(text), width=width)

def get_rank(item, index):
    rank = item.get("Rank")
    if rank is None or rank == "":
        return index + 1
    try:
        return int(rank)
    except:
        return index + 1

def draw_gradient(draw, rect, color1, color2):
    x1, y1, x2, y2 = rect
    height = y2 - y1
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(x1, y1 + y), (x2, y1 + y)], fill=(r, g, b))

# =========================================================
# TITLE / END SLIDES
# =========================================================
def create_title_slide(title, subtitle, output_path):
    theme = random.choice(THEMES)
    img = Image.new("RGB", (MOBILE_WIDTH, MOBILE_HEIGHT), (252, 252, 253))
    draw = ImageDraw.Draw(img)

    card_width, card_height = 980, 1650
    card_x1 = (MOBILE_WIDTH - card_width) // 2
    card_y1 = 130
    card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
    radius = 70

    shadow = Image.new("RGBA", (MOBILE_WIDTH, MOBILE_HEIGHT), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [card_x1 + 12, card_y1 + 14, card_x2 + 12, card_y2 + 14],
        radius=radius, fill=(0, 0, 0, 35)
    )
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)

    gradient_layer = Image.new("RGB", (MOBILE_WIDTH, MOBILE_HEIGHT), (255, 255, 255))
    gradient_draw = ImageDraw.Draw(gradient_layer)
    draw_gradient(gradient_draw, (card_x1, card_y1, card_x2, card_y2), theme["bg1"], theme["bg2"])

    mask = Image.new("L", (MOBILE_WIDTH, MOBILE_HEIGHT), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)
    img.paste(gradient_layer, (0, 0), mask)
    draw = ImageDraw.Draw(img)

    # Clean Dark Slate Accents for title elements
    text_color = (30, 41, 59) 
    secondary_text = (71, 85, 105)

    for i in range(6):
        offset = (i + 1) * 45
        draw.arc(
            [card_x1 - 180, card_y1 - 80 + offset, card_x2 + 180, card_y1 + 260 + offset],
            start=0, end=180, fill=(255, 255, 255, 130), width=6
        )

    wrapped_title = wrap_text(title, width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=intro_font, spacing=28)
    tw = bbox[2] - bbox[0]
    draw.multiline_text(((MOBILE_WIDTH - tw) / 2, 760), wrapped_title, font=intro_font, fill=text_color, spacing=28, align="center")

    bbox = draw.multiline_textbbox((0, 0), subtitle, font=sub_font, spacing=16)
    sw = bbox[2] - bbox[0]
    draw.multiline_text(((MOBILE_WIDTH - sw) / 2, 1220), subtitle, font=sub_font, fill=secondary_text, spacing=16, align="center")

    circle_radius, circle_x, circle_y = 120, MOBILE_WIDTH // 2, 520
    draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius], fill=text_color)

    icon_text = f"{year}"
    bbox = draw.textbbox((0, 0), icon_text, font=rank_font)
    iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((circle_x - iw / 2, circle_y - ih / 2 - 10), icon_text, font=rank_font, fill=(255, 255, 255))

    img.save(output_path)

# =========================================================
# CREATE CARD SLIDES (LIGHT DUAL-GRADIENT ENGINE)
# =========================================================
slide_paths = []
used_theme_history = []

for index, item in enumerate(data):
    # Dynamic 4-Card Screen History filter to avoid screen duplicates on the right box
    available_indices = [k for k in range(len(THEMES)) if k not in used_theme_history]
    if not available_indices:
        available_indices = [k for k in range(len(THEMES))]
        
    chosen_right_index = random.choice(available_indices)
    right_theme = THEMES[chosen_right_index]
    
    # Randomly select a completely different light color layout pool for the Left Box
    chosen_left_index = random.choice([k for k in range(len(THEMES)) if k != chosen_right_index])
    left_theme = THEMES[chosen_left_index]
    
    # Maintain tracking queue for up to 4 elements max
    used_theme_history.append(chosen_right_index)
    if len(used_theme_history) > 4:
        used_theme_history.pop(0)

    rank = get_rank(item, index)
    print(f"Creating Bright Pastel Layout Card: {rank}")

    # Pure high-end modern off-white background canvas
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (250, 250, 252))
    draw = ImageDraw.Draw(img)

    card_width, card_height = 940, 420
    card_x1 = (VIDEO_WIDTH - card_width) // 2
    card_y1 = 60
    card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
    radius = 40
    blade_width = 180

    # Draw Subtle Light Soft Drop Shadow (Updated for high-key bright canvas design)
    shadow = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([card_x1 + 8, card_y1 + 10, card_x2 + 8, card_y2 + 10], radius=radius, fill=(15, 23, 42, 30))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 1. Base Mask Setup
    mask = Image.new("L", (VIDEO_WIDTH, VIDEO_HEIGHT), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)

    # 2. Render Independent Right Box Bright Gradient Layer
    right_layer = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (255, 255, 255))
    right_draw = ImageDraw.Draw(right_layer)
    draw_gradient(right_draw, (card_x1 + blade_width, card_y1, card_x2, card_y2), right_theme["bg1"], right_theme["bg2"])
    img.paste(right_layer, (0, 0), mask)

    # 3. Render Independent Left Box Bright Accent Gradient Layer (Replaced Black)
    left_layer = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (255, 255, 255))
    left_draw = ImageDraw.Draw(left_layer)
    draw_gradient(left_draw, (card_x1, card_y1, card_x1 + blade_width, card_y2), left_theme["bg1"], left_theme["bg2"])
    img.paste(left_layer, (0, 0), mask)
    
    draw = ImageDraw.Draw(img)

    # =========================================================
    # INTEL-DRIVEN CONTRAST DESIGN: HIGH READABILITY DARK SLATE TYPOGRAPHY
    # =========================================================
    primary_text_color = (30, 41, 59)     # Slate 800 (Sharp Headline Boldness)
    secondary_text_color = (71, 85, 105) # Slate 600 (Clean Metadata Readability)
    score_highlight_color = (220, 38, 38) # Vivid Premium Red Anchor for Crisp Contrast on pastels

    # Left Column Typography overlays
    draw.text((card_x1 + 45, card_y1 + 110), "RANK", font=label_font, fill=secondary_text_color)
    rank_text = f"#{rank}"
    bbox_r = draw.textbbox((0, 0), rank_text, font=rank_font)
    rw = bbox_r[2] - bbox_r[0]
    draw.text((card_x1 + (blade_width - rw) // 2, card_y1 + 150), rank_text, font=rank_font, fill=primary_text_color)

    # Right Column Typography space parameters
    content_left_x = card_x1 + blade_width + 50
    
    # 1. Main Institute Label Banner
    draw.text((content_left_x, card_y1 + 40), "INSTITUTE", font=label_font, fill=secondary_text_color)
    institute = wrap_text(item.get("Name", "Unknown Institute"), width=28)
    draw.multiline_text((content_left_x, card_y1 + 75), institute, font=institute_font, fill=primary_text_color, spacing=6)

    # 2. Geolocation Address Block
    city = item.get("City", "Unknown City")
    state = item.get("State", "Unknown State")
    address = wrap_text(f"{city}, {state}, India", width=32)
    draw.multiline_text((content_left_x, card_y2 - 110), address, font=address_font, fill=secondary_text_color, spacing=4)

    # 3. Score Data Badge Matrix
    score_left_x = card_x2 - 200
    draw.text((score_left_x, card_y2 - 110), "SCORE", font=label_font, fill=secondary_text_color)
    score = str(item.get("Score", "N/A"))
    draw.text((score_left_x, card_y2 - 80), score, font=score_font, fill=score_highlight_color) 

    slide_path = os.path.join(TEMP_FOLDER, f"slide_{rank:03d}_{index}.png")
    img.save(slide_path)
    slide_paths.append(slide_path)

# =========================================================
# CREATE MOBILE IMAGES
# =========================================================
print("\nCreating mobile canvas composites...")

CARD_WIDTH, CARD_HEIGHT = 980, 420
TOP_MARGIN, GAP = 40, 20
CANVAS_CONTENT_HEIGHT = TOP_MARGIN + (4 * (CARD_HEIGHT + GAP)) - GAP + TOP_MARGIN

group_index = 1
for i in range(0, len(slide_paths), 4):
    group = slide_paths[i:i + 4]
    current_canvas_height = MOBILE_HEIGHT if (i + 4 >= len(slide_paths)) else CANVAS_CONTENT_HEIGHT
    mobile_canvas = Image.new("RGB", (MOBILE_WIDTH, current_canvas_height), (252, 252, 253))

    for idx, slide_path in enumerate(group):
        card_img = Image.open(slide_path).convert("RGB")
        card_img = card_img.resize((CARD_WIDTH, CARD_HEIGHT))
        x = (MOBILE_WIDTH - CARD_WIDTH) // 2
        y = TOP_MARGIN + idx * (CARD_HEIGHT + GAP)
        mobile_canvas.paste(card_img, (x, y))

    output_path = os.path.join(MOBILE_FOLDER, f"{group_index:03d}_mobile.png")
    mobile_canvas.save(output_path)
    group_index += 1

# =========================================================
# INTRO + END IMAGES
# =========================================================
INTRO_IMAGE = os.path.join(MOBILE_FOLDER, "000_intro.png")
END_IMAGE = os.path.join(MOBILE_FOLDER, "999_end.png")

create_title_slide(f"NIRF {course_name} College Ranking {year}", f"Top {course_name} Institutes in India", INTRO_IMAGE)
create_title_slide("Thank You", "Please Subscribe Channel\nFor More Videos", END_IMAGE)

# =========================================================
# LOAD MOBILE IMAGES
# =========================================================
mobile_images = sorted([
    os.path.join(MOBILE_FOLDER, f)
    for f in os.listdir(MOBILE_FOLDER)
    if f.endswith(".png") and not (f.startswith("000_") or f.startswith("999_"))
])

# =========================================================
# VIDEO GENERATION: RAM-FRIENDLY MARQUEE ENGINE (GAP FIXED)
# =========================================================
print("\nCompiling Video Track via Stream-Optimized Scroll Engine...")

total_scroll_height = 0
canvas_positions = []

for p in mobile_images:
    with Image.open(p) as img_obj:
        canvas_positions.append(total_scroll_height)
        total_scroll_height += img_obj.height

long_canvas = Image.new("RGB", (MOBILE_WIDTH, total_scroll_height), (252, 252, 253))

for idx, p in enumerate(mobile_images):
    with Image.open(p) as img_obj:
        long_canvas.paste(img_obj.convert("RGB"), (0, canvas_positions[idx]))

last_list_viewport = long_canvas.crop((0, total_scroll_height - MOBILE_HEIGHT, MOBILE_WIDTH, total_scroll_height))
last_list_np = np.array(last_list_viewport)

scroll_speed = 5  
total_scroll_pixels = total_scroll_height - MOBILE_HEIGHT
scroll_duration = total_scroll_pixels / (scroll_speed * FPS)

intro_clip = ImageClip(INTRO_IMAGE).with_duration(3.5)
end_clip = ImageClip(END_IMAGE).with_duration(4.0)

def scroll_frame_processor(get_frame, t):
    current_y = int(t * FPS * scroll_speed)
    current_y = min(current_y, total_scroll_pixels)
    viewport = long_canvas.crop((0, current_y, MOBILE_WIDTH, current_y + MOBILE_HEIGHT))
    return np.array(viewport)

scroll_base = ImageClip(last_list_np).with_duration(scroll_duration)
scroll_clip = scroll_base.transform(scroll_frame_processor, apply_to=[])

fade_duration = 0.8
end_np = np.array(Image.open(END_IMAGE).convert("RGB"))

def fade_frame_processor(get_frame, t):
    alpha = t / fade_duration
    alpha = min(max(alpha, 0.0), 1.0)
    blended = np.clip((last_list_np * (1.0 - alpha) + end_np * alpha), 0, 255).astype(np.uint8)
    return blended

fade_base = ImageClip(last_list_np).with_duration(fade_duration)
fade_clip = fade_base.transform(fade_frame_processor, apply_to=[])

final_video = concatenate_videoclips([intro_clip, scroll_clip, fade_clip, end_clip], method="chain")

print(f"Rendering track to file: {OUTPUT_MOBILE_VIDEO}...")
final_video.write_videofile(
    OUTPUT_MOBILE_VIDEO,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    preset="medium",
    threads=4,
    logger="bar"
)

final_video.close()
intro_clip.close()
scroll_clip.close()
fade_clip.close()
end_clip.close()
long_canvas.close()
last_list_viewport.close()

# =========================================================
# CLEANUP
# =========================================================
print("\nCleaning temporary folders...")

if os.path.exists(TEMP_FOLDER):
    shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
    print(f"Deleted: {TEMP_FOLDER}")

if os.path.exists(MOBILE_FOLDER):
    shutil.rmtree(MOBILE_FOLDER, ignore_errors=True)
    print(f"Deleted: {MOBILE_FOLDER}")

print("\n======================================")
print("FINAL VIDEO CREATED SUCCESSFULLY")
print(OUTPUT_MOBILE_VIDEO)
print("TEMP FILES CLEANED")
print("======================================")
import os
import sys

# 1. Force-calculate the exact absolute path to your target folder
target_dir = r"02_videos_processing"

print("=== DIAGNOSTICS ===")
print(f"Does the target directory exist?: {os.path.exists(target_dir)}")

if os.path.exists(target_dir):
    print(f"Files found inside that directory: {os.listdir(target_dir)}")
else:
    # If it doesn't exist, let's see where Python thinks it currently is
    print(f"Current working directory: {os.getcwd()}")
    try:
        print(f"Current script location: {os.path.abspath(__file__)}")
    except NameError:
        print("Running in an interactive environment (__file__ not defined)")

print("===================")

# Try appending and importing
sys.path.insert(0, target_dir)  # insert at 0 to prioritize it over everything else
try:
    from yt_downloader import MediaDownLoader
    print("SUCCESS: Module imported successfully!")
    mediaDownLoader = MediaDownLoader()
    
    inputput_video_folder = "00_data_processing/outputs/videos"
    
    # 1. Trigger the download
    downloaded_video_file = mediaDownLoader.download_video_with_ytdlp(
        inputput_video_folder, audio_url, file_name_part=f"{course_name}_audio"
    )
    print("downloading video Completed")
    
    # 2. FIX: If the downloader function returned None, manually construct the path
    if downloaded_video_file is None:
        expected_base = os.path.join(inputput_video_folder, f"{course_name}_audio")
        
        # Check if it downloaded as an mp4 or webm file
        if os.path.exists(f"{expected_base}.webm"):
            downloaded_video_file = f"{expected_base}.webm"
        elif os.path.exists(f"{expected_base}.mp4"):
            downloaded_video_file = f"{expected_base}.mp4"
        else:
            # Fallback/Search the directory if yt-dlp appended a random ID
            files = os.listdir(inputput_video_folder)
            for f in files:
                if f"{course_name}_audio" in f:
                    downloaded_video_file = os.path.join(inputput_video_folder, f)
                    break

    # Create a temporary name for processing
    temp_output = "temp_output_processing.mp4"
    
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import concatenate_audioclips
    
    try:
        # Extra safety check
        if not downloaded_video_file or not os.path.exists(downloaded_video_file):
            raise FileNotFoundError(f"Could not find downloaded audio/video track file. Path parsed: {downloaded_video_file}")
            
        # 1. Load the main video track
        print(f"Loading main video: {OUTPUT_MOBILE_VIDEO}")
        video_clip = VideoFileClip(OUTPUT_MOBILE_VIDEO)
        video_duration = video_clip.duration
        
        # 2. Load the external track 
        print(f"Loading external track for trimming: {downloaded_video_file}")
        raw_audio_clip = AudioFileClip(downloaded_video_file)
        
        # --- TRIM LOGIC ---
        start_trim = 0
        end_trim = raw_audio_clip.duration - 1
        
        if raw_audio_clip.duration <= 10:
            print(f"⚠️ Warning: File duration ({raw_audio_clip.duration}s) is too short to trim. Keeping original.")
            working_audio = raw_audio_clip
        else:
            print(f"Trimming external track from {start_trim}s to {end_trim}s (Original: {raw_audio_clip.duration}s)")
            if hasattr(raw_audio_clip, "subclipped"):
                working_audio = raw_audio_clip.subclipped(start_trim, end_trim)
            else:
                working_audio = raw_audio_clip.subclip(start_trim, end_trim)
                
        # --- DUPLICATION / LOOPING LOGIC ---
        if working_audio.duration < video_duration:
            print(f"🔄 Audio ({working_audio.duration}s) is shorter than video ({video_duration}s). Duplicating track...")
            
            # Calculate total loops required
            repeats = int(video_duration // working_audio.duration) + 1
            
            # Concatenate the array of duplicated clips
            extended_audio = concatenate_audioclips([working_audio] * repeats)
            
            # Slice down precisely to match video track duration
            if hasattr(extended_audio, "subclipped"):
                final_audio = extended_audio.subclipped(0, video_duration)
            else:
                final_audio = extended_audio.subclip(0, video_duration)
        else:
            # If it's already long enough, no repetition needed
            final_audio = working_audio

        # 3. Combine video and the processed audio track
        print("Combining tracks...")
        if hasattr(video_clip, "with_audio"):
            final_clip = video_clip.with_audio(final_audio)
        else:
            final_clip = video_clip.set_audio(final_audio)
        
        # 4. Save to temporary file
        print("Writing temporary file...")
        final_clip.write_videofile(
            temp_output, 
            codec="libx264", 
            audio_codec="aac"
        )
        
        # 5. CRITICAL FIX: Safe nested close routines to release file pointers sequentially
        print("Releasing media handlers...")
        final_clip.close()
        video_clip.close()
        
        # Close out generated clip derivatives up the ancestry chain
        if 'final_audio' in locals():
            final_audio.close()
        if 'extended_audio' in locals():
            extended_audio.close()
        if 'working_audio' in locals() and working_audio != raw_audio_clip:
            working_audio.close()
            
        raw_audio_clip.close() # Safely release underlying file stream
        
        # 6. Overwrite the original video file safely
        print(f"Overwriting {OUTPUT_MOBILE_VIDEO} with final output...")
        if os.path.exists(OUTPUT_MOBILE_VIDEO):
            os.remove(OUTPUT_MOBILE_VIDEO)
        os.rename(temp_output, OUTPUT_MOBILE_VIDEO)
        
        # Cleanup the downloaded file
        if os.path.exists(downloaded_video_file):
            os.remove(downloaded_video_file)
        print(f"Success! {OUTPUT_MOBILE_VIDEO} has been updated.")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
            
except Exception as e:
    print(f"FAILURE: Could not import or download. Error details: {type(e).__name__} - {e}")