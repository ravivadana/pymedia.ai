import cv2
import numpy as np
import torch
from ultralytics import YOLO

# -----------------------------
# ROBUST MOVIEPY IMPORT
# -----------------------------
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.VideoClip import ImageClip, ColorClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy import concatenate_videoclips
    IS_V2 = True
except ImportError:
    # from moviepy.editor import (
    #     VideoFileClip,
    #     ImageClip,
    #     ColorClip,
    #     CompositeVideoClip,
    #     concatenate_videoclips,
    # )
    IS_V2 = False


# -----------------------------
# LOAD YOLO SEGMENTATION MODEL
# -----------------------------
print("Loading YOLOv8 segmentation model...")
device = 0 if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8n-seg.pt")
model.to(device)


# -----------------------------
# ARTISTIC FREEZE FUNCTION
# -----------------------------
def process_artistic_freeze(frame):
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    h, w = frame_bgr.shape[:2]

    # Run YOLO
    results = model(frame_bgr, verbose=False)[0]

    mask = np.zeros((h, w), dtype=np.float32)

    if results.masks is not None:
        largest_area = 0
        best_mask = None

        for i, cls in enumerate(results.boxes.cls):
            if int(cls) == 0:  # person class
                person_mask = results.masks.data[i].cpu().numpy()
                area = person_mask.sum()

                if area > largest_area:
                    largest_area = area
                    best_mask = person_mask

        if best_mask is not None:
            best_mask = cv2.resize(
                best_mask, (w, h), interpolation=cv2.INTER_NEAREST
            )
            mask = best_mask

    # Convert to 0-255
    mask = (mask > 0.5).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (31, 31), 0)

    alpha = np.expand_dims(mask, axis=-1)

    # Foreground enhancement (natural)
    fg = cv2.convertScaleAbs(frame_bgr, alpha=1.15, beta=15)

    # Background blur + slight darkening
    bg = cv2.GaussianBlur(frame_bgr, (41, 41), 0)
    bg = cv2.convertScaleAbs(bg, alpha=0.75, beta=-15)

    # Soft blend
    combined = (fg * alpha + bg * (1 - alpha)).astype(np.uint8)

    # -----------------------------
    # Subtle Shadow for Depth
    # -----------------------------
    shadow = np.zeros((h, w), dtype=np.uint8)
    contours, _ = cv2.findContours(
        (mask * 255).astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    cv2.drawContours(shadow, contours, -1, 255, 20)
    shadow = cv2.GaussianBlur(shadow, (51, 51), 0)
    shadow = np.expand_dims(shadow / 255.0, axis=-1)

    combined = (combined * (1 - 0.25 * shadow)).astype(np.uint8)

    # -----------------------------
    # Subtle Glow (Cinematic)
    # -----------------------------
    glow = combined.copy()
    cv2.drawContours(glow, contours, -1, (0, 255, 255), 10)
    glow = cv2.GaussianBlur(glow, (35, 35), 0)

    combined = cv2.addWeighted(glow, 0.4, combined, 1.0, 0)

    return cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)


# -----------------------------
# CONFIG
# -----------------------------
VIDEO_PATH = "02_videos_processing/inputs/videos/2.mp4"
OUTPUT_PATH = "02_videos_processing/outputs/2.mp4"


# -----------------------------
# PROCESS VIDEO
# -----------------------------
with VideoFileClip(VIDEO_PATH) as video:

    clips = []
    t = 0

    while t < video.duration:
        end = min(t + 5, video.duration)

        clips.append(
            video.subclipped(t, end) if IS_V2 else video.subclip(t, end)
        )

        if end < video.duration:
            freeze_time = min(end, video.duration - 0.01)
            raw_frame = video.get_frame(freeze_time)

            art_frame = process_artistic_freeze(raw_frame)

            freeze_clip = ImageClip(art_frame)

            if IS_V2:
                freeze_clip = freeze_clip.with_duration(1.5).resized(
                    lambda x: 1 + 0.05 * x
                )
            else:
                freeze_clip = freeze_clip.set_duration(1.5).resize(
                    lambda x: 1 + 0.05 * x
                )

            flash = ColorClip(size=video.size, color=(255, 255, 255))

            if IS_V2:
                flash = flash.with_duration(0.15).with_opacity(0.5)
            else:
                flash = flash.set_duration(0.15).set_opacity(0.5)

            freeze_with_flash = CompositeVideoClip([freeze_clip, flash])

            clips.append(freeze_with_flash)

        t += 5

    final_video = concatenate_videoclips(clips, method="compose")

    final_video.write_videofile(
        OUTPUT_PATH,
        fps=video.fps,
        codec="libx264",
    )

    final_video.close()

print("✅ Done! Output saved to:", OUTPUT_PATH)
