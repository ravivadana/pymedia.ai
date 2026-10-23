import os
import json
import matplotlib
import shutil
import random
import urllib.request
import subprocess
import glob
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
from PIL import Image, ImageDraw
import numpy as np

# MoviePy v2 compatible imports
from moviepy import VideoFileClip, ColorClip, ImageClip, Clip, CompositeVideoClip
from moviepy import AudioFileClip, CompositeAudioClip, concatenate_audioclips
from moviepy.video.fx import Loop 
from moviepy.audio.fx import MultiplyVolume

# Import the configured dependency layer
from config import Config

def log_message(message):
    log_line = f"[{Config.TOURNAMENT_NAME} {Config.YEAR}] {message}\n"
    print(message)
    with open(Config.LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

# =====================================================================
# INTEGRATED YT_DOWNLOADER UTILITIES
# =====================================================================
class Converter:
    def convert_to_mp4(self, input_file, output_file):
        command = [
            'ffmpeg', '-y', 
            '-i', input_file,
            '-c:v', 'libx264',   
            '-crf', '23',        
            '-preset', 'medium', 
            '-c:a', 'aac',       
            '-b:a', '128k',      
            output_file
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            log_message(f"✅ Successfully converted '{input_file}' to '{output_file}'")
        except subprocess.CalledProcessError as e:
            log_message(f"❌ Error during conversion: {e}\nSTDERR: {e.stderr}")
            if os.path.exists(input_file):
                os.remove(input_file)
        except FileNotFoundError:
            log_message("❌ FFmpeg not found. Please ensure FFmpeg is installed and accessible in system PATH.")
        
        if os.path.exists(input_file) and input_file != output_file:
            os.remove(input_file)
        return output_file

class MediaDownloader:
    def download_video_with_ytdlp(self, output_path, url, file_name_part="", duration=58, extract_audio_only=False):
        os.makedirs(output_path, exist_ok=True)
        ext_target = "mp3" if extract_audio_only else "mp4"
        
        if file_name_part != "":
            out_template = os.path.join(output_path, f"{file_name_part}.%(ext)s")
            final_expected_path = os.path.join(output_path, f"{file_name_part}.{ext_target}")
        else:
            last_part = url.rstrip("/").split("/")[-1]
            out_template = os.path.join(output_path, f"{last_part}_%(title)s.%(ext)s")
            final_expected_path = None

        if extract_audio_only:
            command = [
                'yt-dlp', '-o', out_template, '-f', 'ba', '-x', '--audio-format', 'mp3', url
            ]
        else:
            command = [
                'yt-dlp', '-o', out_template, '--merge-output-format', 'mp4',
                '--download-sections', f'*00:00:00-00:00:{duration:02d}',
                '--force-keyframes-at-cuts', url
            ]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            log_message(f"✅ Download process complete for URL: {url}")
            if final_expected_path and os.path.exists(final_expected_path):
                return final_expected_path
        except subprocess.CalledProcessError as e:
            log_message(f"❌ Error during download processing for {url}: {e}\nyt-dlp stderr: {e.stderr}")
            return None
        except FileNotFoundError:
            log_message("❌ Error: 'yt-dlp' executable command not accessible.")
            return None

        list_of_files = glob.glob(os.path.join(output_path, '*'))
        if not list_of_files:
            return None
            
        latest_file = max(list_of_files, key=os.path.getctime)
        root, ext = os.path.splitext(latest_file)
        
        if not extract_audio_only and ext.lower() != ".mp4":
            mp4_file_path = f"{root}.mp4"
            converter = Converter() 
            converter.convert_to_mp4(latest_file, mp4_file_path)
            return mp4_file_path
            
        return latest_file

# =====================================================================
# BGM MIXING & VIDEO GENERATION CORE
# =====================================================================
class BgmAudioAdder:
    def add_bgm_inplace(self, video_path, bgm_path, bgm_volume=0.9):
        if not os.path.exists(bgm_path):
            log_message(f"⚠️ BGM Audio file missing at: {bgm_path}. Skipping background music step.")
            return

        video_clip_path = Path(video_path)
        temp_output_path = video_clip_path.with_name(f"temp_bgm_{video_clip_path.name}")
        
        video = VideoFileClip(str(video_clip_path))
        bgm = AudioFileClip(str(bgm_path))
        
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

        bgm = bgm.with_effects([MultiplyVolume(bgm_volume)])

        if video.audio is not None:
            final_audio = CompositeAudioClip([video.audio, bgm])
        else:
            final_audio = bgm

        final_video = video.with_audio(final_audio)
        
        log_message(f"Adding Background Music to: {video_clip_path.name}...")
        final_video.write_videofile(
            str(temp_output_path), 
            codec=Config.VIDEO_SETTINGS.get("codec", "libx264"), 
            audio_codec="aac",
            logger=None
        )
        
        video.close(); bgm.close(); final_video.close()
        
        try:
            if os.path.exists(video_clip_path):
                os.remove(video_clip_path)
            temp_output_path.rename(video_clip_path)
            log_message(f"🎵 Successfully mixed BGM into: {video_clip_path.name}")
        except Exception as e:
            log_message(f"❌ Error replacing original file with BGM track: {e}")

def build_tournament_timeline(tournament_data):
    stage_order = ["group_stage_teams", "round_of_32_teams", "round_of_16_teams", "quarter_finals_teams", "semi_finals_teams", "finals_teams", "winner"]
    timeline = []
    for stage_key in stage_order:
        if stage_key in tournament_data:
            teams = tournament_data[stage_key]
            if isinstance(teams, str):
                teams = [teams]
            if teams:
                cleaned_teams = {str(t).strip().lower() for t in teams}
                timeline.append({
                    "stage_key": stage_key,
                    "stage_name": stage_key.replace("_teams", "").replace("_", " ").title(),
                    "teams": cleaned_teams
                })
    return timeline

def get_deterministic_color(country_name):
    random.seed(hash(country_name.lower()))
    return "#%06x" % random.randint(0x222222, 0xDDDDDD)

def plot_single_polygon_flag(ax, poly, img_array):
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
    if not flag_path or not flag_path.exists():
        return False
    try:
        img = Image.open(flag_path).convert("RGBA")
        img_array = np.array(img)
        polys = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
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
            combined_stage_audio = combined_stage_audio.with_duration(duration_per_stage)
            audio_clips_list.append(combined_stage_audio)
        else:
            from moviepy.audio.AudioClip import AudioClip
            silence = AudioClip(lambda t: 0, duration=duration_per_stage)
            audio_clips_list.append(silence)
            
    if audio_clips_list:
        return concatenate_audioclips(audio_clips_list)
    return None

def generate_elimination_video(output_path, world_df, tournament_timeline, is_audio_required=True, map_style="satellite"):
    log_message(f"Initializing video canvas with map style: {map_style}...")
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])

    frames_per_stage = 24  
    total_stages = len(tournament_timeline)
    
    # Increase the frames allocated for the final segment to cleanly display the dynamic zoom-out sequence
    winner_stage_frames = 64
    total_frames = ((total_stages - 1) * frames_per_stage) + winner_stage_frames
    
    fps = Config.VIDEO_SETTINGS["fps"]
    total_video_duration = total_frames / fps

    satellite_img_array = None
    if map_style == "satellite":
        satellite_img_path = Path(getattr(Config, "SATELLITE_IMG_PATH", "./assets/satellite_background.jpg"))
        online_satellite_url = "https://assets.science.nasa.gov/dynamicimage/assets/science/esd/eo/images/bmng/bmng-topography-bathymetry/january/world.topo.bathy.200401.3x5400x2700.jpg?w=5400&h=2700&fit=clip&crop=faces%2Cfocalpoint"

        if not satellite_img_path.exists():
            log_message("Downloading authentic NASA Blue Marble texture matching reference style...")
            try:
                satellite_img_path.parent.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(online_satellite_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(satellite_img_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception as e:
                log_message(f"Could not save online satellite map to disk: {e}. Streaming directly to RAM...")
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
        if map_style == "satellite" and satellite_img_array is not None:
            ax.imshow(satellite_img_array, origin='upper', extent=[-180, 180, -90, 90], aspect='auto', zorder=0)
            ax.grid(color=(1.0, 1.0, 1.0, 0.15), linestyle='-', linewidth=0.5, zorder=0.5)
        else:
            ax.set_facecolor(Config.MAP_SETTINGS["sea_color"])
        
        # Determine current timeline phase index
        normal_stages_total_frames = (total_stages - 1) * frames_per_stage
        if frame < normal_stages_total_frames:
            stage_idx = frame // frames_per_stage
            winner_stage_frame_idx = 0
        else:
            stage_idx = total_stages - 1
            winner_stage_frame_idx = frame - normal_stages_total_frames
            
        current_phase = tournament_timeline[stage_idx]
        active_teams = current_phase["teams"] 
        
        def check_active(country_name):
            if not country_name: return 'inactive'
            c_low = str(country_name).strip().lower()
            if "united states" in c_low or "usa" == c_low: c_low = "united states of america"
            elif "united kingdom" in c_low or "uk" == c_low: c_low = "united kingdom"
            for team in active_teams:
                if team in c_low or c_low in team: return 'active'
            return 'inactive'
            
        world_df['status'] = world_df['name'].apply(check_active)
        border_color = "#a3e635" if map_style == "satellite" else Config.MAP_SETTINGS["inactive_border_color"]
        
        world_df.plot(ax=ax, facecolor="none", edgecolor=border_color, linewidth=0.35, alpha=0.6, zorder=1)
        
        winner_geom = None
        for _, row in world_df[world_df['status'] == 'active'].iterrows():
            country_name = str(row['name']).strip().lower()
            if "united states" in country_name or "usa" == country_name: country_name = "united states of america"
            elif "united kingdom" in country_name or "uk" == country_name: country_name = "united kingdom"

            if current_phase["stage_key"] == "winner":
                winner_geom = row['geometry']

            flag_filename = f"{country_name}_flag.png"
            flag_path = Path(Config.FLAG_DIR) / flag_filename
            
            success = False
            if flag_path.exists():
                success = plot_country_with_flag_texture(ax, row['geometry'], flag_path)
                
            if not success:
                fallback_color = get_deterministic_color(country_name)
                gpd.GeoSeries(row['geometry']).plot(ax=ax, color=fallback_color, edgecolor="#ffffff", linewidth=0.8, zorder=2)
            else:
                gpd.GeoSeries(row['geometry']).geometry.boundary.plot(ax=ax, color="#ffffff", linewidth=0.75, zorder=3)

            label_point = max(row['geometry'].geoms, key=lambda p: p.area).centroid if row['geometry'].geom_type == 'MultiPolygon' else row['geometry'].centroid
            if not row['geometry'].is_empty:
                display_name = "USA" if str(row['name']).title() == "United States Of America" else str(row['name']).title()
                ax.text(label_point.x, label_point.y, display_name, color='white', fontsize=9, fontweight='bold', ha='center', va='center', zorder=5,
                        bbox=dict(facecolor='#1e293b', alpha=0.85, edgecolor='#ffffff', boxstyle='round,pad=0.2', linewidth=0.5))

        ax.set_axis_off()
        
        # --- ZOOM-OUT LOGIC ORCHESTRATION ---
        # Adjusted Y limits from (-56, 115) to (-90, 90) to let the map fit the screen fully without top/bottom cropping.
        if current_phase["stage_key"] == "winner" and winner_geom is not None:
            minx, miny, maxx, maxy = winner_geom.bounds
            
            # Maintain 16:9 canvas ratio constraints for local zoom frames
            target_w = maxx - minx
            target_h = maxy - miny
            if target_w / target_h > 19.2 / 10.8:
                adjusted_h = target_w * (10.8 / 19.2)
                diff = adjusted_h - target_h
                miny -= diff / 2
                maxy += diff / 2
            else:
                adjusted_w = target_h * (19.2 / 10.8)
                diff = adjusted_w - target_w
                minx -= diff / 2
                maxx += diff / 2

            # Configure timing splits across the winner sequence frames
            zoom_duration_frames = 34  
            hold_duration_frames = winner_stage_frames - zoom_duration_frames
            
            if winner_stage_frame_idx < zoom_duration_frames:
                # Calculate progress scaling linearly from 0.0 (full screen occupy) to 1.0 (complete world map bounds view)
                t = winner_stage_frame_idx / (zoom_duration_frames - 1)
                
                # Dynamic interpolation formulas for smooth bounds translation
                cur_minx = minx + t * (-180 - minx)
                cur_maxx = maxx + t * (180 - maxx)
                cur_miny = miny + t * (-90 - miny)
                cur_maxy = maxy + t * (90 - maxy)
                
                ax.set_xlim(cur_minx, cur_maxx)
                ax.set_ylim(cur_miny, cur_maxy)
            else:
                # Hold full comprehensive view landscape window
                ax.set_xlim(-180, 180)
                ax.set_ylim(-90, 90)
        else:
            # Default viewport projection for standard stages matches standard static view limits
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
        
        if current_phase["stage_key"] == "winner":
            winner_name = list(active_teams)[0].upper() if active_teams else "UNKNOWN"
            title_string = f" {Config.YEAR} {Config.TOURNAMENT_NAME.replace('_', ' ')} CHAMPIONS \nCONGRATULATIONS {winner_name}!"
            ax.text(0.5, 0.98, transform=ax.transAxes, s=title_string, fontsize=26, fontweight='bold', color='#ffffff', zorder=10, va='top', ha='center', 
                    bbox=dict(facecolor='#eab308', alpha=0.95, edgecolor='#ffffff', boxstyle='round,pad=0.8', linewidth=3.0))
        else:
            title_string = f"{Config.YEAR} {Config.TOURNAMENT_NAME.replace('_', ' ')} ELIMINATIONS\nStage: {current_phase['stage_name']}"
            ax.text(0.5, 0.98, transform=ax.transAxes, s=title_string, fontsize=22, fontweight='bold', color='#ffffff', zorder=10, va='top', ha='center', 
                    bbox=dict(facecolor='#f97316', alpha=0.95, edgecolor='#ffffff', boxstyle='round,pad=0.6', linewidth=2.0))

    writer = FFMpegWriter(fps=fps, bitrate=Config.VIDEO_SETTINGS["bitrate"], extra_args=['-pix_fmt', 'yuv420p'])
    temp_video_path = output_path.with_name(f"temp_{output_path.name}")
    ani = animation.FuncAnimation(fig, update, frames=total_frames, repeat=False)
    ani.save(str(temp_video_path), writer=writer)
    plt.close(fig)
    
    final_clip = video_clip = audio_clip = None
    try:
        video_clip = VideoFileClip(str(temp_video_path))
        if is_audio_required:
            audio_clip = build_stitched_audio(tournament_timeline, total_video_duration)
            final_clip = video_clip.with_audio(CompositeAudioClip([audio_clip])) if audio_clip else video_clip
        else:
            final_clip = video_clip
            
        final_clip.write_videofile(str(output_path), codec=Config.VIDEO_SETTINGS["codec"], audio_codec=Config.VIDEO_SETTINGS["audio_codec"] if is_audio_required else None, logger=None)
    except Exception as e:
        log_message(f"Audio processing failure fallback triggered: {e}")
        if temp_video_path.exists():
            try: shutil.move(str(temp_video_path), str(output_path))
            except Exception: pass
    finally:
        if final_clip: final_clip.close()
        if video_clip: video_clip.close()
        if audio_clip: audio_clip.close()
        if temp_video_path.exists():
            try: os.remove(temp_video_path)
            except Exception: pass

def make_rounded_mask(size, radius):
    mask_img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask_img)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return np.array(mask_img) / 255.0

def create_mobile_video_from_desktop(desktop_video_path, mobile_video_path, mobile_bg_path=None, corner_radius=30, winner_stage_duration=2.66):
    log_message("\n--- Creating True 9:16 Vertical Video (1080x1920) ---")
    clip = VideoFileClip(desktop_video_path)
    normal_duration = clip.duration - winner_stage_duration
    
    # --- Part A: Normal Stages Layout ---
    normal_map_clip = clip.subclipped(0, normal_duration).resized(width=1080)
    w, h = normal_map_clip.size
    mask_array = make_rounded_mask((w, h), corner_radius)
    
    mask_clip = ImageClip(mask_array, is_mask=True).with_duration(normal_map_clip.duration)
    normal_map_clip = normal_map_clip.with_mask(mask_clip).with_position(('center', 'center'))
    
    background = None
    if mobile_bg_path and os.path.exists(mobile_bg_path):
        ext = os.path.splitext(mobile_bg_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            background = (ImageClip(mobile_bg_path)
                          .with_duration(normal_map_clip.duration)
                          .resized(new_size=(1080, 1920)))
        elif ext == '.mp4':
            bg_video = VideoFileClip(mobile_bg_path).resized(new_size=(1080, 1920))
            if bg_video.duration > normal_map_clip.duration:
                bg_video = bg_video.subclipped(0, normal_map_clip.duration)
            else:
                bg_video = bg_video.with_effects([Loop(duration=normal_map_clip.duration)])
            background = bg_video.without_audio()
            
    if background is None:
        background = ColorClip(size=(1080, 1920), color=(248, 250, 252), duration=normal_map_clip.duration)
        
    composite_normal = CompositeVideoClip([background, normal_map_clip])
    
    # --- Part B: Winner Finale Layout ---
    winner_map_clip = clip.subclipped(normal_duration, clip.duration)
    winner_map_clip = winner_map_clip.resized(height=1920)
    crop_x = (winner_map_clip.w - 1080) // 2
    winner_map_full = winner_map_clip.cropped(x1=crop_x, y1=0, width=1080, height=1920)
    
    # --- Part C: Append Tracks ---
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    final_clip = concatenate_videoclips([composite_normal, winner_map_full])
    
    if clip.audio is not None:
        final_clip.write_videofile(mobile_video_path, codec="libx264", audio_codec="aac", preset="medium", logger=None)
    else:
        final_clip.write_videofile(mobile_video_path, codec="libx264", preset="medium", logger=None)
    
    clip.close(); normal_map_clip.close(); background.close(); winner_map_clip.close(); final_clip.close()

# =====================================================================
# SYSTEM MAIN CONTEXT ORCHESTRATION PIPELINE
# =====================================================================
def main(tournament_name, run_year, is_audio_required=True, map_types=["satellite"], video_types=["desktop", "mobile"], audio_url=None, mobile_bg_path=None, border_radius=35):
    Config.setup_runtime_context(tournament_name, run_year)
    Config.initialize_dirs()
    
    bgm_file_track = getattr(Config, "AUDIO_PATH", "./audio/bgm.mp3")
    
    if audio_url:
        if os.path.exists(bgm_file_track):
            log_message(f"✨ Audio file already exists at {bgm_file_track}. Skipping downloader step.")
        else:
            log_message(f"🚀 Audio file not found. Starting background track download from: {audio_url}")
            downloader = MediaDownloader()
            audio_dir_path = os.path.dirname(bgm_file_track)
            audio_file_name = os.path.splitext(os.path.basename(bgm_file_track))[0]
            
            downloaded_asset = downloader.download_video_with_ytdlp(
                output_path=audio_dir_path, url=audio_url, file_name_part=audio_file_name, extract_audio_only=True
            )
            if downloaded_asset:
                log_message(f"🎵 Background music successfully saved to: {downloaded_asset}")
            else:
                log_message("⚠️ Downloader failed to retrieve background track. Proceeding with existing folder resources.")

    log_message("Parsing configurations and world shapes...")
    if Path(Config.SHAPEFILE_PATH).exists():
        world = gpd.read_file(str(Config.SHAPEFILE_PATH))
    else:
        log_message(f"CRITICAL ERROR: Local shapefile not found at {Config.SHAPEFILE_PATH}.")
        return
        
    name_col = next((col for col in ['name', 'NAME', 'NAME_LONG', 'ADMIN', 'cntr_name'] if col in world.columns), None)
    if name_col and name_col != 'name': world['name'] = world[name_col]
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
        
    fps = Config.VIDEO_SETTINGS["fps"]
    winner_segment_seconds = 64.0 / fps

    for current_style in map_types:
        formatted_style = current_style.strip().title()
        log_message(f"\n==================================================")
        log_message(f"🎬 PROCESSING MAP STYLE: {formatted_style}")
        log_message(f"==================================================")
        
        desktop_video_file = Path(Config.OUTPUT_DIR) / f"Tournament_Complete_Elimination_Map_{formatted_style}_desktop.mp4"
        
        generate_elimination_video(desktop_video_file, world, tournament_timeline, is_audio_required, map_style=current_style)
        
        bgm_mixer = BgmAudioAdder()
        
        if "desktop" in video_types:
            bgm_mixer.add_bgm_inplace(str(desktop_video_file), str(bgm_file_track))
        
        if "mobile" in video_types:
            mobile_video_file = Path(Config.OUTPUT_DIR) / f"Tournament_Complete_Elimination_Map_{formatted_style}_mobile.mp4"
            create_mobile_video_from_desktop(
                desktop_video_path=str(desktop_video_file), 
                mobile_video_path=str(mobile_video_file), 
                mobile_bg_path=mobile_bg_path, 
                corner_radius=border_radius,
                winner_stage_duration=winner_segment_seconds
            )
            bgm_mixer.add_bgm_inplace(str(mobile_video_file), str(bgm_file_track))
            
            if "desktop" not in video_types and desktop_video_file.exists():
                os.remove(desktop_video_file)

    log_message("Tournament countdown video processing completed successfully.")

if __name__ == "__main__":
    BGM_TARGET_URL = "https://www.youtube.com/watch?v=WPni755-Krg"
    MOBILE_BG_ASSET = Config.BG_IMAGE
    
    main(
        tournament_name="FIFA", 
        run_year=2026, 
        is_audio_required=True, 
        map_types=["simple","satellite"], 
        video_types=["desktop"],
        audio_url=BGM_TARGET_URL,
        mobile_bg_path=MOBILE_BG_ASSET,
        border_radius=40 
    )