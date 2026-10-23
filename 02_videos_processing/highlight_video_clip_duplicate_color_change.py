import cv2
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import VideoClip

VIDEO_PATH = "videos_processing/inputs/videos/madhuri_rathod.mp4"
OUTPUT_PATH = "videos_processing/outputs/madhuri_rathod_output_trail.mp4"
STYLE = "sketch"  # options: "oil", "sketch", "cartoon"

# --- Artistic effect function ---
def artistic_frame(frame, style="cartoon"):
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

# --- Motion trail + duplicate person ---
trail_buffer = []

def duplicate_person_with_trail(frame, trail_length=5, alpha_decay=0.6):
    global trail_buffer
    h, w, _ = frame.shape

    # Center 50% width as "person"
    left = w // 4
    right = 3 * w // 4
    person_region = frame[:, left:right, :]

    # Place left copy
    new_frame = np.zeros_like(frame)
    new_frame[:, :right-left, :] = person_region

    # Place mirrored right copy
    mirrored = cv2.flip(person_region, 1)
    new_frame[:, w-(right-left):, :] = mirrored

    # Middle background
    new_frame[:, right-left:w-(right-left), :] = frame[:, right-left:w-(right-left), :]

    # Add motion trail
    trail_buffer.append(new_frame.copy())
    if len(trail_buffer) > trail_length:
        trail_buffer.pop(0)

    blended = new_frame.astype(np.float32)
    for i, past_frame in enumerate(trail_buffer[:-1]):
        alpha = alpha_decay * (i+1)/trail_length
        blended = cv2.addWeighted(blended, 1.0, past_frame.astype(np.float32), alpha, 0)

    return blended.astype(np.uint8)

# --- Process video ---
with VideoFileClip(VIDEO_PATH) as video:
    fps = int(video.fps)
    duration = video.duration

    def make_frame(t):
        frame = video.get_frame(t)
        art = artistic_frame(frame, style=STYLE)
        #dup_trail = duplicate_person_with_trail(art)
        return art

    final_clip = VideoClip(make_frame, duration=duration)
    final_clip.audio = video.audio

    final_clip.write_videofile(
        OUTPUT_PATH,
        fps=fps,
        codec="libx264",
        audio_codec="aac"
    )
