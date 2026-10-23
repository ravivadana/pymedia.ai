import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import contextily as cx
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from geopy.geocoders import Nominatim
from moviepy import ImageSequenceClip, AudioFileClip, CompositeAudioClip
from PIL import Image, ImageDraw

# ==========================================================
# CONFIGURATION
# ==========================================================
class Config:
    BASE_DIR = Path(__file__).resolve().parent
    IMAGES_DIR = Path(r"C:\Ravi\Python\2025\Media\03_map_processing\data\images\1")
    MAPS_ASSETS = Path(r"C:\Ravi\Python\2025\Media\assets\common\maps\ne_10m_admin_1_states_provinces\ne_10m_admin_1_states_provinces.shp")
    AUDIO_PATH = Path(r"C:\Ravi\Python\2025\Media\03_map_processing\data\audios\s1.mp4")
    OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
    TEMP_DIR = BASE_DIR / "outputs" / "temp"

    @classmethod
    def ensure_directories(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# EXTRACT CITY NAMES FROM FILENAMES IN ASCENDING ORDER
# ==========================================================
class WhatsAppImageLoader:
    def __init__(self, images_dir, shapefile_path):
        self.images_dir = Path(images_dir)
        self.shapefile_path = Path(shapefile_path)
        self.geolocator = Nominatim(user_agent="whatsapp_map_route_app")

    def load_sequence(self):
        if not self.images_dir.exists():
            raise FileNotFoundError(f"Images directory not found: {self.images_dir}")

        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
        # Sort image files in ascending order by their filenames
        image_files = sorted([p for p in self.images_dir.iterdir() if p.suffix.lower() in image_extensions], key=lambda x: x.name)

        location_records = []
        for img_path in image_files:
            # Trim sequence number or index from filename (e.g., "1_Delhi.jpg" -> "Delhi", "01_Mumbai" -> "Mumbai")
            raw_stem = img_path.stem
            parts = raw_stem.split('_', 1)
            if len(parts) > 1 and parts[0].isdigit():
                clean_name = parts[1].strip()
            else:
                clean_name = raw_stem.strip()

            dt_captured = datetime.fromtimestamp(img_path.stat().st_mtime)

            print(f"Geocoding location from filename '{img_path.name}' (City: {clean_name})...")
            try:
                query_str = f"{clean_name}, India"
                location = self.geolocator.geocode(query_str, timeout=10)
                
                if location:
                    location_records.append({
                        'file_name': img_path.name,
                        'city': clean_name.capitalize(),
                        'path': str(img_path),
                        'datetime': dt_captured,
                        'latitude': location.latitude,
                        'longitude': location.longitude
                    })
                else:
                    print(f"Warning: Could not resolve coordinates for city '{clean_name}'")
            except Exception as e:
                print(f"Geocoding error for {clean_name}: {e}")

        # Keep the exact ascending filename order established via sorted file iteration
        world_gdf = gpd.read_file(self.shapefile_path).to_crs(epsg=3857)
        india_gdf = world_gdf[world_gdf['admin'] == 'India'].copy()
        india_gdf['color_id'] = np.arange(len(india_gdf))
        neighbors_gdf = world_gdf[world_gdf['admin'] != 'India'].copy()

        return location_records, india_gdf, neighbors_gdf

# ==========================================================
# MAP FRAME VISUALIZER (WITH SPOTLIGHT CONE RAY)
# ==========================================================
class HDMapVisualizer:
    def __init__(self, width=1080, height=1920, dpi=150):
        self.width = width
        self.height = height
        self.dpi = dpi

    def render_route_frame(self, india_gdf, neighbors_gdf, locations, current_idx, output_frame_path):
        fig = plt.figure(figsize=(self.width / 100, self.height / 100), dpi=self.dpi)
        fig.patch.set_facecolor('#0A9396')
        
        # --------------------------------------------------
        # 1. MAP SECTION: Full Screen Edge-to-Edge Coverage
        # --------------------------------------------------
        ax_map = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax_map.set_facecolor('#0A9396')

        neighbors_gdf.plot(ax=ax_map, facecolor='#000000', edgecolor='#475569', linewidth=0.6, alpha=0.45, zorder=2)
        india_gdf.plot(ax=ax_map, column='color_id', cmap='tab20', edgecolor='#FFFFFF', linewidth=0.8, alpha=0.45, zorder=3)

        minx, miny, maxx, maxy = india_gdf.total_bounds
        center_x, center_y = (minx + maxx) / 2, ((miny + maxy) / 2) - ((maxy - miny) * 0.08)
        
        canvas_aspect = self.width / self.height
        india_width = maxx - minx
        india_height = maxy - miny
        
        if (india_width / india_height) > canvas_aspect:
            x_range = india_width * 0.92
            y_range = x_range / canvas_aspect
        else:
            y_range = india_height * 0.92
            x_range = y_range * canvas_aspect

        ax_map.set_xlim(center_x - x_range / 2, center_x + x_range / 2)
        ax_map.set_ylim(center_y - y_range / 2, center_y + y_range / 2)
        ax_map.axis('off')

        cx.add_basemap(ax_map, source=cx.providers.Esri.WorldImagery, zorder=1, reset_extent=False)

        # Convert locations to Web Mercator & draw path lines
        projected_coords = []
        for loc in locations:
            pt_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy([loc['longitude']], [loc['latitude']]), crs="EPSG:4326").to_crs(epsg=3857)
            projected_coords.append((pt_gdf.geometry.iloc[0].x, pt_gdf.geometry.iloc[0].y))

        active_path = projected_coords[:current_idx + 1]
        if len(active_path) > 1:
            pxs, pys = zip(*active_path)
            ax_map.plot(pxs, pys, color='#FFD166', linewidth=4, linestyle='--', alpha=0.9, zorder=5)

        current_px, current_py = projected_coords[current_idx]

        for i, (px, py) in enumerate(projected_coords):
            loc_name = locations[i]['city'].upper()
            
            if i < current_idx:
                ax_map.scatter(px, py, color='#118AB2', s=500, marker='o', edgecolor='#FFFFFF', linewidth=1.5, zorder=6)
                txt = ax_map.text(px + (x_range * 0.015), py, loc_name, fontsize=14, fontweight='bold', color='#FFFFFF', va='center', zorder=6)
                txt.set_path_effects([path_effects.Stroke(linewidth=3, foreground='#000000'), path_effects.Normal()])
                
            elif i == current_idx:
                # Clean circular map marker (no crosshair lines below)
                ax_map.scatter(px, py, color='#D90429', s=1400, marker='o', edgecolor='#FFFFFF', linewidth=2.5, zorder=7)
                ax_map.scatter(px, py, color='#FFFFFF', s=300, marker='o', zorder=8)
                
                txt = ax_map.text(px + (x_range * 0.02), py, loc_name, fontsize=18, fontweight='black', color='#FFD166', va='center', zorder=9)
                txt.set_path_effects([path_effects.Stroke(linewidth=4, foreground='#000000'), path_effects.Normal()])

        # --------------------------------------------------
        # 2. OVERLAY SECTION: City Title, Image & Spotlight Beam Cone
        # --------------------------------------------------
        cur_loc = locations[current_idx]
        
        # City Name Header with Rich AI-style Multi-Layer Glow Effects
        header_y_pos = current_py + (y_range * 0.09)
        
        glow_effect = ax_map.text(current_px, header_y_pos, cur_loc['city'].upper(), fontsize=36, fontweight='heavy', family='sans-serif', color='#4cc9f0', ha='center', va='center', zorder=10)
        glow_effect.set_path_effects([
            path_effects.Stroke(linewidth=12, foreground='#7209b7', alpha=0.6),
            path_effects.Stroke(linewidth=6, foreground='#3a0ca3', alpha=0.9),
            path_effects.Normal()
        ])
        
        core_text = ax_map.text(current_px, header_y_pos, cur_loc['city'].upper(), fontsize=36, fontweight='heavy', family='sans-serif', color='#ffffff', ha='center', va='center', zorder=11)
        core_text.set_path_effects([
            path_effects.Stroke(linewidth=2, foreground='#f72585'),
            path_effects.Normal()
        ])

        try:
            img_path = Path(cur_loc['path'])
            if not img_path.exists():
                print(f"Image file missing on disk: {img_path}")
            else:
                img_pil = Image.open(img_path).convert("RGBA")
                
                target_max_side = 560
                img_pil.thumbnail((target_max_side, target_max_side), Image.Resampling.LANCZOS)
                w, h = img_pil.size
                
                mask = Image.new("L", (w, h), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, w, h), radius=15, fill=255)
                
                final_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                final_img.paste(img_pil, (0, 0), mask)
                
                imagebox = OffsetImage(final_img, zoom=0.85)
                imagebox.set_zorder(10)
                
                # Image pinned at bottom right
                img_x_frac, img_y_frac = 0.6, 0.25
                ab = AnnotationBbox(imagebox, (img_x_frac, img_y_frac), xycoords='axes fraction', frameon=False, zorder=10)
                ax_map.add_artist(ab)

                # Compute approximate data coordinates for the image box
                xmin, xmax = ax_map.get_xlim()
                ymin, ymax = ax_map.get_ylim()
                img_data_x = xmin + img_x_frac * (xmax - xmin)
                img_data_y = ymin + img_y_frac * (ymax - ymin)

                # Estimate thumbnail width/height in data units for the spotlight base span
                box_width_data = (xmax - xmin) * 0.22
                box_height_data = (ymax - ymin) * 0.18

                # Left and right corners of the image thumbnail base
                img_left_x = img_data_x - (box_width_data / 2)
                img_right_x = img_data_x + (box_width_data / 2)
                img_top_y = img_data_y + (box_height_data / 2)

                # Draw semi-transparent projecting spotlight polygon/cone beam
                triangle_x = [current_px, img_left_x, img_right_x]
                triangle_y = [current_py, img_top_y, img_top_y]
                ax_map.fill(triangle_x, triangle_y, color='#FFFFFF', alpha=0.25, zorder=9)
                
        except Exception as e:
            print(f"Error embedding image thumbnail for {cur_loc['file_name']}: {e}")

        plt.savefig(output_frame_path, facecolor=fig.get_facecolor(), dpi=self.dpi)
        plt.close(fig)


# ==========================================================
# MAIN EXECUTION
# ==========================================================
if __name__ == "__main__":
    Config.ensure_directories()

    loader = WhatsAppImageLoader(Config.IMAGES_DIR, Config.MAPS_ASSETS)
    locations, india_map, neighbors_map = loader.load_sequence()

    if not locations:
        print("No valid geocoded locations parsed from filenames.")
        sys.exit(1)

    visualizer = HDMapVisualizer()
    frame_paths = []
    seconds_per_item = 5  
    fps = 30
    frames_per_item = seconds_per_item * fps

    print("\n--- Rendering Sequential Route Frames ---")
    for idx, loc in enumerate(locations):
        frame_path = Config.TEMP_DIR / f"wa_frame_{idx:03d}.png"
        visualizer.render_route_frame(india_map, neighbors_map, locations, idx, frame_path)
        frame_paths.extend([str(frame_path)] * frames_per_item)
        print(f"Processed [{idx+1}/{len(locations)}]: {loc['city']} ({loc['file_name']})")

    video_clip = ImageSequenceClip(frame_paths, fps=fps)

    final_audio = None
    if Config.AUDIO_PATH.exists():
        print(f"\n--- Attaching Audio Track from {Config.AUDIO_PATH} ---")
        audio_clip = AudioFileClip(str(Config.AUDIO_PATH))
        
        if audio_clip.duration < video_clip.duration:
            repeats = int(np.ceil(video_clip.duration / audio_clip.duration))
            audio_clip = CompositeAudioClip([
                audio_clip.with_start(i * audio_clip.duration) for i in range(repeats)
            ]).subclipped(0, video_clip.duration)
        else:
            audio_clip = audio_clip.subclipped(0, video_clip.duration)
            
        final_audio = audio_clip
        video_clip = video_clip.with_audio(final_audio)
    else:
        print(f"\n--- Warning: Audio file not found at {Config.AUDIO_PATH}. Exporting silent video. ---")

    output_video = str(Config.OUTPUT_DIR / "WhatsApp_Images_Route_Sequence.mp4")
    
    print(f"\n--- Exporting Video to {output_video} ---")
    video_clip.write_videofile(
        output_video, 
        fps=fps, 
        codec='libx264', 
        audio_codec='aac' if final_audio else None, 
        preset='medium', 
        bitrate='8000k',
        logger='bar'
    )
    
    if final_audio:
        final_audio.close()
    video_clip.close()

    print("Video generation successfully completed!")