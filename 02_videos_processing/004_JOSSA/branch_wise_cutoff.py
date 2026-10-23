import os
import re
import json
from PIL import Image, ImageDraw, ImageFont
from Image2VideoGenerator import Image2VideoGenerator
from pathlib import Path

# =====================================================================
# 1. CONFIGURATION MANIFEST CLASS
# =====================================================================
class ProcessingConfig:
    WHITE = (255, 255, 255)
    GOLD = (212, 175, 55)          # Metallic Gold Accent
    LIGHT_GOLD = (255, 235, 160)    # Highlight Gold Accent
    TEXT_RED = (255, 255, 255)      # Highlight Color for Female Ranks
    MUTED_TEXT = (160, 180, 200)    # Color used for empty data points (-)
    GRID_LINE_COLOR = (50, 70, 100) # Grid lines inside table
 
    def __init__(self, course_name="engineering", target_year=2026, video_per_image=True, video_per_folder=False):
        self.COURSE_NAME = course_name.lower().strip()
        self.YEAR = target_year
        
        # --- VIDEO GENERATION MODE CONTROLS ---
        self.VIDEO_PER_IMAGE = video_per_image
        self.VIDEO_PER_FOLDER = video_per_folder

        # Base asset directories structure
        self.ASSETS_FOLDER = r"C:\Ravi\Python\2025\Media\assets"
        
        # --- PREVIOUS YEAR FALLBACK RESOLUTION LOGIC ---
        resolved_year = target_year
        found_valid_file = False
        
        for attempt in range(6):
            check_year = target_year - attempt
            test_path = os.path.join(
                self.ASSETS_FOLDER, "nirf", "data", 
                f"NIRF_{self.COURSE_NAME}_{check_year}_Ranking.json"
            )
            if os.path.exists(test_path):
                resolved_year = check_year
                self.INSTITUTE_RANKING_PATH = test_path
                found_valid_file = True
                if attempt > 0:
                    print(f"[!] Target year {target_year} missing. Fell back to: {resolved_year}")
                break
        
        if not found_valid_file:
            self.INSTITUTE_RANKING_PATH = os.path.join(
                self.ASSETS_FOLDER, "nirf", "data", 
                f"NIRF_{self.COURSE_NAME}_{target_year}_Ranking.json"
            )

        self.DATA_BASE_DIR = os.path.dirname(self.INSTITUTE_RANKING_PATH)
        self.CUTOFF_DATA_PATH = os.path.join(
                self.ASSETS_FOLDER, "jossa", "data", 
                f"JOSSA_{self.COURSE_NAME}_cutoff_{self.YEAR}.json"
            )
        BASE_DIR = Path(__file__).resolve().parent
        
        # Swapped folder name destination to point to branch_wise_cutoff
        self.OUTPUT_FOLDER = f"{BASE_DIR}/outputs/images/{self.YEAR}_{self.COURSE_NAME}/branch_wise_cutoff"
        self.AUDIO_PATH = os.path.join(self.ASSETS_FOLDER, "jossa", "audios", "rangeela.mp4")

        self.video_engine = Image2VideoGenerator(
            target_width=1080,
            target_height=1920,
            default_duration=59,
            fps=30,
            audio=self.AUDIO_PATH
        )

        self.CATEGORY_MAP = ["OPEN", "EWS", "OBC-NCL", "SC", "ST"]
        
        # Setup specific theme palette for column headers
        self.CATEGORY_COLORS = {
            "OPEN": (255, 140, 0),     # Orange
            "EWS": (34, 139, 34),       # Green
            "OBC-NCL": (218, 165, 32),   # Yellow-Gold
            "SC": (220, 20, 60),        # Red
            "ST": (148, 0, 211)         # Purple
        }

        self.DYNAMIC_BRANCH_RULES = {
            "CSE":         {"keywords": ["computer science"], "color": (255, 140, 0)},
            "AIDA":        {"keywords": ["artificial intelligence", "data science"], "color": (34, 139, 34)},
            "Electrical":  {"keywords": ["electrical"], "color": (218, 165, 32)},
            "Mechanical":  {"keywords": ["mechanical"], "color": (220, 20, 60)},
            "Civil":       {"keywords": ["civil"], "color": (148, 0, 211)},
            "Electronics": {"keywords": ["electronics"], "color": (255, 140, 0)},
            "Chemical":    {"keywords": ["chemical"], "color": (0, 139, 139)}
        }


# =====================================================================
# 2. PROGRAM MAP CHART GENERATOR CLASS
# =====================================================================
class ProgramChartGenerator:
    def __init__(self, config: ProcessingConfig):
        self.cfg = config

    def draw_linear_gradient(self, image, top_color, bottom_color):
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for y in range(height):
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / height))
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / height))
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    def draw_gold_gradient_box(self, draw, box, radius=15):
        x0, y0, x1, y1 = box
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(23, 35, 55), outline=self.cfg.GOLD, width=2)

    def generate(self, admission_name, branch_name, quota_name, matrix_data, is_iit):
        # Scale chart gracefully depending on categories width
        WIDTH = max(1650, 360 + (len(self.cfg.CATEGORY_MAP) * 220) + 60)
        table_top = 320   # Increased spacing to give larger headers breathing room
        row_height = 72  
        
        total_table_height = (len(matrix_data) + 2) * row_height
        HEIGHT = table_top + total_table_height + 140
        
        base_image = Image.new("RGB", (WIDTH, HEIGHT))
        self.draw_linear_gradient(base_image, (20, 36, 61), (10, 18, 32))
        draw = ImageDraw.Draw(base_image)

        try:
            font_title = ImageFont.truetype("arialbd.ttf", 52)      
            font_sub = ImageFont.truetype("arialbd.ttf", 42)         
            font_data_bold = ImageFont.truetype("arialbd.ttf", 35)   
            font_data_reg = ImageFont.truetype("arial.ttf", 40)      
        except IOError:
            font_title = font_sub = font_data_bold = font_data_reg = ImageFont.load_default()

        draw.rectangle([15, 15, WIDTH-15, HEIGHT-15], outline=self.cfg.GOLD, width=3)

        # Dynamic Titles optimized for Academic Branch Context
        title_line1 = admission_name.upper()
        title_line2 = f"{branch_name} ({quota_name}) BRANCH CUTOFF ({self.cfg.YEAR})" if quota_name else f"{branch_name} BRANCH CUTOFF ({self.cfg.YEAR})"
        subtitle_str = "ROUND 1 CLOSING RANKS ANALYSIS"
            
        y_line1, y_line2, y_sub = 75, 150, 225
        
        # --- FIXED HEADER GRAPHICS BLOCK ---
        for offset_x, offset_y in [(3, 3), (-1, 1)]:
            draw.text((WIDTH // 2 + offset_x, y_line1 + offset_y), title_line1, fill=(0, 0, 0), font=font_sub, anchor="mm")
            draw.text((WIDTH // 2 + offset_x, y_line2 + offset_y), title_line2, fill=(0, 0, 0), font=font_title, anchor="mm")
            draw.text((WIDTH // 2 + offset_x, y_sub + offset_y), subtitle_str, fill=(0, 0, 0), font=font_sub, anchor="mm")
            
        draw.text((WIDTH // 2, y_line1), title_line1, fill=self.cfg.LIGHT_GOLD, font=font_sub, anchor="mm")
        draw.text((WIDTH // 2, y_line2), title_line2, fill=self.cfg.WHITE, font=font_title, anchor="mm")
        draw.text((WIDTH // 2, y_sub), subtitle_str, fill=self.cfg.GOLD, font=font_sub, anchor="mm")

        col_inst_w = 360  
        table_inner_w = WIDTH - 60
        col_cat_w = (table_inner_w - col_inst_w) // len(self.cfg.CATEGORY_MAP)
        sub_col_w = col_cat_w // 2

        # Draw Table headers dynamically
        draw.rounded_rectangle([30, table_top, WIDTH-30, table_top + total_table_height], radius=12, outline=self.cfg.GOLD, width=3)
        draw.rectangle([32, table_top + 2, 30 + col_inst_w, table_top + (2 * row_height) - 1], fill=(16, 28, 48))
        draw.text((30 + col_inst_w // 2, table_top + row_height), "INSTITUTE (Tier)", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

        for i, cat_name in enumerate(self.cfg.CATEGORY_MAP):
            x_start = 30 + col_inst_w + (i * col_cat_w)
            assigned_color = self.cfg.CATEGORY_COLORS.get(cat_name, (40, 50, 70))
            
            draw.rectangle([x_start, table_top + 2, x_start + col_cat_w - 1, table_top + row_height], fill=assigned_color)
            draw.text((x_start + col_cat_w // 2, table_top + row_height // 2), cat_name, fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

            dark_tint_m = tuple(int(c * 0.6) for c in assigned_color)
            dark_tint_f = tuple(int(c * 0.45) for c in assigned_color)

            draw.rectangle([x_start, table_top + row_height, x_start + sub_col_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_m)
            draw.text((x_start + sub_col_w // 2, table_top + row_height + row_height // 2), "M", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")
            
            draw.rectangle([x_start + sub_col_w, table_top + row_height, x_start + col_cat_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_f)
            draw.text((x_start + sub_col_w + sub_col_w // 2, table_top + row_height + row_height // 2), "F", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

        draw.line([(30 + col_inst_w, table_top), (30 + col_inst_w, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=2)
        for i in range(1, len(self.cfg.CATEGORY_MAP)):
            x_sep = 30 + col_inst_w + (i * col_cat_w)
            draw.line([(x_sep, table_top), (x_sep, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=2)
            draw.line([(x_sep - sub_col_w, table_top + row_height), (x_sep - sub_col_w, table_top + (2 * row_height))], fill=self.cfg.GRID_LINE_COLOR, width=1)
        draw.line([(WIDTH - 30 - sub_col_w, table_top + row_height), (WIDTH - 30 - sub_col_w, table_top + (2 * row_height))], fill=self.cfg.GRID_LINE_COLOR, width=1)
        draw.line([(30 + col_inst_w, table_top + row_height), (WIDTH - 30, table_top + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=2)
        draw.line([(30, table_top + (2 * row_height)), (WIDTH - 30, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=3)

        # Draw matrix body rows
        current_y = table_top + (2 * row_height)
        for idx, (inst_name, categories) in enumerate(matrix_data.items()):
            row_bg = (24, 38, 61) if idx % 2 == 0 else (14, 22, 38)
            draw.rectangle([32, current_y + 1, 30 + col_inst_w, current_y + row_height - 1], fill=row_bg)
            draw.line([(30, current_y + row_height), (WIDTH - 30, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=1)
            draw.text((45, current_y + row_height // 2), inst_name, fill=(255, 245, 210), font=font_data_bold, anchor="lm")
            draw.line([(30 + col_inst_w, current_y), (30 + col_inst_w, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=2)

            for c_idx, cat_name in enumerate(self.cfg.CATEGORY_MAP):
                ranks = categories.get(cat_name, ["-", "-"])
                x_cat_start = 30 + col_inst_w + (c_idx * col_cat_w)
                assigned_color = self.cfg.CATEGORY_COLORS.get(cat_name, (0, 0, 0))
                
                draw.rectangle([x_cat_start + 1, current_y + 1, x_cat_start + col_cat_w - 1, current_y + row_height - 1], fill=self.cfg.WHITE)
                
                m_rank = str(ranks[0])
                m_color = assigned_color if m_rank != "-" else (130, 140, 155)
                draw.text((x_cat_start + sub_col_w // 2, current_y + row_height // 2), m_rank, fill=m_color, font=font_data_reg if m_rank != "-" else font_data_bold, anchor="mm")
                
                f_rank = str(ranks[1])
                deep_f_color = tuple(int(c * 0.75) for c in assigned_color)
                f_color = deep_f_color if f_rank != "-" else (130, 140, 155)
                draw.text((x_cat_start + sub_col_w + sub_col_w // 2, current_y + row_height // 2), f_rank, fill=f_color, font=font_data_bold, anchor="mm")

                if c_idx < len(self.cfg.CATEGORY_MAP) - 1:
                    draw.line([(x_cat_start + col_cat_w, current_y), (x_cat_start + col_cat_w, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=2)
                draw.line([(x_cat_start + sub_col_w, current_y), (x_cat_start + sub_col_w, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=1)

            current_y += row_height

        footer_y = HEIGHT - 85
        self.draw_gold_gradient_box(draw, [30, footer_y, WIDTH - 30, footer_y + 55], radius=10)
        draw.text((WIDTH // 2, footer_y + 27), f"DATA SOURCE: JoSAA {self.cfg.YEAR} CLOSING RANKS (ROUND 1)", fill=self.cfg.LIGHT_GOLD, font=font_data_bold, anchor="mm")

        subfolder = "iit" if is_iit else "nit"
        output_folder_path = os.path.join(self.cfg.OUTPUT_FOLDER, subfolder)
        os.makedirs(output_folder_path, exist_ok=True)
        
        clean_admission_name = admission_name.replace(" ", "_")
        clean_branch_filename = branch_name.replace("-", "_")
        quota_suffix = f"_{quota_name.replace(' ', '_')}" if quota_name else ""
        output_path = os.path.join(output_folder_path, f"{clean_admission_name}_{clean_branch_filename}{quota_suffix}_{self.cfg.YEAR}_#JoSAA_chart_branches.png")
        
        base_image.save(output_path)
        print(f"Generated Sheet successfully at: {output_path}")
        
        # Return path out so the pipeline handles video routing rules dynamically
        return output_path


# =====================================================================
# 3. PIPELINE MAIN CONTROLLER CLASS
# =====================================================================
class JosaaPipelineManager:
    def __init__(self, config: ProcessingConfig):
        self.cfg = config
        self.chart_generator = ProgramChartGenerator(self.cfg)
        self.video_engine = config.video_engine

    def normalize_name(self, name):
        if not name: return ""
        return re.sub(r'\s+', ' ', name.lower().strip())

    def clean_branch_name(self, raw_program_name):
        if not raw_program_name: return None
        normalized_program = raw_program_name.lower()
        for clean_acronym, rules in self.cfg.DYNAMIC_BRANCH_RULES.items():
            for keyword in rules["keywords"]:
                if keyword in normalized_program:
                    return clean_acronym
        return None

    def shorten_institute_name(self, name):
        name = name.replace("Indian Institute of Technology", "IIT").replace("National Institute of Technology", "NIT")
        name = name.replace("Institute of Engineering and Technology","IET").replace("Indian Institute of Engineering Science and Technology","IIEST")
        if "Banaras Hindu University" in name or "BHU" in name: return "IIT (BHU) Varanasi"
        if "Indian School of Mines" in name or "ISM" in name: return "IIT (ISM) Dhanbad"
        if "(" in name: name = name.split("(")[0].strip()
        return name[:24]

    def execute(self, branches_list):
        if not os.path.exists(self.cfg.INSTITUTE_RANKING_PATH) or not os.path.exists(self.cfg.CUTOFF_DATA_PATH):
            print("CRITICAL ERROR: Source JSON databases missing.")
            return

        with open(self.cfg.INSTITUTE_RANKING_PATH, 'r', encoding='utf-8') as f:
            master_rankings = json.load(f)
        with open(self.cfg.CUTOFF_DATA_PATH, 'r', encoding='utf-8') as f:
            cutoff_raw = json.load(f)

        execution_modes = [
            {"is_iit": True,  "admission_name": "IITs Admission based on IIT JEE Advanced", "filter_keyword": "Indian Institute of Technology"},
            {"is_iit": False, "admission_name": "NITs Admission based on IIT JEE Mains",    "filter_keyword": "Indian Institute of Technology"}
        ]

        for mode in execution_modes:
            is_iit = mode["is_iit"]
            admission_name = mode["admission_name"]
            filter_keyword = mode["filter_keyword"]

            # Store generated paths per mode execution context (iit vs nit folders)
            folder_image_paths = []

            if is_iit:
                rankings = [inst for inst in master_rankings if filter_keyword in inst["Name"]]
                branch_grouped_data = {b: {"": {}} for b in branches_list}
            else:
                rankings = [inst for inst in master_rankings if filter_keyword not in inst["Name"]]
                branch_grouped_data = {b: {"HOME STATE": {}, "OTHER STATE": {}} for b in branches_list}

            for inst_item in rankings:
                norm_rank_name = self.normalize_name(inst_item["Name"])
                tier_suffix = str(inst_item.get("Tier", "N/A")).strip().replace('Tier', '').strip()
                short_name = f"{self.shorten_institute_name(inst_item['Name'])} ({tier_suffix})"
                
                for item in cutoff_raw:
                    if self.normalize_name(item.get("Institute", "")) != norm_rank_name: continue
                    seat_type = item["Seat Type"]
                    if seat_type not in self.cfg.CATEGORY_MAP: continue
                        
                    branch_clean = self.clean_branch_name(item["Academic Program Name"])
                    if not branch_clean or branch_clean not in branches_list: continue

                    quota = item.get("Quota", "")
                    gender_offset = 1 if "Female-only" in item["Gender"] else 0

                    if is_iit:
                        target_map = branch_grouped_data[branch_clean][""]
                        if short_name not in target_map: target_map[short_name] = {c: ["-", "-"] for c in self.cfg.CATEGORY_MAP}
                        target_map[short_name][seat_type][gender_offset] = str(item["Closing Rank"])
                    else:
                        if quota in ["HS", "OS"]:
                            quota_key = "HOME STATE" if quota == "HS" else "OTHER STATE"
                            target_map = branch_grouped_data[branch_clean][quota_key]
                            if short_name not in target_map: target_map[short_name] = {c: ["-", "-"] for c in self.cfg.CATEGORY_MAP}
                            target_map[short_name][seat_type][gender_offset] = str(item["Closing Rank"])
               
            # Generate charts routing via branch names loop
            for b_name in branches_list:
                for quota_name, matrix_sheet_data in branch_grouped_data[b_name].items():
                    if matrix_sheet_data:
                        img_path = self.chart_generator.generate(admission_name, b_name, quota_name, matrix_sheet_data, is_iit)
                        folder_image_paths.append(img_path)
                        
                        # Rule 1: Video per Single Image Context
                        if self.cfg.VIDEO_PER_IMAGE:
                            output_video = img_path.replace('images', 'videos').replace('.png', '.mp4')
                            os.makedirs(os.path.dirname(output_video), exist_ok=True)
                            self.video_engine.generate_video(img_path, output_video)
                    else:
                        quota_log = f" [{quota_name}]" if quota_name else ""
                        print(f"Skipping branch [{b_name}]{quota_log}: No row data context match.")

            # Rule 2: Combined Video per Category Folder Context
            hashtags = ' '.join([f'#{item}' for item in target_branches])
            if self.cfg.VIDEO_PER_FOLDER and folder_image_paths:
                subfolder = "iit" if is_iit else "nit"
                hashtags = f'{hashtags} #{subfolder}'
                folder_video_output = os.path.join(
                    self.cfg.OUTPUT_FOLDER.replace('images', 'videos'),
                    subfolder, 
                    f"Popular Branches  {subfolder.upper()}_Admission_Cutoff_{self.cfg.YEAR} #nirf #jossa #{hashtags}.mp4"
                )
                os.makedirs(os.path.dirname(folder_video_output), exist_ok=True)
                print(f"[!] Compilation Mode: Generating video combining {len(folder_image_paths)} images...")
                
                # Assuming your standard generate_video engine signature can map structural image lists
                self.video_engine.generate_video(folder_image_paths, folder_video_output)


# =====================================================================
# 4. RUNTIME SYSTEM EXECUTION BLOCK
# =====================================================================
if __name__ == "__main__":
    target_branches = ["CSE", "AIDA", "Electrical", "Mechanical", "Civil", "Chemical"]
    
    # Configure processing controls explicitly here
    config_blueprint = ProcessingConfig(
        course_name="engineering", 
        target_year=2026, 
        video_per_image=False,   # Set to True to output a standalone video clip per image chart
        video_per_folder=True   # Set to True to bundle all processed outputs inside subfolders into 1 master sequence
    )
    
    pipeline = JosaaPipelineManager(config=config_blueprint)
    pipeline.execute(target_branches)