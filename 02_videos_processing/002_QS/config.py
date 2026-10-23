import os
from pathlib import Path
import json

class Config:
    # --- Strict Unified Folder Structure ---
    BASE_DIR = Path(__file__).resolve().parent
    QS_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/qs")
    COMMON_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/common")
    
    YEAR = "2027"
    FILE_NAME = "QS"
    COURSE_NAME = "QS_World"
    
    # Subdirectories
    IMAGE_DIR = QS_ASSETS / "images" / FILE_NAME / "logos"
    LOGO_FOLDER = QS_ASSETS / "images" / FILE_NAME / "logos"
    CAMPUS_FOLDER = QS_ASSETS / "images" / FILE_NAME / "campus"
    DATA_DIR = QS_ASSETS / "data"
    
    OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
    AUDIO_DIR = BASE_DIR / "outputs" / "audios"
    AUDIO_PATH = AUDIO_DIR / "background_music.mkv"
    
    JSON_DATA_PATH = DATA_DIR / f'qs_{YEAR}_ranking_top100.json' 
    SHAPEFILE_PATH = COMMON_ASSETS / "maps" / "ne_110m_admin_0_countries" / "ne_110m_admin_0_countries.shp"
    GEO_COORDINATES_FILE= COMMON_ASSETS / "data" / "cities.json"
    # Dynamic properties map
    COUNTRIES_ABBREVIATIONS = {}
    COUNTRY_FLAGS_DIR = os.path.join(COMMON_ASSETS, "images", "countries_flags")
    TARGET_SIZE = (1080, 1920)
    VIDEO_SETTINGS = {
        "seconds_per_item": 5,
        "fps": 5,
        "bitrate": 4000
    }
    
    INSTITUTE_MAPPINGS = {
        "Indian Institute of Technology": "IIT",
        "National Institute of Technology": "NIT",
        "Indian Institute of Information Technology": "IIIT"
    }

    THEMES = [
    # 1. Midnight Blue & Deep Indigo
    {"bg1": (15, 23, 42), "bg2": (30, 41, 59)},
    # 2. Charcoal & Dark Slate Gray
    {"bg1": (24, 24, 27), "bg2": (39, 39, 42)},
    # 3. Obsidian & Emerald Night Green
    {"bg1": (6, 26, 21), "bg2": (12, 54, 44)},
    # 4. Deep Violet & Dark Plum
    {"bg1": (20, 10, 35), "bg2": (38, 18, 66)},
    # 5. Velvet Burgundy & Dark Crimson
    {"bg1": (28, 10, 15), "bg2": (54, 18, 25)},
    # 6. Dark Ocean Teal & Cyber Blue
    {"bg1": (8, 32, 43), "bg2": (15, 61, 82)},
    # 7. Graphite Onyx & Cool Gray
    {"bg1": (17, 17, 17), "bg2": (40, 42, 46)},
    # 8. Dark Chocolate & Burnt Umber
    {"bg1": (24, 15, 10), "bg2": (43, 27, 18)},
    # 9. Shadow Navy & Steel Blue
    {"bg1": (11, 19, 36), "bg2": (23, 37, 67)},
    # 10. Eclipse Violet & Shadow Gray
    {"bg1": (24, 18, 30), "bg2": (45, 35, 54)},
]
   

    @classmethod
    def initialize_dirs(cls):
        """Creates all structural folders sequentially if they don't exist."""
        directories = [
            cls.IMAGE_DIR, 
            cls.DATA_DIR, 
            cls.OUTPUT_DIR
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        countries_abbreviations_file=os.path.join(cls.COMMON_ASSETS,'data','countries_abbreviations.json')
        with open(countries_abbreviations_file, "r", encoding="utf-8") as f:
            cls.COUNTRIES_ABBREVIATIONS = json.load(f)