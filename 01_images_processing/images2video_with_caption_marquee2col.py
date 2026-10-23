import os
import math
import re
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ExifTags, ImageOps

from moviepy import VideoClip, AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip

dynamic_keywords = []

# ----------------- SAFE FACE DETECTION -----------------
try:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        face_cascade = None
except (AttributeError, Exception):
    face_cascade = None


def get_face_center(img):
    if face_cascade is None or face_cascade.empty():
        h, w, _ = img.shape
        return w // 2, h // 2

    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
        if len(faces) == 0:
            h, w, _ = img.shape
            return w // 2, h // 2
        x, y, w_f, h_f = faces[0]
        return x + w_f // 2, y + h_f // 2
    except Exception:
        h, w, _ = img.shape
        return w // 2, h // 2


# ----------------- VERSION SAFE AUDIO SUBCLIP -----------------
def audio_subclip(audio, start, end):
    """Return a subclip of audio compatible across MoviePy versions."""
    sr = getattr(audio, "fps", 44100)
    arr = audio.to_soundarray(fps=sr)
    total_samples = arr.shape[0]
    duration = audio.duration
    start_sample = int(start / duration * total_samples)
    end_sample = int(end / duration * total_samples)
    sub_arr = arr[start_sample:end_sample]
    return AudioArrayClip(sub_arr, fps=sr)


def loop_audio_to_duration(audio, target):
    """Loop audio manually until it reaches the target duration."""
    clips = []
    total = 0
    while total < target:
        remaining = target - total
        if remaining < audio.duration:
            clips.append(audio_subclip(audio, 0, remaining))
            total += remaining
        else:
            clips.append(audio)
            total += audio.duration
    return concatenate_audioclips(clips)


# ----------------- FILENAME HELPERS -----------------
def get_image_file_name(path):
    filename = os.path.basename(path)
    filename = os.path.splitext(filename)[0]
    parts = filename.split('_')
    if len(parts) > 1:
        dynamic_keywords.append(f'#{parts[1]}')
    filename = filename.replace("_", "#")
    return filename


# ----------------- VISUAL HELPERS -----------------
def create_film_reel_overlay(vw, vh, t, scroll_speed):
    overlay = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bar_thickness = 30
    spacing = 36
    pulse = int(150 + 50 * math.sin(t * 3))
    offset = int((-scroll_speed * t * 0.5) % spacing)

    # Black side rails
    draw.rectangle([0, 0, bar_thickness, vh], fill=(0, 0, 0, 120))
    draw.rectangle([vw - bar_thickness, 0, vw, vh], fill=(0, 0, 0, 120))
    
    # Center divider rail
    mid_x = vw // 2
    draw.rectangle([mid_x - bar_thickness // 2, 0, mid_x + bar_thickness // 2, vh], fill=(0, 0, 0, 140))

    # Film sprocket holes (Left, Center, Right)
    for y in range(-spacing + offset, vh + spacing, spacing):
        # Left edge
        draw.rectangle([bar_thickness // 2 - 8, y - 6, bar_thickness // 2 + 8, y + 6], fill=(255, 255, 255, pulse))
        # Center divider
        draw.rectangle([mid_x - 8, y - 6, mid_x + 8, y + 6], fill=(255, 255, 255, pulse))
        # Right edge
        draw.rectangle([vw - bar_thickness // 2 - 8, y - 6, vw - bar_thickness // 2 + 8, y + 6], fill=(255, 255, 255, pulse))

    return overlay


def get_metadata_params():
    current_file = Path(__file__).resolve()
    meta_dir = current_file.parent
    inputs_path = meta_dir / "meta/inputs" / "metadata.json"
    
    metadata = {}
    if os.path.exists(inputs_path):
        with open(inputs_path, "r") as file:
            metadata = json.load(file)

    existing_keywords = metadata.get("keywords", "")
    keywords_list = [k.strip() for k in existing_keywords.split(";") if k.strip()]
    for k in dynamic_keywords:
        if k not in keywords_list:
            keywords_list.append(k)
    keywords_str = "; ".join(keywords_list)

    ffmpeg_params = []
    if "title" in metadata:
        ffmpeg_params += ["-metadata", f"title={metadata['title']}"]
    if "author" in metadata:
        ffmpeg_params += ["-metadata", f"author={metadata['author']}"]
    if "description" in metadata:
        ffmpeg_params += ["-metadata", f"description={metadata['description']}"]

    ffmpeg_params += ["-metadata", f"comment={keywords_str}"]
    ffmpeg_params += ["-movflags", "+faststart"]

    return ffmpeg_params


# ----------------- DUAL OPPOSING SCROLLING CLASS -----------------
class DualOpposingScrollingVideo:
    def __init__(self, image_dir, output,
                 video_size=(1080, 1920),
                 fps=30,
                 scroll_speed=150,
                 image_corner_radius=20):

        self.image_dir = image_dir
        self.output = output
        self.VIDEO_W, self.VIDEO_H = video_size
        self.FPS = fps
        self.SCROLL_SPEED = scroll_speed
        self.image_corner_radius = image_corner_radius
        self.half_w = self.VIDEO_W // 2

        # Gather and sort images by filename
        paths = [
            os.path.join(image_dir, f)
            for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        self.image_paths = sorted(paths, key=lambda p: os.path.basename(p))

        if not self.image_paths:
            raise ValueError(f"No image files (.jpg, .jpeg, .png) found in: {image_dir}")

        all_frames = self.load_resize_frames()
        
        # Split images: Even index to Left column, Odd index to Right column
        self.left_frames = all_frames[0::2]
        self.right_frames = all_frames[1::2] if len(all_frames) > 1 else all_frames[0::2]

        self.left_total_h = sum(f.shape[0] for f in self.left_frames)
        self.right_total_h = sum(f.shape[0] for f in self.right_frames)

        # Set duration based on max distance required to scroll through images
        max_dist = max(
            max(self.left_total_h - self.VIDEO_H, 0),
            max(self.right_total_h - self.VIDEO_H, 0)
        )
        self.DURATION = max(max_dist / self.SCROLL_SPEED, len(all_frames) * 0.5)

    def load_resize_frames(self):
        frames = []
        target_w = self.half_w

        for p in self.image_paths:
            img = Image.open(p)
            img = ImageOps.exif_transpose(img)

            w, h = img.size
            scale = target_w / w
            new_w, new_h = target_w, int(h * scale)

            img = img.resize((new_w, new_h), Image.LANCZOS)

            # Rounded corners mask
            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0, 0, img.width, img.height],
                                   radius=self.image_corner_radius, fill=255)
            img.putalpha(mask)

            frame = np.array(img.convert("RGB"))
            frames.append(frame)

        return frames

    def render_column(self, canvas, frames, total_h, t, x_offset, direction="up"):
        if direction == "up":
            scroll_pos = -int(self.SCROLL_SPEED * t)
        else:  # "down"
            scroll_pos = int(self.SCROLL_SPEED * t) - total_h + self.VIDEO_H

        col_w = self.half_w

        for img in frames:
            h = img.shape[0]
            top, bottom = scroll_pos, scroll_pos + h

            if bottom <= 0:
                scroll_pos += h
                continue
            if top >= self.VIDEO_H:
                break

            vtop, vbottom = max(top, 0), min(bottom, self.VIDEO_H)
            crop_top = max(0, -top)
            crop_bottom = h - max(0, bottom - self.VIDEO_H)

            slice_img = img[crop_top:crop_bottom, :, :]
            canvas[vtop:vbottom, x_offset:x_offset + col_w] = slice_img

            scroll_pos += h

    def make_frame(self, t):
        canvas = np.zeros((self.VIDEO_H, self.VIDEO_W, 3), dtype=np.uint8)

        # 1. Left Column -> Scroll UP
        self.render_column(
            canvas, self.left_frames, self.left_total_h, t,
            x_offset=0, direction="up"
        )

        # 2. Right Column -> Scroll DOWN
        self.render_column(
            canvas, self.right_frames, self.right_total_h, t,
            x_offset=self.half_w, direction="down"
        )

        # 3. Film Reel Overlay with center division
        overlay = create_film_reel_overlay(self.VIDEO_W, self.VIDEO_H, t, self.SCROLL_SPEED)
        return np.array(Image.alpha_composite(Image.fromarray(canvas).convert("RGBA"), overlay).convert("RGB"))

    def render(self, audio_path):
        audio = AudioFileClip(audio_path)
        try:
            if audio.duration > self.DURATION:
                audio = audio_subclip(audio, 0, self.DURATION)
            else:
                audio = loop_audio_to_duration(audio, self.DURATION)

            video = VideoClip(self.make_frame, duration=self.DURATION)
            video.audio = audio
            ffmpeg_params = get_metadata_params()

            os.makedirs(os.path.dirname(self.output), exist_ok=True)

            video.write_videofile(
                self.output,
                fps=self.FPS,
                codec="libx264",
                audio_codec="aac",
                ffmpeg_params=ffmpeg_params
            )
        finally:
            audio.close()


# ----------------- EXECUTION -----------------
if __name__ == "__main__":
    project = "01_images_processing"
    os.makedirs(f"{project}/videos", exist_ok=True)
    os.makedirs(f"{project}/audios", exist_ok=True)

    img_dir = r'C:\Users\ravik\Downloads\cleaned_photos\output\1_images_portrait'
    output = r'C:\Users\ravik\Downloads\cleaned_photos\output\1_images_portrait.mp4'
    audio_path = f"{project}/audios/s6.webm"

    video = DualOpposingScrollingVideo(
        image_dir=img_dir,
        output=output,
        video_size=(1080, 1920),
        fps=30,
        scroll_speed=250,
        image_corner_radius=20
    )

    video.render(audio_path=audio_path)