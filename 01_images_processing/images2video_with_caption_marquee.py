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


# ----------------- FILENAME & DATE HELPERS -----------------
def get_image_file_name(path):
    filename = os.path.basename(path)
    filename = os.path.splitext(filename)[0]
    
    parts = filename.split('_')
    if len(parts) > 1:
        clean_keyword = re.sub(r'\d+', '', parts[1]).strip()
        if clean_keyword:
            dynamic_keywords.append(f'#{clean_keyword}')
            
    # Remove digits, replace underscores with spaces, and convert to Title Case
    clean_name = re.sub(r'\d+', '', filename)
    clean_name = clean_name.replace('_', ' ')
    caption = ' '.join(word.capitalize() for word in clean_name.split())
    return caption


def get_image_date(path):
    """Extracts date taken from EXIF metadata, falls back to file modification time."""
    try:
        with Image.open(path) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        return dt.strftime('%B %d, %Y')
    except Exception:
        pass
    
    mtime = os.path.getmtime(path)
    return datetime.fromtimestamp(mtime).strftime('%B %d, %Y')


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


def create_film_reel_overlay(vw, vh, t, scroll_speed, direction="up"):
    overlay = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bar_thickness = 40
    spacing = 36
    pulse = int(150 + 50 * math.sin(t * 3))
    offset = int((scroll_speed * t * 0.5) % spacing)
    
    # If images scroll "up" or "right", make the reel overlay move in the opposite direction
    if direction in ("up", "right"):
        offset = -offset

    if direction in ("up", "down"):
        draw.rectangle([0, 0, bar_thickness, vh], fill=(0, 0, 0, 120))
        draw.rectangle([vw - bar_thickness, 0, vw, vh], fill=(0, 0, 0, 120))
        for y in range(-spacing + offset, vh + spacing, spacing):
            draw.rectangle([bar_thickness // 2 - 12, y - 8, bar_thickness // 2 + 12, y + 8], fill=(255, 255, 255, pulse))
            draw.rectangle([vw - bar_thickness // 2 - 12, y - 8, vw - bar_thickness // 2 + 12, y + 8], fill=(255, 255, 255, pulse))
    else:
        draw.rectangle([0, 0, vw, bar_thickness], fill=(0, 0, 0, 120))
        draw.rectangle([0, vh - bar_thickness, vw, vh], fill=(0, 0, 0, 120))
        for x in range(-spacing + offset, vw + spacing, spacing):
            draw.rectangle([x - 8, bar_thickness // 2 - 12, x + 8, bar_thickness // 2 + 12], fill=(255, 255, 255, pulse))
            draw.rectangle([x - 8, vh - bar_thickness // 2 - 12, x + 8, vh - bar_thickness // 2 + 12], fill=(255, 255, 255, pulse))
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


# ----------------- SCROLLING VIDEO CLASS -----------------
class NoGapScrollingVideo:
    def __init__(self, image_dir, output,
                 video_size=(1080, 1920),
                 fps=30,
                 scroll_speed=250,
                 image_corner_radius=30,
                 direction="up",
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
        elif self.caption_type == "date":
            self.image_caption = [get_image_date(p) for p in self.image_paths]
        else:
            self.image_caption = [os.path.basename(p) for p in self.image_paths]

        self.frames, self.colors, self.face_centers = self.load_resize_frames()

        if self.direction in ("up", "down"):
            self.total_length = sum(f.shape[0] for f in self.frames)
            visible = self.VIDEO_H
        else:
            self.total_length = sum(f.shape[1] for f in self.frames)
            visible = self.VIDEO_W

        scroll_dist = max(self.total_length - visible, 0)
        self.DURATION = max(scroll_dist / self.SCROLL_SPEED, len(self.frames) * 0.5)

    def load_resize_frames(self):
        frames, colors, face_centers = [], [], []
        valid_paths, valid_captions = [], []
        
        is_vertical = self.direction in ("up", "down")
        target_side = self.VIDEO_W if is_vertical else self.VIDEO_H
        max_side = int(self.VIDEO_H * 1.4) if is_vertical else int(self.VIDEO_W * 1.4)

        for i, p in enumerate(self.image_paths):
            try:
                img = Image.open(p)
                img = ImageOps.exif_transpose(img)

                w, h = img.size
                if is_vertical:
                    scale = target_side / w
                    new_w, new_h = target_side, int(h * scale)
                    if new_h > max_side:
                        new_h = max_side
                else:
                    scale = target_side / h
                    new_w, new_h = int(w * scale), target_side
                    if new_w > max_side:
                        new_w = max_side

                img = img.resize((new_w, new_h), Image.LANCZOS)

                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle([0, 0, img.width, img.height],
                                     radius=self.image_corner_radius, fill=255)
                img.putalpha(mask)

                frame = np.array(img.convert("RGB"))
                frames.append(frame)
                colors.append(get_dominant_color(frame))
                if self.enable_face_detect:
                    face_centers.append(get_face_center(frame))
                else:
                    face_centers.append((new_w // 2, new_h // 2))

                valid_paths.append(p)
                valid_captions.append(self.image_caption[i])
            except Exception:
                continue

        if not frames:
            raise ValueError("No valid images could be loaded from the directory!")

        self.image_paths = valid_paths
        self.image_caption = valid_captions

        return frames, colors, face_centers

    def get_contrasting_color(self, rgb):
        r, g, b = rgb
        brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return (0, 0, 0) if brightness > 0.5 else (255, 255, 255)

    def make_frame(self, t):
        canvas = np.zeros((self.VIDEO_H, self.VIDEO_W, 3), dtype=np.uint8)
        
        if self.direction == "up":
            scroll_pos = -int(self.SCROLL_SPEED * t)
        elif self.direction == "down":
            scroll_pos = int(self.SCROLL_SPEED * t) - self.total_length + self.VIDEO_H
        elif self.direction == "left":
            scroll_pos = -int(self.SCROLL_SPEED * t)
        elif self.direction == "right":
            scroll_pos = int(self.SCROLL_SPEED * t) - self.total_length + self.VIDEO_W

        for i, img in enumerate(self.frames):
            if self.direction in ("up", "down"):
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
                canvas[vtop:vbottom, 0:self.VIDEO_W] = slice_img

                if self.caption_type != "none":
                    cap_h = estimate_caption_height(self.VIDEO_H)
                    alpha = min(1.0, (vbottom - vtop) / h * 1.5)
                    contrast_color = self.get_contrasting_color(self.colors[i])
                    canvas = draw_caption(canvas, self.image_caption[i], alpha,
                                          self.VIDEO_W, self.VIDEO_H, contrast_color,
                                          vbottom - cap_h - 10)

                scroll_pos += h

            else:  # left or right
                w = img.shape[1]
                left, right = scroll_pos, scroll_pos + w
                
                if right <= 0:
                    scroll_pos += w
                    continue
                if left >= self.VIDEO_W:
                    break

                vleft, vright = max(left, 0), min(right, self.VIDEO_W)
                crop_left = max(0, -left)
                crop_right = w - max(0, right - self.VIDEO_W)
                
                slice_img = img[:, crop_left:crop_right, :]
                canvas[0:self.VIDEO_H, vleft:vright] = slice_img

                scroll_pos += w

        overlay = create_film_reel_overlay(self.VIDEO_W, self.VIDEO_H, t, self.SCROLL_SPEED, self.direction)
        return np.array(Image.alpha_composite(Image.fromarray(canvas).convert("RGBA"), overlay).convert("RGB"))

    def render(self, audio_path=None):
        audio = None
        try:
            video = VideoClip(self.make_frame, duration=self.DURATION)
            
            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                if audio.duration > self.DURATION:
                    audio = audio_subclip(audio, 0, self.DURATION)
                else:
                    audio = loop_audio_to_duration(audio, self.DURATION)
                video.audio = audio

            ffmpeg_params = get_metadata_params()
            os.makedirs(os.path.dirname(self.output), exist_ok=True)

            video.write_videofile(
                self.output, 
                fps=self.FPS, 
                codec="libx264", 
                audio_codec="aac" if audio else None,
                ffmpeg_params=ffmpeg_params
            )
        finally:
            if audio is not None:
                audio.close()


# ----------------- RUN -----------------
if __name__ == "__main__":
    project = "01_images_processing"
    os.makedirs(f"{project}/videos", exist_ok=True)
    direction = "up"
    img_dir = r'C:\Ravi\Python\2025\Media\01_images_processing\images'
    output = r'C:\Ravi\Python\2025\Media\01_images_processing\videos\AKHI_NANNA_HAPPY_BIRTH_DAY_WORK_HARD_LOOK_AT_HUMANITY_PROBLEMS_STAY_WELL_RESPECT_EVERY_ONE.mp4'
    audio_path = r'C:\Ravi\Python\2025\Media\01_images_processing\images\AKHI_NANNA_HAPPY_BIRTH_DAY_WORK_HARD_LOOK_AT_HUMANITY_PROBLEMS_STAY_WELL_RESPECT_EVERY_ONE.mov'  # Path to your audio file

    video = NoGapScrollingVideo(
        image_dir=img_dir,
        output=output,
        video_size=(1080,1920),
        fps=30,
        scroll_speed=150,
        direction=direction,
        caption="filename",
        enable_face_detect=False
    )

    # Render with the stitched audio file
    video.render(audio_path=audio_path)