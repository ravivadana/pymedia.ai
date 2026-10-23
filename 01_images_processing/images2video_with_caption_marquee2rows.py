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
    sr = getattr(audio, "fps", 44100)
    arr = audio.to_soundarray(fps=sr)
    total_samples = arr.shape[0]
    duration = audio.duration
    start_sample = int(start / duration * total_samples)
    end_sample = int(end / duration * total_samples)
    sub_arr = arr[start_sample:end_sample]
    return AudioArrayClip(sub_arr, fps=sr)


def loop_audio_to_duration(audio, target):
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
def estimate_caption_height(vh):
    return int(vh * 0.03) + 12


def get_dominant_color(frame, sample=10):
    small = Image.fromarray(frame).resize((sample, sample))
    pixels = list(small.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)


def draw_caption(frame, text, alpha, vw, vh, rect_color, rect_y):
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))

    font_size = int(vh * 0.03)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    draw_temp = ImageDraw.Draw(overlay)
    bbox = draw_temp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    padding_x, padding_top, padding_bottom = 12, 6, 20
    rect_w = tw + 2 * padding_x
    rect_h = th + padding_top + padding_bottom
    rect_x0 = (vw - rect_w) // 2
    rect_y0 = rect_y
    rect_x1, rect_y1 = rect_x0 + rect_w, rect_y0 + rect_h
    corner_radius, border_width = 12, 3

    r, g, b = rect_color

    gradient = Image.new("RGBA", (rect_w, rect_h), color=0)
    for y in range(rect_h):
        a = int(220 * alpha)
        r_grad = max(0, min(255, r - int(30 * y / rect_h)))
        g_grad = max(0, min(255, g - int(30 * y / rect_h)))
        b_grad = max(0, min(255, b - int(30 * y / rect_h)))
        for x in range(rect_w):
            gradient.putpixel((x, y), (r_grad, g_grad, b_grad, a))

    overlay.paste(gradient, (rect_x0, rect_y0), gradient)

    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        [(rect_x0, rect_y0), (rect_x1, rect_y1)],
        radius=corner_radius,
        outline=(255, 255, 255, int(255 * alpha)),
        width=border_width
    )

    draw.text(
        (rect_x0 + padding_x, rect_y0 + padding_top),
        text,
        font=font,
        fill=(255, 255, 255, int(255 * alpha))
    )

    return np.array(Image.alpha_composite(img, overlay).convert("RGB"))


def create_two_row_film_reel_overlay(vw, vh, t, scroll_speed, direction="left"):
    """Draws horizontal film reel perforations for a two-row scrolling layout."""
    overlay = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bar_thickness = 30
    spacing = 36
    pulse = int(150 + 50 * math.sin(t * 3))
    
    offset = int((scroll_speed * t * 0.5) % spacing)
    if direction == "left":
        offset = -offset

    y_positions = [0, (vh // 2) - (bar_thickness // 2), vh - bar_thickness]

    for y_top in y_positions:
        draw.rectangle([0, y_top, vw, y_top + bar_thickness], fill=(0, 0, 0, 120))
        for x in range(-spacing + offset, vw + spacing, spacing):
            draw.rectangle(
                [x - 6, y_top + (bar_thickness // 2) - 8, x + 6, y_top + (bar_thickness // 2) + 8],
                fill=(255, 255, 255, pulse)
            )

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


# ----------------- HORIZONTAL TWO-ROW SCROLLING VIDEO CLASS -----------------
class TwoRowHorizontalScrollingVideo:
    def __init__(self, image_dir, output,
                 video_size=(1080, 1920),
                 fps=30,
                 scroll_speed=250,
                 image_corner_radius=20,
                 direction="left",
                 caption="none",
                 enable_face_detect=False):

        self.image_dir = image_dir
        self.output = output
        self.VIDEO_W, self.VIDEO_H = video_size
        self.FPS = fps
        self.SCROLL_SPEED = scroll_speed
        self.image_corner_radius = image_corner_radius
        self.caption_type = caption
        self.direction = direction.lower()
        self.enable_face_detect = enable_face_detect

        paths = [
            os.path.join(image_dir, f)
            for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        self.image_paths = sorted(paths, key=lambda p: os.path.basename(p))

        if self.caption_type == "filename":
            self.image_caption = [get_image_file_name(p) for p in self.image_paths]
        else:
            self.image_caption = [os.path.basename(p) for p in self.image_paths]

        # Process frames into two horizontal rows
        self.rows_frames, self.rows_colors, self.row_lengths = self.load_resize_two_rows()

        max_row_length = max(self.row_lengths)
        scroll_dist = max(max_row_length - self.VIDEO_W, 0)
        self.DURATION = max(scroll_dist / self.SCROLL_SPEED, 5.0)

    def load_resize_two_rows(self):
        """Resizes images to fit exactly half video height and alternates them between Row 0 and Row 1."""
        target_height = self.VIDEO_H // 2
        
        rows_frames = [[], []]
        rows_colors = [[], []]
        row_lengths = [0, 0]

        for i, p in enumerate(self.image_paths):
            row_idx = i % 2  # Alternate between Top Row (0) and Bottom Row (1)
            
            img = Image.open(p)
            img = ImageOps.exif_transpose(img)

            w, h = img.size
            scale = target_height / h
            new_w, new_h = int(w * scale), target_height

            img = img.resize((new_w, new_h), Image.LANCZOS)

            # Mask for rounded corners
            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0, 0, img.width, img.height],
                                   radius=self.image_corner_radius, fill=255)
            img.putalpha(mask)

            frame = np.array(img.convert("RGB"))
            rows_frames[row_idx].append(frame)
            rows_colors[row_idx].append(get_dominant_color(frame))
            row_lengths[row_idx] += new_w

        return rows_frames, rows_colors, row_lengths

    def make_frame(self, t):
        canvas = np.zeros((self.VIDEO_H, self.VIDEO_W, 3), dtype=np.uint8)

        # Calculate horizontal scroll position
        if self.direction == "left":
            base_scroll_pos = -int(self.SCROLL_SPEED * t)
        else:  # right
            max_len = max(self.row_lengths)
            base_scroll_pos = int(self.SCROLL_SPEED * t) - max_len + self.VIDEO_W

        # Render top row (row_idx = 0) and bottom row (row_idx = 1)
        for row_idx in range(2):
            y_offset = row_idx * (self.VIDEO_H // 2)
            scroll_pos = base_scroll_pos

            for i, img in enumerate(self.rows_frames[row_idx]):
                w = img.shape[1]
                left, right = scroll_pos, scroll_pos + w

                # Off-screen skip
                if right <= 0:
                    scroll_pos += w
                    continue
                if left >= self.VIDEO_W:
                    break

                vleft, vright = max(left, 0), min(right, self.VIDEO_W)
                crop_left = max(0, -left)
                crop_right = w - max(0, right - self.VIDEO_W)

                slice_img = img[:, crop_left:crop_right, :]
                canvas[y_offset:y_offset + (self.VIDEO_H // 2), vleft:vright] = slice_img

                scroll_pos += w

        overlay = create_two_row_film_reel_overlay(self.VIDEO_W, self.VIDEO_H, t, self.SCROLL_SPEED, self.direction)
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


# ----------------- RUN -----------------
if __name__ == "__main__":
    project = "01_images_processing"
    os.makedirs(f"{project}/videos", exist_ok=True)
    
    # Set horizontal scroll direction ("left" or "right")
    direction = "left" 
    img_dir = r'C:\Users\ravik\Downloads\all'
    output = r'C:\Users\ravik\Downloads\all_2rows.mp4'
    audio_path = f"{project}/audios/s6.webm"

    video = TwoRowHorizontalScrollingVideo(
        image_dir=img_dir,
        output=output,
        video_size=(1080, 1920),
        fps=30,
        scroll_speed=300,
        direction=direction,
        caption="none",
        enable_face_detect=False
    )

    audio_file = audio_path if os.path.exists(audio_path) else f"{project}/audios/song4.mp4"
    video.render(audio_path=audio_file)