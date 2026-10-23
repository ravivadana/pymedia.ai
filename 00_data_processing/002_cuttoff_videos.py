import os
from pathlib import Path

from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
)

# =========================================================
# CONFIG
# =========================================================
BASE_DIR = "00_data_processing"

YEAR = 2026
COURSE_NAME = "engineering"

IMAGE_FOLDER = Path(
    f"{BASE_DIR}/images/nrif_ranking/{YEAR}/{COURSE_NAME}/cutoff_matrix"
)

AUDIO_FILE = f"{BASE_DIR}/audio/rangeela1.mp4"

OUTPUT_FOLDER = Path(
    str(IMAGE_FOLDER).replace("images", "videos")
)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Desktop / Landscape Video
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

VIDEO_DURATION = 59  # seconds
FPS = 30

# Zoom amount over full video duration
ZOOM_PERCENT = 0.05  # 5%

# =========================================================
# LOAD AUDIO
# =========================================================
audio = None

if os.path.exists(AUDIO_FILE):
    print(f"Loading audio: {AUDIO_FILE}")
    audio = AudioFileClip(AUDIO_FILE)
else:
    print("Audio file not found. Videos will be silent.")

# =========================================================
# GET IMAGES
# =========================================================
if not IMAGE_FOLDER.exists():
    raise FileNotFoundError(
        f"Image folder not found:\n{IMAGE_FOLDER}"
    )

images = sorted(
    f for f in IMAGE_FOLDER.iterdir()
    if f.suffix.lower() == ".png"
)

print(f"Found {len(images)} images")

# =========================================================
# CREATE VIDEOS
# =========================================================
for image_path in images:

    output_video = OUTPUT_FOLDER / f"{image_path.stem}.mp4"

    if output_video.exists():
        print(f"Skipping: {image_path.name}")
        continue

    print(f"Creating: {image_path.name}")

    # =====================================================
    # DETERMINE BASE SCALE
    # =====================================================
    temp_clip = ImageClip(str(image_path))

    base_scale = min(
        VIDEO_WIDTH / temp_clip.w,
        VIDEO_HEIGHT / temp_clip.h
    )

    temp_clip.close()

    # =====================================================
    # ZOOM FUNCTION
    # =====================================================
    def zoom(t):
        return base_scale * (
            1 + ZOOM_PERCENT * (t / VIDEO_DURATION)
        )

    # =====================================================
    # FOREGROUND IMAGE
    # =====================================================
    img_clip = (
        ImageClip(str(image_path))
        .resized(zoom)
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
            clip_audio = audio.subclipped(
                0,
                VIDEO_DURATION
            )
        else:
            loops = int(
                VIDEO_DURATION / audio.duration
            ) + 1

            clip_audio = concatenate_audioclips(
                [audio] * loops
            ).subclipped(
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
        threads=min(4, os.cpu_count() or 1),
    )

    # =====================================================
    # CLEANUP
    # =====================================================
    video.close()
    img_clip.close()

print("\nDone!")
print(f"Videos saved to:\n{OUTPUT_FOLDER}")

# =========================================================
# FINAL CLEANUP
# =========================================================
if audio is not None:
    audio.close()