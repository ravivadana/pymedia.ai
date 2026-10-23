from moviepy import VideoClip, AudioFileClip, concatenate_audioclips
import numpy as np
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ExifTags, ImageOps
import re
import math
import cv2

# ----------------- VERSION SAFE AUDIO SUBCLIP -----------------
def audio_subclip(audio, start, end):
    if hasattr(audio, "subclip"):
        return audio.subclip(start, end)
    return audio.subclipped(start, end)

# ----------------- DATE HELPERS -----------------
def get_image_date(path):
    filename = os.path.basename(path)
    match = re.search(r'(\d{14})', filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        except:
            pass
    try:
        img = Image.open(path)
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if ExifTags.TAGS.get(tag) == "DateTimeOriginal":
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except:
        pass
    return datetime.fromtimestamp(os.path.getctime(path))
def get_image_file_name(path):
    filename = os.path.basename(path)
    filename= os.path.splitext(filename)[0]
    filename=filename.replace("_","#")
    return filename
def get_image_file_index(path):
    filename = os.path.basename(path)
    return filename[:2]
# ----------------- HELPERS -----------------
def estimate_caption_height(vh):
    return int(vh * 0.03) + 12

def get_dominant_color(frame, sample=10):
    small = Image.fromarray(frame).resize((sample, sample))
    pixels = list(small.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)

import random

def draw_caption(frame, text, alpha, vw, vh, rect_color, rect_y):
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))

    font_size = int(vh * 0.03)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    draw_temp = ImageDraw.Draw(overlay)
    bbox = draw_temp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    padding_x = 12
    padding_top = 6
    padding_bottom = 20
    rect_w = tw + 2 * padding_x
    rect_h = th + padding_top + padding_bottom
    rect_x0 = (vw - rect_w) // 2
    rect_y0 = rect_y
    rect_x1, rect_y1 = rect_x0 + rect_w, rect_y0 + rect_h
    corner_radius = 12
    border_width = 3

    # --- Use the color passed in rect_color ---
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

# ----------------- FILM REEL OVERLAY -----------------
def create_film_reel_overlay(vw, vh, t, scroll_speed):
    overlay = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_width = 40
    rect_w, rect_h = 24, 16
    spacing = 36

    draw.rectangle([0, 0, bar_width, vh], fill=(0, 0, 0, 120))
    draw.rectangle([vw - bar_width, 0, vw, vh], fill=(0, 0, 0, 120))

    pulse = int(150 + 50 * math.sin(t * 3))
    offset = int((scroll_speed * t * 0.5) % spacing)

    for y in range(-spacing + offset, vh + spacing, spacing):
        draw.rectangle(
            [bar_width // 2 - rect_w // 2, y - rect_h // 2,
             bar_width // 2 + rect_w // 2, y + rect_h // 2],
            fill=(255, 255, 255, pulse),
        )
        draw.rectangle(
            [vw - bar_width // 2 - rect_w // 2, y - rect_h // 2,
             vw - bar_width // 2 + rect_w // 2, y + rect_h // 2],
            fill=(255, 255, 255, pulse),
        )
    return overlay

# ----------------- FACE DETECTION -----------------
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def get_face_center(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
    if len(faces) == 0:
        h, w, _ = img.shape
        return w // 2, h // 2
    x, y, w_f, h_f = faces[0]
    return x + w_f // 2, y + h_f // 2

# ----------------- AUDIO LOOP -----------------
def loop_audio_to_duration(audio, target):
    clips, total = [], 0
    while total < target:
        remaining = target - total
        if remaining < audio.duration:
            clips.append(audio_subclip(audio, 0, remaining))
            total += remaining
        else:
            clips.append(audio)
            total += audio.duration
    return concatenate_audioclips(clips)

# ----------------- SCROLLING VIDEO CLASS -----------------
class NoGapScrollingVideo:
    def __init__(self, image_dir, output,
                 video_size=(1080, 1920),
                 fps=30,
                 scroll_speed=250,
                 image_corner_radius=30,
                 caption="date"):

        self.image_dir = image_dir
        self.output = output
        self.VIDEO_W, self.VIDEO_H = video_size
        self.FPS = fps
        self.SCROLL_SPEED = scroll_speed
        self.image_corner_radius = image_corner_radius
        self.MAX_IMAGE_HEIGHT = int(self.VIDEO_H * 1.4)

        paths = [
            os.path.join(image_dir, f)
            for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        pairs = [(p, get_image_date(p)) for p in paths]
        if caption=="filename":
            pairs = [(p, get_image_file_name(p)) for p in paths]
        if caption=="index":
            pairs = [(p, get_image_file_index(p)) for p in paths]
        pairs.sort(key=lambda x: x[1])

        self.image_paths = [p for p, _ in pairs]
        if caption=="date":
            self.image_caption = [dt.strftime("%d %b %Y") for _, dt in pairs]
        else:
             self.image_caption = [dt for _, dt in pairs]

        self.frames, self.colors, self.face_centers = self.load_resize_frames()

        self.total_height = sum(f.shape[0] for f in self.frames)
        scroll_dist = max(self.total_height - self.VIDEO_H, 0)
        self.DURATION = max(scroll_dist / self.SCROLL_SPEED, 1)

    def load_resize_frames(self):
        frames, colors, face_centers = [], [], []
        for p in self.image_paths:
            img = Image.open(p)
            img = ImageOps.exif_transpose(img)

            w, h = img.size
            scale = self.VIDEO_W / w
            new_h = int(h * scale)
            if new_h > self.MAX_IMAGE_HEIGHT:
                scale = self.MAX_IMAGE_HEIGHT / h
                new_h = self.MAX_IMAGE_HEIGHT
            img = img.resize((self.VIDEO_W, new_h), Image.LANCZOS)

            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0, 0, img.width, img.height],
                                   radius=self.image_corner_radius, fill=255)
            img.putalpha(mask)

            frame = np.array(img.convert("RGB"))
            frames.append(frame)
            colors.append(get_dominant_color(frame))
            face_centers.append(get_face_center(frame))

        return frames, colors, face_centers
    def get_contrasting_color(self,rgb):
        r, g, b = rgb
        # Compute perceived brightness
        brightness = (0.299*r + 0.587*g + 0.114*b) / 255
        if brightness > 0.5:
            # Image is bright → use dark background
            return (0, 0, 0)
        else:
            # Image is dark → use bright background
            return (255, 255, 255)

    def make_frame(self, t):
        canvas = np.zeros((self.VIDEO_H, self.VIDEO_W, 3), dtype=np.uint8)
        scroll_pos = -int(self.SCROLL_SPEED * t)

        for i, img in enumerate(self.frames):
            h = img.shape[0]
            top, bottom = scroll_pos, scroll_pos + h
            if bottom <= 0:
                scroll_pos += h
                continue
            if top >= self.VIDEO_H:
                break

            vtop, vbottom = max(top, 0), min(bottom, self.VIDEO_H)
            slice_h = vbottom - vtop

            # Face-aware centering
            face_x, face_y = self.face_centers[i]
            y0 = max(0, face_y - slice_h // 2)
            y1_crop = y0
            y2_crop = min(h, y0 + slice_h)
            slice_img = img[y1_crop:y2_crop, :, :]

            # Fix broadcasting issue
            fade_alpha = slice_h / h
            slice_h_actual = min(slice_img.shape[0], vbottom - vtop)
            slice_img = slice_img[:slice_h_actual]
            canvas[vtop:vtop + slice_h_actual] = (
                slice_img * fade_alpha + canvas[vtop:vtop + slice_h_actual] * (1 - fade_alpha)
            ).astype(np.uint8)

            # Caption
            cap_h = estimate_caption_height(self.VIDEO_H)
            alpha = min(1.0, (vbottom - vtop) / h * 1.5)
            contrast_color = self.get_contrasting_color(self.colors[i])
            canvas = draw_caption(canvas, self.image_caption[i], alpha,
                                self.VIDEO_W, self.VIDEO_H, contrast_color,
                                vbottom - cap_h - 10)


            scroll_pos += h

        overlay = create_film_reel_overlay(self.VIDEO_W, self.VIDEO_H, t, self.SCROLL_SPEED)
        return np.array(Image.alpha_composite(Image.fromarray(canvas).convert("RGBA"), overlay).convert("RGB"))

    def render(self, audio_path):
        audio = AudioFileClip(audio_path)
        if audio.duration > self.DURATION:
            audio = audio_subclip(audio, 0, self.DURATION)
        else:
            audio = loop_audio_to_duration(audio, self.DURATION)

        video = VideoClip(self.make_frame, duration=self.DURATION)
        video.audio = audio
        video.write_videofile(self.output, fps=self.FPS, codec="libx264", audio_codec="aac")


# ----------------- RUN -----------------
if __name__ == "__main__":
    project = "01_images_processing"
    os.makedirs(f"{project}/videos", exist_ok=True)
    input_folder="2025_ranking"
    direction="up"  # up, down, left, right
    video = NoGapScrollingVideo(
        image_dir=f"01_images_processing/images/{input_folder}",
        output=f"01_images_processing/videos/{input_folder}_{direction}.mp4",
        video_size=(1080, 1920),
        fps=30,
        scroll_speed=550,
        caption="filename"
    )

    video.render(audio_path=f"{project}/audios/song.mp4")
