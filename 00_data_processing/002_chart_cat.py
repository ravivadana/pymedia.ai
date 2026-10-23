import os
import re
import json
from PIL import Image, ImageDraw, ImageFont
from Image2VideoGenerator import Image2VideoGenerator

# --- 1. GLOBAL BASE STYLING CONFIGURATION ---
WHITE = (255, 255, 255)
DARK_BLUE = (12, 28, 54)
GOLD = (212, 175, 55)          # Metallic Gold accent
LIGHT_GOLD = (255, 235, 160)    # Highlight Gold
TEXT_RED = (255, 255, 255)        # Bright highlight color for Female ranks

video_engine = Image2VideoGenerator(
        target_width=1080, 
        target_height=1920, 
        default_duration=59, 
        fps=30,
        audio=f"00_data_processing/assets/audios/arginine_fifa_2026.mp4")
year = 2026

# Paths mapped precisely to your setup
INSTITUTE_RANKING_PATH = f"00_data_processing/data/nrif_ranking/{year}/engineering/institute_ranking.json"
CUTOFF_DATA_PATH = f"00_data_processing/data/nrif_ranking/{year}/engineering/Cutoff/round1.json"
OUTPUT_FOLDER = f"00_data_processing/images/nrif_ranking/{year}/engineering/chart_categories"

CATEGORY_MAP = ["OPEN", "EWS", "OBC-NCL", "SC", "ST"]

# --- 2. DYNAMIC MAPPING DEFINITIONS ---
DYNAMIC_BRANCH_RULES = {
    "CSE":         {"keywords": ["computer science"], "color": (255, 140, 0)},       # Orange
    "AIDA":        {"keywords": ["artificial intelligence", "data science"], "color": (34, 139, 34)}, # Green
    "Electrical":  {"keywords": ["electrical"], "color": (218, 165, 32)},            # Yellow-Gold
    "Mechanical":  {"keywords": ["mechanical"], "color": (220, 20, 60)},             # Red
    "Civil":       {"keywords": ["civil"], "color": (148, 0, 211)},                  # Purple
    "Electronics": {"keywords": ["electronics"], "color": (255, 140, 0)},            # Orange
    "Chemical":    {"keywords": ["chemical"], "color": (0, 139, 139)}                # Dark Cyan
}

# --- 3. DYNAMIC DATA UTILITIES & CLEANING ---
def normalize_name(name):
    if not name: return ""
    return re.sub(r'\s+', ' ', name.lower().strip())

def dynamic_clean_branch_name(raw_program_name):
    """Scans the raw program text against your defined keywords."""
    if not raw_program_name:
        return None
        
    normalized_program = raw_program_name.lower()
    for clean_acronym, rules in DYNAMIC_BRANCH_RULES.items():
        for keyword in rules["keywords"]:
            if keyword in normalized_program:
                return clean_acronym
    return None

def shorten_institute_name(name):
    name = name.replace("Indian Institute of Technology", "IIT")
    name = name.replace("National Institute of Technology", "NIT")
    name = name.replace("Institute of Engineering and Technology","IET")
    name = name.replace("Indian Institute of Engineering Science and Technology","IIEST")
    name = name.replace("Ambedkar","A")
    name = name.replace("University of","UO ")

    if "Banaras Hindu University" in name or "BHU" in name:
        return "IIT (BHU) Varanasi"
    if "Indian School of Mines" in name or "ISM" in name:
        return "IIT (ISM) Dhanbad"
    if "(" in name:
        name = name.split("(")[0].strip()
    return name[:24]

# --- 4. RENDERING HELPERS ---
def draw_linear_gradient(image, top_color, bottom_color):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for y in range(height):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / height))
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / height))
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_gold_gradient_box(draw, box, radius=15):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(23, 35, 55), outline=GOLD, width=2)

# --- 5. CATEGORY MATRIX CHART GENERATOR ---
def generate_category_chart(admision_name, category_name, quota_name, matrix_data, branches_list):
    WIDTH = max(1650, 360 + (len(branches_list) * 220) + 60)
    table_top = 280   
    row_height = 72  
    
    total_table_height = (len(matrix_data) + 2) * row_height
    HEIGHT = table_top + total_table_height + 140
    
    base_image = Image.new("RGB", (WIDTH, HEIGHT))
    draw_linear_gradient(base_image, (20, 36, 61), (10, 18, 32))
    draw = ImageDraw.Draw(base_image)

    try:
        font_title = ImageFont.truetype("timesbd.ttf", 66)      
        font_sub = ImageFont.truetype("arialbd.ttf", 34)         
        font_data_bold = ImageFont.truetype("arialbd.ttf", 35)   
        font_data_reg = ImageFont.truetype("arial.ttf", 40)      
    except IOError:
        font_title = font_sub = font_data_bold = font_data_reg = ImageFont.load_default()

    # 1. Outer Frame Border
    draw.rectangle([15, 15, WIDTH-15, HEIGHT-15], outline=GOLD, width=3)

    # 2. Main Title Banner (Split into separate lines)
    title_line1 = admision_name
    if quota_name:
        title_line2 = f"{category_name} ({quota_name}) CATEGORY CUTOFF ({year})"
    else:
        title_line2 = f"{category_name} CATEGORY CUTOFF ({year})"
        
    y_line1 = 80
    y_line2 = 155
    y_sub = 220
    
    # Render Line 1 (Admission Body Profile)
    draw.text((WIDTH // 2 + 3, y_line1 + 3), title_line1, fill=(0, 0, 0), font=font_title, anchor="mm")
    draw.text((WIDTH // 2 - 1, y_line1 + 1), title_line1, fill=(0, 0, 0), font=font_title, anchor="mm")
    draw.text((WIDTH // 2, y_line1), title_line1, fill=(255, 255, 255), font=font_title, anchor="mm")

    if title_line2 is not None:
        # Render Line 2 (Category Rules Target Profile)
        draw.text((WIDTH // 2 + 3, y_line2 + 3), title_line2, fill=(0, 0, 0), font=font_title, anchor="mm")
        draw.text((WIDTH // 2 - 1, y_line2 + 1), title_line2, fill=(0, 0, 0), font=font_title, anchor="mm")
        draw.text((WIDTH // 2, y_line2), title_line2, fill=(255, 255, 255), font=font_title, anchor="mm")
        
    # Subtitle Segment Banner Placement
    subtitle_str = "ROUND 1 CLOSING RANKS ANALYSIS"
    draw.text((WIDTH // 2 + 2, y_sub + 2), subtitle_str, fill=(0, 0, 0), font=font_sub, anchor="mm")
    draw.text((WIDTH // 2, y_sub), subtitle_str, fill=(255, 225, 130), font=font_sub, anchor="mm")

    # 3. Grid Calculations 
    col_inst_w = 360  
    table_inner_w = WIDTH - 60
    col_branch_w = (table_inner_w - col_inst_w) // len(branches_list)
    sub_col_w = col_branch_w // 2
    GRID_LINE_COLOR = (50, 75, 110)

    # 4. Draw Master Table Outline
    draw.rounded_rectangle([30, table_top, WIDTH-30, table_top + total_table_height], radius=12, outline=GOLD, width=3)

    # 5. "INSTITUTE" Column Header Block
    draw.rectangle([32, table_top + 2, 30 + col_inst_w, table_top + (2 * row_height) - 1], fill=(16, 28, 48))
    draw.text((30 + col_inst_w // 2, table_top + row_height), "INSTITUTE (Tier)", fill=WHITE, font=font_data_bold, anchor="mm")

    for i, b_name in enumerate(branches_list):
        x_start = 30 + col_inst_w + (i * col_branch_w)
        assigned_color = DYNAMIC_BRANCH_RULES.get(b_name, {}).get("color", (40, 50, 70))
        
        draw.rectangle([x_start, table_top + 2, x_start + col_branch_w - 1, table_top + row_height], fill=assigned_color)
        draw.text((x_start + col_branch_w // 2, table_top + row_height // 2), b_name, fill=WHITE, font=font_data_bold, anchor="mm")

        dark_tint_m = tuple(int(c * 0.6) for c in assigned_color)
        dark_tint_f = tuple(int(c * 0.45) for c in assigned_color)

        draw.rectangle([x_start, table_top + row_height, x_start + sub_col_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_m)
        draw.text((x_start + sub_col_w // 2, table_top + row_height + row_height // 2), "M", fill=WHITE, font=font_data_bold, anchor="mm")
        
        draw.rectangle([x_start + sub_col_w, table_top + row_height, x_start + col_branch_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_f)
        draw.text((x_start + sub_col_w + sub_col_w // 2, table_top + row_height + row_height // 2), "F", fill=WHITE, font=font_data_bold, anchor="mm")

    draw.line([(30 + col_inst_w, table_top), (30 + col_inst_w, table_top + (2 * row_height))], fill=GOLD, width=2)
    for i in range(1, len(branches_list)):
        x_sep = 30 + col_inst_w + (i * col_branch_w)
        draw.line([(x_sep, table_top), (x_sep, table_top + (2 * row_height))], fill=GOLD, width=2)
        draw.line([(x_sep - sub_col_w, table_top + row_height), (x_sep - sub_col_w, table_top + (2 * row_height))], fill=GRID_LINE_COLOR, width=1)
    draw.line([(WIDTH - 30 - sub_col_w, table_top + row_height), (WIDTH - 30 - sub_col_w, table_top + (2 * row_height))], fill=GRID_LINE_COLOR, width=1)

    draw.line([(30 + col_inst_w, table_top + row_height), (WIDTH - 30, table_top + row_height)], fill=GRID_LINE_COLOR, width=2)
    draw.line([(30, table_top + (2 * row_height)), (WIDTH - 30, table_top + (2 * row_height))], fill=GOLD, width=3)

    # 6. Data Row Renderer
    current_y = table_top + (2 * row_height)
    for idx, (inst_name, branches) in enumerate(matrix_data.items()):
        row_bg = (24, 38, 61) if idx % 2 == 0 else (14, 22, 38)
        
        draw.rectangle([32, current_y + 1, 30 + col_inst_w, current_y + row_height - 1], fill=row_bg)
        draw.line([(30, current_y + row_height), (WIDTH - 30, current_y + row_height)], fill=GRID_LINE_COLOR, width=1)
        
        draw.text((45, current_y + row_height // 2), inst_name, fill=(255, 245, 210), font=font_data_bold, anchor="lm")
        draw.line([(30 + col_inst_w, current_y), (30 + col_inst_w, current_y + row_height)], fill=GRID_LINE_COLOR, width=2)

        for b_idx, b_name in enumerate(branches_list):
            ranks = branches.get(b_name, ["-", "-"])
            x_branch_start = 30 + col_inst_w + (b_idx * col_branch_w)
            assigned_color = DYNAMIC_BRANCH_RULES.get(b_name, {}).get("color", (0, 0, 0))
            
            draw.rectangle([x_branch_start + 1, current_y + 1, x_branch_start + col_branch_w - 1, current_y + row_height - 1], fill=(255, 255, 255))
            
            m_rank = str(ranks[0])
            m_x = x_branch_start + sub_col_w // 2
            m_color = assigned_color if m_rank != "-" else (130, 140, 155)
            draw.text((m_x, current_y + row_height // 2), m_rank, fill=m_color, font=font_data_reg if m_rank != "-" else font_data_bold, anchor="mm")
            
            f_rank = str(ranks[1])
            f_x = x_branch_start + sub_col_w + sub_col_w // 2
            deep_f_color = tuple(int(c * 0.75) for c in assigned_color)
            f_color = deep_f_color if f_rank != "-" else (130, 140, 155)
            draw.text((f_x, current_y + row_height // 2), f_rank, fill=f_color, font=font_data_bold, anchor="mm")

            if b_idx < len(branches_list) - 1:
                draw.line([(x_branch_start + col_branch_w, current_y), (x_branch_start + col_branch_w, current_y + row_height)], fill=GRID_LINE_COLOR, width=2)
            draw.line([(x_branch_start + sub_col_w, current_y), (x_branch_start + sub_col_w, current_y + row_height)], fill=GRID_LINE_COLOR, width=1)

        current_y += row_height

    # Footer processing block
    footer_y = HEIGHT - 85
    draw_gold_gradient_box(draw, [30, footer_y, WIDTH - 30, footer_y + 55], radius=10)
    draw.text((WIDTH // 2, footer_y + 27), f"DATA SOURCE: JoSAA {year} CLOSING RANKS (ROUND 1)", fill=LIGHT_GOLD, font=font_data_bold, anchor="mm")

    OUTPUT_FOLDER=f'{OUTPUT_FOLDER}'
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # File naming system normalization
    clean_admission_name = admision_name.replace(" ", "_")
    clean_cat_filename = category_name.replace("-", "_")
    quota_suffix = f"_{quota_name.replace(' ', '_')}" if quota_name else ""
    output_path = os.path.join(OUTPUT_FOLDER, f"{clean_admission_name}_{clean_cat_filename}{quota_suffix}_{year}_#JoSAA_chart_categories.png")
    
    base_image.save(output_path)
    print(f"Generated Sheet successfully at: {output_path}")
    
    input_chart = output_path
    output_video = input_chart.replace('images','videos').replace('.png','.mp4')
    
    # Dynamic runtime verification preventing audio/render crashes if destination workspace structure changes
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    #video_engine.generate_scrolling_video(input_chart, output_video)

# --- 6. EXECUTION PIPELINE ---
def main(branches_list):
    if not os.path.exists(INSTITUTE_RANKING_PATH) or not os.path.exists(CUTOFF_DATA_PATH):
        print("CRITICAL ERROR: Source JSON databases missing. Verify file paths configuration pipeline.")
        return

    with open(INSTITUTE_RANKING_PATH, 'r', encoding='utf-8') as f:
        master_rankings = json.load(f)
    with open(CUTOFF_DATA_PATH, 'r', encoding='utf-8') as f:
        cutoff_raw = json.load(f)

    # Automated structural execution settings configuration matrix
    execution_modes = [
        {"is_iit": True,  "admision_name": f"IITs Admission based on IIT JEE Advanced ",          "filter_keyword": "Indian Institute of Technology"},
        {"is_iit": False, "admision_name": f"NITs Admission based on IIT JEE Mains", "filter_keyword": "Indian Institute of Technology"}
    ]

    for mode in execution_modes:
        is_iit = mode["is_iit"]
        admision_name = mode["admision_name"]
        filter_keyword = mode["filter_keyword"]

        # Filter the target subset of rankings dynamically
        if is_iit:
            rankings = [inst_item for inst_item in master_rankings if filter_keyword in inst_item["Name"]]
            category_grouped_data = {cat: {"": {}} for cat in CATEGORY_MAP}
        else:
            rankings = [inst_item for inst_item in master_rankings if filter_keyword not in inst_item["Name"]]
            category_grouped_data = {cat: {"HOME STATE": {}, "OTHER STATE": {}} for cat in CATEGORY_MAP}

        for inst_item in rankings:
            norm_rank_name = normalize_name(inst_item["Name"])
            tier_suffix = str(inst_item.get("Tier", "N/A")).strip().replace('Tier', '').strip()
            short_name = f"{shorten_institute_name(inst_item['Name'])} ({tier_suffix})"
            
            for item in cutoff_raw:
                cutoffdata_item = item.get("Institute", "")
                if normalize_name(cutoffdata_item) != norm_rank_name:
                    continue
                    
                seat_type = item["Seat Type"]
                if seat_type not in CATEGORY_MAP:
                    continue
                    
                branch_clean = dynamic_clean_branch_name(item["Academic Program Name"])
                if not branch_clean or branch_clean not in branches_list:
                    continue

                quota = item.get("Quota", "")
                gender_offset = 1 if "Female-only" in item["Gender"] else 0

                if is_iit:
                    # Direct assignment for AI Quota fields
                    target_map = category_grouped_data[seat_type][""]
                    if short_name not in target_map:
                        target_map[short_name] = {b: ["-", "-"] for b in branches_list}
                    target_map[short_name][branch_clean][gender_offset] = str(item["Closing Rank"])
                else:
                    # Quota routing conditions targeting two images per seat type
                    if quota == "HS":
                        target_map = category_grouped_data[seat_type]["HOME STATE"]
                        if short_name not in target_map:
                            target_map[short_name] = {b: ["-", "-"] for b in branches_list}
                        target_map[short_name][branch_clean][gender_offset] = str(item["Closing Rank"])
                    elif quota == "OS":
                        target_map = category_grouped_data[seat_type]["OTHER STATE"]
                        if short_name not in target_map:
                            target_map[short_name] = {b: ["-", "-"] for b in branches_list}
                        target_map[short_name][branch_clean][gender_offset] = str(item["Closing Rank"])
           
        # Trigger image generator loop across allocations map
        for category_name in CATEGORY_MAP:
            for quota_name, matrix_sheet_data in category_grouped_data[category_name].items():
                if matrix_sheet_data:
                    generate_category_chart(admision_name, category_name, quota_name, matrix_sheet_data, branches_list)
                else:
                    quota_log = f" [{quota_name}]" if quota_name else ""
                    print(f"Skipping category [{category_name}]{quota_log}: No row data matches context criteria.")

if __name__ == "__main__":
    target_branches = ["CSE", "AIDA", "Electrical", "Mechanical", "Civil", "Chemical"]
    main(target_branches)