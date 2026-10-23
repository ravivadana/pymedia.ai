import cv2
import numpy as np
from moviepy import (
    VideoFileClip,
    ImageSequenceClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips
)

VIDEO_PATH = "videos_processing/inputs/videos/madhuri_rathod.mp4"
OUTPUT_PATH = "videos_processing/outputs/madhuri_rathod.mp4"

INTERVAL = 5
FREEZE_DURATION = 1

DARK_COLOR = (0, 0, 0)
OVERLAY_OPACITY = 0.5

# Artistic effect function with style parameter
def artistic_frame(frame, style="oil"):
    frame_uint8 = cv2.convertScaleAbs(frame)
    
    if style == "oil":
        art = cv2.stylization(frame_uint8, sigma_s=60, sigma_r=0.6)
        return cv2.cvtColor(art, cv2.COLOR_BGR2RGB)

    elif style == "sketch":
        sketch_gray, sketch_color = cv2.pencilSketch(frame_uint8, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
        return cv2.cvtColor(sketch_color, cv2.COLOR_BGR2RGB)

    elif style == "cartoon":
        gray = cv2.cvtColor(frame_uint8, cv2.COLOR_BGR2GRAY)
        blur = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2
        )
        color = cv2.bilateralFilter(frame_uint8, 9, 250, 250)
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        return cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB)

    else:
        # Default: return original frame
        return frame

# Choose your style here
STYLE = "cartoon"  # options: "oil", "sketch", "cartoon"

with VideoFileClip(VIDEO_PATH) as video:
    clips = []
    t = 0
    fps = int(video.fps)

    while t < video.duration:
        end = min(t + INTERVAL, video.duration)

        # Normal video
        clips.append(video.subclipped(t, end))

        if end < video.duration:
            # 1️⃣ Extract frame
            frame = video.get_frame(end)

            # 2️⃣ Apply chosen artistic style
            art_frame = artistic_frame(frame, style=STYLE)

            # 3️⃣ Freeze by repeating frame
            freeze_frames = [art_frame] * int(FREEZE_DURATION * fps)
            frozen = ImageSequenceClip(freeze_frames, fps=fps)

            # 4️⃣ Optional dark overlay
            overlay = ColorClip(
                video.size,
                color=DARK_COLOR,
                duration=FREEZE_DURATION
            )
            overlay = overlay.with_mask(
                ColorClip(
                    video.size,
                    color=OVERLAY_OPACITY,
                    is_mask=True,
                    duration=FREEZE_DURATION
                )
            )

            artistic_freeze = CompositeVideoClip(
                [frozen, overlay],
                size=video.size
            )

            clips.append(artistic_freeze)

        t += INTERVAL

    # Combine all clips
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        OUTPUT_PATH,
        fps=fps,
        codec="libx264",
        audio_codec="aac"
    )
