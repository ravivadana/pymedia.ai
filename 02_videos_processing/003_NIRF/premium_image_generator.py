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
from moviepy import ImageClip, concatenate_videoclips
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd

# Import contextily for fetching satellite map layers safely
try:
    import contextily as cx
except ImportError:
    cx = None

class PremiumImageGenerator:
    """Handles parsing dataset metrics, pulling local country/logo assets,
    and generating clean high-fidelity mobile static slides tailored for Indian Institute Data.
    """

    THEMES = [
        {"bg1": (255, 236, 210), "bg2": (252, 182, 159)},  # Peach Blossom Cream
        {"bg1": (212, 252, 242), "bg2": (150, 230, 210)},  # Fresh Mint Sorbet
        {"bg1": (230, 242, 255), "bg2": (180, 210, 255)},  # Clean Sky Blue
        {"bg1": (254, 211, 252), "bg2": (253, 161, 234)},  # Bubblegum Pink
        {"bg1": (255, 243, 195), "bg2": (255, 213, 115)},  # Soft Lemon Honey
        {"bg1": (224, 255, 210), "bg2": (163, 235, 140)},  # Lime Pistachio
        {"bg1": (243, 231, 255), "bg2": (211, 181, 255)},  # Lavender Mist
        {"bg1": (255, 222, 222), "bg2": (255, 164, 164)},  # Light Rose Petal
        {"bg1": (206, 246, 253), "bg2": (132, 220, 238)},  # Electric Ice
        {"bg1": (255, 237, 188), "bg2": (253, 202, 131)},  # Summer Apricot
        {"bg1": (225, 253, 200), "bg2": (175, 235, 210)},  # Matcha Melon Slim
        {"bg1": (240, 240, 245), "bg2": (200, 205, 220)},  # Platinum Silk Grid
        {"bg1": (255, 225, 240), "bg2": (255, 170, 210)},  # Cotton Candy Dream
        {"bg1": (215, 255, 225), "bg2": (160, 230, 190)},  # Aqua Marine Mint
    ]
    
    def __init__(self, config):
        self.config = config
        self.config.setdefault("logos_folder", getattr(config, "LOGO_FOLDER", "logos"))
        
        # Read the map configuration style (defaults to "simple")
        self.map_type = self.config.get("map_type", "simple").lower()
        
        from config import Config
        self.inst_mappings = getattr(Config, "INSTITUTE_MAPPINGS", {})
        self.shapefile_path = getattr(Config, "SHAPEFILE_PATH", {})

        self._initialize_workspace()
        self._load_typography()

    def _initialize_workspace(self):
        os.makedirs(self.config["temp_folder"], exist_ok=True)
        os.makedirs(self.config["mobile_folder"], exist_ok=True)
        os.makedirs(self.config["logos_folder"], exist_ok=True)

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
                "rank": ImageFont.truetype(target_path, 60),
                "name": ImageFont.truetype(target_path, 34),
                "location": ImageFont.truetype(target_path, 28),
                "state": ImageFont.truetype(target_path, 26),
                "score": ImageFont.truetype(target_path, 44),
                "label": ImageFont.truetype(target_path, 20),
                "intro": ImageFont.truetype(target_path, 80),
                "sub": ImageFont.truetype(target_path, 40),
            }
        except Exception:
            default = ImageFont.load_default()
            self.fonts = {k: default for k in ["rank", "name", "location", "state", "score", "label", "intro", "sub"]}

    def clean_name(self, name):
        if not name or str(name).strip().lower() == "nan":
            return ""
        name = str(name)
        name = re.sub(r"/(.*?/)", "", name)
        name = re.sub(r"/[.*?/]", "", name)
        name = name.replace("’", "'").replace("`", "'").replace("“", '"').replace("”", '"')
        name = unicodedata.normalize("NFKD", name)
        name = "".join([c for c in name if not unicodedata.combining(c)])
        name = re.sub(r'[///:*?"<>|]', '', name)
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
        bbox = draw.textbbox((0, 0), icon_text, font=self.fonts["sub"])
        iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((circle_x - iw / 2, circle_y - ih / 2 - 10), icon_text, font=self.fonts["sub"], fill=(255, 255, 255))

        img.save(output_path)
    
    def _short_institute_name(self, name, rank_str):
        name = name.replace("`", "'")
        name=name.replace(",","").replace(" ","_")
        name=name.replace(" & "," and ")
        for k, v in self.inst_mappings.items():
            if name.startswith(k):
                name = name.replace(k, v)
                break
        rank = f'{int(rank_str):03d}'
        inst_short = f'{rank}_{name}'
        return inst_short
    
    def _get_coordinates(self, city, state):
        country_cities_file_name=f'{self.config["country_code"]}_cities.json'
        country_cities_file_path=f'{self.config["common_assets"]}/data/{country_cities_file_name}'
        try:
            df = pd.read_json(country_cities_file_path)
        except FileNotFoundError:
            print(f"Error: Could not find the file at {country_cities_file_path}")
            exit()

        # 2. Define the city you want to search for
        search_city = city  # Change this to "Delhi", "Bengaluru", etc.

        # 3. Filter the dataframe (case-insensitive search to prevent typos)
        result_df = df[df["name"].str.lower() == search_city.lower()]

        # 4. Display the result
        if not result_df.empty:
            print(f"\nFound {len(result_df)} record(s) for '{search_city}':")

            # To see it formatted as a clean DataFrame table in your console:
            #print(result_df)

            # Alternative: To convert just this city's data back to a JSON string or dict:
            # city_json = result_df.to_dict(orient="records")
            # print(city_json)
        else:
            print(f"\nNo records found for city: '{search_city}'")
       
        return (result_df.lat,result_df.lon)

    def generate_india_map(self, city_name, state_name, output_path, width=340, height=400, map_type="simple"):
        """Generates either a standard simple vector map frame or a satellite imagery frame 
        based on the map_type parameter.
        """
        shapefile_path = self.shapefile_path
        if not os.path.exists(shapefile_path) and map_type == "simple":
            print(f"Error: Shapefile missing at {shapefile_path}")
            return False

        try:
            fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=200)
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            ax.set_axis_off()

            coords = self._get_coordinates(city_name, state_name)
            if not coords:
                plt.close(fig)
                return False
                
            lat, lon = coords
            point_geom = Point(lon, lat)
            
            if map_type == "satellite" and cx is not None:
                # Create a tightly zoomed bounding box area around the institution coordinate
                # Modifying buffer size safely scales the zoom depth
                zoom_buffer = 0.05 
                city_gdf = gpd.GeoDataFrame(geometry=[point_geom], crs="EPSG:4326")
                city_gdf = city_gdf.to_crs(epsg=3857)
                
                # Fetch base limits in Web Mercator
                cx_bounds = city_gdf.geometry.buffer(8000).total_bounds # 8km range zoom context
                ax.set_xlim(cx_bounds[0], cx_bounds[2])
                ax.set_ylim(cx_bounds[1], cx_bounds[3])
                
                # Add satellite tiles directly via contextily
                cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=1)
                
                # Render clean premium pinpoint overlays onto the satellite raster
                city_gdf.plot(ax=ax, marker='o', color='#EF4444', markersize=180, alpha=0.4, zorder=4)
                city_gdf.plot(ax=ax, marker='*', color='#FFFF00', markersize=60, edgecolor='#000000', linewidth=0.5, zorder=5)
                
            else:
                # --- FALLBACK / SIMPLE VECTOR MAP MODE ---
                world_states = gpd.read_file(shapefile_path)
                cntry_col = next((c for c in ['admin', 'ADMIN', 'SOVEREIGNT'] if c in world_states.columns), None)
                
                if cntry_col:
                    india_gdf = world_states[world_states[cntry_col].str.lower().str.contains('india', na=False)]
                else:
                    india_gdf = world_states

                if india_gdf.crs is None or india_gdf.crs.to_epsg() != 3857:
                    india_gdf = india_gdf.to_crs(epsg=3857)
                india_bounds = india_gdf.total_bounds

                india_gdf.plot(ax=ax, facecolor='#E2E8F0', edgecolor='#94A3B8', linewidth=0.5, zorder=1)

                city_gdf = gpd.GeoDataFrame(geometry=[point_geom], crs="EPSG:4326")
                city_gdf = city_gdf.to_crs(epsg=3857)

                city_gdf.plot(ax=ax, marker='o', color='#EF4444', markersize=140, alpha=0.35, zorder=4)
                city_gdf.plot(ax=ax, marker='o', color='#DC2626', markersize=35, edgecolor='#FFFFFF', linewidth=1.0, zorder=5)

                ax.set_xlim(india_bounds[0], india_bounds[2])
                ax.set_ylim(india_bounds[1], india_bounds[3])

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, bbox_inches='tight', pad_inches=0, transparent=True)
            plt.close(fig)
            return True
            
        except Exception as e:
            print(f"Failed handling shapefile/satellite rendering pipeline for {city_name}: {e}")
            plt.close(fig)
            return False
        
    def generate_images(self):
        """Runs dataset mapping iterations and outputs static frames to temp paths."""
        if not os.path.exists(self.config["json_file"]):
            print(f"X Core Data file missing: {self.config['json_file']}")
            return

        with open(self.config["json_file"], "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"Loaded {len(data)} data records from configuration matrix.")
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

            sequence_str = f"{(index + 1):03d}"
            rank = self.get_rank(item, index)

            img = Image.new("RGB", (self.config["video_width"], self.config["video_height"]), (250, 250, 252))
            draw = ImageDraw.Draw(img)

            card_width, card_height = 940, 420
            card_x1 = (self.config["video_width"] - card_width) // 2
            card_y1 = 60
            card_x2, card_y2 = card_x1 + card_width, card_y1 + card_height
            radius, blade_width = 40, 150

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
            
            composite_img = img.convert("RGBA")
            draw = ImageDraw.Draw(composite_img)

            primary_text_color = (30, 41, 59)
            secondary_text_color = (71, 85, 105)
            score_highlight_color = (220, 38, 38)

            column_center_x = card_x1 + (blade_width // 2)

            # --- LEFT BLADE PANEL (RANK BOX) ---
            label_1 = "RANK"
            bbox_l1 = draw.textbbox((0, 0), label_1, font=self.fonts["label"])
            l1_w = bbox_l1[2] - bbox_l1[0]
            draw.text((column_center_x - (l1_w // 2), card_y1 + 130), label_1, font=self.fonts["label"], fill=secondary_text_color)

            rank_text = f"#{rank}"
            bbox_r = draw.textbbox((0, 0), rank_text, font=self.fonts["rank"])
            rw = bbox_r[2] - bbox_r[0]
            draw.text((column_center_x - (rw // 2), card_y1 + 170), rank_text, font=self.fonts["rank"], fill=primary_text_color)

            # --- DYNAMIC MAP IMAGE PLACEMENT (RIGHT ALIGNED) ---
            state = item.get("State", "Unknown").strip()
            city = item.get("City", "Unknown").strip()

            clean_state_name = re.sub(r'\s+', '_', state.lower())
            clean_city_name = re.sub(r'\s+', '_', city.lower())

            map_max_w, map_max_h = 340, 400   
            map_placed = False
            
            # Appended map type to filename to prevent caching/overwriting if types match
            map_file = os.path.join(self.config["temp_folder"], f"map_{clean_city_name}_{self.map_type}.png")
            
            # FIXED: Passing self.map_type directly into map generation pipeline execution
            success = self.generate_india_map(city, state, map_file, width=map_max_w, height=map_max_h, map_type=self.map_type)
            
            if success and os.path.exists(map_file):
                try:
                    map_asset = Image.open(map_file).convert("RGBA")
                    map_asset.thumbnail((map_max_w, map_max_h), Image.Resampling.LANCZOS)
                    
                    mx = card_x2 - map_asset.width - 15
                    my = card_y1 + (card_height - map_asset.height) // 2
                    
                    composite_img.paste(map_asset, (mx, my), map_asset)
                    map_placed = True
                except Exception as e:
                    print(f"Could not blend generated map asset for {city}: {e}")

            # --- DYNAMIC LOGO PLACEMENT ---
            raw_uni_name = item.get("Name", "Unknown Institution")
            cleaned_filename = self.clean_name(raw_uni_name)
            logo_max_w, logo_max_h = 120, 120
            logo_padding = 25
            content_left_x = card_x1 + blade_width + 35
            short_name = self._short_institute_name(cleaned_filename, rank)
            logo_file = os.path.join(str(self.config["logos_folder"]), short_name)
            logo_file = f'{logo_file}.png'

            if os.path.exists(logo_file):
                try:
                    logo_asset = Image.open(logo_file).convert("RGBA")
                    logo_asset.thumbnail((logo_max_w, logo_max_h), Image.Resampling.LANCZOS)
                    
                    lx = content_left_x
                    ly = card_y1 + 45
                    
                    composite_img.paste(logo_asset, (lx, ly), logo_asset)
                    content_left_x += logo_asset.width + logo_padding
                except Exception as e:
                    print(f"Could not load logo asset for {raw_uni_name}: {e}")

            # --- MAIN CONTENT TEXT AREA ---
            text_wrap_limit = 14 if map_placed else 26
            university_name = self.wrap_text(raw_uni_name, width=text_wrap_limit)
            
            # draw.text((content_left_x, card_y1 + 40), "INSTITUTE", font=self.fonts["label"], fill=secondary_text_color)
            draw.multiline_text((content_left_x, card_y1 + 70), university_name, font=self.fonts["name"], fill=primary_text_color, spacing=6)

            city_val = item.get("City", "Unknown")
            address_line = self.wrap_text(f"{city_val}, {state}", width=text_wrap_limit + 4)

            draw.multiline_text((content_left_x, card_y2 - 100), address_line, font=self.fonts["location"], fill=secondary_text_color, spacing=4)

            # --- SCORE HIGHLIGHT ---
            score_left_x = content_left_x+400
            score_top_y = card_y2 - 65
            
            draw.text((score_left_x, score_top_y), "SCORE: ", font=self.fonts["label"], fill=secondary_text_color)
            
            label_bbox = draw.textbbox((score_left_x, score_top_y), "SCORE: ", font=self.fonts["label"])
            score_value_x = label_bbox[2] + 5
            
            score = str(item.get("Score", "N/A"))
            draw.text((score_value_x, score_top_y - 18), score, font=self.fonts["score"], fill=score_highlight_color)

            img = composite_img.convert("RGB")
            slide_path = os.path.join(self.config["temp_folder"], f"slide_{sequence_str}_{index}.png")
            img.save(slide_path)
            slide_paths.append(slide_path)

        print("\nCombining individual slides into mobile layouts...")
        card_w_m, card_h_m = 980, 420
        top_margin, gap = 40, 20
        canvas_content_height = (top_margin + (4 * (card_h_m + gap)) - gap + top_margin)

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

        self.create_title_slide(f"NIRF {self.config['course_name']} College Rankings {self.config['year']}", f"Top Indian Institutes Overview", intro_img_path)
        self.create_title_slide("Thank You", "Please Subscribe Channel\nFor More Videos", end_img_path)
        print("Image processing steps fully completed successfully.")