import os
import json
import re
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips

# =========================================================
# CONFIG
# =========================================================

INPUT_FOLDER = "00_data_processing/data/SeatAllotmentResult2025/ranking"
SEAT_ALLOTMENT_FOLDER = "00_data_processing/data/SeatAllotmentResult2025"
OUTPUT_FOLDER = "00_data_processing/videos"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

SLIDE_DURATION = 3
FPS = 30

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================================================
# COLORS
# =========================================================

TOP_COLOR = (36, 214, 73)
BOTTOM_COLOR = (116, 214, 134)

TITLE_COLOR = (255, 255, 255)

RANK_BG = (250, 250, 250)
RANK_TEXT = (37, 99, 235)

CARD_BG = (255, 255, 255)

# =========================================================
# NORMALIZATION (CRITICAL FIX)
# =========================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = text.replace("&", "and")
    text = text.replace(",", "")
    text = text.replace(".", "")
    text = text.replace("-", " ")
    text = text.replace("(", "")
    text = text.replace(")", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# FONT LOADER
# =========================================================

def load_font(size, bold=False):
    
    font_list_bold = [
        "arialbd.ttf",              # Windows bold
        "Arial Bold.ttf",
        "DejaVuSans-Bold.ttf"
    ]

    font_list_regular = [
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf"
    ]

    fonts = font_list_bold if bold else font_list_regular

    for f in fonts:
        try:
            return ImageFont.truetype(f, size)
        except:
            continue

    return ImageFont.load_default()


HEADER_FONT = load_font(38)
RANK_FONT = load_font(95)
INSTITUTE_FONT = load_font(60, bold=True)
LABEL_FONT = load_font(30, bold=False)
RANK_FONT_SMALL = load_font(34, bold=True)
PROGRAM_FONT = load_font(30, bold=True)
VALUE_FONT = load_font(40)
FOOTER_FONT = load_font(26)

# =========================================================
# LOAD DATA
# =========================================================

def load_seat_allotment_data():

    institute_cutoffs = {}

    files = [
        os.path.join(SEAT_ALLOTMENT_FOLDER, f"round_{i}.json")
        for i in range(1, 7)
    ]

    for file_path in files:

        if not os.path.exists(file_path):
            continue

        print("Loading:", file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:

            institute = item.get("Institute") or item.get("Name") or ""
            institute = institute.strip()

            if not institute:
                continue

            program = item.get("Academic Program Name", "")
            quota = item.get("Quota", "")
            seat_type = item.get("Seat Type", "")
            gender = item.get("Gender", "")

            try:
                opening_rank = int(item.get("Opening Rank"))
            except:
                opening_rank = None

            try:
                closing_rank = int(item.get("Closing Rank"))
            except:
                closing_rank = None

            key = (program, quota, seat_type, gender)

            norm = normalize_text(institute)

            if norm not in institute_cutoffs:
                institute_cutoffs[norm] = {
                    "display": institute,
                    "data": {}
                }

            if key not in institute_cutoffs[norm]["data"]:
                institute_cutoffs[norm]["data"][key] = {
                    "opening_rank": opening_rank,
                    "closing_rank": closing_rank
                }
            else:
                ex = institute_cutoffs[norm]["data"][key]

                if opening_rank is not None:
                    ex["opening_rank"] = (
                        opening_rank
                        if ex["opening_rank"] is None
                        else min(ex["opening_rank"], opening_rank)
                    )

                if closing_rank is not None:
                    ex["closing_rank"] = (
                        closing_rank
                        if ex["closing_rank"] is None
                        else max(ex["closing_rank"], closing_rank)
                    )

    return institute_cutoffs


INSTITUTE_CUTOFFS = load_seat_allotment_data()


# =========================================================
# LOOKUP (FIX IIT / NIT / & / VARIATIONS)
# =========================================================

def find_cutoff_data(name):

    norm = normalize_text(name)

    if norm in INSTITUTE_CUTOFFS:
        return INSTITUTE_CUTOFFS[norm]["data"]

    # fuzzy match
    for k, v in INSTITUTE_CUTOFFS.items():
        if norm in k or k in norm:
            return v["data"]

    return {}


# =========================================================
# BACKGROUND
# =========================================================

def create_gradient_background():

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), TOP_COLOR)
    draw = ImageDraw.Draw(img)

    for y in range(VIDEO_HEIGHT):

        r = int(TOP_COLOR[0] * (1 - y / VIDEO_HEIGHT) + BOTTOM_COLOR[0] * (y / VIDEO_HEIGHT))
        g = int(TOP_COLOR[1] * (1 - y / VIDEO_HEIGHT) + BOTTOM_COLOR[1] * (y / VIDEO_HEIGHT))
        b = int(TOP_COLOR[2] * (1 - y / VIDEO_HEIGHT) + BOTTOM_COLOR[2] * (y / VIDEO_HEIGHT))

        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))

    return img


# =========================================================
# WRAP TEXT
# =========================================================

def wrap_text(draw, text, font, max_width):

    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = current + " " + w if current else w
        bbox = draw.textbbox((0, 0), test, font=font)

        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines


# =========================================================
# SLIDE
# =========================================================

def create_slide(rank_data, output_image):

    img = create_gradient_background()
    draw = ImageDraw.Draw(img)

    rank = rank_data.get("Rank", "")
    name = rank_data.get("Name", "")

    city = rank_data.get("City", "")
    state = rank_data.get("State", "")
    score = rank_data.get("Score", "")

    cutoff_data = find_cutoff_data(name)

    # ================= RANK =================

    rank_text = f"#{rank}"

    bbox = draw.textbbox((0, 0), rank_text, font=RANK_FONT)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]

    draw.rounded_rectangle(
        [60, 80, 60 + w + 80, 80 + h + 60],
        radius=25,
        fill=RANK_BG
    )

    draw.text((90, 100), rank_text, font=RANK_FONT, fill=RANK_TEXT)

    # ================= NAME =================

    x = 300
    lines = wrap_text(draw, name, INSTITUTE_FONT, 700)

    y = 80
    for line in lines:
        draw.text((x, y), line, font=INSTITUTE_FONT, fill=TITLE_COLOR)
        y += 60

    # ================= DETAILS =================

    card_y = y + 40

    draw.rounded_rectangle(
        [70, card_y, VIDEO_WIDTH-70, card_y+160],
        radius=25,
        fill=CARD_BG
    )

    info = [("City", city), ("State", state), ("Score", score)]
    sec = (VIDEO_WIDTH-140)//3

    for i,(k,v) in enumerate(info):
        cx = 70 + sec*i + sec//2
        draw.text((cx-40, card_y+25), k, font=LABEL_FONT, fill=(80,80,80))
        draw.text((cx-40, card_y+75), str(v), font=VALUE_FONT, fill=(0,0,0))

    # ================= CUTOFF =================

    cy = card_y + 200

    draw.rounded_rectangle(
        [70, cy, VIDEO_WIDTH-70, VIDEO_HEIGHT-100],
        radius=30,
        fill=(255,255,255)
    )

    draw.text((80, cy+20), "BRANCHWISE CUTOFFS", font=LABEL_FONT, fill=(0,0,0))

    items = rank_data.get("_cutoff_items", list(cutoff_data.items()))

    y = cy + 100

    for (prog,q,s,g), val in items[:8]:

        card_x1 = 90
        card_x2 = VIDEO_WIDTH - 90

        card_y1 = y
        card_y2 = y + 120

        draw.rounded_rectangle(
            [card_x1, card_y1, card_x2, card_y2],
            radius=15,
            fill=(240, 244, 255)
        )

        # =============================================
        # PROGRAM (LEFT 70%)
        # =============================================

        prog_width = int((card_x2 - card_x1) * 0.70)

        # ================= PROGRAM =================

        x = card_x1 + 15
        y = card_y1 + 10

        program_lines = wrap_text(draw, prog, LABEL_FONT, prog_width)

        line_height = 26
        max_program_lines = 2

        for i, line in enumerate(program_lines[:max_program_lines]):
            draw.text(
                (x, y),
                line,
                font=LABEL_FONT,
                fill=(20, 20, 20)
            )
            y += line_height

        # IMPORTANT: force minimum program block height
        program_block_bottom = max(y, card_y1 + 70)

        # ================= META =================

        meta = f"{q} | {s} | {g}"

        meta_y = program_block_bottom + 10   # 👈 FIXED GAP CONTROL

        draw.text(
            (x, meta_y),
            meta,
            font=LABEL_FONT,
            fill=(90, 90, 90)
        )

        # update bottom tracker for next sections
        meta_block_bottom = meta_y + 10
        # =============================================
        # RANK (RIGHT SIDE)
        # =============================================

        if isinstance(val.get("opening_rank"), int) and isinstance(val.get("closing_rank"), int):
                rr = f"{val['opening_rank']:,} - {val['closing_rank']:,}"
        else:
            rr = "-"

        bbox = draw.textbbox((0, 0), rr, font=RANK_FONT_SMALL)
        rw = bbox[2] - bbox[0]

        draw.text(
            (
                card_x2 - rw - 15,
                card_y1 + 25
            ),
            rr,
            font=RANK_FONT_SMALL,
            fill=(37, 99, 235)
        )

        y += 80

    img.save(output_image)


# =========================================================
# VIDEO
# =========================================================

def create_video_from_json(json_path):
    
    from moviepy import ImageClip, concatenate_videoclips
    import gc

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    temp = "temp_slides"
    os.makedirs(temp, exist_ok=True)

    clips = []

    idx = 0

    for item in data:

        cutoff = find_cutoff_data(item.get("Name", ""))
        cutoff_items = list(cutoff.items())

        ITEMS_PER_SLIDE = 8

        pages = [
            cutoff_items[i:i+ITEMS_PER_SLIDE]
            for i in range(0, len(cutoff_items), ITEMS_PER_SLIDE)
        ]

        if not pages:
            pages = [[]]

        for p, page in enumerate(pages):

            item["_cutoff_items"] = page

            path = os.path.join(temp, f"{idx}.png")

            create_slide(item, path)

            clip = ImageClip(path, duration=SLIDE_DURATION)

            clips.append(clip)

            idx += 1

            # SAFETY FLUSH
            if len(clips) >= 50:

                temp_video = concatenate_videoclips(
                    clips,
                    method="chain"
                )

                chunk_path = os.path.join(
                    temp,
                    f"chunk_{idx}.mp4"
                )

                temp_video.write_videofile(
                    chunk_path,
                    fps=FPS,
                    codec="libx264",
                    audio=False,
                    logger=None
                )

                # cleanup
                for c in clips:
                    c.close()

                temp_video.close()

                clips.clear()

                gc.collect()

    # FINAL REMAINING CLIPS
    if clips:

        final = concatenate_videoclips(
            clips,
            method="chain"
        )

        out = os.path.join(
            OUTPUT_FOLDER,
            os.path.basename(json_path).replace(".json", ".mp4")
        )

        final.write_videofile(
            out,
            fps=FPS,
            codec="libx264",
            audio=False
        )

        for c in clips:
            c.close()

        final.close()

        gc.collect()

    print("DONE")


# =========================================================
# RUN
# =========================================================

for f in os.listdir(INPUT_FOLDER):
    if f.endswith(".json"):
        create_video_from_json(os.path.join(INPUT_FOLDER, f))

print("ALL DONE")