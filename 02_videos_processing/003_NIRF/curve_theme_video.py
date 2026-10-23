import json
import os
from pathlib import Path
import random
import textwrap
import shutil
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips

# =========================================================
# CONFIGURATION CLASS
# =========================================================
@dataclass
class VideoConfig:
    course_name: str = "management"
    year:int=2025
    json_file: str = field(init=False)
    output_mobile_video: str = field(init=False)
    
    video_width: int = 1080
    video_height: int = 540
    mobile_width: int = 1080
    mobile_height: int = 1920
    fps: int = 30
    slide_duration: float = 3.0
    scroll_speed: int = 5  # Pixels per frame step updates
    fade_duration: float = 0.8
    BASE_DIR = Path(__file__).resolve().parent
    temp_folder: str = f"{BASE_DIR}/outputs/images/slides"
    mobile_folder: str = f"{BASE_DIR}/outputs/images/slides_mobile"
    NIRF_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/nirf")
    file_name=f"NIRF_{course_name}_{year}_Ranking"
    input_file_name=f"{file_name}.json"
    output_file_name=f"{file_name}.mp4"
    json_file=NIRF_ASSETS / "data" / input_file_name
    output_mobile_video = BASE_DIR / "outputs/videos" / output_file_name
    
    # Expanded short-form production themes
    themes: List[Dict[str, Tuple[int, int, int]]] = field(default_factory=lambda: [
        {"bg1": (10, 24, 63), "bg2": (252, 70, 107)},     # Midnight Cyberpunk
        {"bg1": (15, 32, 39), "bg2": (32, 201, 151)},    # Electric Aurora
        {"bg1": (45, 3, 59), "bg2": (255, 110, 64)},     # Solar Flares
        {"bg1": (20, 20, 20), "bg2": (229, 9, 20)},      # Volcanic Magma
        {"bg1": (19, 12, 45), "bg2": (160, 32, 240)},    # Cosmic Violet
        {"bg1": (2, 16, 46), "bg2": (253, 184, 19)},     # Deep Ocean Gold
        {"bg1": (17, 17, 17), "bg2": (57, 255, 20)},     # Neon Matrix
        {"bg1": (123, 0, 41), "bg2": (0, 180, 216)},     # Royal Velvet
        {"bg1": (24, 28, 36), "bg2": (219, 0, 194)},     # Toxic Amethyst
        {"bg1": (11, 26, 21), "bg2": (0, 255, 163)},     # Deep Cyber Mint
        {"bg1": (28, 11, 0), "bg2": (255, 140, 0)},      # Retro Arcade
        {"bg1": (33, 37, 41), "bg2": (206, 212, 218)},   # Carbon Steel
        {"bg1": (14, 14, 24), "bg2": (0, 225, 255)},     # Deep Nebula
        {"bg1": (53, 0, 101), "bg2": (255, 214, 0)}      # Ultraviolet Eclipse
    ])

    font_paths: List[str] = field(default_factory=lambda: [
        "arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf",
        "arial.ttf", "C:/Windows/Fonts/arial.ttf"
    ])

   
# =========================================================
# VIDEO GENERATOR ENGINE CLASS
# =========================================================
class VideoGenerator:
    def __init__(self, config: VideoConfig):
        self.cfg = config
        self.fonts = {}
        self.data = []
        self.slide_paths = []
        self.mobile_images = []
        
        self._init_workspace()
        self._load_fonts()
        self._load_data()

    def _init_workspace(self):
        os.makedirs(self.cfg.temp_folder, exist_ok=True)
        os.makedirs(self.cfg.mobile_folder, exist_ok=True)
        os.makedirs(os.path.dirname(self.cfg.output_mobile_video), exist_ok=True)

    def _load_fonts(self):
        font_path = next((p for p in self.cfg.font_paths if os.path.exists(p)), None)
        font_sizes = {
            "rank": 72, "institute": 38, "score": 42,
            "label": 18, "address": 30, "intro": 80, "sub": 40
        }
        
        for key, size in font_sizes.items():
            try:
                self.fonts[key] = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
            except Exception:
                self.fonts[key] = ImageFont.load_default()

    def _load_data(self):
        with open(self.cfg.json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        print(f"Loaded {len(self.data)} records")

    @staticmethod
    def wrap_text(text: str, width: int = 18) -> str:
        return textwrap.fill(str(text), width=width)

    @staticmethod
    def draw_gradient(draw: ImageDraw.Draw, rect: Tuple[int, int, int, int], color1: Tuple[int, int, int], color2: Tuple[int, int, int]):
        x1, y1, x2, y2 = rect
        height = y2 - y1
        for y in range(height):
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(x1, y1 + y), (x2, y1 + y)], fill=(r, g, b))

    def create_title_slide(self, title: str, subtitle: str, output_path: str):
        theme = random.choice(self.cfg.themes)
        img = Image.new("RGB", (self.cfg.mobile_width, self.cfg.mobile_height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        card_width, card_height = 980, 1650
        card_x1 = (self.cfg.mobile_width - card_width) // 2
        card_y1 = 130
        card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
        radius = 70

        shadow = Image.new("RGBA", (self.cfg.mobile_width, self.cfg.mobile_height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([card_x1 + 12, card_y1 + 14, card_x2 + 12, card_y2 + 14], radius=radius, fill=(0, 0, 0, 70))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
        draw = ImageDraw.Draw(img)

        gradient_layer = Image.new("RGB", (self.cfg.mobile_width, self.cfg.mobile_height), (0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient_layer)
        self.draw_gradient(gradient_draw, (card_x1, card_y1, card_x2, card_y2), theme["bg1"], theme["bg2"])

        mask = Image.new("L", (self.cfg.mobile_width, self.cfg.mobile_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)
        img.paste(gradient_layer, (0, 0), mask)
        draw = ImageDraw.Draw(img)

        for i in range(6):
            offset = (i + 1) * 45
            draw.arc([card_x1 - 180, card_y1 - 80 + offset, card_x2 + 180, card_y1 + 260 + offset], start=0, end=180, fill=(255, 255, 255), width=8)

        wrapped_title = self.wrap_text(title, width=14)
        bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=self.fonts["intro"], spacing=28)
        tw = bbox[2] - bbox[0]
        draw.multiline_text(((self.cfg.mobile_width - tw) / 2, 760), wrapped_title, font=self.fonts["intro"], fill=(255, 255, 255), spacing=28, align="center")

        bbox = draw.multiline_textbbox((0, 0), subtitle, font=self.fonts["sub"], spacing=16)
        sw = bbox[2] - bbox[0]
        draw.multiline_text(((self.cfg.mobile_width - sw) / 2, 1220), subtitle, font=self.fonts["sub"], fill=(255, 255, 255), spacing=16, align="center")

        circle_radius, circle_x, circle_y = 120, self.cfg.mobile_width // 2, 520
        draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius], fill=(255, 255, 255))

        icon_text = "2025"
        bbox = draw.textbbox((0, 0), icon_text, font=self.fonts["rank"])
        iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((circle_x - iw / 2, circle_y - ih / 2 - 10), icon_text, font=self.fonts["rank"], fill=theme["bg1"])

        img.save(output_path)

    def generate_card_slides(self):
        last_theme_index = -1
        for index, item in enumerate(self.data):
            available_indices = [k for k in range(len(self.cfg.themes)) if k != last_theme_index]
            chosen_index = random.choice(available_indices)
            theme = self.cfg.themes[chosen_index]
            last_theme_index = chosen_index

            rank = item.get("Rank", "")
            if not rank:
                rank = index + 1
            try:
                rank = int(rank)
            except ValueError:
                rank = index + 1
                
            print(f"Creating slide card {rank}")

            img = Image.new("RGB", (self.cfg.video_width, self.cfg.video_height), (255, 255, 255))
            draw = ImageDraw.Draw(img)

            card_width, card_height = 940, 420
            card_x1 = (self.cfg.video_width - card_width) // 2
            card_y1 = 60
            card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
            radius = 60

            shadow = Image.new("RGBA", (self.cfg.video_width, self.cfg.video_height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.rounded_rectangle([card_x1 + 10, card_y1 + 12, card_x2 + 10, card_y2 + 12], radius=radius, fill=(0, 0, 0, 60))
            img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
            draw = ImageDraw.Draw(img)

            gradient_layer = Image.new("RGB", (self.cfg.video_width, self.cfg.video_height), (0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient_layer)
            self.draw_gradient(gradient_draw, (card_x1, card_y1, card_x2, card_y2), theme["bg1"], theme["bg2"])

            mask = Image.new("L", (self.cfg.video_width, self.cfg.video_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)
            img.paste(gradient_layer, (0, 0), mask)
            draw = ImageDraw.Draw(img)

            for i in range(5):
                offset = (i + 2) * 22
                draw.arc([card_x1 - 120, card_y1 - 40 + offset, card_x2 + 120, card_y1 + 180 + offset], start=0, end=180, fill=(255, 255, 255), width=6)

            draw.text((card_x1 + 75, card_y1 + 50), "RANK", font=self.fonts["label"], fill=(255, 255, 255))
            rank_text = str(rank)
            bbox = draw.textbbox((0, 0), rank_text, font=self.fonts["rank"])
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            padding = 18
            circle_radius = int(max(tw, th) / 2) + padding
            circle_x, circle_y = card_x1 + 105, card_y1 + 130

            draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius], fill=(255, 255, 255))
            draw.text((circle_x - tw / 2, circle_y - th / 2 - 14), rank_text, font=self.fonts["rank"], fill=theme["bg1"])

            draw.text((card_x1 + 35, card_y2 - 105), "SCORE", font=self.fonts["label"], fill=(255, 255, 255))
            score = str(item.get("Score", "N/A"))
            draw.text((card_x1 + 30, card_y2 - 70), score, font=self.fonts["score"], fill=(255, 255, 255))

            right_x = card_x1 + 300
            institute = self.wrap_text(item.get("Name", "Unknown Institute"), width=18)
            draw.multiline_text((right_x, card_y1 + 40), institute, font=self.fonts["institute"], fill=(255, 255, 255), spacing=6)

            city = item.get("City", "Unknown City")
            state = item.get("State", "Unknown State")
            address = self.wrap_text(f"{city}, {state}, India", width=32)
            draw.multiline_text((right_x, card_y2 - 80), address, font=self.fonts["address"], fill=(255, 255, 255), spacing=4)

            slide_path = os.path.join(self.cfg.temp_folder, f"slide_{rank:03d}_{index}.png")
            img.save(slide_path)
            self.slide_paths.append(slide_path)

    def build_mobile_composites(self):
        print("\nCreating mobile canvas composites...")
        card_width, card_height = 980, 420
        top_margin, gap = 40, 20
        canvas_content_height = top_margin + (4 * (card_height + gap)) - gap + top_margin

        group_index = 1
        for i in range(0, len(self.slide_paths), 4):
            group = self.slide_paths[i:i + 4]
            current_canvas_height = self.cfg.mobile_height if (i + 4 >= len(self.slide_paths)) else canvas_content_height
            mobile_canvas = Image.new("RGB", (self.cfg.mobile_width, current_canvas_height), (255, 255, 255))

            for idx, slide_path in enumerate(group):
                card_img = Image.open(slide_path).convert("RGB").resize((card_width, card_height))
                x = (self.cfg.mobile_width - card_width) // 2
                y = top_margin + idx * (card_height + gap)
                mobile_canvas.paste(card_img, (x, y))

            output_path = os.path.join(self.cfg.mobile_folder, f"{group_index:03d}_mobile.png")
            mobile_canvas.save(output_path)
            group_index += 1

        intro_image = os.path.join(self.cfg.mobile_folder, "000_intro.png")
        end_image = os.path.join(self.cfg.mobile_folder, "999_end.png")
        self.create_title_slide("NIRF Medical College Ranking 2025", "Top Medical Institutes in India", intro_image)
        self.create_title_slide("Thank You", "Please Subscribe Channel\nFor More Videos", end_image)

        self.mobile_images = sorted([
            os.path.join(self.cfg.mobile_folder, f)
            for f in os.listdir(self.cfg.mobile_folder)
            if f.endswith(".png") and not (f.startswith("000_") or f.startswith("999_"))
        ])

    def compile_video(self):
        print("\nCompiling Video Track via Stream-Optimized Scroll Engine...")
        total_scroll_height = 0
        canvas_positions = []

        for p in self.mobile_images:
            with Image.open(p) as img_obj:
                canvas_positions.append(total_scroll_height)
                total_scroll_height += img_obj.height

        long_canvas = Image.new("RGB", (self.cfg.mobile_width, total_scroll_height), (255, 255, 255))
        for idx, p in enumerate(self.mobile_images):
            with Image.open(p) as img_obj:
                long_canvas.paste(img_obj.convert("RGB"), (0, canvas_positions[idx]))

        last_list_viewport = long_canvas.crop((0, total_scroll_height - self.cfg.mobile_height, self.cfg.mobile_width, total_scroll_height))
        last_list_np = np.array(last_list_viewport)

        total_scroll_pixels = total_scroll_height - self.cfg.mobile_height
        scroll_duration = total_scroll_pixels / (self.cfg.scroll_speed * self.cfg.fps)

        intro_image_path = os.path.join(self.cfg.mobile_folder, "000_intro.png")
        end_image_path = os.path.join(self.cfg.mobile_folder, "999_end.png")
        
        intro_clip = ImageClip(intro_image_path).with_duration(3.5)
        end_clip = ImageClip(end_image_path).with_duration(4.0)

        def scroll_frame_processor(get_frame, t):
            current_y = min(int(t * self.cfg.fps * self.cfg.scroll_speed), total_scroll_pixels)
            viewport = long_canvas.crop((0, current_y, self.cfg.mobile_width, current_y + self.cfg.mobile_height))
            return np.array(viewport)

        scroll_base = ImageClip(last_list_np).with_duration(scroll_duration)
        scroll_clip = scroll_base.transform(scroll_frame_processor, apply_to=[])

        end_np = np.array(Image.open(end_image_path).convert("RGB"))

        def fade_frame_processor(get_frame, t):
            alpha = min(max(t / self.cfg.fade_duration, 0.0), 1.0)
            blended = np.clip((last_list_np * (1.0 - alpha) + end_np * alpha), 0, 255).astype(np.uint8)
            return blended

        fade_base = ImageClip(last_list_np).with_duration(self.cfg.fade_duration)
        fade_clip = fade_base.transform(fade_frame_processor, apply_to=[])

        final_video = concatenate_videoclips([intro_clip, scroll_clip, fade_clip, end_clip], method="chain")
        print(f"Rendering track to file: {self.cfg.output_mobile_video}...")
        
        final_video.write_videofile(
            self.cfg.output_mobile_video,
            fps=self.cfg.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger="bar"
        )

        # Teardown internal structures safely
        final_video.close()
        intro_clip.close()
        scroll_clip.close()
        fade_clip.close()
        end_clip.close()
        long_canvas.close()
        last_list_viewport.close()

    def cleanup(self):
        print("\nCleaning temporary folders...")
        for folder in [self.cfg.temp_folder, self.cfg.mobile_folder]:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
                print(f"Deleted: {folder}")
        print("\n======================================")
        print("FINAL VIDEO CREATED SUCCESSFULLY")
        print(self.cfg.output_mobile_video)
        print("TEMP FILES CLEANED")
        print("======================================")


# =========================================================
# MAIN EXECUTION ENTRY POINT
# =========================================================
if __name__ == "__main__":
    # 1. Instantiate Configuration Object
    config_setup = VideoConfig(course_name="management",year=2025)
    
    # 2. Build Generator System Instance
    generator = VideoGenerator(config=config_setup)
    
    try:
        # 3. Streamlined Pipeline Execution Stages
        generator.generate_card_slides()
        generator.build_mobile_composites()
        generator.compile_video()
    finally:
        # 4. Strict workspace footprint management guaranteed execution
        generator.cleanup()