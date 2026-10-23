import cv2
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import VideoClip

VIDEO_PATH = "videos_processing/inputs/videos/madhuri_rathod.mp4"
OUTPUT_PATH = "videos_processing/outputs/madhuri_rathod_output_duplicate_mirror.mp4"

STYLE = "sketch"  # "oil", "sketch", "cartoon"

# Artistic effect (optional)
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

# Function to duplicate person in the center
def duplicate_person(frame):
    h, w, _ = frame.shape

    # Take center 50% width as the "person region"
    left = w // 4
    right = 3 * w // 4
    person_region = frame[:, left:right, :]

    # Create empty frame
    new_frame = np.zeros_like(frame)

    # Place person on left
    new_frame[:, :right-left, :] = person_region

    # Place mirrored person on right
    mirrored = cv2.flip(person_region, 1)  # 1 = horizontal flip
    new_frame[:, w-(right-left):, :] = mirrored

    # Fill middle with original background (optional)
    middle_start = right-left
    middle_end = w-(right-left)
    if middle_end > middle_start:
        new_frame[:, middle_start:middle_end, :] = frame[:, middle_start:middle_end, :]

    return new_frame


# Load video
with VideoFileClip(VIDEO_PATH) as video:
    fps = int(video.fps)
    duration = video.duration

    # Create VideoClip frame by frame
    def make_frame(t):
        frame = video.get_frame(t)
        art = artistic_frame(frame, STYLE)
        #dup = duplicate_person(art)
        return art

    final_clip = VideoClip(make_frame, duration=duration)
    final_clip.audio = video.audio

    # Export
    final_clip.write_videofile(
        OUTPUT_PATH,
        fps=fps,
        codec="libx264",
        audio_codec="aac"
    )
