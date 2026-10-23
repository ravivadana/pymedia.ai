import cv2
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import VideoClip

VIDEO_PATH = "videos_processing/inputs/videos/madhuri_rathod.mp4"
OUTPUT_PATH = "videos_processing/outputs/madhuri_rathod_artistic.mp4"

STYLE = "cartoon"  # "oil", "sketch", "cartoon"

# Artistic effect function
def artistic_frame(frame, style="oil"):
    frame_uint8 = cv2.convertScaleAbs(frame)

    if style == "oil":
        art = cv2.stylization(frame_uint8, sigma_s=60, sigma_r=0.6)
        return cv2.cvtColor(art, cv2.COLOR_BGR2RGB)

    elif style == "sketch":
        sketch_gray, sketch_color = cv2.pencilSketch(
            frame_uint8, sigma_s=60, sigma_r=0.07, shade_factor=0.05
        )
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

    return frame

# Load original video
with VideoFileClip(VIDEO_PATH) as video:
    fps = int(video.fps)
    w, h = video.size
    duration = video.duration

    print("Creating artistic video using fl_image...")

    # Create a VideoClip that applies the artistic effect on each frame
    artistic_clip = VideoClip(lambda t: artistic_frame(video.get_frame(t), style=STYLE),
                              duration=duration)

    # Attach original audio
    artistic_clip.audio = video.audio

    # Export video
    artistic_clip.write_videofile(
        OUTPUT_PATH,
        fps=fps,
        codec="libx264",
        audio_codec="aac"
    )
