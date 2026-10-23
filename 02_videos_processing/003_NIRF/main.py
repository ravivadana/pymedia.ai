import os
import json
import sys
import re
import time
import shutil  # <-- Added for folder cleanup operations
from tqdm import tqdm
from config import Config
from premium_image_generator import PremiumImageGenerator
from premium_video_engine import PremiumVideoEngine
from nirf_map_videos_generator import NirfRankingMapVideosGenerator
MODULE_DIR = r"C:/Ravi/Python/2025/Media/assets"
if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)
# Import the class out of your creater module file now
from AssetCreater import AssetCreater
from premium_add_bgm import BgmAudioAdder
def main():
    #assets preparation like images logs,campusimages
    print("🚀 Initializing reusable Scraper Engine instance...")
    # Example: You can override properties instantly via constructor parameters if required!
    Config.YEAR=2025
    Config.COURSE_NAME="Architecture"
    asserts_directory=f"{Config.NIRF_ASSETS}/images/{Config.COURSE_NAME}"
    Config.JSON_DATA_PATH=f'{Config.NIRF_ASSETS}/data/NIRF_{Config.COURSE_NAME}_{Config.YEAR}_Ranking.json'
    Config.LOGO_FOLDER=Config.NIRF_ASSETS / "images" / Config.COURSE_NAME / "logos"
    Config.OUTPUT_DIR = Config.BASE_DIR / "outputs" / "videos"
    Config.OUTPUT_PATH=Config.OUTPUT_DIR/f"{Config.FILE_NAME}_{Config.COURSE_NAME}_{Config.YEAR}_Ranking.mp4"
    scraper = AssetCreater(json_file_path=Config.JSON_DATA_PATH, assets_dir=asserts_directory)
    
    # Run loop logic bound into instance instance properties
    scraper.run_scraper()
    print("\n🏁 Image gathering process wrapped cleanly.")


    # Call initializer to automatically create missing structure
    Config.initialize_dirs()

    institutes_data = None
    if os.path.exists(Config.JSON_DATA_PATH):
        with open(Config.JSON_DATA_PATH, "r", encoding="utf-8") as f:
            institutes_data = json.load(f)

    # Define the desired map style here: "simple" or "satellite"
    target_map_type = "simple" 
    
    if not os.path.exists(Config.AUDIO_PATH ):
        try:
            folder_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            # Add it to the Python path
            sys.path.append(folder_path)
            from yt_downloader import MediaDownloader
            print("SUCCESS: Module imported successfully!")
            mediaDownLoader = MediaDownloader()
                    
            inputput_video_folder = f"{Config.BASE_DIR}/outputs/audios"
                    
            # 1. Trigger the download
            downloaded_video_file = mediaDownLoader.download_video_with_ytdlp(
                        inputput_video_folder, Config.AUDIO_URL, file_name_part=f"{Config.FILE_NAME}_{Config.COURSE_NAME}_{Config.YEAR}_Ranking"
            )
            Config['audio_path']=downloaded_video_file
            print("downloading video Completed")
        except Exception as e:
                    print(f"FAILURE: Could not import or download. Error details: {type(e).__name__} - {e}")
            
    # Cleaned shared configuration variables pointing safely to string versions of paths
    shared_config = {
        "year": Config.YEAR,
        "fps": 30,
        "scroll_speed": 5,
        "video_width": 1080,
        "video_height": 540,
        "mobile_width": 1080,
        "mobile_height": 1920,
        "json_file": str(Config.JSON_DATA_PATH),
        "temp_folder": str(Config.BASE_DIR / "outputs" / "images" / "slides"),
        "mobile_folder": str(Config.BASE_DIR / "outputs" / "images" / "slides_mobile"),
        "output_video_path": str(Config.OUTPUT_PATH),
        "logos_folder": str(Config.LOGO_FOLDER),
        "maps_folder": "03_map_processing/images/countries",
        "flags_folder": "03_map_processing/images/countries_flags",
        "audio_path": str(Config.AUDIO_PATH),
        "shape_file_path": str(Config.SHAPEFILE_PATH),
        "map_type": target_map_type,
        "course_name":Config.COURSE_NAME,
        'country_code':Config.COUNTRY_CODE,
        'common_assets':Config.COMMON_ASSETS
    }   
    
    # # Step 1: Initialize image rendering worker engine
    # generator = PremiumImageGenerator(config=shared_config)
    # generator.generate_images()
        
    # # Step 2: Initialize video layout compiler engine
    # # (Uncommented so the video actually compiles before wiping the imagery sources)
    # compiler = PremiumVideoEngine(config=shared_config)
    # compiler.create_video()

    # # --- POST-PROCESSING ASSET CLEANUP ---
    # print("/n Initiating post-render workspace cleanup...")
    
    # folders_to_clean = [shared_config["temp_folder"], shared_config["mobile_folder"]]
    
    # for folder in folders_to_clean:
    #     if os.path.exists(folder):
    #         try:
    #             shutil.rmtree(folder)
    #             # Recreate empty directories so missing path errors don't trigger on consecutive runs
    #             os.makedirs(folder, exist_ok=True)
    #             print(f"✅ Cleaned and reset workspace folder: {os.path.basename(folder)}")
    #         except Exception as e:
    #             print(f"⚠️ Error while purging directory contents {folder}: {e}")

    # print("🎉 Pipeline run completely finalized.")

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