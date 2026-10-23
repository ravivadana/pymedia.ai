import os
import json
import matplotlib
import shutil
import random
import urllib.request
from io import BytesIO
from pathlib import Path

# Force Matplotlib to use a non-interactive backend
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import PathPatch
import matplotlib.path as mpath
import geopandas as gpd
from PIL import Image
import numpy as np

# MoviePy v2 compatible imports
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip, concatenate_audioclips

# Import the configured dependency layer
from config import Config

def log_message(message):
    log_line = f"[{Config.TOURNAMENT_NAME} {Config.YEAR}] {message}\n"
    print(message)
    with open(Config.LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

def build_tournament_timeline(tournament_data):
    stage_order = [
        "group_stage_teams",
        "round_of_32_teams",
        "round_of_16_teams",
        "quarter_finals_teams",
        "semi_finals_teams",
        "finals_teams",
        "winner"
    ]
    
    timeline = []
    for stage_key in stage_order:
        if stage_key in tournament_data:
            teams = tournament_data[stage_key]
            if isinstance(teams, str):
                teams = [teams]
            if teams:
                cleaned_teams = {str(t).strip().lower() for t in teams}
                timeline.append({
                    "stage_name": stage_key.replace("_teams", "").replace("_", " ").title(),
                    "teams": cleaned_teams
                })
    return timeline

def get_deterministic_color(country_name):
    random.seed(hash(country_name.lower()))
    return "#%06x" % random.randint(0x222222, 0xDDDDDD)

def plot_single_polygon_flag(ax, poly, img_array):
    """Renders and clips the flag texture array to a single polygon geometry."""
    try:
        bounds = poly.bounds  
        extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
        
        ext_coords = np.array(poly.exterior.coords)
        path = mpath.Path(ext_coords)
        patches = [PathPatch(path, facecolor='none', edgecolor='none')]
        
        for interior in poly.interiors:
            int_coords = np.array(interior.coords)
            path_hole = mpath.Path(int_coords)
            patches.append(PathPatch(path_hole, facecolor='none', edgecolor='none'))

        im = ax.imshow(img_array, origin='upper', extent=extent, aspect='auto', zorder=2)
        
        for patch in patches:
            ax.add_patch(patch)
            im.set_clip_path(patch)
        return True
    except Exception:
        return False

def plot_country_with_flag_texture(ax, geometry, flag_path):
    """Breaks down MultiPolygons to project textures cleanly without distortion."""
    if not flag_path or not flag_path.exists():
        return False
        
    try:
        img = Image.open(flag_path).convert("RGBA")
        img_array = np.array(img)
        
        if geometry.geom_type == 'Polygon':
            polys = [geometry]
        elif geometry.geom_type == 'MultiPolygon':
            polys = list(geometry.geoms)
        else:
            return False

        success = False
        for poly in polys:
            if poly.area < 0.05: 
                continue
            if plot_single_polygon_flag(ax, poly, img_array):
                success = True
                
        return success
    except Exception:
        return False

def build_stitched_audio(tournament_timeline, total_video_duration):
    """
    Sequentially builds an audio track by checking active teams per stage
    and concatenating their corresponding pre-recorded country mp3 files.
    """
    log_message("Compiling stage-by-stage country audio sequences...")
    audio_clips_list = []
    audio_dir = Path(Config.AUDIO_DIR) if hasattr(Config, 'AUDIO_DIR') else Path("./audio")
    
    total_stages = len(tournament_timeline)
    duration_per_stage = total_video_duration / total_stages

    for stage in tournament_timeline:
        stage_audio_clips = []
        
        for team in sorted(list(stage["teams"])):
            clean_name = team.strip().lower().replace(" ", "_")
            audio_path = audio_dir / f"{clean_name}.mp3"
            
            if audio_path.exists():
                try:
                    stage_audio_clips.append(AudioFileClip(str(audio_path)))
                except Exception as e:
                    log_message(f"Could not load audio file {audio_path}: {e}")
            else:
                log_message(f"Warning: Audio file missing for team: {audio_path.name}")
        
        if stage_audio_clips:
            combined_stage_audio = concatenate_audioclips(stage_audio_clips)
            
            if combined_stage_audio.duration > duration_per_stage:
                combined_stage_audio = combined_stage_audio.with_duration(duration_per_stage)
            else:
                combined_stage_audio = combined_stage_audio.with_duration(duration_per_stage)
                
            audio_clips_list.append(combined_stage_audio)
        else:
            from moviepy.audio.AudioClip import AudioClip
            silence = AudioClip(lambda t: 0, duration=duration_per_stage)
            audio_clips_list.append(silence)
            
    if audio_clips_list:
        return concatenate_audioclips(audio_clips_list)
    return None

def generate_elimination_video(output_path, world_df, tournament_timeline, is_audio_required=True, map_style="simple"):
    log_message(f"Initializing video canvas with map style: {map_style}...")
    
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])

    frames_per_stage = 24  
    total_stages = len(tournament_timeline)
    total_frames = total_stages * frames_per_stage
    fps = Config.VIDEO_SETTINGS["fps"]
    total_video_duration = total_frames / fps

    # Pre-load satellite texture if needed
    satellite_img_array = None
    if map_style == "satellite":
        satellite_img_path = Path(getattr(Config, "SATELLITE_IMG_PATH", "./assets/satellite_background.jpg"))
        online_satellite_url = "https://upload.wikimedia.org/wikipedia/commons/c/c4/Earthmap1000x500compac.jpg"

        # Download automatically if not found locally
        if not satellite_img_path.exists():
            log_message("Satellite image not found locally. Attempting to retrieve from online storage...")
            try:
                satellite_img_path.parent.mkdir(parents=True, exist_ok=True)
                # Standard User-Agent to bypass potential server-side blockades
                req = urllib.request.Request(online_satellite_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(satellite_img_path, 'wb') as out_file:
                    out_file.write(response.read())
                log_message(f"Successfully downloaded online satellite map to {satellite_img_path}")
            except Exception as e:
                log_message(f"Could not save online satellite map to disk: {e}. Streaming to RAM instead...")
                try:
                    req = urllib.request.Request(online_satellite_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        sat_img = Image.open(BytesIO(response.read())).convert("RGB")
                        satellite_img_array = np.array(sat_img)
                except Exception as stream_err:
                    log_message(f"Online map retrieve failed: {stream_err}. Falling back to clean colors.")

        if satellite_img_array is None and satellite_img_path.exists():
            try:
                sat_img = Image.open(satellite_img_path).convert("RGB")
                satellite_img_array = np.array(sat_img)
            except Exception as e:
                log_message(f"Error reading background file: {e}. Falling back to solid color background.")

    def update(frame):
        ax.clear()
        
        # 1. Draw the background (Sea / Space / Satellite)
        if map_style == "satellite" and satellite_img_array is not None:
            # Map extent matches global limits: X: [-180, 180], Y: [-90, 90]
            ax.imshow(satellite_img_array, origin='upper', extent=[-180, 180, -90, 90], aspect='auto', zorder=0)
        else:
            ax.set_facecolor(Config.MAP_SETTINGS["sea_color"])
        
        stage_idx = min(frame // frames_per_stage, total_stages - 1)
        current_phase = tournament_timeline[stage_idx]
        active_teams = current_phase["teams"] 
        
        def check_active(country_name):
            if not country_name:
                return 'inactive'
            c_low = str(country_name).strip().lower()
            
            if "united states" in c_low or "usa" == c_low:
                c_low = "united states of america"
            elif "united kingdom" in c_low or "uk" == c_low:
                c_low = "united kingdom"
                
            for team in active_teams:
                if team in c_low or c_low in team:
                    return 'active'
            return 'inactive'
            
        world_df['status'] = world_df['name'].apply(check_active)
        
        # 2. Draw inactive background landmasses
        inactive_color = Config.MAP_SETTINGS["inactive_land_color"]
        inactive_alpha = 1.0
        
        if map_style == "satellite":
            # Dark, semi-transparent mask to let the beautiful offline/online terrain shine through
            inactive_color = "#000000"
            inactive_alpha = 0.4
            
        world_df[world_df['status'] == 'inactive'].plot(
            ax=ax, color=inactive_color, alpha=inactive_alpha,
            edgecolor=Config.MAP_SETTINGS["inactive_border_color"], linewidth=0.5, zorder=1
        )
        
        # 3. Iterate through active teams and render textures / borders
        for _, row in world_df[world_df['status'] == 'active'].iterrows():
            country_name = str(row['name']).strip().lower()
            
            if "united states" in country_name or "usa" == country_name:
                country_name = "united states of america"
            elif "united kingdom" in country_name or "uk" == country_name:
                country_name = "united kingdom"

            flag_filename = f"{country_name}_flag.png"
            flag_path = Path(Config.FLAG_DIR) / flag_filename
            
            success = False
            if flag_path.exists():
                success = plot_country_with_flag_texture(ax, row['geometry'], flag_path)
                
            if not success:
                fallback_color = get_deterministic_color(country_name)
                gpd.GeoSeries(row['geometry']).plot(
                    ax=ax, color=fallback_color, 
                    edgecolor=Config.MAP_SETTINGS["active_border_color"], linewidth=0.8, zorder=2
                )
            else:
                gpd.GeoSeries(row['geometry']).geometry.boundary.plot(
                    ax=ax, color=Config.MAP_SETTINGS["active_border_color"], linewidth=0.6, zorder=3
                )

            # --- DISPLAY COUNTRY NAMES ---
            if row['geometry'].geom_type == 'MultiPolygon':
                largest_polygon = max(row['geometry'].geoms, key=lambda p: p.area)
                label_point = largest_polygon.centroid
            else:
                label_point = row['geometry'].centroid

            if not row['geometry'].is_empty:
                display_name = str(row['name']).title()
                if display_name == "United States Of America":
                    display_name = "USA"

                ax.text(
                    label_point.x, label_point.y, display_name,
                    color='white', fontsize=10, fontweight='bold', ha='center', va='center', zorder=5,
                    bbox=dict(facecolor='#1e293b', alpha=0.75, edgecolor='#ffffff', boxstyle='round,pad=0.2', linewidth=0.5)
                )

        ax.set_axis_off()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        
        ax.set_xlim(-180, 180)
        ax.set_ylim(-58, 83)  
        
        team_count = len(world_df[world_df['status'] == 'active']['name'].unique())
        count_suffix = f"({team_count} Teams)" if team_count > 1 else "(Champion!)"
        title_string = f"{Config.YEAR} {Config.TOURNAMENT_NAME.replace('_', ' ')}"
        
        ax.text(0.04, 0.94, title_string, transform=ax.transAxes, 
                fontsize=24, fontweight='bold', color='#111827', zorder=10,
                va='top', ha='left', bbox=dict(facecolor='#FFFFFF', alpha=0.85, edgecolor='none', boxstyle='round,pad=0.6'))

    writer = FFMpegWriter(fps=fps, bitrate=Config.VIDEO_SETTINGS["bitrate"], extra_args=['-pix_fmt', 'yuv420p'])
    temp_video_path = output_path.with_name("temp_tournament_eliminations.mp4")
    
    ani = animation.FuncAnimation(fig, update, frames=total_frames, repeat=False)
    ani.save(str(temp_video_path), writer=writer)
    plt.close(fig)
    
    video_clip = None
    audio_clip = None
    final_clip = None
    
    try:
        video_clip = VideoFileClip(str(temp_video_path))
        
        if is_audio_required:
            audio_clip = build_stitched_audio(tournament_timeline, total_video_duration)
            if audio_clip:
                final_clip = video_clip.with_audio(CompositeAudioClip([audio_clip]))
            else:
                final_clip = video_clip
        else:
            final_clip = video_clip
            
        final_clip.write_videofile(
            str(output_path), 
            codec=Config.VIDEO_SETTINGS["codec"], 
            audio_codec=Config.VIDEO_SETTINGS["audio_codec"] if is_audio_required else None, 
            logger=None
        )
    except Exception as e:
        log_message(f"Audio processing failure fallback triggered: {e}")
        if final_clip: final_clip.close()
        if video_clip: video_clip.close()
        if audio_clip: audio_clip.close()
        if temp_video_path.exists():
            try: shutil.move(str(temp_video_path), str(output_path))
            except Exception: pass
    finally:
        if final_clip: final_clip.close()
        if video_clip: video_clip.close()
        if audio_clip: audio_clip.close()
        try:
            if temp_video_path.exists(): os.remove(temp_video_path)
        except Exception: pass

def main(tournament_name, run_year, is_audio_required=True, map_style="simple"):
    Config.setup_runtime_context(tournament_name, run_year)
    Config.initialize_dirs()
    
    log_message("Parsing offline configurations and local maps...")
    
    if Path(Config.SHAPEFILE_PATH).exists():
        world = gpd.read_file(str(Config.SHAPEFILE_PATH))
    else:
        log_message(f"CRITICAL ERROR: Local shapefile not found at {Config.SHAPEFILE_PATH}.")
        return
        
    possible_name_columns = ['name', 'NAME', 'NAME_LONG', 'ADMIN', 'cntr_name']
    name_col = next((col for col in possible_name_columns if col in world.columns), None)
    if name_col and name_col != 'name':
        world['name'] = world[name_col]
        
    world['name'] = world['name'].replace(Config.COUNTRY_NAME_MAPPINGS)
    
    if not Path(Config.JSON_DATA_PATH).exists():
        log_message(f"Fatal error: Local dataset configuration file missing: {Config.JSON_DATA_PATH}")
        return
        
    with open(Config.JSON_DATA_PATH, "r", encoding="utf-8") as f:
        tournament_data = json.load(f)
        
    tournament_timeline = build_tournament_timeline(tournament_data)
    if not tournament_timeline:
        log_message("Error: No tournament matching stages parsed out of JSON structure.")
        return
        
    # --- UPDATED FILENAME FORMATTING ---
    formatted_style = map_style.strip().title()
    output_video_file = Path(Config.OUTPUT_DIR) / f"Tournament_Complete_Elimination_Map_{formatted_style}.mp4"
    
    # Passing map style directly down to the generator engine
    generate_elimination_video(output_video_file, world, tournament_timeline, is_audio_required, map_style=map_style)
    log_message("Tournament countdown video processing completed successfully.")

if __name__ == "__main__":
    # Choose either "simple" or "satellite"
    main(tournament_name="FIFA", run_year=2026, is_audio_required=True, map_style="simple")