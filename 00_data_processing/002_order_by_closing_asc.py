import json
import os
import re
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIG
# ============================================================

year = 2025
course_name = "engineering"

BASE_DIR = "00_data_processing"

CUTOFF_FILE = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/Cutoff/max_closing_rank.json"

OUTPUT_FOLDER = f"{BASE_DIR}/images/nrif_ranking/{year}/{course_name}/matrix_genderwise"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ============================================================
# SETTINGS
# ============================================================

FONT_PATH = "arial.ttf"

PADDING = 25
CELL_HEIGHT = 42
HEADER_HEIGHT = 38

COL_WIDTH_INSTITUTE = 420
COL_WIDTH_PROGRAM = 80

TOP_INSTITUTES = 36

POPULAR_BRANCHES = ["CSE", "ECE", "EE", "ME", "CE", "CHE"]

# ============================================================
# HELPERS
# ============================================================

def extract_branch_code(program_name):
    mapping = {
        "Computer Science": "CSE",
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


# ============================================================
# LOAD DATA
# ============================================================

with open(CUTOFF_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

raw_data.sort(key=lambda x: clean_rank(x.get("Closing Rank")))

# ============================================================
# DATA STRUCTURE
# ============================================================

# institute -> branch -> seat -> gender -> rank
data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

institutes_order = []

# ============================================================
# BUILD MATRIX
# ============================================================

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

# limit top institutes
institutes_order = institutes_order[:TOP_INSTITUTES]

# ============================================================
# SEAT TYPES (COLUMNS)
# ============================================================

SEAT_TYPES = ["OPEN", "EWS", "OBC-NCL", "SC", "ST"]

# ============================================================
# IMAGE GENERATION
# ============================================================

for seat in SEAT_TYPES:

    programs = POPULAR_BRANCHES

    total_width = (
        COL_WIDTH_INSTITUTE +
        len(programs) * 2 * COL_WIDTH_PROGRAM
    )

    total_height = (
        120 +
        HEADER_HEIGHT * 2 +
        len(institutes_order) * CELL_HEIGHT +
        PADDING
    )

    img = Image.new("RGB", (total_width + 2 * PADDING, total_height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 20)
        font_header = ImageFont.truetype(FONT_PATH, 14)
        font_body = ImageFont.truetype(FONT_PATH, 13)
    except:
        font_title = font_header = font_body = ImageFont.load_default()

    # ========================================================
    # TITLE
    # ========================================================

    draw.text(
        (PADDING, 10),
        f"{seat} IITs Expected Cut Off 2026",
        fill=(0, 0, 0),
        font=font_title
    )

    y = 60

    # ========================================================
    # HEADER ROW 1 (BRANCH)
    # ========================================================

    draw.rectangle(
        [PADDING, y, PADDING + COL_WIDTH_INSTITUTE, y + HEADER_HEIGHT * 2],
        fill=(230, 230, 230)
    )

    draw.text(
        (PADDING + 10, y + 10),
        "Institute",
        fill=(0, 0, 0),
        font=font_header
    )

    x = PADDING + COL_WIDTH_INSTITUTE

    for branch in programs:

        draw.rectangle(
            [x, y, x + COL_WIDTH_PROGRAM * 2, y + HEADER_HEIGHT],
            fill=(200, 200, 255)
        )

        draw.text(
            (x + 20, y + 10),
            branch,
            fill=(0, 0, 0),
            font=font_header
        )

        x += COL_WIDTH_PROGRAM * 2

    # ========================================================
    # HEADER ROW 2 (M/F)
    # ========================================================

    y2 = y + HEADER_HEIGHT
    x = PADDING + COL_WIDTH_INSTITUTE

    for branch in programs:
        for g in ["M", "F"]:

            draw.rectangle(
                [x, y2, x + COL_WIDTH_PROGRAM, y2 + HEADER_HEIGHT],
                fill=(240, 240, 240)
            )

            draw.text(
                (x + 25, y2 + 10),
                g,
                fill=(0, 0, 0),
                font=font_header
            )

            x += COL_WIDTH_PROGRAM

    y = y + HEADER_HEIGHT * 2

    # ========================================================
    # BODY
    # ========================================================

    for i, inst in enumerate(institutes_order):

        bg = (255, 255, 255) if i % 2 == 0 else (245, 245, 245)

        draw.rectangle(
            [PADDING, y, PADDING + total_width, y + CELL_HEIGHT],
            fill=bg
        )

        x = PADDING

        draw.text(
            (x + 5, y + 10),
            inst[:40],
            fill=(0, 0, 0),
            font=font_body
        )

        x += COL_WIDTH_INSTITUTE

        for branch in programs:

            male = data[inst][branch][seat].get("M", "-")
            female = data[inst][branch][seat].get("F", "-")

            for val in [male, female]:

                draw.text(
                    (x + 20, y + 10),
                    str(val),
                    fill=(0, 0, 0),
                    font=font_body
                )

                x += COL_WIDTH_PROGRAM

        y += CELL_HEIGHT

    # ========================================================
    # SAVE
    # ========================================================

    out_file = f"{OUTPUT_FOLDER}/{seat}_matrix.png"
    img.save(out_file)

    print("Generated:", out_file)

print("\nDONE: All cutoff matrices generated successfully.")