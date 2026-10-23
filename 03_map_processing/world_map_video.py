import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tkinter as tk
import os
import sys
import numpy as np
from matplotlib.path import Path
import matplotlib.patches as patches
from PIL import Image

# MoviePy v2.0+ imports (Only importing VideoFileClip now)
from moviepy.video.io.VideoFileClip import VideoFileClip

class WorldMapTournamentAnimation:
    def __init__(self, shapefile_path, flags_directory, tournament_data):
        self.shapefile_path = shapefile_path
        self.flags_directory = flags_directory
        self.tournament_data = tournament_data

        print(">>> Initializing World Map Shapefile...")
        self.world = gpd.read_file(self.shapefile_path)
        self.world_merc = self.world.to_crs(epsg=3857)

        self.shapefile_name_map = {
            "united states": "united states of america",
            "congo dr": "dem. rep. congo",
            "ir iran": "iran",
            "turkiye": "turkey",
            "czechia": "czech rep.",
            "korea republic": "south korea",
            "côte d'ivoire": "ivory coast",
            "england": "united kingdom",
            "scotland": "united kingdom"
        }
        
        all_countries = set()
        for stage_teams in self.tournament_data.values():
            if isinstance(stage_teams, list):
                for c in stage_teams:
                    all_countries.add(c)
                    
        clean_names = [self.shapefile_name_map.get(c.lower().strip(), c.lower().strip()) for c in all_countries]
        matched_countries = self.world[self.world['NAME'].str.lower().isin(clean_names)]
        self.selected_countries = matched_countries.to_crs(epsg=3857)
        print(f">>> Found and matched {len(self.selected_countries)} unique tournament countries.")

    def _get_flag_path(self, country_name):
        flag_name_map = {
            "United States of America": "United States",
            "Dem. Rep. Congo": "Congo DR",
            "Iran": "IR Iran",
            "Turkey": "Türkiye",
            "Czech Rep.": "Czechia",
            "South Korea": "Korea Republic",
            "Ivory Coast": "Côte d'Ivoire"
        }
        display_name = flag_name_map.get(country_name, country_name)
        for name in [display_name, display_name.replace(' ', '_')]:
            path = os.path.join(self.flags_directory, f"{name}_flag.png")
            if os.path.exists(path):
                return path
        return None

    def _prepare_country_assets(self, ax, geom, flag_path, country_name):
        try:
            img = Image.open(flag_path)
            xmin, ymin, xmax, ymax = geom.bounds
            im = ax.imshow(img, extent=[xmin, xmax, ymin, ymax], origin='upper', aspect='auto', alpha=0.0)
            
            geoms = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
            verts, codes = [], []
            for g in geoms:
                ext_coords = np.array(g.exterior.coords)
                verts.extend(ext_coords)
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ext_coords) - 2) + [Path.CLOSEPOLY])
                for interior in g.interiors:
                    int_coords = np.array(interior.coords)
                    verts.extend(int_coords)
                    codes.extend([Path.MOVETO] + [Path.LINETO] * (len(int_coords) - 2) + [Path.CLOSEPOLY])
            
            path = Path(verts, codes)
            patch = patches.PathPatch(path, facecolor='#fff', edgecolor='none', alpha=0.0, transform=ax.transData)
            ax.add_patch(patch)
            im.set_clip_path(patch)

            im.set_zorder(2)
            patch.set_zorder(1)

            outline_patch = patches.PathPatch(path, facecolor='none', edgecolor='#333333', linewidth=0.6, alpha=0.0, transform=ax.transData)
            ax.add_patch(outline_patch)

            display_name_map = {
                "United States of America": "United States",
                "Dem. Rep. Congo": "Congo DR",
                "Iran": "Iran",
                "Turkey": "Türkiye",
                "Czech Rep.": "Czechia",
                "South Korea": "Korea Republic",
                "Ivory Coast": "Côte d'Ivoire"
            }
            label_text = display_name_map.get(country_name, country_name)
            x, y = (1113194, 8400000) if country_name.lower() == "norway" else geom.representative_point().coords[0]

            text_label = ax.text(
                x, y, label_text, fontsize=9, fontweight='bold',
                color='black', ha='center', va='center', alpha=0.0,
                bbox=dict(facecolor='white', alpha=0.0, edgecolor='none', boxstyle='round,pad=0.15')
            )
            return im, outline_patch, text_label, patch
        except Exception:
            return None, None, None, None

    def _get_screen_size(self):
        root = tk.Tk()
        root.withdraw()
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        root.quit()
        return width, height

    def generate_video(self, output_filename="tournament_recap.mp4", fps=30):
        screen_width, screen_height = self._get_screen_size()
        fig, ax = plt.subplots(figsize=(screen_width/100, screen_height/100), dpi=100)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax.set_axis_off()
        ax.set_xlim(-20026376, 20026376)
        ax.set_ylim(-7018754, 13018754)

        self.world_merc.boundary.plot(ax=ax, color="gainsboro", linewidth=0.4)

        print(">>> Pre-rendering visual objects on map grid...")
        country_assets = {}
        for i, row in self.selected_countries.iterrows():
            flag_path = self._get_flag_path(row.NAME)
            if flag_path:
                im, outline, label, patch = self._prepare_country_assets(ax, row.geometry, flag_path, row.NAME)
                if im:
                    norm_name = row.NAME.lower().strip()
                    country_assets[norm_name] = {'im': im, 'outline': outline, 'label': label, 'patch': patch}

        stages_config = [
            ("group_stage_teams", "round_of_32_teams"),
            ("round_of_32_teams", "round_of_16_teams"),
            ("round_of_16_teams", "quarter_finals_teams"),
            ("quarter_finals_teams", "semi_finals_teams"),
            ("semi_finals_teams", "finals_teams"),
            ("finals_teams", "winner"),
            ("winner", None)
        ]

        print(">>> Constructing tracking timeline sheets...")
        timeline_frames = []
        step_duration = 1.5  # Fixed duration in seconds per elimination step

        for stage_key, next_stage_key in stages_config:
            teams = self.tournament_data.get(stage_key, [])
            if not teams and stage_key != "winner":
                continue

            if next_stage_key:
                next_teams = self.tournament_data.get(next_stage_key, [])
                next_teams_lower = [self.shapefile_name_map.get(t.lower(), t.lower()) for t in next_teams]
                
                eliminated = []
                for team in teams:
                    norm_t = self.shapefile_name_map.get(team.lower(), team.lower())
                    if norm_t not in next_teams_lower:
                        eliminated.append(team)

                if eliminated:
                    print(f"    Structuring layout to drop {len(eliminated)} countries step-by-step...")
                for target_country in eliminated:
                    curr_start = sum([f['dur'] for f in timeline_frames])
                    elim_frame_len = int(step_duration * fps)
                    
                    timeline_frames.append({
                        'type': 'elimination_step',
                        'stage': stage_key,
                        'start': curr_start,
                        'dur': elim_frame_len,
                        'eliminated_targets': [target_country]
                    })

        # Safeguard if no eliminations occurred (adds a brief holding frame sequence)
        if not timeline_frames:
            timeline_frames.append({
                'type': 'elimination_step',
                'stage': 'winner',
                'start': 0,
                'dur': int(step_duration * fps),
                'eliminated_targets': []
            })

        total_frames = sum([f['dur'] for f in timeline_frames])

        def update(frame):
            current_block = timeline_frames[-1]
            current_block_index = len(timeline_frames) - 1
            for idx, block in enumerate(timeline_frames):
                if block['start'] <= frame < (block['start'] + block['dur']):
                    current_block = block
                    current_block_index = idx
                    break

            stage_key = current_block['stage']
            stage_teams = self.tournament_data.get(stage_key, [])
            stage_teams_lower = [self.shapefile_name_map.get(t.lower(), t.lower()) for t in stage_teams]

            dead_teams_by_now = set()
            for idx in range(current_block_index):
                b = timeline_frames[idx]
                if b['type'] == 'elimination_step':
                    for t in b['eliminated_targets']:
                        dead_teams_by_now.add(self.shapefile_name_map.get(t.lower(), t.lower()))

            updated_artists = []

            for norm_name, assets in country_assets.items():
                # 1. Base rule: Missing completely from current stage tier roster
                if norm_name not in stage_teams_lower:
                    alpha = 0.0
                    blue_alpha = 1.0
                # 2. Sequential persistence rule: Faded out in previous steps of current stage
                elif norm_name in dead_teams_by_now:
                    alpha = 0.0
                    blue_alpha = 1.0
                # 3. Processing active fading step rule
                elif (current_block['type'] == 'elimination_step' and 
                      current_block['eliminated_targets'] and 
                      norm_name == self.shapefile_name_map.get(current_block['eliminated_targets'][0].lower(), current_block['eliminated_targets'][0].lower())):
                    progress = (frame - current_block['start']) / current_block['dur']
                    alpha = max(0.0, 1.0 - progress)
                    blue_alpha = progress
                # 4. Standard active country visibility rule
                else:
                    alpha = 1.0
                    blue_alpha = 0.0

                assets['im'].set_alpha(alpha)
                assets['outline'].set_alpha(max(alpha, blue_alpha))
                assets['label'].set_alpha(alpha)
                assets['label'].get_bbox_patch().set_alpha(alpha * 0.7 if alpha > 0 else 0.0)
                assets['patch'].set_alpha(blue_alpha)

                updated_artists.extend([assets['im'], assets['outline'], assets['label'], assets['patch']])

            percent = (frame + 1) / total_frames * 100
            bar_length = 40
            filled_length = int(bar_length * (frame + 1) // total_frames)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(f"\r>>> Rendering Video Frames: |{bar}| {percent:.1f}% ({frame + 1}/{total_frames})")
            sys.stdout.flush()

            return updated_artists

        print(f">>> Processing background map track visuals over {total_frames} frames...")
        ani = animation.FuncAnimation(fig, update, frames=total_frames, blit=True)
        
        temp_video = "temp_silent_recap.mp4"
        ani.save(temp_video, fps=fps, extra_args=['-vcodec', 'libx264'])
        plt.close(fig)
        print("\n>>> Visual frame sequence rendering complete.")

        print(">>> Finalizing video file container...")
        video_clip = VideoFileClip(temp_video)
        
        video_clip.write_videofile(
            output_filename, 
            codec="libx264", 
            audio=False,  # Set to False as audio tracks are removed
            logger=None
        )

        video_clip.close()
        try: os.remove(temp_video)
        except: pass
        print(f">>> Finished! Video recap successfully saved to:\n    {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    shapefile_path = "C:/Ravi/Python/2025/Media/assets/common/maps/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    flags_directory = r"C:\Ravi\Python\2025\Media\assets\common\images\countries_flags"

    fifa_data = {
      "group_stage_teams": [
        "Algeria", "Argentina", "Australia", "Austria", "Belgium", "Bosnia and Herzegovina", 
        "Brazil", "Cabo Verde", "Canada", "Colombia", "Congo DR", "Croatia", "Côte d'Ivoire", 
        "Curaçao", "Czechia", "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", 
        "Haiti", "IR Iran", "Iraq", "Japan", "Jordan", "Korea Republic", "Mexico", "Morocco", 
        "Netherlands", "Norway", "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia", 
        "Scotland", "Senegal", "South Africa", "Spain", "Sweden", "Switzerland", "Tunisia", 
        "Türkiye", "United States", "Uruguay", "Uzbekistan", "New Zealand"
      ],
      "round_of_32_teams": [
        "Algeria", "Argentina", "Australia", "Austria", "Belgium", "Bosnia and Herzegovina",
        "Brazil", "Cabo Verde", "Canada", "Colombia", "Congo DR", "Croatia", "Côte d'Ivoire",
        "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", "Japan", "Mexico",
        "Morocco", "Netherlands", "Norway", "Paraguay", "Portugal", "Senegal", "South Africa",
        "Spain", "Sweden", "Switzerland", "United States"
      ],
      "round_of_16_teams": [
        "Argentina", "Belgium", "Brazil", "Canada", "Colombia", "Egypt", "England", "France",
        "Mexico", "Morocco", "Norway", "Paraguay", "Portugal", "Spain", "Switzerland", "United States"
      ],
      "quarter_finals_teams": [
        "Argentina", "Belgium", "England", "France", "Morocco", "Norway", "Spain", "Switzerland"
      ],
      "semi_finals_teams": [
        "France", "Spain","England","Argentina"
      ],
      "finals_teams": ["France", "England"],
      "winner": [ "England"]
    }

    plotter = WorldMapTournamentAnimation(shapefile_path, flags_directory, tournament_data=fifa_data)
    output_folder = "03_map_processing/outputs/videos"
    os.makedirs(output_folder, exist_ok=True)
    plotter.generate_video(output_filename=f"{output_folder}/fifa_tournament_recap.mp4", fps=30)