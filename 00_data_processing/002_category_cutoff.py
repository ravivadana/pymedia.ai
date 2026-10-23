import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
from io import BytesIO
import json
import glob
import os
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont,ImageFilter
# =========================================================
# CONFIG
# =========================================================
year = 2026
course_name = "engineering"

BASE_DIR = "00_data_processing"
headers = {"User-Agent": "Mozilla/5.0"}
RANKING_JSON = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/institute_ranking.json"
CUTOFF_FOLDER = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/Cutoff"
CUTOFF_FILE = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/Cutoff/round1.json"
OUTPUT_IMAGE_FOLDER = f"{BASE_DIR}/images/nrif_ranking/{year}/{course_name}/cat_chart_institutes"
OUTPUT_VIDEO_FOLDER = f"{BASE_DIR}/videos/nrif_ranking/{year}/{course_name}/cat_chart_institutes"
AUDIO_FILE = f"{BASE_DIR}/audio/rangeela1.mp4"
ASSETS_FOLDER=f"{BASE_DIR}/assets"
SIZE = (400, 400)

os.makedirs(OUTPUT_IMAGE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_VIDEO_FOLDER, exist_ok=True)
# =========================================================
# HIGH QUALITY SCALE (AI STYLE)
# =========================================================
SCALE = 2
WIDTH = 1860 * SCALE
INSTITUTE_W = 220 * SCALE
CELL_W = 103 * SCALE
HEADER1 = 70 * SCALE
HEADER2 = 60 * SCALE
HEADER_BLOCK_H = HEADER1 + HEADER2
ROW_H = 40 * SCALE
# bigger thumbnail header
TOP_H = 620 * SCALE
NOTE_H = 120 * SCALE
TABLE_LINE = (228, 228, 228)
TABLE_LINE_BOLD = (210, 210, 210)
# =========================================================
# COLORS
# =========================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID = (210, 210, 210)
NAVY = (5, 33, 91)
OPEN_COLOR = (255,120,0)
EWS_COLOR = (0,180,60)
OBC_COLOR = (255,190,0)
SC_COLOR = (255,40,0)
ST_COLOR = (140,0,180)
MALE_BG = (235, 245, 255)
FEMALE_BG = (255, 235, 245)
MALE_COLOR = (0, 102, 204)
FEMALE_COLOR = (255, 105, 180)
POPULAR_BRANCHES = ["CSE", "EE", "ME", "CE", "CHE"]

COL_WIDTH_INSTITUTE = 420
COL_WIDTH_PROGRAM = 80
CELL_HEIGHT = 42

def extract_branch_code(program_name):
    mapping = {
        "Computer Science": "CSE",
        "Artificial Intelligence and Data Science":"AI&DS",
        "Data Science and Artificial Intelligence":"AI&DS",
        "Artificial Intelligence": "AI",
        "Electronics and Communication": "ECE",
        "Electrical": "EE",
        "Mechanical": "ME",
        "Civil": "CE",
        "Chemical": "CHE",
    }

    for k, v in mapping.items():
        if k.lower() in program_name.lower():
            return v
    return None

def clean_rank(v):
    if v is None:
        return float("inf")
    digits = re.sub(r"\D", "", str(v))
    return int(digits) if digits else float("inf")

# =========================================================
# FONT
# =========================================================
def load_font(size, bold=False):
    fonts = [
        "fonts/Anton-Regular.ttf",
        "fonts/BebasNeue-Regular.ttf",
        "arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for f in fonts:
        try:
            return ImageFont.truetype(f, size)
        except:
            pass
    return ImageFont.load_default()

TITLE_FONT = load_font(200, True)
SUBTITLE_FONT = load_font(124, True)
HEADER_FONT = load_font(60, True)
INSTITUTE_FONT = load_font(50, True)
VALUE_FONT = load_font(50, True)

# =========================================================
# HELPERS
# =========================================================
def normalize(text):
    return " ".join(str(text).lower().split())
def parse_rank(value):
    if value is None:
        return -1
    try:
        return int(float(str(value).replace("P", "").strip()))
    except:
        return -1
def short_institute_name(name):
    mapping = {
        "Indian Institute of Technology": "IIT",
        "National Institute of Technology": "NIT",
        "Indian Institute of Information Technology": "IIIT",
    }
    for k, v in mapping.items():
        if name.startswith(k):
            return name.replace(k, v)
    return name

def gradient(img):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        r = int(5 - 5 * y / h)
        g = int(20 - 20 * y / h)
        b = int(80 - 60 * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))


def get_matrix_data(CUTOFF_FILE):
    with open(CUTOFF_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_data.sort(key=lambda x: clean_rank(x.get("Closing Rank")))
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    institutes_order = []
    for item in raw_data:
        institute = item.get("Institute", "").strip()
        institute = institute.replace('  ',' ')
        # Keep only IITs
        if not re.search(r"\bIIT\b|Indian Institute of Technology", institute, re.IGNORECASE):
            continue
        program = item.get("Academic Program Name", "")
        seat = item.get("Seat Type", "").strip()
        gender = item.get("Gender", "").strip()
        rank = str(item.get("Closing Rank"))
        branch = extract_branch_code(program)
        if branch is None:
            continue
        if branch not in POPULAR_BRANCHES:
            continue
        # Gender mapping
        if "Female" in gender:
            g = "F"
        else:
            g = "M"   # Gender-Neutral
        data[institute][branch][seat][g] = rank
        if institute not in institutes_order:
            institutes_order.append(institute)

    return (institutes_order,data)
institutes_ordered_data,data=get_matrix_data(CUTOFF_FILE)
SEAT_TYPES = ["OPEN", "EWS", "OBC-NCL", "SC", "ST"]

def create_thumbnail_background(width, height):
    """
    Creates dark blue background with blurred glow
    similar to educational YouTube thumbnails.
    """
    # --------------------------------------------------
    # Base Gradient
    # --------------------------------------------------
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    TOP = (4, 15, 60)
    MID = (2, 10, 35)
    BOTTOM = (0, 0, 12)
    for y in range(height):
        if y < height * 0.5:
            ratio = y / (height * 0.5)
            r = int(TOP[0] + (MID[0] - TOP[0]) * ratio)
            g = int(TOP[1] + (MID[1] - TOP[1]) * ratio)
            b = int(TOP[2] + (MID[2] - TOP[2]) * ratio)
        else:
            ratio = (y - height * 0.5) / (height * 0.5)
            r = int(MID[0] + (BOTTOM[0] - MID[0]) * ratio)
            g = int(MID[1] + (BOTTOM[1] - MID[1]) * ratio)
            b = int(MID[2] + (BOTTOM[2] - MID[2]) * ratio)
        draw.line(
            [(0, y), (width, y)],
            fill=(r, g, b)
        )
    # --------------------------------------------------
    # Blue Glow Behind Header
    # --------------------------------------------------
    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )
    glow = ImageDraw.Draw(overlay)
    glow.ellipse(
        (
            width//2 - 550,
            50,
            width//2 + 550,
            900
        ),
        fill=(0, 90, 255, 90)
    )
    glow.ellipse(
        (
            width//2 - 400,
            150,
            width//2 + 400,
            700
        ),
        fill=(0, 120, 255, 110)
    )
    overlay = overlay.filter(
        ImageFilter.GaussianBlur(150)
    )
    img = Image.alpha_composite(
        img.convert("RGBA"),
        overlay
    ).convert("RGB")
    return img
def rr(draw, box, fill, radius=25, outline=None):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=3
    )
# =========================================================
# MOBILE PORTRAIT CONVERTER (1080 x 1920)
# =========================================================
def save_mobile_version(img, out_file, title_text=None):
    TARGET_W = 1080
    TARGET_H = 1920

    mobile = create_thumbnail_background(
        TARGET_W,
        TARGET_H
    )

    draw = ImageDraw.Draw(mobile)

    if title_text:
        title_font = load_font(70, True)

        draw.text(
            (TARGET_W // 2 + 3, 63),
            title_text,
            fill=(50, 30, 0),
            font=title_font,
            anchor="mt"
        )

        draw.text(
            (TARGET_W // 2, 60),
            title_text,
            fill=(255, 215, 0),
            font=title_font,
            anchor="mt"
        )

        top_margin = 180
    else:
        top_margin = 40

    side_margin = 20
    bottom_margin = 40

    available_w = TARGET_W - (side_margin * 2)
    available_h = TARGET_H - top_margin - bottom_margin

    scale = min(
        available_w / img.width,
        available_h / img.height
    )

    new_w = int(img.width * scale)
    new_h = int(img.height * scale)

    resized = img.resize(
        (new_w, new_h),
        Image.LANCZOS
    )

    x = (TARGET_W - new_w) // 2
    y = top_margin + ((available_h - new_h) // 2)

    mobile.paste(resized, (x, y))

    mobile.save(
        out_file,
        quality=95
    )

for seat in SEAT_TYPES:
    programs = POPULAR_BRANCHES
    HEIGHT = TOP_H + HEADER_BLOCK_H + ROW_H * len(POPULAR_BRANCHES) + NOTE_H
    img = Image.new("RGB", (WIDTH, HEIGHT))
    gradient(img)
    img = create_thumbnail_background(
        WIDTH,
        HEIGHT
    )
    draw = ImageDraw.Draw(img)
    TITLE_Y = 60
    CUT_OFF_TABLE_Y=160
    title_font = load_font(80, True)

    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------
    title=f"{seat} IIT's Admission CuttOff 2026"
    draw.text(
        (WIDTH//2 + 6, TITLE_Y + 6),
        title,
        fill=(60,40,0),
        font=title_font,
        anchor="mt"
    )
    draw.text(
        (WIDTH//2, TITLE_Y),
        title,
        fill=(255,215,0),
        font=title_font,
        anchor="mt"
    )


    # =====================================================
    # TABLE HEADER (ROWSPAN FIX)
    # =====================================================

    table_y = CUT_OFF_TABLE_Y
    rr(
        draw,
        [10, table_y, WIDTH - 10, HEIGHT - 130],
        fill=(4,15,60),   # same as thumbnail background
        radius=30
    )

      # LEFT CELL (ROWSPAN=2)
    draw.rectangle(
        [0, table_y, INSTITUTE_W, table_y + HEADER_BLOCK_H],
        fill=NAVY
    )
    draw.multiline_text(
        (INSTITUTE_W // 2, table_y + HEADER_BLOCK_H // 2),
        "INSTITUTE",
        fill=WHITE,
        font=HEADER_FONT,
        anchor="mm",
        align="center"
    ) 

    # =====================================================
    # BRANCH HEADERS
    # =====================================================
    x = INSTITUTE_W
    for branch in POPULAR_BRANCHES:
        draw.rectangle(
            [x, table_y, x + CELL_W * 2, table_y + HEADER1],
            fill={
                "CSE": OPEN_COLOR,
                "AI&DS":ST_COLOR,
                "AI": OBC_COLOR,
                "ECE": EWS_COLOR,
                "EE": OBC_COLOR,
                "ME": SC_COLOR,
                "CE": ST_COLOR,
                "CHE":OPEN_COLOR
            }[branch]
        )
        draw.text(
            (x + CELL_W, table_y + HEADER1 // 2),
            branch,
            fill=WHITE,
            font=HEADER_FONT,
            anchor="mm"
        )
        # M / F row
        draw.rectangle(
            [x, table_y + HEADER1, x + CELL_W, table_y + HEADER_BLOCK_H],
            fill=MALE_COLOR
        )
        draw.rectangle(
            [x + CELL_W, table_y + HEADER1, x + CELL_W * 2, table_y + HEADER_BLOCK_H],
            fill=FEMALE_COLOR
        )
        draw.text(
            (x + CELL_W // 2, table_y + HEADER1 + HEADER2 // 2),
            "M",
            fill=WHITE,
            font=HEADER_FONT,
            anchor="mm"
        )
        draw.text(
            (x + CELL_W + CELL_W // 2, table_y + HEADER1 + HEADER2 // 2),
            "F",
            fill=WHITE,
            font=HEADER_FONT,
            anchor="mm"
        )
        x += CELL_W * 2

            # =====================================================
    # DATA ROWS
    # =====================================================
    start_y = table_y + HEADER_BLOCK_H
    INSTITUTE_BG = (4,38,96)
    BRANCH_BORDER = (90,140,255)
    for i, institute in enumerate(institutes_ordered_data):
        y = start_y + i * ROW_H
        short_institute=short_institute_name(institute)
        row_bg = (245, 245, 245) if i % 2 == 0 else WHITE
        # 1. draw full row background
        draw.rectangle(
            [0, y, WIDTH, y + ROW_H],
            fill=row_bg
        )
        draw.rectangle([0, y, INSTITUTE_W, y + ROW_H],
                    fill=INSTITUTE_BG)
        # branch text
        draw.text((80, y + ROW_H // 2),
                short_institute,
                fill=WHITE,
                font=INSTITUTE_FONT,
                anchor="lm")
        x = INSTITUTE_W

        for branch in POPULAR_BRANCHES:
            m = data[institute][branch][seat].get("M", "-")
            f = data[institute][branch][seat].get("F", "-")

            draw.rectangle([x, y, x + CELL_W, y + ROW_H], fill=MALE_BG)
            draw.rectangle([x + CELL_W, y, x + CELL_W * 2, y + ROW_H], fill=FEMALE_BG)
            draw.text((x + CELL_W // 2, y + ROW_H // 2),
                      str(m),
                      fill=BLACK,
                      font=VALUE_FONT,
                      anchor="mm")
            draw.text((x + CELL_W + CELL_W // 2, y + ROW_H // 2),
                      str(f),
                      fill=(200, 0, 0),
                      font=VALUE_FONT,
                      anchor="mm")
            x += CELL_W * 2
    
    # ========================================================
    # SAVE ORIGINAL
    # ========================================================
    desktop_file = (
        f"{OUTPUT_IMAGE_FOLDER}/{seat}_category_IIT Cutoff {year} Round 1.png"
    )
    img.save(
        desktop_file,
        quality=95
    )
    print("Generated:", desktop_file)
    # ========================================================
    # SAVE MOBILE 1080x1920
    # ========================================================
    mobile_file = (
        f"{OUTPUT_IMAGE_FOLDER}/{seat}_matrix_mobile.png"
    )
    save_mobile_version(
        img,
        mobile_file,
        title_text=f"{seat} Category IIT Cutoff {year} Round 1"
    )
    print("Generated:", mobile_file)
    print("\nDONE: All cutoff matrices generated successfully.")


from pathlib import Path
from Images2VideoGenerator import Images2VideoGenerator


img_src = Path(f"{BASE_DIR}/images/nrif_ranking/{year}/{course_name}/cat_cutoff_matrix")
audio_src = f"{BASE_DIR}/audio/rangeela1.mp4"

# Instantiate and fire
video_pipeline = Images2VideoGenerator(
    image_folder=img_src,
    audio_file=audio_src,
    video_duration=5,
    fps=30
)

video_pipeline.generate_videos(overwrite=False)