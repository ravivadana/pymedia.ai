import os
import shutil
from pathlib import Path
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips
)

# =========================================================
# CONFIG
# =========================================================
BASE_DIR = "00_data_processing"
year = 2026
course_name = "engineering"

IMAGE_FOLDER = Path(f"{BASE_DIR}/images/nrif_ranking/{year}/{course_name}/cutoff_matrix")
AUDIO_FILE = f"{BASE_DIR}/audio/rangeela1.mp4"

OUTPUT_FOLDER = Path(str(IMAGE_FOLDER).replace("images", "videos"))
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_DURATION = 59
FPS = 30

# =========================================================
# LOAD AUDIO
# =========================================================
audio = None
if os.path.exists(AUDIO_FILE):
    print("Loading audio...")
    audio = AudioFileClip(AUDIO_FILE)

# =========================================================
# GET IMAGES
# =========================================================
images = sorted(
    f for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith(".png")
)

print(f"Found {len(images)} images")

# =========================================================
# CREATE VIDEOS
# =========================================================
for image_name in images:

    image_path = IMAGE_FOLDER / image_name
    output_video = OUTPUT_FOLDER / image_name.replace(".png", "_Admission 2026 Cut Off #JoSSA #IIT.mp4")

    if os.path.exists(output_video):
        print("Skipping:", image_name)
        continue

    print("Creating:", image_name)

    # =====================================================
    # IMAGE CLIP
    # =====================================================
    img_clip = ImageClip(str(image_path))

    # 🔥 COVER SCALE (fill full screen)
    TOP_PADDING = 100

    # Fit image within available height
    available_height = VIDEO_HEIGHT - TOP_PADDING

    scale = min(
        VIDEO_WIDTH / img_clip.w,
        available_height / img_clip.h
    )

    img_clip = img_clip.resized(scale)

    # Position image below top padding
    img_clip = img_clip.with_position(
        (
            "center",
            TOP_PADDING
        )
    )

    # =====================================================
    # ZOOM EFFECT (fixed)
    # =====================================================
    def zoom(t):
        return 1.0 + 0.05 * (t / VIDEO_DURATION)

    img_clip = img_clip.resized(zoom)

    img_clip = (
        img_clip
        .with_duration(VIDEO_DURATION)
        .with_position("center")
    )

    # =====================================================
    # COMPOSITE VIDEO
    # =====================================================
    video = CompositeVideoClip(
        [img_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).with_duration(VIDEO_DURATION)

    # =====================================================
    # AUDIO
    # =====================================================
    if audio is not None:
        if audio.duration >= VIDEO_DURATION:
            clip_audio = audio.subclipped(0, VIDEO_DURATION)
        else:
            loops = int(VIDEO_DURATION / audio.duration) + 1
            clip_audio = concatenate_audioclips([audio] * loops).subclipped(
                0,
                VIDEO_DURATION
            )

        video = video.with_audio(clip_audio)

    # =====================================================
    # EXPORT
    # =====================================================
    video.write_videofile(
        str(output_video),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=min(4, os.cpu_count())
    )

    video.close()
    img_clip.close()

print("\nDone!")
print("Videos saved to:", OUTPUT_FOLDER)

# =========================================================
# CLEANUP / EXTRA MP4 COPY FIXED
# =========================================================
for mp4 in IMAGE_FOLDER.rglob("*.mp4"):
    shutil.copy2(mp4, OUTPUT_FOLDER / mp4.name)