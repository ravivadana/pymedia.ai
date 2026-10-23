import os
import json
import sys
import random  # <--- Integrated for selecting random video URLs
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from config import Config
from asset_scraper import AssetScraper
from video_generator import VideoGenerator
from tqdm import tqdm

# Safe Injection pointing to external systems downloader modules
current_dir = Path(__file__).resolve().parent
target_dir = current_dir.parent / "02_videos_processing"
if str(target_dir) not in sys.path:
    sys.path.append(str(target_dir))

try:
    from yt_downloader import MediaDownLoader
except ImportError:
    class MediaDownLoader:
        def download_video_with_ytdlp(self, folder, url, name):
            return

def get_file_starting_with(folder_path, start_string):
    folder = Path(folder_path)
    if not folder.exists():
        return None
    for file_path in folder.iterdir():
        if file_path.name.lower().startswith(start_string.lower()):
            return str(file_path)
    return None

# Worker process target function
def render_worker(team, index, total_teams, CHOSEN_SHAPE, TARGET_SIZE, force_replace_lower):
    video_engine = VideoGenerator()
    video_engine.canvas_w = TARGET_SIZE[0]
    video_engine.canvas_h = TARGET_SIZE[1]
    
    SHAPE_SEQUENCE = ['circle', 'rectangle', 'star', 'diamond']
    countryname = team["country"].strip()
    country_upper = countryname.upper()
    
    current_shape = SHAPE_SEQUENCE[(index - 1) % len(SHAPE_SEQUENCE)] if CHOSEN_SHAPE == 'random' else CHOSEN_SHAPE
    sequence_str = f"{index:03d}"
    custom_filename = f"{sequence_str}_FIFA 2026 Football {country_upper} #{country_upper} #FIFA2026.mp4"
    output_file = os.path.join(Config.OUTPUT_DIR, custom_filename)
    
    should_force = countryname.lower() in force_replace_lower
    
    if os.path.exists(output_file) and not should_force:
        return f"⏭️ Skipped (Already Exists): {countryname}"
        
    main_video_path = os.path.join(Config.VIDEO_SOURCE_DIR, f"{countryname}.mp4")
    center_png = os.path.join(Config.IMAGE_DIR, f"{countryname}.png")
    animated_flag = get_file_starting_with(Config.FLAG_ANIMATED_DIR, countryname)
    background_img = get_file_starting_with(Config.BG_DIR, countryname)
    
    if not os.path.exists(main_video_path) or not os.path.exists(center_png) or not animated_flag:
        return f"⚠ Missing components for: {countryname}"
        
    try:
        video_engine.create_composite_video(
            index,
            main_video_path=main_video_path,
            center_png_path=center_png,
            bottom_gif_path=animated_flag,
            country_name=countryname,
            output_path=output_file,
            bg_image_path=background_img,
            shape=current_shape,
            force_replace=should_force
        )
        return f"✓ Rendered: {countryname} ({current_shape})"
    except Exception as e:
        return f"❌ Failed {countryname}: {str(e)}"

def main():
    print("=== INITIALIZING PARALLEL CPU RENDERING ARCHITECTURE ===")
    
    WIKIPEDIA_FLAGS_URL = "https://en.wikipedia.org/wiki/List_of_national_flags_of_sovereign_states"
    GOOGLE_IMAGE_SEARCH_URL = "https://www.google.com/search?q="
    BING_IMAGE_SEARCH_URL = "https://www.bing.com/images/search?q="
    
    CHOSEN_SHAPE = 'circle'          
    TARGET_SIZE = (1080, 1920)       
    FORCE_REPLACE_COUNTRIES = ['spain']     
    force_replace_lower = [country.strip().lower() for country in FORCE_REPLACE_COUNTRIES]
    
    if CHOSEN_SHAPE == 'random':
        Config.OUTPUT_DIR = os.path.join(Config.BASE_DIR, "outputs", "random")
    else:
        Config.OUTPUT_DIR = os.path.join(Config.BASE_DIR, "outputs", f"{CHOSEN_SHAPE}s")

    Config.TARGET_SIZE = TARGET_SIZE
    Config.initialize_dirs()
    
    # Pre-checking scraper requirements
    has_flags = os.path.exists(Config.FLAG_DIR) and any(os.scandir(Config.FLAG_DIR))
    has_bgs = os.path.exists(Config.BG_DIR) and any(os.scandir(Config.BG_DIR))
    
    if not (has_flags and has_bgs and not FORCE_REPLACE_COUNTRIES):
        scraper = AssetScraper()
        scraper.download_wikipedia_assets(
            wiki_url=WIKIPEDIA_FLAGS_URL, google_base_url=GOOGLE_IMAGE_SEARCH_URL, 
            bing_base_url=BING_IMAGE_SEARCH_URL, force_replace_list=FORCE_REPLACE_COUNTRIES
        )
    
    if not os.path.exists(Config.JSON_DATA_PATH):
        print(f"Critical Error: Missing configuration index: {Config.JSON_DATA_PATH}")
        return

    with open(Config.JSON_DATA_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)
    teams_list = data.get("qualified_countries", [])
    
    # Pre-download phase (sequential to prevent IP throttling/network clashes)
    print("\n--- STAGE 1: VERIFYING AND RESOLVING SOURCE STREAMS ---")
    media_downloader = MediaDownLoader()
    for team in teams_list:
        countryname = team["country"].strip()
        main_video_path = os.path.join(Config.VIDEO_SOURCE_DIR, f"{countryname}.mp4")
        
        if not os.path.exists(main_video_path):
            # Extract video URL out of the new list setup dynamically
            urls_list = team.get("video_urls", [])
            
            if urls_list and isinstance(urls_list, list):
                chosen_url = random.choice(urls_list).strip()
            else:
                # Safe backward-compatible fallback if it's still using standard single string format
                chosen_url = team.get("video_url", "").strip()
                
            if not chosen_url:
                print(f"⚠ Skip download: No valid URL references found for {countryname}")
                continue
                
            print(f"-> Selected random stream for {countryname}: {chosen_url}")
            try: 
                media_downloader.download_video_with_ytdlp(Config.VIDEO_SOURCE_DIR, chosen_url, countryname)
            except Exception as e: 
                print(f"   Download Error: {e}")

    # Parallel Rendering Processing Phase
    print("\n--- STAGE 2: PROCESSING CONCURRENT TIMELINES ---")
    
    # Calculate CPU distribution (Total physical threads / 2 to manage RAM safely)
    max_workers = max(1, os.cpu_count() // 2)
    print(f"System Cores: {os.cpu_count()} | Allocating Workers: {max_workers} concurrent tasks\n")
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                render_worker, team, idx, len(teams_list), CHOSEN_SHAPE, TARGET_SIZE, force_replace_lower
            ): team for idx, team in enumerate(teams_list, start=1)
        }
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Pipeline Progress", unit="video"):
            try:
                log_message = future.result()
                tqdm.write(log_message)
            except Exception as e:
                tqdm.write(f"❌ Worker critically failed: {e}")
                
    print("\n🎉 Parallel processing matrix finished execution successfully!")

if __name__ == "__main__":
    main()