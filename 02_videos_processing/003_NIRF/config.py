import os
from pathlib import Path

class Config:
    # --- Strict Unified Folder Structure ---
    NIRF_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/nirf")
    BASE_DIR = Path(__file__).resolve().parent
    COMMON_ASSETS=Path("C:/Ravi/Python/2025/Media/assets/common")
    COURSE_NAME = "Architecture"
    YEAR = "2025"
    FILE_NAME = "NIRF"
    COUNTRY_CODE='IN'
    # Image subdirectories
    IMAGE_DIR = NIRF_ASSETS / "images" / COURSE_NAME / "logos"
    LOGO_FOLDER = NIRF_ASSETS / "images" / COURSE_NAME / "logos"
    CAMPUS_FOLDER = NIRF_ASSETS / "images" / COURSE_NAME / "campus"
    
    # Map Boundaries
    SHAPEFILE_PATH = COMMON_ASSETS / "maps" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
    
    # Data and Video subdirectories
    DATA_DIR = NIRF_ASSETS / "data"
    OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
    AUDIO_DIR = BASE_DIR / "outputs" / "audios"
    
    AUDIO_PATH = AUDIO_DIR / f"{FILE_NAME}_{COURSE_NAME}_{YEAR}_Ranking.mp4"
    OUTPUT_PATH = OUTPUT_DIR / f"{FILE_NAME}_{COURSE_NAME}_{YEAR}_Ranking.mp4"
    
    # Path files
    JSON_DATA_PATH = DATA_DIR / f"NIRF_{COURSE_NAME}_{YEAR}_Ranking.json"
    GEO_COORDINATES_FILE=COMMON_ASSETS /  "data" / f"{COUNTRY_CODE}_Cities.json"
    # Network / Scraping properties
    AUDIO_URL = "https://www.youtube.com/shorts/nuCQcJSiEqM"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # Video layout parameters
    TARGET_SIZE = (1080, 1920)
    VIDEO_SETTINGS = {
        "seconds_per_item": 8,
        "fps": 5,
        "bitrate": 4000
    }

    # State postal abbreviations map
    STATE_ABBREVIATIONS = {
        "Andhra Pradesh": "AP", "Arunachal Pradesh": "AR", "Assam": "AS", "Bihar": "BR",
        "Chhattisgarh": "CG", "Goa": "GA", "Gujarat": "GT", "Haryana": "HR", 
        "Himachal Pradesh": "HP", "Jharkhand": "JH", "Karnataka": "KA", "Kerala": "KL",
        "Madhya Pradesh": "MP", "Maharashtra": "MH", "Manipur": "MN", "Meghalaya": "ML",
        "Mizoram": "MZ", "Nagaland": "NL", "Odisha": "OD", "Punjab": "PN", 
        "Rajasthan": "RS", "Sikkim": "SK", "Tamil Nadu": "TN", "Telangana": "TG",
        "Tripura": "TR", "Uttar Pradesh": "UP", "Uttarakhand": "UK", "West Bengal": "WB",
        "Delhi": "DL", "Jammu and Kashmir": "JK", "Ladakh": "LA", "Puducherry": "PY",
        "Chandigarh": "CH", "Andaman and Nicobar Islands": "AN", "Lakshadweep": "LD"
    }

    # Acronym mapping rules for subtitle titles
    INSTITUTE_MAPPINGS = {
        "Indian Institute of Technology": "IIT",
        "National Institute of Technology": "NIT",
        "Indian Institute of Information Technology": "IIIT"
    }

    # Video Theme Configurations
    THEMES = [
        {"bg1": (255, 236, 210), "bg2": (252, 182, 159)},  # Peach Blossom Cream
        {"bg1": (212, 252, 242), "bg2": (150, 230, 210)},  # Fresh Mint Sorbet
        {"bg1": (230, 242, 255), "bg2": (180, 210, 255)},  # Clean Sky Blue
        {"bg1": (254, 211, 252), "bg2": (253, 161, 234)},  # Bubblegum Pink
        {"bg1": (255, 243, 195), "bg2": (255, 213, 115)},  # Soft Lemon Honey
        {"bg1": (224, 255, 210), "bg2": (163, 235, 140)},  # Lime Pistachio
        {"bg1": (243, 231, 255), "bg2": (211, 181, 255)},  # Lavender Mist
        {"bg1": (255, 222, 222), "bg2": (255, 164, 164)},  # Light Rose Petal
        {"bg1": (206, 246, 253), "bg2": (132, 220, 238)},  # Electric Ice
        {"bg1": (255, 237, 188), "bg2": (253, 202, 131)},  # Summer Apricot
    ]

    @classmethod
    def initialize_dirs(cls):
        """Creates all structural folders sequentially if they don't exist."""
        directories = [
            cls.IMAGE_DIR, 
            cls.LOGO_FOLDER,
            cls.CAMPUS_FOLDER,
            cls.DATA_DIR, 
            cls.OUTPUT_DIR,
            cls.AUDIO_DIR
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)