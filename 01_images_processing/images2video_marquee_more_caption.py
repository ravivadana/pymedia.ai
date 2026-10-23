import numpy as np
from moviepy import (
    VideoFileClip,
    ColorClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont

# ------------------------
# Load Existing Video
# ------------------------
main_video = VideoFileClip("01_videos_processing/inputs/videos/VID20260115125346.mp4")

WIDTH, HEIGHT = main_video.w, main_video.h
INTRO_DURATION = 4
FPS = main_video.fps

# ------------------------
# Create Intro Background
# ------------------------
background = ColorClip(
    size=(WIDTH, HEIGHT),
    color=(15, 15, 40)
).with_duration(INTRO_DURATION)

# ------------------------
# Create Text Image (YOUR FONT LOGIC)
# ------------------------
def create_text_image():

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    TEXT_LINES = [
        {"text": "AA23", "size": 150}
    ]

    line_heights = []
    total_height = 0
    fonts = []

    # Calculate heights
    for line in TEXT_LINES:
        size = int(line["size"])  # ensure integer

        try:
            font = ImageFont.truetype("arial.ttf", size)
        except:
            font = ImageFont.load_default()

        fonts.append(font)

        bbox = draw.textbbox((0, 0), line["text"], font=font)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        total_height += h + 4

    # Vertical center
    y_offset = (HEIGHT - total_height) // 2

    # Draw text
    for i, line in enumerate(TEXT_LINES):
        text = line["text"]
        font = fonts[i]
        h = line_heights[i]

        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]

        x = (WIDTH - w) // 2

        # Draw main text
        draw.text((x, y_offset), text, font=font, fill=(255, 255, 255))

        y_offset += h + 4

    return np.array(img)

# ------------------------
# Convert Text to Clip
# ------------------------
text_img = create_text_image()

text_clip = (
    ImageClip(text_img)
    .with_duration(INTRO_DURATION)
    .with_position("center")
)

# Zoom animation
def zoom(t):
    return 0.6 + 0.4 * (t / INTRO_DURATION)

text_clip = text_clip.resized(zoom).fadein(1).fadeout(1)

# ------------------------
# Combine Intro
# ------------------------
intro = CompositeVideoClip([background, text_clip]).with_fps(FPS)
intro = intro.without_audio()

# ------------------------
# Merge Intro + Main Video
# ------------------------
final_video = concatenate_videoclips(
    [intro, main_video],
    method="compose"
)

# ------------------------
# Export Final Video
# ------------------------
final_video.write_videofile(
    "videos_processing/outputs/final_output.mp4",
    fps=FPS,
    codec="libx264",
    audio_codec="aac"
)

# Cleanup
final_video.close()
main_video.close()
