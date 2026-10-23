import os
import json
import sys
import re
import random
import textwrap
import shutil
import unicodedata
import subprocess
import numpy as np
import cv2
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
from config import Config

# =====================================================================
# PART 1: PREMIUM IMAGE GENERATOR
# =====================================================================
class PremiumImageGenerator:
    """Handles parsing dataset metrics, pulling local country/logo assets,
    and generating clean high-fidelity mobile static slides.
    """
    THEMES = [
        {"bg1": (255, 236, 210), "bg2": (252, 182, 159)},
        {"bg1": (212, 252, 242), "bg2": (150, 230, 210)},
        {"bg1": (230, 242, 255), "bg2": (180, 210, 255)},
        {"bg1": (254, 211, 252), "bg2": (253, 161, 234)},
        {"bg1": (255, 243, 195), "bg2": (255, 213, 115)},
        {"bg1": (224, 255, 210), "bg2": (163, 235, 140)},
        {"bg1": (243, 231, 255), "bg2": (211, 181, 255)},
        {"bg1": (255, 222, 222), "bg2": (255, 164, 164)},
        {"bg1": (206, 246, 253), "bg2": (132, 220, 238)},
        {"bg1": (255, 237, 188), "bg2": (253, 202, 131)},
        {"bg1": (225, 253, 200), "bg2": (175, 235, 210)},
        {"bg1": (240, 240, 245), "bg2": (200, 205, 220)},
        {"bg1": (255, 225, 240), "bg2": (255, 170, 210)},
        {"bg1": (215, 255, 225), "bg2": (160, 230, 190)},
    ]

    def __init__(self, config):
        self.config = config
        self._initialize_workspace()
        self._load_typography()

    def _initialize_workspace(self):
        os.makedirs(self.config["temp_folder"], exist_ok=True)
        os.makedirs(self.config["mobile_folder"], exist_ok=True)

    def _load_typography(self):
        font_paths = [
            "arialbd.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        target_path = next((p for p in font_paths if os.path.exists(p)), None)
        try:
            self.fonts = {
                "rank": ImageFont.truetype(target_path, 50),
                "previous_rank": ImageFont.truetype(target_path, 22),
                "name": ImageFont.truetype(target_path, 34),
                "country": ImageFont.truetype(target_path, 30),
                "region": ImageFont.truetype(target_path, 26),
                "size": ImageFont.truetype(target_path, 24),
                "focus": ImageFont.truetype(target_path, 24),
                "research": ImageFont.truetype(target_path, 26),
                "status": ImageFont.truetype(target_path, 24),
                "overall_score": ImageFont.truetype(target_path, 44),
                "label": ImageFont.truetype(target_path, 18),
                "intro": ImageFont.truetype(target_path, 80),
                "sub": ImageFont.truetype(target_path, 40),
            }
        except Exception:
            default = ImageFont.load_default()
            self.fonts = {k: default for k in ["rank", "previous_rank", "name", "country", "region", "size", "focus", "research", "status", "overall_score", "label", "intro", "sub"]}

    def clean_name(self, name):
        if not name or str(name).strip().lower() == "nan":
            return ""
        name = str(name)
        name = re.sub(r"\(.*?\)", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = name.replace("’", "'").replace("`", "'").replace("“", '"').replace("”", '"')
        name = unicodedata.normalize("NFKD", name)
        name = "".join([c for c in name if not unicodedata.combining(c)])
        name = re.sub(r'[\\/:*?"<>|]', '', name)
        return " ".join(name.split()).strip()

    def wrap_text(self, text, width=18):
        return textwrap.fill(str(text), width=width)

    def get_rank(self, item, index):
        rank = item.get("Rank")
        if rank is None or rank == "":
            return index + 1
        return str(rank).strip().replace("=", "")

    def draw_gradient(self, draw, rect, color1, color2):
        x1, y1, x2, y2 = rect
        height = y2 - y1
        for y in range(height):
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(x1, y1 + y), (x2, y1 + y)], fill=(r, g, b))

    def draw_rank_indicator(self, draw, current_rank_str, prev_rank_val, x, y):
        def clean_to_int(rank_val):
            if not rank_val or str(rank_val).strip().lower() in ("nan", "n/a", ""):
                return None
            match = re.search(r"\d+", str(rank_val))
            return int(match.group()) if match else None

        curr_num = clean_to_int(current_rank_str)
        prev_num = clean_to_int(prev_rank_val)
        center_x = x + 65

        if curr_num is None or prev_num is None:
            draw.ellipse([center_x - 12, y + 4, center_x + 12, y + 28], fill=(100, 116, 139))
            draw.rectangle([center_x - 6, y + 14, center_x + 6, y + 18], fill=(255, 255, 255))
        elif curr_num < prev_num:
            draw.polygon([(center_x - 18, y + 16), (center_x, y - 4), (center_x + 18, y + 16)], fill=(22, 163, 74))
            draw.rectangle([(center_x - 8, y + 16), (center_x + 8, y + 34)], fill=(22, 163, 74))
        elif curr_num > prev_num:
            draw.polygon([(center_x - 18, y + 14), (center_x, y + 34), (center_x + 18, y + 14)], fill=(220, 38, 38))
            draw.rectangle([(center_x - 8, y - 4), (center_x + 8, y + 14)], fill=(220, 38, 38))

    def create_title_slide(self, title, subtitle, output_path):
        theme = random.choice(self.THEMES)
        img = Image.new("RGB", (self.config["mobile_width"], self.config["mobile_height"]), (252, 252, 253))
        draw = ImageDraw.Draw(img)

        card_width, card_height = 980, 1650
        card_x1 = (self.config["mobile_width"] - card_width) // 2
        card_y1 = 130
        card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
        radius = 70

        shadow = Image.new("RGBA", (self.config["mobile_width"], self.config["mobile_height"]), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([card_x1 + 12, card_y1 + 14, card_x2 + 12, card_y2 + 14], radius=radius, fill=(0, 0, 0, 35))
        img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
        draw = ImageDraw.Draw(img)

        gradient_layer = Image.new("RGB", (self.config["mobile_width"], self.config["mobile_height"]), (255, 255, 255))
        gradient_draw = ImageDraw.Draw(gradient_layer)
        self.draw_gradient(gradient_draw, (card_x1, card_y1, card_x2, card_y2), theme["bg1"], theme["bg2"])

        mask = Image.new("L", (self.config["mobile_width"], self.config["mobile_height"]), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)
        img.paste(gradient_layer, (0, 0), mask)
        draw = ImageDraw.Draw(img)

        text_color, secondary_text = (30, 41, 59), (71, 85, 105)

        for i in range(6):
            offset = (i + 1) * 45
            draw.arc([card_x1 - 180, card_y1 - 80 + offset, card_x2 + 180, card_y1 + 260 + offset], start=0, end=180, fill=(255, 255, 255, 130), width=6)

        wrapped_title = self.wrap_text(title, width=14)
        bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=self.fonts["intro"], spacing=28)
        tw = bbox[2] - bbox[0]
        draw.multiline_text(((self.config["mobile_width"] - tw) / 2, 760), wrapped_title, font=self.fonts["intro"], fill=text_color, spacing=28, align="center")

        bbox = draw.multiline_textbbox((0, 0), subtitle, font=self.fonts["sub"], spacing=16)
        sw = bbox[2] - bbox[0]
        draw.multiline_text(((self.config["mobile_width"] - sw) / 2, 1220), subtitle, font=self.fonts["sub"], fill=secondary_text, spacing=16, align="center")

        circle_radius, circle_x, circle_y = 120, self.config["mobile_width"] // 2, 520
        draw.ellipse([circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius], fill=text_color)

        icon_text = f"{self.config['year']}"
        bbox = draw.textbbox((0, 0), icon_text, font=self.fonts["rank"])
        iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((circle_x - iw / 2, circle_y - ih / 2 - 10), icon_text, font=self.fonts["rank"], fill=(255, 255, 255))

        img.save(output_path)

    def _find_country_asset(self, folder, country_name):
        if not os.path.exists(folder):
            return None
        cleaned_search = self.clean_name(country_name).lower().replace(" ", "_")
        extensions = [".png", ".jpg", ".jpeg", ".webp"]
        for file in os.listdir(folder):
            base, ext = os.path.splitext(file)
            if ext.lower() in extensions:
                cleaned_file = self.clean_name(base).lower().replace(" ", "_")
                if cleaned_search in cleaned_file or cleaned_file in cleaned_search:
                    return os.path.join(folder, file)
        return None

    def generate_images(self):
        if not os.path.exists(self.config["json_file"]):
            print(f"X Core Data file missing: {self.config['json_file']}")
            return

        with open(self.config["json_file"], "r", encoding="utf-8") as f:
            data = json.load(f)

        data = data[:self.config["top_number"]]
        print(f"Loaded and filtered precisely {len(data)} records for processing.")
        
        slide_paths = []
        used_theme_history = []

        for index, item in enumerate(data):
            available_indices = [k for k in range(len(self.THEMES)) if k not in used_theme_history]
            if not available_indices:
                available_indices = [k for k in range(len(self.THEMES))]

            chosen_right_index = random.choice(available_indices)
            right_theme = self.THEMES[chosen_right_index]
            chosen_left_index = random.choice([k for k in range(len(self.THEMES)) if k != chosen_right_index])
            left_theme = self.THEMES[chosen_left_index]

            used_theme_history.append(chosen_right_index)
            if len(used_theme_history) > 4:
                used_theme_history.pop(0)

            seq_val = item.get("Index", index + 1)
            try:
                sequence_str = f"{int(seq_val):03d}"
            except (ValueError, TypeError):
                sequence_str = f"{(index + 1):03d}"

            rank = self.get_rank(item, index)
            img = Image.new("RGB", (self.config["video_width"], self.config["video_height"]), (250, 250, 252))
            draw = ImageDraw.Draw(img)

            card_width, card_height = 940, 420
            card_x1 = (self.config["video_width"] - card_width) // 2
            card_y1 = 60
            card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
            radius, blade_width = 40, 180

            shadow = Image.new("RGBA", (self.config["video_width"], self.config["video_height"]), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.rounded_rectangle([card_x1 + 8, card_y1 + 10, card_x2 + 8, card_y2 + 10], radius=radius, fill=(15, 23, 42, 30))
            img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
            draw = ImageDraw.Draw(img)

            mask = Image.new("L", (self.config["video_width"], self.config["video_height"]), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=radius, fill=255)

            right_layer = Image.new("RGB", (self.config["video_width"], self.config["video_height"]), (255, 255, 255))
            right_draw = ImageDraw.Draw(right_layer)
            self.draw_gradient(right_draw, (card_x1 + blade_width, card_y1, card_x2, card_y2), right_theme["bg1"], right_theme["bg2"])
            img.paste(right_layer, (0, 0), mask)

            left_layer = Image.new("RGB", (self.config["video_width"], self.config["video_height"]), (255, 255, 255))
            left_draw = ImageDraw.Draw(left_layer)
            self.draw_gradient(left_draw, (card_x1, card_y1, card_x1 + blade_width, card_y2), left_theme["bg1"], left_theme["bg2"])
            img.paste(left_layer, (0, 0), mask)
            draw = ImageDraw.Draw(img)

            primary_text_color = (30, 41, 59)
            secondary_text_color = (71, 85, 105)
            score_highlight_color = (220, 38, 38)

            column_center_x = card_x1 + (blade_width // 2)
            max_allowed_width = blade_width - 20

            def get_dynamic_font(text_string, base_font_key):
                current_font = self.fonts[base_font_key]
                font_path = current_font.path
                current_size = current_font.size
                while current_size > 14:
                    test_font = ImageFont.truetype(font_path, current_size)
                    bbox = draw.textbbox((0, 0), text_string, font=test_font)
                    text_w = bbox[2] - bbox[0]
                    if text_w <= max_allowed_width:
                        return test_font
                    current_size -= 2
                return current_font

            label_1 = "RANK"
            bbox_l1 = draw.textbbox((0, 0), label_1, font=self.fonts["label"])
            l1_w = bbox_l1[2] - bbox_l1[0]
            draw.text((column_center_x - (l1_w // 2), card_y1 + 40), label_1, font=self.fonts["label"], fill=secondary_text_color)

            rank_text = f"#{rank}"
            dynamic_rank_font = get_dynamic_font(rank_text, "rank")
            bbox_r = draw.textbbox((0, 0), rank_text, font=dynamic_rank_font)
            rw = bbox_r[2] - bbox_r[0]
            draw.text((column_center_x - (rw // 2), card_y1 + 65), rank_text, font=dynamic_rank_font, fill=primary_text_color)

            prev_rank = item.get("Previous Rank", "N/A")
            self.draw_rank_indicator(draw, rank, prev_rank, x=column_center_x - 65, y=card_y1 + 155)

            label_2 = "PREV RANK"
            bbox_l2 = draw.textbbox((0, 0), label_2, font=self.fonts["label"])
            l2_w = bbox_l2[2] - bbox_l2[0]
            draw.text((column_center_x - (l2_w // 2), card_y1 + 225), label_2, font=self.fonts["label"], fill=secondary_text_color)

            prev_rank_text = f"#{prev_rank}"
            dynamic_prev_font = get_dynamic_font(prev_rank_text, "rank")
            bbox_pr = draw.textbbox((0, 0), prev_rank_text, font=dynamic_prev_font)
            prw = bbox_pr[2] - bbox_pr[0]
            draw.text((column_center_x - (prw // 2), card_y1 + 250), prev_rank_text, font=dynamic_prev_font, fill=primary_text_color)

            content_left_x = card_x1 + blade_width + 50
            raw_uni_name = item.get("Name", "Unknown Institution")
            uni_clean = self.clean_name(raw_uni_name)

            safe_target_base = uni_clean.replace(" ", "_").replace("'", "")
            target_file_prefix = f"{sequence_str}_{safe_target_base}"

            logo_extensions = [".png", ".jpg", ".jpeg", ".webp"]
            logo_img_path = None

            if os.path.exists(self.config["logos_folder"]):
                for ext in logo_extensions:
                    check_path = os.path.join(self.config["logos_folder"], f"{target_file_prefix}{ext}")
                    if os.path.exists(check_path):
                        logo_img_path = check_path
                        break

            fallback_logo_path = os.path.join(self.config["logos_folder"], "default_logo.png")
            if not logo_img_path and os.path.exists(fallback_logo_path):
                logo_img_path = fallback_logo_path

            logo_display_height = 0
            if logo_img_path:
                try:
                    with Image.open(logo_img_path) as logo_file:
                        max_logo_w, max_logo_h = 360, 110
                        logo_w, logo_h = logo_file.size
                        scale = min(max_logo_w / logo_w, max_logo_h / logo_h)
                        new_size = (int(logo_w * scale), int(logo_h * scale))
                        logo_rescaled = logo_file.resize(new_size, Image.Resampling.LANCZOS)
                        if logo_rescaled.mode in ("RGBA", "LA") or (logo_rescaled.mode == "P" and "transparency" in logo_rescaled.info):
                            img.paste(logo_rescaled, (content_left_x, card_y1 + 25), logo_rescaled)
                        else:
                            img.paste(logo_rescaled, (content_left_x, card_y1 + 25))
                        logo_display_height = new_size[1] + 15
                except Exception as logo_err:
                    print(f"Skipping logo render: {logo_err}")

            university_name = self.wrap_text(raw_uni_name, width=32)
            draw.multiline_text((content_left_x, card_y1 + 20 + logo_display_height), university_name, font=self.fonts["name"], fill=primary_text_color, spacing=2)

            country = item.get("Country/Territory", "Global")
            draw.text((content_left_x, card_y2 - 190), "COUNTRY / TERRITORY", font=self.fonts["label"], fill=secondary_text_color)
            draw.text((content_left_x, card_y2 - 165), country, font=self.fonts["country"], fill=primary_text_color)

            flag_img_path = self._find_country_asset(self.config["flags_folder"], country)
            if flag_img_path:
                try:
                    with Image.open(flag_img_path) as flag_file:
                        fl_w, fl_h = flag_file.size
                        fl_scale = 30 / fl_h
                        fl_new_size = (int(fl_w * fl_scale), 30)
                        flag_rescaled = flag_file.resize(fl_new_size, Image.Resampling.LANCZOS)
                        c_bbox = draw.textbbox((content_left_x, card_y2 - 165), country, font=self.fonts["country"])
                        flag_x = c_bbox[2] + 15
                        flag_y = card_y2 - 165 + int((c_bbox[3] - c_bbox[1] - 30) / 2)
                        if flag_rescaled.mode in ("RGBA", "LA"):
                            img.paste(flag_rescaled, (flag_x, flag_y), flag_rescaled)
                        else:
                            img.paste(flag_rescaled, (flag_x, flag_y))
                except Exception as flag_err:
                    print(f"Skipping flag overlay: {flag_err}")

            map_img_path = self._find_country_asset(self.config["maps_folder"], country)
            if map_img_path:
                try:
                    with Image.open(map_img_path) as map_file:
                        max_map_w, max_map_h = 260, 240
                        m_w, m_h = map_file.size
                        m_scale = min(max_map_w / m_w, max_map_h / m_h)
                        m_new_size = (int(m_w * m_scale), int(m_h * m_scale))
                        map_rescaled = map_file.resize(m_new_size, Image.Resampling.LANCZOS)
                        map_x = card_x2 - 240
                        map_y = card_y2 - 150 - m_new_size[1]
                        if map_rescaled.mode in ("RGBA", "LA"):
                            img.paste(map_rescaled, (map_x, map_y), map_rescaled)
                        else:
                            img.paste(map_rescaled, (map_x, map_y))
                except Exception as map_err:
                    print(f"Skipping map overlay: {map_err}")

            region = item.get("Region", "N/A")
            research = item.get("Research", "N/A")
            draw.text((content_left_x, card_y2 - 100), f"Region: {region}", font=self.fonts["region"], fill=secondary_text_color)
            draw.text((content_left_x, card_y2 - 70), f"Research Intensity: {research}", font=self.fonts["research"], fill=secondary_text_color)

            size_val = item.get("Size", "N/A")
            focus_val = item.get("Focus", "N/A")
            status_val = item.get("Status", "N/A")
            meta_line = f"Size: {size_val}  |  Focus: {focus_val}  |  Status: {status_val}"
            draw.text((content_left_x, card_y2 - 40), meta_line, font=self.fonts["status"], fill=secondary_text_color)

            score_left_x = card_x2 - 180
            draw.text((score_left_x, card_y2 - 140), "OVERALL SCORE", font=self.fonts["label"], fill=secondary_text_color)
            score = str(item.get("Overall SCORE", "N/A"))
            draw.text((score_left_x, card_y2 - 115), score, font=self.fonts["overall_score"], fill=score_highlight_color)

            slide_path = os.path.join(self.config["temp_folder"], f"slide_{sequence_str}_{index}.png")
            img.save(slide_path)
            slide_paths.append(slide_path)

        print("\nCombining individual slides into fixed-4 grouped mobile templates layout...")
        card_w_m, card_h_m = 980, 420
        top_margin, gap = 40, 20
        canvas_content_height = top_margin + (4 * (card_h_m + gap)) - gap + top_margin

        group_index = 1
        for i in range(0, len(slide_paths), 4):
            group = slide_paths[i : i + 4]
            current_canvas_height = self.config["mobile_height"] if (i + 4 >= len(slide_paths)) else canvas_content_height
            mobile_canvas = Image.new("RGB", (self.config["mobile_width"], current_canvas_height), (252, 252, 253))

            for idx, slide_path in enumerate(group):
                card_img = Image.open(slide_path).convert("RGB")
                card_img = card_img.resize((card_w_m, card_h_m))
                x = (self.config["mobile_width"] - card_w_m) // 2
                y = top_margin + idx * (card_h_m + gap)
                mobile_canvas.paste(card_img, (x, y))

            output_path = os.path.join(self.config["mobile_folder"], f"{group_index:03d}_mobile.png")
            mobile_canvas.save(output_path)
            group_index += 1

        intro_img_path = os.path.join(self.config["mobile_folder"], "000_intro.png")
        end_img_path = os.path.join(self.config["mobile_folder"], "999_end.png")

        self.create_title_slide(f"{self.config['filename']} World University Rankings {self.config['year']}", f"Top Global Universities Overview", intro_img_path)
        self.create_title_slide("Thank You", "Please Subscribe Channel\nFor More Videos", end_img_path)
        print("Image processing steps fully completed successfully.")

import json
import os
import random
import textwrap
import shutil
import unicodedata
import re
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
# Import the audio effects sub-module to safely access looping configurations
import math
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
# Add this import here:
from moviepy.audio.AudioClip import concatenate_audioclips

class PremiumVideoEngine:
    """Takes pre-rendered frames from the disk, applies custom audio loops, 
    and outputs smooth, scrolling mp4 tracks.
    """

    def __init__(self, config):
        self.config = config
        os.makedirs(os.path.dirname(self.config["output_video_path"]), exist_ok=True)

    def create_video(self):
        # Quick bypass if the video target already exists
        if os.path.exists(self.config["output_video_path"]):
            return self.config["output_video_path"]
            
        intro_img_path = os.path.join(self.config["mobile_folder"], "000_intro.png")
        end_img_path = os.path.join(self.config["mobile_folder"], "999_end.png")

        if not os.path.exists(intro_img_path) or not os.path.exists(end_img_path):
            print("X Compile error: Static structures missing from source path workspace.")
            return

        mobile_images = sorted(
            [
                os.path.join(self.config["mobile_folder"], f)
                for f in os.listdir(self.config["mobile_folder"])
                if f.endswith(".png") and not (f.startswith("000_") or f.startswith("999_"))
            ]
        )

        if not mobile_images:
            print("X Compile error: No scrolling layout parts discovered.")
            return

        print("\nCompiling Video Track via Stream-Optimized Scroll Engine...")
        total_scroll_height = 0
        canvas_positions = []

        for p in mobile_images:
            with Image.open(p) as img_obj:
                canvas_positions.append(total_scroll_height)
                total_scroll_height += img_obj.height

        long_canvas = Image.new("RGB", (self.config["mobile_width"], total_scroll_height), (252, 252, 253))
        for idx, p in enumerate(mobile_images):
            with Image.open(p) as img_obj:
                long_canvas.paste(img_obj.convert("RGB"), (0, canvas_positions[idx]))

        last_list_viewport = long_canvas.crop((0, total_scroll_height - self.config["mobile_height"], self.config["mobile_width"], total_scroll_height))
        last_list_np = np.array(last_list_viewport)

        total_scroll_pixels = total_scroll_height - self.config["mobile_height"]
        scroll_duration = total_scroll_pixels / (self.config["scroll_speed"] * self.config["fps"])

        intro_clip = ImageClip(intro_img_path).with_duration(3.5)
        end_clip = ImageClip(end_img_path).with_duration(4.0)

        def scroll_frame_processor(get_frame, t):
            current_y = int(t * self.config["fps"] * self.config["scroll_speed"])
            current_y = min(current_y, total_scroll_pixels)
            viewport = long_canvas.crop((0, current_y, self.config["mobile_width"], current_y + self.config["mobile_height"]))
            return np.array(viewport)

        scroll_base = ImageClip(last_list_np).with_duration(scroll_duration)
        scroll_clip = scroll_base.transform(scroll_frame_processor, apply_to=[])

        fade_duration = 0.8
        end_np = np.array(Image.open(end_img_path).convert("RGB"))

        def fade_frame_processor(get_frame, t):
            alpha = min(max(t / fade_duration, 0.0), 1.0)
            blended = np.clip((last_list_np * (1.0 - alpha) + end_np * alpha), 0, 255).astype(np.uint8)
            return blended

        fade_base = ImageClip(last_list_np).with_duration(fade_duration)
        fade_clip = fade_base.transform(fade_frame_processor, apply_to=[])

        main_video = concatenate_videoclips([intro_clip, scroll_clip, fade_clip, end_clip], method="chain")
       
        audio_clip = None
        # Robust version-agnostic audio duplication engine
        if "audio_path" in self.config and self.config["audio_path"] and os.path.exists(self.config["audio_path"]):
            print(f"Injecting audio layout soundtrack: {self.config['audio_path']}...")
            try:
                base_audio = AudioFileClip(self.config["audio_path"])
                
                # Check if the video duration exceeds our available sound duration
                if base_audio.duration < main_video.duration:
                    print(f"🔄 Audio clip ({base_audio.duration:.2f}s) is shorter than video track ({main_video.duration:.2f}s). Calculating loop array...")
                    
                    # Calculate how many times the sound track must repeat to cover the full video
                    loops_needed = math.ceil(main_video.duration / base_audio.duration)
                    
                    # Chain the audio track back-to-back using basic list replication
                    extended_audio = concatenate_audioclips([base_audio] * loops_needed)
                    
                    # Trim any excess audio to match the video length precisely
                    audio_clip = extended_audio.with_duration(main_video.duration)
                else:
                    audio_clip = base_audio.with_duration(main_video.duration)
                
                main_video = main_video.with_audio(audio_clip)
            except Exception as audio_err:
                print(f"X Warning: Audio insertion skipped due to runtime error: {audio_err}")
        else:
            print("! No valid background audio track path found in configurations. Outputting silent track.")

        print(f"Rendering track to file: {self.config['output_video_path']}...")
        main_video.write_videofile(
            self.config["output_video_path"],
            fps=self.config["fps"],
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger="bar",
        )

        # Clean closures across active resource streams
        main_video.close()
        intro_clip.close()
        scroll_clip.close()
        fade_clip.close()
        end_clip.close()
        long_canvas.close()
        last_list_viewport.close()
        
        if audio_clip is not None:
            audio_clip.close()
            
        self.cleanup_workspace()
        return self.config["output_video_path"]

    def cleanup_workspace(self):
        print("\nCleaning temporary folders...")
        for folder in [self.config["temp_folder"], self.config["mobile_folder"]]:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)


# =====================================================================
# PART 3: MAIN ORCHESTRATION PIPELINE WITH AUDIO IMPORT FALLBACK
# =====================================================================
def main(year, filename, top_number, audio_url):
    os.makedirs(Config.IMAGE_DIR, exist_ok=True)
    
    Config.YEAR = str(year)
    Config.FILE_NAME = str(filename)
    
    json_data_path, audio_file_path = Config.get_dynamic_paths(Config.FILE_NAME, Config.YEAR, top_number)

    if not os.path.exists(audio_file_path):
        # Automated dynamic module resolution & shell-execution hotfix
        try:
            folder_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            sys.path.append(folder_path)
            from yt_downloader import MediaDownLoader
            print("SUCCESS: Downloader module imported successfully via dynamic sys.path!")
            mediaDownLoader = MediaDownLoader()
            input_audio_folder = f"{Config.BASE_DIR}/outputs/audios"
            audio_file_path = mediaDownLoader.download_video_with_ytdlp(
                input_audio_folder, audio_url, file_name_part=f"{Config.FILE_NAME}_{Config.YEAR}_audio"
            )
        except Exception as e:
            print(f"Module import failed ({type(e).__name__}). Launching robust local inline subprocess downloader...")
            try:
                input_audio_folder = os.path.join(Config.BASE_DIR, "outputs", "audios")
                os.makedirs(input_audio_folder, exist_ok=True)
                audio_file_path = os.path.join(input_audio_folder, f"{Config.FILE_NAME}_{Config.YEAR}_audio.mp4")
                
                # Directly run native yt-dlp binary to grab audio stream instantly and bypass script import limitations
                cmd = ["yt-dlp", "-f", "ba", "-x", "--audio-format", "mp3", "-o", audio_file_path.replace(".mp4", ".%(ext)s"), audio_url]
                subprocess.run(cmd, check=True)
                if os.path.exists(audio_file_path.replace(".mp4", ".mp3")):
                    os.rename(audio_file_path.replace(".mp4", ".mp3"), audio_file_path)
                print("Inline background audio track downloaded successfully via shell.")
            except Exception as sub_e:
                print(f"FAILURE: Could not download audio via fallback. Slide will execute silently. Error: {sub_e}")

    output_file_name = f"{Config.FILE_NAME}_{Config.YEAR}_RANKING_TOP{top_number}.mp4"
    
    shared_config = {
        "year": Config.YEAR,
        "filename": Config.FILE_NAME,
        "top_number": top_number,
        "fps": 30,
        "scroll_speed": 5,
        "video_width": 1080,
        "video_height": 540,
        "mobile_width": 1080,
        "mobile_height": 1920,
        "json_file": json_data_path,
        "temp_folder": f"{Config.BASE_DIR}/outputs/images/slides",
        "mobile_folder": f"{Config.BASE_DIR}/outputs/images/slides_mobile",
        "output_video_path": f"{Config.BASE_DIR}/outputs/videos/{output_file_name}",
        "logos_folder": f"{Config.BASE_DIR}/assets/images/logos",
        "maps_folder": f"03_map_processing/images/countries",
        "flags_folder": r"03_map_processing/images/countries_flags",
        "audio_path": audio_file_path
    }

    generator = PremiumImageGenerator(config=shared_config)
    generator.generate_images()

    compiler = PremiumVideoEngine(config=shared_config)
    compiler.create_video()


if __name__ == "__main__":
    EXEC_YEAR = 2027
    EXEC_FILENAME = "QS"
    EXEC_TOP_NUMBER = 12  
    EXEC_AUDIO_URL = "https://www.youtube.com/shorts/oOkd2z1BuKI"
    
    main(
        year=EXEC_YEAR, 
        filename=EXEC_FILENAME, 
        top_number=EXEC_TOP_NUMBER, 
        audio_url=EXEC_AUDIO_URL
    )