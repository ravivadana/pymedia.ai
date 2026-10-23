import os
import json
import numpy as np
import matplotlib
import shutil
import gc  # Added for explicit garbage collection memory management
from pathlib import Path

# Force Matplotlib to use a non-interactive backend
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Rectangle, Polygon
from matplotlib.path import Path as MPath  # Aliased to avoid conflict with pathlib.Path
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

import geopandas as gpd
import contextily as ctx
from shapely.geometry import LineString, Point
from gtts import gTTS
from PIL import Image

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.fx import MultiplyVolume  # Modern MoviePy v2 Effects import

# Internal custom configurations class file layer importing
from config import Config


class BgmAudioAdder:
    def add_bgm_inplace(self, video_path, bgm_path, bgm_volume=0.09):
        """
        Adds background music to a video file and overwrites the original video file safely.
        """
        if not os.path.exists(bgm_path):
            print(f"⚠️ BGM Audio file missing at: {bgm_path}. Skipping background music step.")
            return

        video_clip_path = Path(video_path)
        temp_output_path = video_clip_path.with_name(f"temp_bgm_{video_clip_path.name}")
        
        video = VideoFileClip(str(video_clip_path))
        bgm = AudioFileClip(str(bgm_path))
        
        # Adjust BGM duration (Trim or Loop to match the master video)
        if bgm.duration > video.duration:
            bgm = bgm.subclipped(0, video.duration)
        elif bgm.duration < video.duration:
            audio_segments = []
            current_time = 0
            while current_time < video.duration:
                if current_time + bgm.duration > video.duration:
                    segment = bgm.subclipped(0, video.duration - current_time)
                else:
                    segment = bgm
                audio_segments.append(segment.with_start(current_time))
                current_time += bgm.duration
            bgm = CompositeAudioClip(audio_segments)

        # Apply volume reduction using modern MoviePy v2 syntax
        bgm = bgm.with_effects([MultiplyVolume(bgm_volume)])

        # Combine voice track over background music
        if video.audio is not None:
            final_audio = CompositeAudioClip([video.audio, bgm])
        else:
            final_audio = bgm

        final_video = video.with_audio(final_audio)
        
        print(f"Adding Background Music to: {video_clip_path.name} (Volume: {bgm_volume})...")
        final_video.write_videofile(
            str(temp_output_path), 
            codec="libx264", 
            audio_codec="aac",
            logger=None
        )
        
        # Release handles explicitly to prevent WinError 145/32 on substitution
        video.close()
        bgm.close()
        final_video.close()
        
        try:
            if os.path.exists(video_clip_path):
                os.remove(video_clip_path)
            temp_output_path.rename(video_clip_path)
            print(f"🎵 Successfully mixed BGM into: {video_clip_path.name}")
        except Exception as e:
            print(f"❌ Error replacing original file with BGM track: {e}")


class WorldRankingMapVideosGenerator:
    def __init__(self, map_type="simple", json_filename=None, top_number_range=None):
        self.shape_world_file_path = str(Config.SHAPEFILE_PATH) 
        
        if json_filename:
            self.ranking_json_path = os.path.join(str(Config.DATA_DIR), json_filename)
        else:
            self.ranking_json_path = str(Config.JSON_DATA_PATH)
            
        self.map_type = map_type.lower()
        self.country_abbrev = Config.COUNTRIES_ABBREVIATIONS  
        self.themes = Config.THEMES
        self.inst_mappings = Config.INSTITUTE_MAPPINGS
        self.top_number_range = top_number_range

        # Standard desktop ratio layout configuration
        self.figsize = (19.2, 10.8)  # 1920 x 1080 standard desktop ratio

        print(f"Reading shapefile from: {self.shape_world_file_path}")
        if os.path.exists(self.shape_world_file_path) and self.shape_world_file_path.endswith('.shp'):
            raw_data = gpd.read_file(self.shape_world_file_path)
        else:
            print("Shapefile missing. Loading Geopandas fallback low-res maps...")
            raw_data = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        
        self.world_countries = raw_data[raw_data.geometry.notnull()].copy()

        print(f"Reading Ranking data from: {self.ranking_json_path}")
        with open(self.ranking_json_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)

        # Filters records safely based on index bounds derived from the range string
        if self.top_number_range and "-" in str(self.top_number_range):
            try:
                start_r, end_r = map(int, str(self.top_number_range).split("-"))
                
                # Convert 1-based human boundary input to absolute 0-indexed slice selections
                start_idx = max(0, start_r - 1)
                end_idx = end_r
                
                # Slice target index range segment out of full JSON array structure
                sliced_subset = full_data[start_idx:end_idx]
                
                # Keep your reverse ranking video countdown sorting pipeline (e.g., Rank 3 -> Rank 2 -> Rank 1)
                self.ranking_data = sorted(sliced_subset, key=lambda x: int(x.get("rank", 0)), reverse=True)
                print(f"✂️ Sliced records index {start_idx} to {end_idx - 1} ({self.top_number_range}). Elements: {len(self.ranking_data)}")
            except Exception as range_err:
                print(f"⚠️ Failed to slice custom target range '{top_number_range}'. Falling back to original payload: {range_err}")
                self.ranking_data = full_data
        else:
            self.ranking_data = full_data

        self.world_merc = self.world_countries.to_crs(epsg=3857)
        self.lines_gdf = self._generate_global_grid_lines()
        
        self.bg_img = None
        self.bg_extent = None
        self.city_coordinates_db = {}
        
        print(f"Loading and transforming coordinate file: {Config.GEO_COORDINATES_FILE}")
        with open(Config.GEO_COORDINATES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transformed = {}
        for item in data:
            city_name = str(item.get("name", "")).strip().upper()
            country_name = str(item.get("country", "")).strip().upper()
            if city_name and country_name:
                composite_key = f"{city_name}_{country_name}"
                transformed[composite_key] = (item["lon"], item["lat"])
        self.city_coordinates_db = transformed

    def _calculate_exact_audio_durations(self, audio_folder, base_fps, is_voice_over_required):
        """Reads durations from files or applies a uniform default if voice-over is skipped."""
        durations = []
        frames_milestones = []
        current_frame_accumulator = 0

        for idx in range(len(self.ranking_data)):
            exact_seconds = 4.0  # Default display time per university slide (seconds)
            
            if is_voice_over_required:
                clip_path = os.path.join(audio_folder, f"audio_{idx}.mp3")
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 3000:
                    try:
                        audio_clip = AudioFileClip(clip_path)
                        exact_seconds = audio_clip.duration + 0.4
                        audio_clip.close()
                    except Exception:
                        print(f"⚠️ Unable to parse track audio_{idx}.mp3 safely. Applying safety buffer timing.")

            calculated_frames = int(np.ceil(exact_seconds * base_fps))
            actual_seconds = calculated_frames / base_fps
            
            durations.append(actual_seconds)
            frames_milestones.append(current_frame_accumulator)
            current_frame_accumulator += calculated_frames

        return durations, frames_milestones, current_frame_accumulator

    def _get_city_mercator_point(self, city_name, country_name, country_gdf):
        """Retrieves point using composite keys to separate cities with identical names."""
        city_clean = str(city_name).strip()
        country_clean = str(country_name).strip()
        
        country_key = self.country_abbrev.get(country_clean, country_clean[:3].upper())
        lookup_composite_key = f"{city_clean.upper()}_{country_key}"
        
        if lookup_composite_key in self.city_coordinates_db:
            lon, lat = self.city_coordinates_db[lookup_composite_key]
            point_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")
            return point_gdf.to_crs(epsg=3857).geometry.iloc[0]
            
        prefix_to_match = f"{city_clean.upper()}_"
        for k, coords in self.city_coordinates_db.items():
            if k.startswith(prefix_to_match):
                lon, lat = coords
                point_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")
                return point_gdf.to_crs(epsg=3857).geometry.iloc[0]

        if not country_gdf.empty:
            return country_gdf.geometry.iloc[0].centroid
            
        return Point(0, 0)

    def _generate_global_grid_lines(self):
        lines = []
        longitudes = range(-180, 181, 30) 
        cmap = plt.colormaps['hsv'].resampled(len(longitudes))
        colors = []
        for i, lon in enumerate(longitudes):
            lines.append(LineString([(lon, -75), (lon, 75)])) 
            colors.append(cmap(i))
        lines_gdf = gpd.GeoDataFrame({'geometry': lines, 'color': colors}, crs="EPSG:4326")
        return lines_gdf.to_crs(epsg=3857)

    def _prepare_static_background(self):
        fig_dummy, ax_dummy = plt.subplots(figsize=self.figsize, dpi=100) 
        fig_dummy.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax_dummy.set_axis_off()
        
        if self.map_type == "satellite":
            edge_color = "#ffffff"
            line_alpha = 0.3
            grid_alpha = 0.20
            basemap_source = ctx.providers.Esri.WorldImagery
        else:
            edge_color = "#1e293b"
            line_alpha = 0.6
            grid_alpha = 0.10
            basemap_source = ctx.providers.CartoDB.PositronNoLabels

        self.world_merc.plot(ax=ax_dummy, facecolor="none" if self.map_type == "satellite" else "#f8fafc", 
                             edgecolor=edge_color, linewidth=0.5, alpha=line_alpha)
        
        for row in self.lines_gdf.itertuples():
            ax_dummy.plot(*row.geometry.xy, color=row.color, linewidth=0.4, alpha=grid_alpha)
            
        ctx.add_basemap(ax_dummy, source=basemap_source)
        
        ax_dummy.set_xlim(-20037508.34, 20037508.34)
        ax_dummy.set_ylim(-6500000.00, 16037508.34)
            
        fig_dummy.canvas.draw()
        
        self.bg_img = np.array(fig_dummy.canvas.buffer_rgba()).copy()
        self.bg_extent = [ax_dummy.get_xlim()[0], ax_dummy.get_xlim()[1], ax_dummy.get_ylim()[0], ax_dummy.get_ylim()[1]]
        plt.close(fig_dummy)

    def generate_audio_scripts(self, audio_folder):
        """Generates the TTS voice files once with robust file integrity verification."""
        import time

        print("\n--- STEP 1: Generating Global Voice-Over Audio Scripts (gTTS) ---")
        os.makedirs(audio_folder, exist_ok=True)
        
        for idx, institute in enumerate(self.ranking_data):
            clip_path = os.path.join(audio_folder, f"audio_{idx}.mp3")
            
            if os.path.exists(clip_path):
                if os.path.getsize(clip_path) < 3000: 
                    print(f"⚠️ Found corrupted or incomplete cache file for asset #{idx}. Purging...")
                    try: os.remove(clip_path)
                    except: pass

            if os.path.exists(clip_path):
                continue

            rank_str = str(institute.get("rank", "0"))
            country_str = institute.get("country_territory", institute.get("Country", ""))
            spoken_text = f"Rank {rank_str}. {institute['institution_name']}, {country_str}."
            
            tts = gTTS(text=spoken_text, lang='en', slow=False)
            
            max_retries = 5
            backoff_delay = 3.0  
            
            for attempt in range(max_retries):
                try:
                    print(f"Generating audio {idx + 1}/{len(self.ranking_data)} (Attempt {attempt + 1})...", end="\r")
                    tts.save(clip_path)
                    
                    if os.path.exists(clip_path) and os.path.getsize(clip_path) < 3000:
                        raise ValueError("Google returned an empty file or HTML block page instead of MP3 data.")
                        
                    time.sleep(0.5)
                    break
                except Exception as e:
                    if os.path.exists(clip_path):
                        try: os.remove(clip_path)
                        except: pass
                        
                    if attempt < max_retries - 1:
                        sleep_time = backoff_delay * (attempt + 1)
                        print(f"\n⚠️ Step failure at item #{idx}. Retrying in {sleep_time}s... Error: {e}")
                        time.sleep(sleep_time)
                    else:
                        print(f"\n❌ Permanent connection block reached at script index line entry #{idx}.")
                        raise e
                    
    def generate_video_with_voice(self, output_path, audio_folder, is_voice_over_required, fps=5, bitrate=4000000):
        num_items = len(self.ranking_data)
        if num_items == 0:
            print("❌ No items inside specified subset partition range. Skipping render cycle execution.")
            return
        
        # Calculate timeline milestones adaptively based on parameter toggling
        durations, milestones, total_frames = self._calculate_exact_audio_durations(audio_folder, fps, is_voice_over_required)
        
        temp_video = "temp_silent_video.mp4"
        self._prepare_static_background()

        fig = plt.figure(figsize=self.figsize, dpi=100, facecolor="#f8fafc")
        ax_map = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        assigned_themes = [self.themes[idx % len(self.themes)] for idx in range(num_items)]

        def update_frame(frame_num):
            item_idx = num_items - 1
            for idx in range(num_items - 1):
                if milestones[idx] <= frame_num < milestones[idx + 1]:
                    item_idx = idx
                    break
                    
            active_institute = self.ranking_data[item_idx]
            current_theme = assigned_themes[item_idx]
            theme_color_hex = '#%02x%02x%02x' % current_theme["bg2"]
            
            rank_str = str(active_institute.get("rank", "0"))
            current_country = active_institute.get("country_territory", active_institute.get("Country", ""))
            current_city = active_institute.get("city", "")
            
            ax_map.clear()
            ax_map.axis('off')
            fig.patch.set_facecolor(np.array(current_theme["bg1"])/255.0)
            ax_map.imshow(self.bg_img, extent=self.bg_extent, aspect='auto')
            
            country_gdf = gpd.GeoDataFrame()
            search_country = current_country.strip().lower()
            
            if "united states" in search_country or "usa" == search_country: 
                search_country = "united states of america"
            elif "united kingdom" in search_country or "uk" == search_country: 
                search_country = "united kingdom"
            
            for col in ['name', 'NAME', 'admin', 'name_long']:
                if col in self.world_merc.columns:
                    matched_rows = self.world_merc[
                        self.world_merc[col].str.lower().apply(lambda x: x in search_country or search_country in x if x else False)
                    ]
                    if not matched_rows.empty:
                        country_gdf = matched_rows
                        break
            
            if not country_gdf.empty:
                map_edge = "#ffffff" if self.map_type == "satellite" else "#1e293b"
                xmin, ymin, xmax, ymax = country_gdf.total_bounds
                flag_filename = f"{search_country}_flag.png"
                flag_path = os.path.join(Config.COUNTRY_FLAGS_DIR, flag_filename)
                
                if not os.path.exists(flag_path):
                    flag_filename_simple = f"{current_country.strip().lower()}_flag.png"
                    flag_path = os.path.join(Config.COUNTRY_FLAGS_DIR, flag_filename_simple)

                try:
                    if os.path.exists(flag_path):
                        with Image.open(flag_path) as img:
                            flag_frame = img.convert("RGB")
                            flag_array = np.array(flag_frame)
                        
                        paths = []
                        for geom in country_gdf.geometry:
                            if geom.geom_type == 'Polygon':
                                paths.append(MPath(np.array(geom.exterior.coords)))
                            elif geom.geom_type == 'MultiPolygon':
                                for sub_geom in geom.geoms:
                                    paths.append(MPath(np.array(sub_geom.exterior.coords)))
                        
                        if paths:
                            combined_path = MPath.make_compound_path(*paths)
                            patch = mpatches.PathPatch(combined_path, facecolor='none', edgecolor=map_edge, linewidth=1.5)
                            im = ax_map.imshow(flag_array, extent=[xmin, xmax, ymin, ymax], aspect='auto', zorder=2)
                            ax_map.add_patch(patch)
                            im.set_clip_path(patch)
                    else:
                        country_gdf.plot(ax=ax_map, facecolor=theme_color_hex, edgecolor=map_edge, linewidth=1.2, alpha=0.90, aspect='auto', zorder=2)
                except Exception:
                    country_gdf.plot(ax=ax_map, facecolor=theme_color_hex, edgecolor=map_edge, linewidth=1.2, alpha=0.90, aspect='auto', zorder=2)
            
            city_loc = self._get_city_mercator_point(current_city, current_country, country_gdf)
            ax_map.scatter(city_loc.x, city_loc.y, s=150, color='#ef4444', edgecolor='#ffffff', linewidth=1.2, zorder=5) 
            ax_map.scatter(city_loc.x, city_loc.y, s=30, color='#ffffff', zorder=6) 
            
            location_string = f"{current_city}, {current_country}" if active_institute.get('City') else current_country
            box_facecolor = '#f54927' if self.map_type == "satellite" else '#1e293b'

            locator_info_text = (
                f"{active_institute['institution_name']}\n"
                f"{location_string}\n"
                f"Rank #{rank_str}  |  overall_score: {active_institute.get('overall_score', 'N/A')}"
            )
            
            global_year = getattr(Config, 'YEAR', 2027)
            # Updates top banner layout explicitly referencing slice boundaries
            display_range = self.top_number_range if self.top_number_range else f"Top {num_items}"
            title_banner_text = f"Universities in the World {global_year} Ranking ({display_range})"
            
            ax_map.text(
                0.5, 0.98, title_banner_text,
                color='white', fontsize=34, fontweight='bold', ha='center', va='top', zorder=8,
                transform=ax_map.transAxes,
                bbox=dict(facecolor='#ef4444', alpha=0.95, edgecolor='#ffffff', boxstyle='round,pad=0.5', linewidth=1.5)
            )

            infobox_x_axes = 0.5
            infobox_y_axes = 0.85

            text_obj = ax_map.text(
                infobox_x_axes, infobox_y_axes, locator_info_text, 
                color='white', fontsize=30, fontweight='bold', ha='center', va='top', zorder=7,
                transform=ax_map.transAxes,
                bbox=dict(facecolor=box_facecolor, alpha=0.95, edgecolor='#ffffff' if self.map_type == "satellite" else '#ef4444', boxstyle='round,pad=0.8', linewidth=2.0)
            )

            try:
                fig.canvas.draw()
                bbox_window = text_obj.get_window_extent()
                infobox_bottom_pixel = (bbox_window.x0 + bbox_window.width / 2, bbox_window.y0)
                infobox_bottom_data = ax_map.transData.inverted().transform(infobox_bottom_pixel)
                
                ax_map.plot(
                    [city_loc.x, infobox_bottom_data[0]], [city_loc.y, infobox_bottom_data[1]], 
                    color='#ef4444', linewidth=2.0, linestyle='-', alpha=0.85, zorder=4
                )
            except Exception:
                fallback_data = ax_map.transData.inverted().transform(ax_map.transAxes.transform((0.5, 0.68)))
                ax_map.plot(
                    [city_loc.x, fallback_data[0]], [city_loc.y, fallback_data[1]], 
                    color='#ef4444', linewidth=2.0, linestyle='-', alpha=0.85, zorder=4
                )
                
            ax_map.set_xlim(self.bg_extent[0], self.bg_extent[1])
            ax_map.set_ylim(self.bg_extent[2], self.bg_extent[3])
            print(f"Rendering Map Animation Frame: {frame_num + 1}/{total_frames}", end="\r")

        print("\n--- STEP 2: Compiling Video Matrix Tracks ---")
        map_animation = animation.FuncAnimation(fig, update_frame, frames=total_frames, interval=1000/fps)
        video_writer = FFMpegWriter(fps=fps, bitrate=bitrate)
        map_animation.save(temp_video, writer=video_writer)
        plt.close(fig)

        video_clip = VideoFileClip(temp_video)

        # Conditional timeline compilation for audio layers
        if is_voice_over_required:
            print("\n--- STEP 3: Stitching Audio Timelines ---")
            audio_clips_timeline = []
            current_time_marker = 0.0
            for idx in range(num_items):
                clip_path = os.path.join(audio_folder, f"audio_{idx}.mp3")
                audio_clip = AudioFileClip(clip_path).with_start(current_time_marker)
                audio_clips_timeline.append(audio_clip)
                current_time_marker += durations[idx]

            composite_audio = CompositeAudioClip(audio_clips_timeline)
            final_video = video_clip.with_audio(composite_audio)
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", audio_fps=44100, preset="medium", logger=None)
            
            composite_audio.close()
            for c in audio_clips_timeline:
                c.close()
        else:
            print("\n--- STEP 3: Skipping Voice Tracks (Writing Base Silent Track) ---")
            video_clip.write_videofile(output_path, codec="libx264", preset="medium", logger=None)

        video_clip.close()
        if os.path.exists(temp_video): 
            os.remove(temp_video)


def create_mobile_video_from_desktop(desktop_video_path, mobile_video_path):
    """Takes the widescreen desktop video and embeds it inside 1080x1920 mobile aspect ratios."""
    from moviepy.video.VideoClip import ColorClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

    print(f"\n--- STEP 4: Creating True 9:16 Vertical Video (1080x1920) ---")
    clip = VideoFileClip(desktop_video_path)
    
    video_width = 1080
    scaled_clip = clip.resized(width=video_width)
    
    background_rgb = (248, 250, 252) 
    background = ColorClip(size=(1080, 1920), color=background_rgb, duration=clip.duration)
    
    positioned_clip = scaled_clip.with_position(('center', 'center'))
    final_clip = CompositeVideoClip([background, positioned_clip])
    
    # Check if input desktop video has audio, to avoid runtime crash on vertical write configuration layers
    if clip.audio is not None:
        final_clip.write_videofile(mobile_video_path, codec="libx264", audio_codec="aac", preset="medium", logger=None)
    else:
        final_clip.write_videofile(mobile_video_path, codec="libx264", preset="medium", logger=None)
    
    clip.close()
    scaled_clip.close()
    background.close()
    final_clip.close()


def main(year, map_types, video_types, is_voice_over_required=True, top_number_range=None):
    print("✅ Initializing configuration files...")
    Config.initialize_dirs()
    
    Config.YEAR = year
    filename = str(Config.JSON_DATA_PATH.name)
    
    custom_settings = {
        "fps": 5,
        "bitrate": 4000000 
    }
    
    v_fps = custom_settings["fps"]
    v_bitrate = custom_settings["bitrate"]
    audio_folder = "temp_audio_clips"
    
    bgm_file_track = str(Config.AUDIO_PATH)
    bgm_mixer = BgmAudioAdder()
    
    # Configure BGM volume adjustments dynamically
    calculated_bgm_volume = 0.09 if is_voice_over_required else 1.0
    
    if map_types and is_voice_over_required:
        base_maker = WorldRankingMapVideosGenerator(map_type=map_types[0], json_filename=filename, top_number_range=top_number_range)
        if len(base_maker.ranking_data) > 0:
            base_maker.generate_audio_scripts(audio_folder)
    
    for map_type in map_types:
        maker = WorldRankingMapVideosGenerator(map_type=map_type, json_filename=filename, top_number_range=top_number_range)
        
        if len(maker.ranking_data) == 0:
            continue
            
        suffix = f"_{top_number_range}" if top_number_range else ""
        desktop_video_output = os.path.join(
            str(Config.OUTPUT_DIR), 
            f"Global_{Config.COURSE_NAME}_{year}_Ranking_{map_type}{suffix}_desktop.mp4"
        )
        os.makedirs(os.path.dirname(desktop_video_output), exist_ok=True)
        
        # Render Desktop Video Track
        maker.generate_video_with_voice(
            output_path=desktop_video_output, 
            audio_folder=audio_folder, 
            is_voice_over_required=is_voice_over_required,
            fps=v_fps,
            bitrate=v_bitrate
        )
        
        if "desktop" in video_types:
            bgm_mixer.add_bgm_inplace(desktop_video_output, bgm_file_track, bgm_volume=calculated_bgm_volume)
        
        if "mobile" in video_types:
            mobile_video_output = os.path.join(
                str(Config.OUTPUT_DIR), 
                f"Global_{Config.COURSE_NAME}_{year}_Ranking_{map_type}{suffix}_mobile.mp4"
            )
            create_mobile_video_from_desktop(desktop_video_output, mobile_video_output)
            bgm_mixer.add_bgm_inplace(mobile_video_output, bgm_file_track, bgm_volume=calculated_bgm_volume)
            
            if "desktop" not in video_types:
                if os.path.exists(desktop_video_output):
                    os.remove(desktop_video_output)
                    
        # Explicitly run clean garbage collection after every map configuration step loops to prevent memory leaks
        gc.collect()
                    
    if os.path.exists(audio_folder):
        try:
            shutil.rmtree(audio_folder)
            print(f"🗑️ Successfully cleaned up intermediate audio tracks completely.")
        except Exception as e:
            print(f"⚠️ Non-blocking filesystem sync hold encountered: {e}")


if __name__ == "__main__":
    main(
        year=2027, 
        map_types=["simple", "satellite"], 
        video_types=["desktop", "mobile"],
        is_voice_over_required=True,
        top_number_range="1-3"  # Slice index 0 to 2 out of the ranking database arrays
    )