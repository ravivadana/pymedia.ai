import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
from io import BytesIO
BASE_DIR = "00_data_processing"
LOGOS_DIR = f"{BASE_DIR}/assets/logos"
CAMPUS_DIR=f"{BASE_DIR}/assets/campus"
headers = {"User-Agent": "Mozilla/5.0"}
import json
import glob
import os
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
# =========================================================
# CONFIG
# =========================================================
year = 2026
course_name = "engineering"

RANKING_JSON = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/institute_ranking.json"
CUTOFF_FOLDER = f"{BASE_DIR}/data/nrif_ranking/{year}/{course_name}/Cutoff"
OUTPUT_IMAGE_FOLDER = f"{BASE_DIR}/images/nrif_ranking/{year}/{course_name}/cutoff_matrix"
OUTPUT_VIDEO_FOLDER = f"{BASE_DIR}/videos/nrif_ranking/{year}/{course_name}/cutoff_matrix"
AUDIO_FILE = f"{BASE_DIR}/audio/rangeela1.mp4"
ASSETS_FOLDER=f"{BASE_DIR}/assets"
SIZE = (400, 400)

os.makedirs(OUTPUT_IMAGE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_VIDEO_FOLDER, exist_ok=True)
# =========================================================
# HIGH QUALITY SCALE (AI STYLE)
# =========================================================
SCALE = 2
WIDTH = 1080 * SCALE
BRANCH_W = 220 * SCALE
CELL_W = 83 * SCALE
HEADER1 = 70 * SCALE
HEADER2 = 60 * SCALE
HEADER_BLOCK_H = HEADER1 + HEADER2
ROW_H = 75 * SCALE
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
from PIL import Image, ImageDraw
def rounded_image(img, radius=25):
    mask = Image.new("L", img.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle(
        [0, 0, img.width, img.height],
        radius=radius,
        fill=255
    )
    result = img.copy()
    result.putalpha(mask)
    return result
def draw_logo_and_campus(
    canvas,
    logo_path=None,
    campus_path=None
):
    """
    Draw logo left side and campus image right side
    """
    draw = ImageDraw.Draw(canvas)
    LOGO_SIZE = 1400   # bigger logo
    logo_x = 10
    logo_y = 10
    campus_w = 500
    campus_h = 350
    campus_x = canvas.width - campus_w
    campus_y = 0
    # ==========================================
    # LOGO
    # ==========================================
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail(
            (LOGO_SIZE, LOGO_SIZE),
             Image.Resampling.LANCZOS
        )
        canvas.paste(
            logo,
            (logo_x, logo_y),
            logo
        )
    # ==========================================
    # CAMPUS IMAGE
    # ==========================================
    if campus_path and os.path.exists(campus_path):
        campus = Image.open(campus_path).convert("RGB")
        campus = campus.resize(
            (campus_w, campus_h),
            Image.LANCZOS
        )
        campus = campus.convert("RGBA")
        fade = Image.new(
            "L",
            campus.size,
            255
        )
        pixels = fade.load()
        for y in range(campus.height):
            if y > campus.height * 0.65:
                ratio = (
                    (y - campus.height * 0.65)
                    / (campus.height * 0.35)
                )
                alpha = int(
                    255 - ratio * 70
                )
                for x in range(campus.width):
                    pixels[x, y] = alpha
        campus.putalpha(fade)
        mask = Image.new("L", campus.size, 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle(
            [0, 0, campus.width, campus.height],
            radius=40,
            fill=255
        )
        # soften edges
        mask = mask.filter(
            ImageFilter.GaussianBlur(3)
        )
        campus.putalpha(mask)
        shadow = Image.new(
            "RGBA",
            (campus_w + 40, campus_h + 40),
            (0,0,0,0)
        )
        sdraw = ImageDraw.Draw(shadow)
        sdraw.rounded_rectangle(
            [20,20,campus_w+20,campus_h+20],
            radius=45,
            fill=(0,0,0,110)
        )
        shadow = shadow.filter(
            ImageFilter.GaussianBlur(35)
        )
        glow = Image.new(
            "RGBA",
            canvas.size,
            (0,0,0,0)
        )
        gdraw = ImageDraw.Draw(glow)
        gdraw.rectangle(
            (
                campus_x - 80,
                campus_y - 50,
                campus_x + campus_w + 80,
                campus_y + campus_h + 80
            ),
            fill=(0,120,255,40)
        )
        glow = glow.filter(
            ImageFilter.GaussianBlur(60)
        )
        canvas.paste(glow, (0,0), glow)
        canvas.paste(
            shadow,
            (campus_x-20, campus_y-20),
            shadow
        )
        canvas.paste(
            campus,
            (campus_x, campus_y),
            campus
        )
       
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
BRANCH_FONT = load_font(70, True)
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
def short_branch_name(name):
    remove_words = [
        "(4 Years, Bachelor of Technology)",
        "(5 Years, Dual Degree)",
        "(5 Years, Bachelor and Master of Technology (Dual Degree))",
        "(4 Years, Bachelor of Science)",
        "(5 Years, Bachelor of Architecture)",
        "(5 Years, Integrated Bachelor of Science-Master of Science)",
        "(5 Years, Integrated Master of Technology)",
         "(5 Years, Integrated B. Tech. and MBA)",
         "(5 Years, Bachelor and Master of Technology (Dual Degree))"
    ]
    for r in remove_words:
        name = name.replace(r, "")
    words = [
        w for w in name.split()
        if w.lower() not in {"and", "of", "in", "for"}
    ]
    if len(words) == 2 and words[0]!='Engineering':
        return words[0]
    elif len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0].upper() for w in words)
def gradient(img):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        r = int(5 - 5 * y / h)
        g = int(20 - 20 * y / h)
        b = int(80 - 60 * y / h)
        draw.line((0, y, w, y), fill=(r, g, b))
from PIL import Image, ImageDraw, ImageFilter
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
def get_favicon(domain):
    return urljoin(domain, "/favicon.ico")
def get_domain(url):
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except:
        return None
def process_image(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    # Make square canvas
    max_side = max(img.size)
    square = Image.new("RGBA", (max_side, max_side), (255, 255, 255, 0))
    # Center image
    x = (max_side - img.size[0]) // 2
    y = (max_side - img.size[1]) // 2
    square.paste(img, (x, y), img if img.mode == "RGBA" else None)
    # High-quality resize
    square = square.resize(SIZE, Image.LANCZOS)
    # Convert to white background (clean UI look)
    final_img = Image.new("RGB", SIZE, (255, 255, 255))
    final_img.paste(square, mask=square.split()[3])
    return final_img
def download_and_process(url, save_path):
    try:
        r = requests.get(url, headers=headers, timeout=10, stream=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            img = process_image(r.content)
            img.save(save_path, "PNG", optimize=True)
            return True
    except:
        pass
    return False
def extract_campus_image(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        images = soup.find_all("img")
        candidates = []
        for img in images:
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            src = urljoin(url, src)
            low = src.lower()
            # ❌ skip junk
            if any(x in low for x in [
                "logo", "icon", "sprite", "avatar",
                "banner-small", "thumb", "ads", "advert"
            ]):
                continue
            # try to guess "campus relevance"
            score = 0
            if any(x in low for x in ["campus", "building", "institute", "university", "college"]):
                score += 5
            if img.get("width") and img.get("height"):
                try:
                    w = int(img.get("width", 0))
                    h = int(img.get("height", 0))
                    if w * h > 50000:
                        score += 3
                except:
                    pass
            # prioritize large images
            score += 1
            candidates.append((score, src))
        if not candidates:
            return None
        # sort by score (best first)
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]
    except Exception as e:
        print(f"⚠️ campus extraction error: {e}")
        return None
def download_campus_image(img_url, save_path):
    try:
        r = requests.get(img_url, headers=headers, timeout=10, stream=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(r.content)).convert("RGB")
            # Resize but KEEP LANDSCAPE (no square forcing)
            img.thumbnail((800, 800), Image.LANCZOS)
            img.save(save_path, "PNG", optimize=True)
            return True
    except Exception as e:
        print(f"⚠️ Campus error: {e}")
    return False
    
def extract_logo_from_html(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Open Graph image (usually large)
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return urljoin(url, og["content"])

        # 2. Apple touch icon (often 180x180+)
        apple = soup.find("link", rel=lambda x: x and "apple-touch-icon" in str(x))
        if apple and apple.get("href"):
            return urljoin(url, apple["href"])

        # 3. Normal favicon
        icon = soup.find("link", rel=lambda x: x and "icon" in str(x).lower())
        if icon and icon.get("href"):
            return urljoin(url, icon["href"])

    except:
        pass

    return None
# =========================================================
# IMAGE CREATION
# =========================================================
def create_cutoff_image(
    institute_name,
    rank,
    score,
    matrix,
    output_file,
    logo_path=None,
    campus_path=None
    ):
    seat_types = ["OPEN", "EWS", "OBC", "SC", "ST"]
    if not matrix or len(matrix) == 0:
        branches = []
    else:
        branches = sorted(
            matrix.keys(),
            key=lambda b: matrix[b].get("OPEN", {}).get("M", 999999)
        )
    HEIGHT = TOP_H + HEADER_BLOCK_H + ROW_H * len(branches) + NOTE_H
    img = Image.new("RGB", (WIDTH, HEIGHT))
    gradient(img)
    img = create_thumbnail_background(
        WIDTH,
        HEIGHT
    )
    draw = ImageDraw.Draw(img)
    draw_logo_and_campus(
        img,
        logo_path,
        campus_path
    )
    # =====================================================
    # TITLE
    # =====================================================
    city = r.get("City", "")
    state = r.get("State", "")
    location = f"{city}, {state}".strip(", ").upper()
    # Header layout
    TITLE_Y = 120
    LOCATION_Y = 340
    CUTOFF_Y = 490
    RANK_BOX_Y = 690
    CUT_OFF_TABLE_Y=840
    title_font = load_font(180, True)
    location_font = load_font(80, True)
    cutoff_font = load_font(150, True)
    rank_font = load_font(100, True)
    # -----------------------------------------------------
    # Institute Name
    # -----------------------------------------------------
    draw.text(
        (WIDTH//2 + 5, TITLE_Y + 5),
        institute_name.upper(),
        fill=(20,20,20),
        font=title_font,
        anchor="mt"
    )
    draw.text(
        (WIDTH//2, TITLE_Y),
        institute_name.upper(),
        fill="white",
        font=title_font,
        anchor="mt"
    )
    # -----------------------------------------------------
    # Location
    # -----------------------------------------------------
    draw.text(
        (WIDTH//2, LOCATION_Y),
        location,
        fill=(255,215,0),
        font=location_font,
        anchor="mt"
    )
    # decorative lines
    line_y = LOCATION_Y + 30
    draw.line(
        (WIDTH//2 - 320, line_y,
        WIDTH//2 - 120, line_y),
        fill=(255,215,0),
        width=4
    )
    draw.line(
        (WIDTH//2 + 120, line_y,
        WIDTH//2 + 320, line_y),
        fill=(255,215,0),
        width=4
    )
    # -----------------------------------------------------
    # EXPECTED CUTOFF 2026
    # -----------------------------------------------------
    draw.text(
        (WIDTH//2 + 6, CUTOFF_Y + 6),
        "ROUND 1 CUTOFF 2026",
        fill=(60,40,0),
        font=cutoff_font,
        anchor="mt"
    )
    draw.text(
        (WIDTH//2, CUTOFF_Y),
        "ROUND 1 CUTOFF 2026",
        fill=(255,215,0),
        font=cutoff_font,
        anchor="mt"
    )
    # -----------------------------------------------------
    # NIRF BOX
    # -----------------------------------------------------
    rr(
        draw,
        [120, RANK_BOX_Y, WIDTH-120, RANK_BOX_Y+90],
        fill=(8,25,80),
        outline=(255,215,0)
    )
    draw.text(
        (WIDTH//2, RANK_BOX_Y+45),
        f"NIRF Rank #{rank}  |  Score {score}",
        fill="white",
        font=rank_font,
        anchor="mm"
    )

    if not branches:
        draw.text(
        (WIDTH // 2, HEIGHT // 2),
        "NO CUTOFF DATA AVAILABLE",
        fill=(255, 200, 0),
        font=load_font(80, True),
        anchor="mm"
    )
    draw.text(
        (WIDTH // 2, HEIGHT // 2 + 120),
        "DATA NOT FOUND FOR THIS INSTITUTE",
        fill=(200, 200, 200),
        font=load_font(40),
        anchor="mm"
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
        [0, table_y, BRANCH_W, table_y + HEADER_BLOCK_H],
        fill=NAVY
    )
    draw.multiline_text(
        (BRANCH_W // 2, table_y + HEADER_BLOCK_H // 2),
        "ENGINEERING\nBRANCH",
        fill=WHITE,
        font=HEADER_FONT,
        anchor="mm",
        align="center"
    )
    # =====================================================
    # SEAT HEADERS
    # =====================================================
    x = BRANCH_W
    for seat in seat_types:
        draw.rectangle(
            [x, table_y, x + CELL_W * 2, table_y + HEADER1],
            fill={
                "OPEN": OPEN_COLOR,
                "EWS": EWS_COLOR,
                "OBC": OBC_COLOR,
                "SC": SC_COLOR,
                "ST": ST_COLOR
            }[seat]
        )
        draw.text(
            (x + CELL_W, table_y + HEADER1 // 2),
            seat,
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
    BRANCH_BG = (4,38,96)
    BRANCH_BORDER = (90,140,255)
    for i, branch in enumerate(branches):
        y = start_y + i * ROW_H
        row_bg = (245, 245, 245) if i % 2 == 0 else WHITE
        # 1. draw full row background
        draw.rectangle(
            [0, y, WIDTH, y + ROW_H],
            fill=row_bg
        )
        # 2. override ONLY branch column background
        draw.rectangle([0, y, BRANCH_W, y + ROW_H],
                    fill=BRANCH_BG)
        # branch text
        draw.text((80, y + ROW_H // 2),
                branch,
                fill=WHITE,
                font=BRANCH_FONT,
                anchor="lm")
        x = BRANCH_W
        for seat in seat_types:
            m = matrix[branch].get(seat, {}).get("M", "-")
            f = matrix[branch].get(seat, {}).get("F", "-")
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
            
    # sharpen
    rr(
        draw,
        [60, HEIGHT - 110, WIDTH - 60, HEIGHT - 25],
        fill=(5,20,70),
        outline=(255,215,0),
        radius=25
    )
    draw.text(
        (WIDTH//2, HEIGHT - 68),
        "BASED ON JOSAA 2025 CLOSING RANKS (ROUND 6)",
        fill="white",
        font=load_font(30, True),
        anchor="mm"
    )
    img.save(output_file, optimize=True)
    print("Saved:", output_file)
all_records = []
for file in glob.glob(f"{CUTOFF_FOLDER}/*.json"):
    with open(file, "r", encoding="utf-8") as f:
        all_records.extend(json.load(f))
grouped = {}
for r in all_records:
    key = (
        r["Institute"].replace(",",""),
        r["Academic Program Name"],
        r["Quota"],
        r["Seat Type"],
        r["Gender"]
    )
    rank = parse_rank(r.get("Closing Rank"))
    if key not in grouped or rank > parse_rank(grouped[key].get("Closing Rank")):
        grouped[key] = r

cutoff_data = list(grouped.values())
cutoff_lookup = defaultdict(list)
for row in cutoff_data:
    cutoff_lookup[normalize(row["Institute"].replace(",",""))].append(row)
# =========================================================
# GENERATE IMAGES
# =========================================================
with open(RANKING_JSON, "r", encoding="utf-8") as f:
    ranking_data = json.load(f)
for r in ranking_data:
    name = r["Name"].replace(",","")
    key = normalize(name)

    
    if key not in cutoff_lookup:
        continue

    rank=int(f'{int(r['Rank']):03d}')
    # # =====================================================
    # # 1. LOGO PROCESS
    # # =====================================================
    # website = r.get("Official Website", "")
    # if not website:
    #     print(f"❌ Missing website: {name}")
    # short_name = short_institute_name(name)
    # domain = get_domain(website)
    # print(f"\n🔍 {rank} - {name}")
    # logo_filename = f"{int(r['Rank']):03d}_{short_name.replace(' ', '_')}.png"
    # logo_path = os.path.join(LOGOS_DIR, logo_filename)
    # logo_url = extract_logo_from_html(website)
    # if not logo_url and domain:
    #     logo_url = get_favicon(domain)
    # if logo_url:
    #     ok = download_and_process(logo_url, logo_path)
    #     if ok:
    #         print(f"✅ Logo saved: {logo_path}")
    #     else:
    #         print(f"⚠️ Logo failed: {logo_url}")
    # else:
    #     print("❌ No logo found")

    # # =====================================================
    # # 2. CAMPUS PROCESS
    # # =====================================================
    # campus_url = extract_campus_image(website)
    # campus_filename = f"{int(r['Rank']):03d}_{short_name.replace(' ', '_')}.jpg"
    # campus_path = os.path.join(CAMPUS_DIR, campus_filename)
    # if campus_url:
    #     ok = download_campus_image(campus_url, campus_path)
    #     if ok:
    #         print(f"🏫 Campus saved: {campus_path}")
    #     else:
    #         print(f"⚠️ Campus failed: {campus_url}")
    # else:
    #     print("❌ No campus image found")

    if key not in cutoff_lookup:
        matrix = None
    else:
        matrix = defaultdict(lambda: defaultdict(dict))
        for row in cutoff_lookup[key]:
            seat = row["Seat Type"]
            if "PwD" in seat:
                continue
            if seat == "OBC-NCL":
                seat = "OBC"
            if seat not in ["OPEN", "EWS", "OBC", "SC", "ST"]:
                continue

            gender = "M" if row["Gender"] == "Gender-Neutral" else "F"
            branch = short_branch_name(row["Academic Program Name"])

            matrix[branch][seat][gender] = parse_rank(row["Closing Rank"])
    matrix = defaultdict(lambda: defaultdict(dict))
    for row in cutoff_lookup[key]:
        seat = row["Seat Type"]
        if "PwD" in seat:
            continue
        if seat == "OBC-NCL":
            seat = "OBC"
        if seat not in ["OPEN", "EWS", "OBC", "SC", "ST"]:
            continue
        gender = "M" if row["Gender"] == "Gender-Neutral" else "F"
        branch = short_branch_name(row["Academic Program Name"])
        matrix[branch][seat][gender] = parse_rank(row["Closing Rank"])
    short_name = short_institute_name(name)
    filename = f"{int(r['Rank']):03d}_{short_name.replace(' ', '_')}.png"
    output_file = os.path.join(OUTPUT_IMAGE_FOLDER, filename)
    logo_path=f"{ASSETS_FOLDER}/logos/{filename}"
    campus_path=f"{ASSETS_FOLDER}/campus/{filename.replace('png','jpg')}"
    create_cutoff_image(
        short_name,
        r["Rank"],
        r["Score"],
        matrix,
        output_file,logo_path,campus_path)
print("DONE")