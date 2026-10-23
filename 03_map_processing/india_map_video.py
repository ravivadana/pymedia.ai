import os
import sys
import json
import re
from pathlib import Path
import numpy as np
import geopandas as gpd
import matplotlib

# Set non-interactive backend before importing pyplot
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

# Tile Basemap Library
import contextily as cx

# Audio & Video Rendering (Using built-in Microsoft SAPI5 via pyttsx3)
import pyttsx3
from moviepy import ImageSequenceClip, AudioFileClip, CompositeAudioClip


# ==========================================================
# CONFIGURATION & PATH SETUP
# ==========================================================
class Config:
    BASE_DIR = Path(__file__).resolve().parent
    ASSETA_BASE_DIR = Path(r"C:\Ravi\Python\2025\Media")
    ASSETS_DIR = ASSETA_BASE_DIR / "assets"
    INDIA_ASSETS = ASSETS_DIR / "india"
    MAPS_ASSETS = ASSETS_DIR / "common" / "maps"
    OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
    TEMP_DIR = BASE_DIR / "outputs" / "temp"

    JSON_DATA_PATH = INDIA_ASSETS / "airports.json"
    SHAPEFILE_PATH = MAPS_ASSETS / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
    BGM_PATH = INDIA_ASSETS / "audios" / "ilovemyindia.webm"

    @classmethod
    def ensure_directories(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# DATA LOADER & PREPROCESSOR
# ==========================================================
class AirportDataLoader:
    def __init__(self, json_path, shapefile_path):
        self.json_path = Path(json_path)
        self.shapefile_path = Path(shapefile_path)

    def load_data(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"Missing airport data at: {self.json_path}")
        if not self.shapefile_path.exists():
            raise FileNotFoundError(f"Missing shapefile maps at: {self.shapefile_path}")

        # Safe JSON Reading
        with open(self.json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            if isinstance(raw_data, dict):
                airports = raw_data.get("airports", raw_data.get("data", list(raw_data.values())))
            else:
                airports = raw_data

        # Ensure airports is a list of dicts
        if not isinstance(airports, list):
            airports = list(airports)

        # Sort by rank if available
        airports.sort(key=lambda x: int(x.get('rank_by_size', 999)) if isinstance(x, dict) else 999)
        
        # Load map spatial bounds & convert to Web Mercator (EPSG:3857) for Satellite Tiles
        world_gdf = gpd.read_file(self.shapefile_path).to_crs(epsg=3857)

        india_gdf = world_gdf[world_gdf['admin'] == 'India'].copy()
        india_gdf['color_id'] = np.arange(len(india_gdf))  # Assign color index per state

        neighbors_gdf = world_gdf[world_gdf['admin'] != 'India'].copy()

        return airports, india_gdf, neighbors_gdf


# ==========================================================
# HD SATELLITE MAP & CARD GENERATOR
# ==========================================================
class HDMapVisualizer:
    def __init__(self, width=1080, height=1920, dpi=150):
        # 9:16 Vertical Video Canvas Format
        self.width = width
        self.height = height
        self.dpi = dpi

    def render_airport_frame(self, india_gdf, neighbors_gdf, current_airport, rank, total_items, output_frame_path):
        """
        Renders an HD 9:16 vertical satellite frame where both the top header and location indicator 
        share the exact same clean text-stroke styling with orange (#F77F00).
        """
        fig = plt.figure(figsize=(self.width / 100, self.height / 100), dpi=self.dpi)
        ax = fig.add_axes([0, 0, 1, 1])  # Occupy 100% of canvas area
        
        # Set background fill color to match greenish-blue tone (#0A9396)
        fig.patch.set_facecolor('#0A9396')
        ax.set_facecolor('#0A9396')

        # LAYER 1: Neighboring Countries
        neighbors_gdf.plot(
            ax=ax,
            facecolor='#000000',
            edgecolor='#475569',
            linewidth=0.6,
            alpha=0.45,
            zorder=2
        )

        # LAYER 2: Multi-Colored Indian States
        india_gdf.plot(
            ax=ax,
            column='color_id',
            cmap='tab20',
            edgecolor='#FFFFFF',
            linewidth=0.8,
            alpha=0.45,
            zorder=3
        )

        # BOUNDS TO FILL SCREEN HEIGHT COMPLETELY
        minx, miny, maxx, maxy = india_gdf.total_bounds
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        
        y_range = (maxy - miny) * 1.35
        x_range = y_range * (9 / 16)

        xmin_val = center_x - x_range / 2
        xmax_val = center_x + x_range / 2
        ymin_val = center_y - y_range / 2
        ymax_val = center_y + y_range / 2

        ax.set_xlim(xmin_val, xmax_val)
        ax.set_ylim(ymin_val, ymax_val)
        ax.axis('off')

        # LAYER 0: Satellite Imagery Basemap
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=1, reset_extent=False)

        # TOP HEADER: Total Airports Count in Country Name (Styled with orange stroke effect matching indicator)
        header_text = f"{total_items} AIRPORTS IN INDIA"
        header_text_obj = fig.text(
            0.5, 0.93, header_text,
            fontsize=22,
            fontweight='black',
            color='#FFFFFF',
            ha='center',
            va='center',
            zorder=12
        )
        header_text_obj.set_path_effects([
            path_effects.Stroke(linewidth=7, foreground='#F77F00'),  # Orange outer stroke
            path_effects.Normal()
        ])

        # LAYER 3: CLASSIC MAP LOCATOR PIN & TITLE PLACED MUCH CLOSER ABOVE IT
        lat = float(current_airport.get('latitude', 0))
        lon = float(current_airport.get('longitude', 0))

        title_y_normalized = 0.75 

        if lat != 0 and lon != 0:
            pt_gdf = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy([lon], [lat]),
                crs="EPSG:4326"
            ).to_crs(epsg=3857)

            x = pt_gdf.geometry.iloc[0].x
            y = pt_gdf.geometry.iloc[0].y

            # Render Classic Map-Pin Marker
            ax.scatter(x, y, color='#D90429', s=1800, marker='o', edgecolor='#FFFFFF', linewidth=2.5, zorder=7)
            ax.scatter(x, y, color='#FFFFFF', s=350, marker='o', zorder=8)
            ax.plot([x, x], [y - (y_range * 0.04), y], color='#FFFFFF', linewidth=4, zorder=6)

            # Calculate normalized screen Y position from map coordinate y
            normalized_y = (y - ymin_val) / (ymax_val - ymin_val)
            
            # Position the title closely above the pin indicator
            title_y_normalized = float(np.clip(normalized_y + 0.06, 0.05, 0.92))

        # LOCATION TITLE STYLED WITH ORANGE STROKE (#F77F00)
        airport_name = str(current_airport.get('name', 'Unknown Airport')).upper()
        city_state = f"{current_airport.get('city', 'N/A')}, {current_airport.get('state', '')}".upper()

        main_card_text = (
            f"{airport_name}\n"
            f"{city_state}"
        )

        title_text_obj = fig.text(
            0.5, title_y_normalized, main_card_text,
            fontsize=17,
            fontweight='black',
            color='#FFFFFF',
            ha='center',
            va='center',
            zorder=10
        )
        
        # Apply orange stroke path effect
        title_text_obj.set_path_effects([
            path_effects.Stroke(linewidth=7, foreground='#2735F5'),  # Orange outer stroke
            path_effects.Normal()
        ])

        plt.savefig(output_frame_path, facecolor=fig.get_facecolor(), dpi=self.dpi)
        plt.close(fig)


# ==========================================================
# VIDEO & AUDIO COMPOSITOR (WITH OPTIONAL VOICE OVER)
# ==========================================================
class VideoMaker:
    def __init__(self, ranking_data, india_gdf, neighbors_gdf):
        self.ranking_data = ranking_data
        self.india_gdf = india_gdf
        self.neighbors_gdf = neighbors_gdf
        self.visualizer = HDMapVisualizer()

    def generate_video(self, output_path, seconds_per_item=6, fps=30, enable_voice=True):
        Config.ensure_directories()

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass

        expanded_frame_paths = []
        audio_clips_timeline = []
        total_items = len(self.ranking_data)
        frames_per_item = int(seconds_per_item * fps)

        print("\n--- STEP 1: Rendering Satellite Map Frames ---")
        for idx, airport in enumerate(self.ranking_data):
            frame_img_path = Config.TEMP_DIR / f"frame_{idx:03d}.png"
            
            self.visualizer.render_airport_frame(
                self.india_gdf,
                self.neighbors_gdf,
                current_airport=airport,
                rank=idx + 1,
                total_items=total_items,
                output_frame_path=frame_img_path
            )
            
            expanded_frame_paths.extend([str(frame_img_path)] * frames_per_item)
            print(f"Rendered [{idx+1}/{total_items}]: {airport.get('name')} (Lat: {airport.get('latitude')}, Lon: {airport.get('longitude')})")

        video_clip = ImageSequenceClip(expanded_frame_paths, fps=fps)
        final_audio = None

        # STEP 2: Synthesize Audio via Microsoft Speech Engine (SAPI5) if enabled
        if enable_voice:
            print("\n--- STEP 2: Synthesizing Audio via Microsoft Speech Engine (SAPI5) ---")
            tts_engine = pyttsx3.init('sapi5')
            tts_engine.setProperty('rate', 150)
            tts_engine.setProperty('volume', 1.0)

            for idx, airport in enumerate(self.ranking_data):
                city = airport.get('city', '')
                city_info = f"in {city}" if city else ""
                
                raw_name = str(airport.get('name', 'Airport'))
                clean_name = re.sub(r'[^\w\s,\.-]', '', raw_name)
                spoken_text = f"{clean_name}, {city_info}."

                clip_path = str(Config.TEMP_DIR / f"audio_{idx:03d}.wav")
                
                tts_engine.save_to_file(spoken_text, clip_path)
                tts_engine.runAndWait()

                start_time = idx * seconds_per_item
                audio_clip = AudioFileClip(clip_path)

                max_duration = seconds_per_item - 0.5
                if audio_clip.duration > max_duration:
                    audio_clip = audio_clip.subclipped(0, max_duration)

                audio_clip = audio_clip.with_start(start_time)
                audio_clips_timeline.append(audio_clip)

            composite_voice = CompositeAudioClip(audio_clips_timeline)

            # Background Music Setup
            if Config.BGM_PATH.exists():
                bgm_clip = AudioFileClip(str(Config.BGM_PATH)).with_volume_scaled(0.15)
                
                if bgm_clip.duration < video_clip.duration:
                    repeats = int(np.ceil(video_clip.duration / bgm_clip.duration))
                    bgm_clip = CompositeAudioClip([
                        bgm_clip.with_start(i * bgm_clip.duration) for i in range(repeats)
                    ]).subclipped(0, video_clip.duration)
                else:
                    bgm_clip = bgm_clip.subclipped(0, video_clip.duration)

                final_audio = CompositeAudioClip([composite_voice, bgm_clip])
            else:
                final_audio = composite_voice
        else:
            print("\n--- STEP 2: Voiceover Skipped (enable_voice=False) ---")
            if Config.BGM_PATH.exists():
                bgm_clip = AudioFileClip(str(Config.BGM_PATH)).with_volume_scaled(0.15)
                if bgm_clip.duration < video_clip.duration:
                    repeats = int(np.ceil(video_clip.duration / bgm_clip.duration))
                    bgm_clip = CompositeAudioClip([
                        bgm_clip.with_start(i * bgm_clip.duration) for i in range(repeats)
                    ]).subclipped(0, video_clip.duration)
                else:
                    bgm_clip = bgm_clip.subclipped(0, video_clip.duration)
                final_audio = bgm_clip

        if final_audio is not None:
            video_clip = video_clip.with_audio(final_audio)

        print(f"\n--- STEP 3: Exporting Final Video to {output_path} ---")
        video_clip.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac' if final_audio else None,
            preset='medium',
            bitrate='8000k'
        )

        if enable_voice:
            composite_voice.close()
            for clip in audio_clips_timeline:
                clip.close()
        
        if final_audio is not None:
            final_audio.close()

        print("\n Video Export Successfully Completed!")


# ==========================================================
# MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    Config.ensure_directories()

    print("Loading Airport Data, Map Vectors, and Tile Reprojections...")
    loader = AirportDataLoader(Config.JSON_DATA_PATH, Config.SHAPEFILE_PATH)
    airports_data, india_map, neighbors_map = loader.load_data()

    video_maker = VideoMaker(airports_data, india_map, neighbors_map)

    output_video_file = str(Config.OUTPUT_DIR / "India_Airports_Satellite_Ranking.mp4")

    # Set enable_voice to True or False based on your preference here:
    video_maker.generate_video(
        output_path=output_video_file,
        seconds_per_item=6,
        fps=30,
        enable_voice=True  # Toggle voiceover on/off easily
    )