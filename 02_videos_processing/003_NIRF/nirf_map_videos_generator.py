import os
import json
import numpy as np
import matplotlib
# Force Matplotlib to use a non-interactive backend (Stops crashes)
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

import geopandas as gpd
import contextily as ctx
from shapely.geometry import LineString, Point
from gtts import gTTS
from PIL import Image

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from premium_add_bgm import BgmAudioAdder
# Import the correct capitalized Configuration class
from config import Config


class NirfRankingMapVideosGenerator:
    def __init__(self, map_type="simple"):
        """
        Initializes the video generator parsing properties from configuration module.
        :param map_type: Str, either "simple" or "satellite" to toggle base maps.
        """
        self.shape_states_file_path = str(Config.SHAPEFILE_PATH)
        self.nirf_json_path = str(Config.JSON_DATA_PATH)
        self.map_type = map_type.lower()
        
        self.state_abbrev = Config.STATE_ABBREVIATIONS
        self.themes = Config.THEMES
        self.inst_mappings = Config.INSTITUTE_MAPPINGS

        print(f"Reading shape_states_file_path from: {self.shape_states_file_path}")
        raw_data = gpd.read_file(self.shape_states_file_path)
        
        india_base = raw_data[
            (raw_data.geometry.notnull()) & 
            ((raw_data['admin'] == 'India') | (raw_data['admin'] == 'India/Pakistan boundary'))
        ].copy()

        disputed_regions = raw_data[
            raw_data['name'].isin(['Azad Kashmir', 'Gilgit-Baltistan', 'Aksai Chin', 'Jammu and Kashmir', 'Ladakh']) |
            raw_data['admin'].str.contains('Jammu & Kashmir', case=False, na=False)
        ].copy()

        for idx, row in disputed_regions.iterrows():
            name_str = str(row['name'])
            if name_str in ['Azad Kashmir', 'Gilgit-Baltistan', 'Jammu and Kashmir']:
                disputed_regions.at[idx, 'name'] = 'Jammu and Kashmir'
            elif name_str in ['Aksai Chin', 'Ladakh']:
                disputed_regions.at[idx, 'name'] = 'Ladakh'
            disputed_regions.at[idx, 'admin'] = 'India'

        combined_gdf = gpd.GeoDataFrame(gpd.pd.concat([india_base, disputed_regions], ignore_index=True), crs=raw_data.crs)
        self.india_states = combined_gdf.dissolve(by='name', as_index=False)

        print(f"Reading NIRF data from: {self.nirf_json_path}")
        with open(self.nirf_json_path, "r", encoding="utf-8") as f:
            self.ranking_data = json.load(f)

        self.india_merc = self.india_states.to_crs(epsg=3857)
        self.lines_gdf = self._generate_vertical_lines()
        
        self.bg_img = None
        self.bg_extent = None
        self.all_state_tallies = self._compute_all_state_tallies()

        # Pre-calculated common city coordinates fallback repository (Lon, Lat) 
        # Crucial for rendering pinpoint city layouts over broader state polygons

        with open(Config.GEO_COORDINATES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        transformed = {item["name"].upper(): (item["lon"], item["lat"]) for item in data}
        self.city_coordinates_db = transformed

    def _get_city_mercator_point(self, city_name, state_gdf):
        """Converts geographical city coordinates to EPSG:3857 Web Mercator tracking points."""
        city_key = str(city_name).strip().upper()
        if city_key in self.city_coordinates_db:
            lon, lat = self.city_coordinates_db[city_key]
            point_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")
            return point_gdf.to_crs(epsg=3857).geometry.iloc[0]
        
        # Fallback to state centroid if city coordinates are absent in dictionary
        return state_gdf.geometry.iloc[0].centroid

    def _generate_vertical_lines(self):
        lines = []
        longitudes = range(65, 100, 5)
        cmap = plt.colormaps['hsv'].resampled(len(longitudes))
        colors = []
        for i, lon in enumerate(longitudes):
            lines.append(LineString([(lon, 5), (lon, 40)]))
            colors.append(cmap(i))
        lines_gdf = gpd.GeoDataFrame({'geometry': lines, 'color': colors}, crs="EPSG:4326")
        return lines_gdf.to_crs(epsg=3857)

    def _prepare_static_background(self):
        fig_dummy, ax_dummy = plt.subplots(figsize=(10.8, 11.5), dpi=100)
        fig_dummy.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax_dummy.set_axis_off()
        
        if self.map_type == "satellite":
            edge_color = "#ffffff"
            line_alpha = 0.4
            grid_alpha = 0.25
            basemap_source = ctx.providers.Esri.WorldImagery
        else:
            edge_color = "#1e293b"
            line_alpha = 0.8
            grid_alpha = 0.15
            basemap_source = ctx.providers.CartoDB.PositronNoLabels

        self.india_merc.plot(ax=ax_dummy, facecolor="none" if self.map_type == "satellite" else "#f8fafc", 
                             edgecolor=edge_color, linewidth=0.8, alpha=line_alpha)
        
        for row in self.lines_gdf.itertuples():
            ax_dummy.plot(*row.geometry.xy, color=row.color, linewidth=0.5, alpha=grid_alpha)
            
        ctx.add_basemap(ax_dummy, source=basemap_source)
        
        bounds = self.india_merc.total_bounds
        ax_dummy.set_xlim(bounds[0] - 100000, bounds[2] + 450000)  
        ax_dummy.set_ylim(bounds[1] - 150000, bounds[3] + 500000)  
                
        fig_dummy.canvas.draw()
        self.bg_img = fig_dummy.canvas.buffer_rgba()
        self.bg_extent = [ax_dummy.get_xlim()[0], ax_dummy.get_xlim()[1], ax_dummy.get_ylim()[0], ax_dummy.get_ylim()[1]]
        plt.close(fig_dummy)

    def _compute_all_state_tallies(self):
        total_counts = {}
        for item in self.ranking_data:
            st = item["State"]
            code = self.state_abbrev.get(st, st[:2].upper())
            total_counts[code] = total_counts.get(code, 0) + 1
        return sorted(total_counts.items(), key=lambda x: (-x[1], x[0]))

    def _apply_axis_gradient(self, ax, theme):
        c1 = np.array(theme["bg1"]) / 255.0
        c2 = np.array(theme["bg2"]) / 255.0
        gradient = np.zeros((100, 1, 3))
        for y in range(100):
            ratio = y / 99.0
            gradient[y, 0, :] = c1 * (1.0 - ratio) + c2 * ratio
        ax.imshow(gradient, aspect='auto', extent=[0, 1, 0, 1], transform=ax.transAxes, zorder=-10)

    def _short_institute_name(self, name, rank_str):
        for k, v in self.inst_mappings.items():
            if name.startswith(k):
                name = name.replace(k, v)
                break
        rank = f'{int(rank_str):03d}'
        inst_short = f'{rank}_{name}'
        return inst_short.replace(" ", "_")

    def generate_video_with_voice(self, output_path="nirf_fixed_layout.mp4", seconds_per_item=6, fps=5):
        num_items = len(self.ranking_data)
        frames_per_item = seconds_per_item * fps
        total_frames = num_items * frames_per_item
        
        temp_video = "temp_silent_video.mp4"
        audio_folder = "temp_audio_clips"
        os.makedirs(audio_folder, exist_ok=True)

        self._prepare_static_background()

        fig = plt.figure(figsize=(10.8, 19.2), dpi=100, facecolor="#f8fafc")
        
        ax_header = fig.add_axes([0.0, 0.81, 1.0, 0.18])
        ax_map    = fig.add_axes([0.0, 0.18, 1.0, 0.63]) 
        ax_table  = fig.add_axes([0.0, 0.0, 1.0, 0.18])

        assigned_themes = [self.themes[idx % len(self.themes)] for idx in range(num_items)]

        def update_frame(frame_num):
            item_idx = min(frame_num // frames_per_item, num_items - 1)
            active_institute = self.ranking_data[item_idx]
            current_theme = assigned_themes[item_idx]
            
            theme_color_hex = '#%02x%02x%02x' % current_theme["bg2"]
            
            # --- 1. HEADER ZONE ---
            ax_header.clear()
            ax_header.axis('off')
            self._apply_axis_gradient(ax_header, current_theme)
            
            border = Rectangle((0.01, 0.03), 0.98, 0.94, transform=ax_header.transAxes,
                               edgecolor='#f59e0b', facecolor='none', linewidth=1.5)
            ax_header.add_patch(border)

            rank_str = str(active_institute["Rank"])
            inst_short = f"{self._short_institute_name(active_institute['Name'], active_institute['Rank'])}.png"
            
            logo_path = os.path.join(str(Config.LOGO_FOLDER), inst_short)
            campus_path = os.path.join(str(Config.CAMPUS_FOLDER), inst_short)

            if os.path.exists(logo_path):
                try:
                    with Image.open(logo_path) as img_raw:
                        img_logo = np.array(img_raw.convert("RGBA"))
                    imagebox_logo = OffsetImage(img_logo, zoom=0.50) 
                    ab_logo = AnnotationBbox(imagebox_logo, (0.12, 0.42), xycoords=ax_header.transAxes, frameon=False) 
                    ax_header.add_artist(ab_logo)
                except Exception as e:
                    print(f"\nWarning: Failed to load logo {logo_path}: {e}")

            if os.path.exists(campus_path):
                try:
                    with Image.open(campus_path) as img_raw:
                        img_campus = np.array(img_raw.convert("RGBA"))
                    imagebox_campus = OffsetImage(img_campus, zoom=0.50) 
                    ab_campus = AnnotationBbox(imagebox_campus, (0.88, 0.42), xycoords=ax_header.transAxes, frameon=False) 
                    ax_header.add_artist(ab_campus)
                except Exception as e:
                    print(f"\nWarning: Failed to load campus image {campus_path}: {e}")

            current_state = active_institute["State"].upper()
            current_city = active_institute.get("City", "").upper()
            tier = active_institute.get("Tier", "Tier 1")
            
            ax_header.text(0.50, 0.76, active_institute["Name"], transform=ax_header.transAxes,
                           fontsize=22, fontweight='bold', color="#bd2b2b" if self.map_type == "satellite" else "#0f172a", 
                           ha='center', va='center', wrap=True)
            
            ax_header.text(0.50, 0.58, f"{active_institute['City']}, {current_state}", transform=ax_header.transAxes,
                           fontsize=22, fontweight='semibold', color="#bd2b2b", ha='center', va='center')
            
            badge_txt = f"  NIRF Rank #{rank_str}  |  {tier}  "
            ax_header.text(0.50, 0.18, badge_txt, transform=ax_header.transAxes,
                           fontsize=22, fontweight='bold', color="#ffffff", ha='center', va='center',
                           bbox=dict(facecolor='#1e293b', alpha=0.85, edgecolor='#f59e0b', boxstyle='round,pad=0.4', linewidth=1.5))
        
            # --- 2. MAP ZONE (PINNING BY TRUE CITY COORDINATES) ---
            ax_map.clear()
            ax_map.axis('off')
            
            fig.patch.set_facecolor(np.array(current_theme["bg1"])/255.0)
            ax_map.imshow(self.bg_img, extent=self.bg_extent)
            
            state_gdf = self.india_merc[self.india_merc['name'].str.lower() == current_state.lower()]
            if not state_gdf.empty:
                map_edge = "#ffffff" if self.map_type == "satellite" else "#1e293b"
                state_gdf.plot(ax=ax_map, facecolor=theme_color_hex, edgecolor=map_edge, linewidth=3.0, alpha=0.85 if self.map_type == "satellite" else 0.95)
                
                # Fetch pinpoint city location instead of state centroid boundary
                city_loc = self._get_city_mercator_point(current_city, state_gdf)
                
                # Plot the Physical Map Pin at the city point location
                ax_map.scatter(city_loc.x, city_loc.y, s=200, color='#ef4444', edgecolor='#ffffff', linewidth=1.5, zorder=5) # Red Outer Pin
                ax_map.scatter(city_loc.x, city_loc.y, s=40, color='#ffffff', zorder=6) # Inner Pivot Core
                
                # Setup city label string layout
                indicator_text = f"{current_city}"
                
                # Plot Label box offset slightly above the specific City location pin to avoid overlapping lines
                ax_map.text(city_loc.x, city_loc.y + 75000, indicator_text, color='white',
                            fontsize=12, fontweight='bold', ha='center', va='center', zorder=7,
                            bbox=dict(facecolor='#1e293b', alpha=0.95, edgecolor='#ef4444', boxstyle='round,pad=0.4', linewidth=1.2))
                
                # Connecting structural line between the label box and city pinpoint anchor
                ax_map.plot([city_loc.x, city_loc.x], [city_loc.y, city_loc.y + 35000], color='#ef4444', linewidth=1.2, zorder=4)

            ax_map.set_xlim(self.bg_extent[0], self.bg_extent[1])
            ax_map.set_ylim(self.bg_extent[2], self.bg_extent[3])

            # --- 3. DASHBOARD FOOTER ---
            ax_table.clear()
            ax_table.axis('off')
            self._apply_axis_gradient(ax_table, current_theme)
            
            cols_per_row = 10
            num_badges = len(self.all_state_tallies)
            total_rows = (num_badges + cols_per_row - 1) // cols_per_row
            
            start_x, end_x = 0.02, 0.98
            start_y, end_y = 0.05, 0.95
            total_w, total_h = (end_x - start_x), (end_y - start_y)
            
            x_spacing = 0.006
            y_spacing = 0.03 if total_rows <= 3 else 0.01 
            
            box_width = (total_w - (x_spacing * (cols_per_row - 1))) / cols_per_row
            box_height = (total_h - (y_spacing * (total_rows - 1))) / total_rows
            
            active_code = self.state_abbrev.get(active_institute["State"], "")
            
            for index, (state_code, tally_count) in enumerate(self.all_state_tallies):
                row_idx = index // cols_per_row
                col_idx = index % cols_per_row
                
                b_x = start_x + col_idx * (box_width + x_spacing)
                b_y = end_y - (row_idx + 1) * box_height - (row_idx * y_spacing)
                
                is_active = (state_code == active_code)
                box_theme = self.themes[index % len(self.themes)]
                box_theme_hex = '#%02x%02x%02x' % box_theme["bg2"]
                
                card_bg = box_theme_hex if not is_active else "#0f172a"
                card_edge = theme_color_hex if is_active else "#475569"
                card_linewidth = 2.5 if is_active else 0.8
                
                card_patch = FancyBboxPatch((b_x, b_y), box_width, box_height, transform=ax_table.transAxes,
                                            boxstyle="round,pad=0.0,rounding_size=0.015",
                                            facecolor=card_bg, alpha=0.9, edgecolor=card_edge, 
                                            linewidth=card_linewidth, zorder=1)
                ax_table.add_patch(card_patch)
                
                state_text_color = "#ffffff" if is_active else "#1e293b"
                count_text_color = "#f8fafc" if is_active else "#1e293b"
                line_color = theme_color_hex if is_active else "#475569"

                font_scaler = 1.0 if total_rows <= 3 else 0.8
                
                ax_table.text(b_x + (box_width * 0.5), b_y + (box_height * 0.65), f"{state_code}", transform=ax_table.transAxes,
                              fontsize=14 * font_scaler, fontweight='bold', color=state_text_color, ha='center', va='center', zorder=2)
                
                ax_table.text(b_x + (box_width * 0.5), b_y + (box_height * 0.28), f"{tally_count}", transform=ax_table.transAxes,
                              fontsize=20 * font_scaler, fontweight='bold', color=count_text_color, ha='center', va='center', zorder=2)
                
                line_y = b_y + (box_height * 0.48)
                ax_table.plot([b_x + (box_width * 0.15), b_x + (box_width * 0.85)], [line_y, line_y], 
                              transform=ax_table.transAxes, color=line_color, linewidth=1.0, zorder=2)
                
            print(f"Rendering Video Frame: {frame_num + 1}/{total_frames}", end="\r")

        print("\n--- STEP 1: Rendering Restored Sizing Map Video ---")
        map_animation = animation.FuncAnimation(fig, update_frame, frames=total_frames, interval=1000/fps)
        video_writer = FFMpegWriter(fps=fps, bitrate=Config.VIDEO_SETTINGS["bitrate"])
        map_animation.save(temp_video, writer=video_writer)
        plt.close(fig)

        print("\n\n--- STEP 2: Generating Voice-Over Audio Scripts ---")
        audio_clips_timeline = []
        for idx, institute in enumerate(self.ranking_data):
            spoken_text = f"Rank {institute['Rank']}. {institute['Name']},{institute['State']} ."
            tts = gTTS(text=spoken_text, lang='en', slow=False)
            clip_path = os.path.join(audio_folder, f"audio_{idx}.mp3")
            tts.save(clip_path)
            
            start_time_seconds = idx * seconds_per_item
            audio_clip = AudioFileClip(clip_path).with_start(start_time_seconds)
            audio_clips_timeline.append(audio_clip)

        print("\n--- STEP 3: Multiplexing Audio tracks with Master Video Stream ---")
        video_clip = VideoFileClip(temp_video)
        composite_audio = CompositeAudioClip(audio_clips_timeline)
        
        final_video = video_clip.with_audio(composite_audio)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", audio_fps=44100, preset="medium", logger="bar")

        video_clip.close()
        composite_audio.close()
        final_video.close()
        
        if os.path.exists(temp_video):
            os.remove(temp_video)
        for idx in range(num_items):
            clip_path = os.path.join(audio_folder, f"audio_{idx}.mp3")
            if os.path.exists(clip_path):
                os.remove(clip_path)
        if os.path.exists(audio_folder):
            os.rmdir(audio_folder)
def main():
# #maps
    shape_file = str(Config.SHAPEFILE_PATH)
    nirf_file = str(Config.JSON_DATA_PATH)
    bgmAudioAdder=BgmAudioAdder()
    if os.path.exists(shape_file) and os.path.exists(nirf_file):
        print("✅ System paths validated! Processing corrected template clip configuration...")
        
        v_secs = Config.VIDEO_SETTINGS["seconds_per_item"]
        v_fps = Config.VIDEO_SETTINGS["fps"]
        
        for maptype in ["simple", "satellite"]:
            maker = NirfRankingMapVideosGenerator(map_type=maptype)
            
            # FIXED: Used correct Config attributes and wrapped Path logic correctly
            output_target_video = os.path.join(
                str(Config.BASE_DIR), 
                "outputs", 
                "videos", 
                f"NIRF_{Config.COURSE_NAME}_{Config.YEAR}_Ranking_{maptype}.mp4"
            )
            if not os.path.exists(output_target_video):
                os.makedirs(os.path.dirname(output_target_video), exist_ok=True)
                video_file=maker.generate_video_with_voice(output_path=output_target_video, seconds_per_item=v_secs, fps=v_fps)
            background_audio = Config.AUDIO_PATH
            bgmAudioAdder.add_bgm_inplace(output_target_video, background_audio)
    else:
        print("/n❌ Error: Paths Verification Failed. Please verify target directories in config.py.")

if __name__ == "__main__":
    main()