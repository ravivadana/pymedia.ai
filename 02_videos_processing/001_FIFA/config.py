import os
from pathlib import Path
import json

class Config:
    # --- Strict Unified Folder Structure ---
    BASE_DIR = Path(__file__).resolve().parent
    BASE_ASSETS_DIR = Path("C:/Ravi/Python/2025/Media/assets/common")
    FIFA_ASSERTS_FOLDER = Path("C:/Ravi/Python/2025/Media/assets/fifa")
    
    # Injected dynamically from main method runtime
    TOURNAMENT_NAME = None
    YEAR = None  
    
    # Image subdirectories (Using clean Path objects)
    IMAGE_DIR = BASE_ASSETS_DIR / "images" / "countries"
    BG_DIR = BASE_ASSETS_DIR / "images" / "countries_backgrounds"
    FLAG_DIR = BASE_ASSETS_DIR / "images" / "countries_flags"
    FLAG_ANIMATED_DIR = BASE_ASSETS_DIR / "images" / "countries_flags_animated"
    
    # Data and Video subdirectories
    DATA_DIR = BASE_ASSETS_DIR / "data"
    VIDEO_SOURCE_DIR = FIFA_ASSERTS_FOLDER / "videos" / "countries"
    OUTPUT_DIR = BASE_DIR / "outputs" / "eliminations"
    LOG_FILE = BASE_DIR / "outputs" / "logs" / "tournament_processing.log"
    BG_IMAGE=FIFA_ASSERTS_FOLDER / "images" / "bg.png"
    # Path components calculated dynamically via classmethod setup
    JSON_DATA_PATH = None
    SHAPEFILE_PATH = BASE_ASSETS_DIR / "maps" / "ne_110m_admin_0_countries" / "ne_110m_admin_0_countries.shp"
    
    # Universal HTTP Headers for secure scraping
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    TARGET_SIZE = (1080, 1920)

    # --- Video & Render Infrastructure Settings ---
    VIDEO_SETTINGS = {
        "seconds_per_item": 10,
        "fps": 5,
        "bitrate": 4000,
        "max_frames_per_stage": 60,
        "codec": "libx264",
        "audio_codec": "aac"
    }
    
    MAP_SETTINGS = {
        "sea_color": "#AADAFF",
        "inactive_land_color": "#F5F5F3",
        "inactive_border_color": "#D0D0D0",
        "active_land_color": "#4CAF50",
        "active_border_color": "#1B5E20",
        "fig_size": (12, 7),
        "dpi": 100
    }
    
    COUNTRY_NAME_MAPPINGS = {
        "United States of America": "United States",
        "Bosnia and Herzegovina": "Bosnia and Herz.",
        "Côte d'Ivoire": "Ivory Coast"
    }

    THEMES = [
        {"bg1": (15, 23, 42), "bg2": (30, 41, 59)},
        {"bg1": (24, 24, 27), "bg2": (39, 39, 42)},
        {"bg1": (6, 26, 21), "bg2": (12, 54, 44)}
    ]

    @classmethod
    def setup_runtime_context(cls, tournament_name, execution_year):
        """Injects running environment variables dynamically from main pipeline execution."""
        cls.TOURNAMENT_NAME = str(tournament_name)
        cls.YEAR = execution_year
        # Generates JSON tracking file name using dynamic inputs (e.g., FIFA_2026.json)
        cls.JSON_DATA_PATH = cls.FIFA_ASSERTS_FOLDER / "data" / f"{cls.TOURNAMENT_NAME}_{cls.YEAR}_eliminations.json"

    @classmethod
    def initialize_dirs(cls):
        """Creates all structural folders sequentially if they don't exist."""
        directories = [
            cls.IMAGE_DIR, cls.BG_DIR, cls.FLAG_DIR, 
            cls.FLAG_ANIMATED_DIR, cls.DATA_DIR, 
            cls.VIDEO_SOURCE_DIR, cls.OUTPUT_DIR,
            cls.LOG_FILE.parent
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)