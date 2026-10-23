import os
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
from Image2VideoGenerator import Image2VideoGenerator

# =====================================================================
# 1. CONFIGURATION MANIFEST CLASS
# =====================================================================
class ProcessingConfig:
    WHITE = (255, 255, 255)
    GOLD = (212, 175, 55)          
    LIGHT_GOLD = (255, 235, 160)    
    TEXT_RED = (255, 255, 255)      
    MUTED_TEXT = (160, 180, 200)    
    GRID_LINE_COLOR = (50, 70, 100) 
 
    def __init__(self, course_name="engineering", target_year=2026, video_per_image=False, video_per_folder=True):
        self.COURSE_NAME = course_name.lower().strip()
        self.YEAR = target_year
        
        # New Feature Flags Control
        self.VIDEO_PER_IMAGE = video_per_image
        self.VIDEO_PER_FOLDER = video_per_folder
        
        self.ASSETS_FOLDER = os.getenv("MEDIA_ASSETS_PATH", r"C:\Ravi\Python\2025\Media\assets")
        
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
        
        self.OUTPUT_BASE_FOLDER = f"{BASE_DIR}/outputs"
        self.OUTPUT_FOLDER = f"{self.OUTPUT_BASE_FOLDER}/images/{self.YEAR}_{self.COURSE_NAME}/institute_wise_cutoff"
        self.AUDIO_PATH = os.path.join(self.ASSETS_FOLDER, "jossa", "audios", "rangeela.mp4")

        self.video_engine = Image2VideoGenerator(
            target_width=1080,
            target_height=1920,
            default_duration=59,
            fps=30,
            audio=self.AUDIO_PATH
        )

        self.CATEGORY_MAP = ["OPEN", "EWS", "OBC-NCL", "SC", "ST"]
        
        self.CATEGORY_COLORS = {
            "OPEN": (255, 140, 0),     
            "EWS": (34, 139, 34),       
            "OBC-NCL": (218, 165, 32),   
            "SC": (220, 20, 60),        
            "ST": (148, 0, 211)         
        }

        self.PROGRAM_ACRONYMS = {
            r"computer science": "CSE",
            r"artificial intelligence": "AIDA",
            r"data science": "AIDA",
            r"electrical": "EE",
            r"electronics": "ECE",
            r"mechanical": "ME",
            r"civil": "Civil",
            r"chemical": "Chemical",
            r"metallurgical": "Meta",
            r"aerospace": "Aero",
            r"engineering physics": "EP"
        }


# =====================================================================
# 2. INSTITUTE PROGRAM CHART GENERATOR CLASS
# =====================================================================
class InstituteWiseProgramChartGenerator:
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

    def generate(self, admission_name, institute_display_name,location, rank, tier_val, quota_name, matrix_data, mode_type, raw_inst_name):
        WIDTH = 1920
        header_height = 420  
        table_top = header_height + 40   
        row_height = 85  
        rank_str = f"{rank:03d}"
        total_table_height = (len(matrix_data) + 2) * row_height
        HEIGHT = table_top + total_table_height + 140
        
        base_image = Image.new("RGB", (WIDTH, HEIGHT))
        self.draw_linear_gradient(base_image, (20, 36, 61), (10, 18, 32))
        draw = ImageDraw.Draw(base_image)

        try:
            font_inst = ImageFont.truetype("arialbd.ttf", 46)
            font_loc = ImageFont.truetype("arialbd.ttf", 36)
            font_cutoff = ImageFont.truetype("arialbd.ttf", 40)
            font_badge = ImageFont.truetype("arialbd.ttf", 44)
            font_data_bold = ImageFont.truetype("arialbd.ttf", 36)   
        except IOError:
            font_inst = font_loc = font_cutoff = font_badge = font_data_bold = ImageFont.load_default()

        # Main Graphic Outer Frame Border
        draw.rectangle([15, 15, WIDTH-15, HEIGHT-15], outline=self.cfg.GOLD, width=3)

        # 1. Outer Header Container Box
        header_box = [30, 30, WIDTH - 30, header_height]
        draw.rounded_rectangle(header_box, radius=8, outline=self.cfg.GOLD, width=2, fill=(13, 27, 47))

        # Parse locations out gracefully
        inst_main = institute_display_name
        inst_loc = location
        if " - " in institute_display_name:
            parts = institute_display_name.split(" - ")
            inst_main = parts[0]
            inst_loc = parts[1]
        elif "(" in institute_display_name:
            inst_main = institute_display_name.split(" (")[0]
            
        # Draw Text Headings
        draw.text((WIDTH // 2, 75), inst_main.upper(), fill=self.cfg.WHITE, font=font_inst, anchor="mm")
        draw.text((WIDTH // 2, 135), inst_loc.upper(), fill=self.cfg.GOLD, font=font_loc, anchor="mm")

        cutoff_label = f"ROUND 1 CUTOFF {self.cfg.YEAR} (JEE ADVANCED)" if "iit" in mode_type.lower() else f"ROUND 1 CUTOFF {self.cfg.YEAR} (JEE MAIN)"
        if quota_name:
            cutoff_label += f" - {quota_name.upper()}"
        draw.text((WIDTH // 2, 210), cutoff_label, fill=self.cfg.WHITE, font=font_cutoff, anchor="mm")

        # Inner Badge Box Layout
        badge_y0, badge_y1 = 265, 375
        badge_w = 900
        badge_x0 = (WIDTH - badge_w) // 2
        badge_x1 = badge_x0 + badge_w
        draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1], radius=20, fill=(38, 54, 78), outline=self.cfg.GOLD, width=1)
        
        badge_str = f"NIRF Rank #{rank}  |  Tier {tier_val}"
        draw.text((WIDTH // 2, (badge_y0 + badge_y1) // 2), badge_str, fill=self.cfg.WHITE, font=font_badge, anchor="mm")

        # -----------------------------------------------------------------
        # LOGO & CAMPUS IMAGE INJECTION LOGIC
        # -----------------------------------------------------------------
        circle_size = (240, 240)
        clean_file_name = re.sub(r'[^a-zA-Z0-9]', '_', inst_main.replace("IIT", "").replace("NIT", "").strip())
        clean_file_name = re.sub(r'_+', '_', clean_file_name).strip('_')
        
        if "madras" in inst_main.lower():
            asset_filename = f"{rank_str}_IIT_Madras.png"
        else:
            prefix = "IIT" if "iit" in mode_type.lower() else "NIT" if "nit" in mode_type.lower() else "IIIT"
            asset_filename = f"{rank_str}_{prefix}_{clean_file_name}.png"

        logo_path = os.path.join(self.cfg.ASSETS_FOLDER, "nirf", "images", self.cfg.COURSE_NAME, "logos", asset_filename)
        campus_path = os.path.join(self.cfg.ASSETS_FOLDER, "nirf", "images", self.cfg.COURSE_NAME, "campus", asset_filename)

        def paste_circular_image(img_path, center_x, center_y):
            if os.path.exists(img_path):
                try:
                    img_asset = Image.open(img_path).convert("RGBA")
                    img_asset = ImageOps.fit(img_asset, circle_size, Image.Resampling.LANCZOS)
                    
                    mask = Image.new("L", circle_size, 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse([0, 0, circle_size[0], circle_size[1]], fill=255)
                    
                    box_x = center_x - (circle_size[0] // 2)
                    box_y = center_y - (circle_size[1] // 2)
                    
                    base_image.paste(img_asset, (box_x, box_y), mask)
                    draw.ellipse([box_x, box_y, box_x + circle_size[0], box_y + circle_size[1]], outline=self.cfg.GOLD, width=3)
                except Exception as e:
                    print(f"Failed handling asset image processing: {img_path}. Exception: {e}")

        paste_circular_image(logo_path, center_x=175, center_y=header_height // 2 + 20)
        paste_circular_image(campus_path, center_x=WIDTH - 175, center_y=header_height // 2 + 20)

        # Table Layout Logic
        col_program_w = 520  
        table_inner_w = WIDTH - 60
        col_cat_w = (table_inner_w - col_program_w) // len(self.cfg.CATEGORY_MAP)
        sub_col_w = col_cat_w // 2

        draw.rounded_rectangle([30, table_top, WIDTH-30, table_top + total_table_height], radius=12, outline=self.cfg.GOLD, width=3)
        draw.rectangle([32, table_top + 2, 30 + col_program_w, table_top + (2 * row_height) - 1], fill=(16, 28, 48))
        draw.text((30 + col_program_w // 2, table_top + row_height), "BRANCH CODE", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

        for i, cat_name in enumerate(self.cfg.CATEGORY_MAP):
            x_start = 30 + col_program_w + (i * col_cat_w)
            assigned_color = self.cfg.CATEGORY_COLORS.get(cat_name, (40, 50, 70))
            
            draw.rectangle([x_start, table_top + 2, x_start + col_cat_w - 1, table_top + row_height], fill=assigned_color)
            draw.text((x_start + col_cat_w // 2, table_top + row_height // 2), cat_name, fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

            dark_tint_m = tuple(int(c * 0.6) for c in assigned_color)
            dark_tint_f = tuple(int(c * 0.45) for c in assigned_color)

            draw.rectangle([x_start, table_top + row_height, x_start + sub_col_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_m)
            draw.text((x_start + sub_col_w // 2, table_top + row_height + row_height // 2), "M", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")
            
            draw.rectangle([x_start + sub_col_w, table_top + row_height, x_start + col_cat_w - 1, table_top + (2 * row_height) - 1], fill=dark_tint_f)
            draw.text((x_start + sub_col_w + sub_col_w // 2, table_top + row_height + row_height // 2), "F", fill=self.cfg.WHITE, font=font_data_bold, anchor="mm")

        draw.line([(30 + col_program_w, table_top), (30 + col_program_w, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=2)
        for i in range(1, len(self.cfg.CATEGORY_MAP)):
            x_sep = 30 + col_program_w + (i * col_cat_w)
            draw.line([(x_sep, table_top), (x_sep, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=2)
            draw.line([(x_sep - sub_col_w, table_top + row_height), (x_sep - sub_col_w, table_top + (2 * row_height))], fill=self.cfg.GRID_LINE_COLOR, width=1)
        draw.line([(WIDTH - 30 - sub_col_w, table_top + row_height), (WIDTH - 30 - sub_col_w, table_top + (2 * row_height))], fill=self.cfg.GRID_LINE_COLOR, width=1)
        draw.line([(30 + col_program_w, table_top + row_height), (WIDTH - 30, table_top + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=2)
        draw.line([(30, table_top + (2 * row_height)), (WIDTH - 30, table_top + (2 * row_height))], fill=self.cfg.GOLD, width=3)

        current_y = table_top + (2 * row_height)
        for idx, (program_name, categories) in enumerate(matrix_data.items()):
            row_bg = (24, 38, 61) if idx % 2 == 0 else (14, 22, 38)
            draw.line([(30, current_y + row_height), (WIDTH - 30, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=1)
            
            x_pad = 3
            draw.rounded_rectangle(
                [30 + x_pad, current_y + 3, 30 + col_program_w - x_pad, current_y + row_height - 3], 
                radius=6, 
                fill=row_bg,
                outline=self.cfg.GOLD if idx % 2 == 0 else None,
                width=1
            )
            
            draw.text((45, current_y + row_height // 2), program_name, fill=(255, 245, 210), font=font_data_bold, anchor="lm")
            draw.line([(30 + col_program_w, current_y), (30 + col_program_w, current_y + row_height)], fill=self.cfg.GRID_LINE_COLOR, width=2)

            for c_idx, cat_name in enumerate(self.cfg.CATEGORY_MAP):
                ranks = categories.get(cat_name, ["-", "-"])
                x_cat_start = 30 + col_program_w + (c_idx * col_cat_w)
                assigned_color = self.cfg.CATEGORY_COLORS.get(cat_name, (0, 0, 0))
                
                draw.rectangle([x_cat_start + 1, current_y + 1, x_cat_start + col_cat_w - 1, current_y + row_height - 1], fill=self.cfg.WHITE)
                
                m_rank = str(ranks[0])
                m_color = assigned_color if m_rank != "-" else (130, 140, 155)
                draw.text((x_cat_start + sub_col_w // 2, current_y + row_height // 2), m_rank, fill=m_color, font=font_data_bold, anchor="mm")
                
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

        output_folder_path = os.path.join(self.cfg.OUTPUT_FOLDER, mode_type)
        os.makedirs(output_folder_path, exist_ok=True)
        
        clean_inst = re.sub(r'[^a-zA-Z0-9]', '_', institute_display_name.split(" (")[0])
        quota_suffix = f"_{quota_name.replace(' ', '_')}" if quota_name else ""
        output_path = os.path.join(output_folder_path, f"{rank_str}_{clean_inst}{quota_suffix}_{self.cfg.YEAR}.png")
        
        base_image.save(output_path)
        print(f"Generated Sheet successfully at: {output_path}")
        
        # FIX: Dynamic routing logic based on execution flags
        if self.cfg.VIDEO_PER_IMAGE:
            output_video_dir = os.path.join(self.cfg.OUTPUT_BASE_FOLDER, "videos", "institute_wise", mode_type)
            os.makedirs(output_video_dir, exist_ok=True)
            output_video = os.path.join(output_video_dir, f"{rank_str}_{clean_inst}{quota_suffix}_{self.cfg.YEAR}.mp4")
            self.cfg.video_engine.generate_video(output_path, output_video)
            
        return output_path


# =====================================================================
# 3. PIPELINE MAIN CONTROLLER CLASS (UPDATED)
# =====================================================================
class JossaPipelineManager:
    def __init__(self, config: ProcessingConfig):
        self.cfg = config
        self.chart_generator = InstituteWiseProgramChartGenerator(self.cfg)

    def normalize_name(self, name):
        if not name: return ""
        cleaned = name.replace(",", " ")
        return re.sub(r'\s+', ' ', cleaned.lower().strip())

    def clean_branch_name(self, raw_program_name):
        if not raw_program_name: return "Unknown"
        normalized = raw_program_name.lower()
        
        for pattern, acronym in self.cfg.PROGRAM_ACRONYMS.items():
            if re.search(pattern, normalized):
                suffix = " (5Y)" if "5 years" in normalized or "dual degree" in normalized else ""
                return f"{acronym}{suffix}"
                
        return raw_program_name.split("(")[0].strip()[:25]

    def shorten_institute_name(self, name):
        name = name.replace(",", " ")
        name = name.replace("Indian Institute of Technology", "IIT")
        name = name.replace("National Institute of Technology", "NIT")
        name = name.replace("Indian Institute of Information Technology", "IIIT")
        name = name.replace("International Institute of Information Technology", "IIIT")
        name = name.replace("Institute of Engineering and Technology","IET")
        name = name.replace("Indian Institute of Engineering Science and Technology","IIEST")
        
        if "Banaras Hindu University" in name or "BHU" in name: return "IIT (BHU) Varanasi"
        if "Indian School of Mines" in name or "ISM" in name: return "IIT (ISM) Dhanbad"
        if "Jawaharlal Nehru Technological University" in name or "JNTU" in name: return "JNTU"
        
        if "(" in name: name = name.split("(")[0].strip()
        return re.sub(r'\s+', ' ', name).strip()

    def _get_sorting_rank(self, branch_data_item):
        ranks = []
        for cat, gender_list in branch_data_item.items():
            for rank_val in gender_list:
                if rank_val != "-":
                    try:
                        ranks.append(int(rank_val))
                    except ValueError:
                        continue
        return min(ranks) if ranks else float('inf')

    def execute(self):
        if not os.path.exists(self.cfg.INSTITUTE_RANKING_PATH) or not os.path.exists(self.cfg.CUTOFF_DATA_PATH):
            print("CRITICAL ERROR: Source JSON databases missing.")
            return

        with open(self.cfg.INSTITUTE_RANKING_PATH, 'r', encoding='utf-8') as f:
            master_rankings = json.load(f)
        with open(self.cfg.CUTOFF_DATA_PATH, 'r', encoding='utf-8') as f:
            cutoff_raw = json.load(f)

        cutoff_institutes_set = {
            self.normalize_name(item.get("Institute", "")) 
            for item in cutoff_raw if item.get("Institute")
        }

        execution_modes = [
            {
                "is_iit": True, "is_nit": False, "is_iiit": False, "is_university": False, "mode_type": "iit",
                "admission_name": "IITs Admission based on IIT JEE Advanced"
            },
            {
                "is_iit": False, "is_nit": True, "is_iiit": False, "is_university": False, "mode_type": "nit",
                "admission_name": "NITs Admission based on IIT JEE Mains"
            },
            {
                "is_iit": False, "is_nit": False, "is_iiit": True, "is_university": False, "mode_type": "iiit",
                "admission_name": "IIITs Admission based on IIT JEE Mains"
            },
            {
                "is_iit": False, "is_nit": False, "is_iiit": False, "is_university": True, "mode_type": "university",
                "admission_name": "Universities/GFTIs Admission based on IIT JEE Mains"
            }
        ]

        for mode in execution_modes:
            mode_type = mode["mode_type"]
            admission_name = mode["admission_name"]
            
            # Container tracking images generated for folder-scoped compilation
            tier_image_frames = []

            if mode["is_iit"]:
                rankings = [inst for inst in master_rankings if re.search(r'\b(IIT|Indian Institute of Technology)\b', inst["Name"], re.IGNORECASE)]
            elif mode["is_iiit"]:
                rankings = [inst for inst in master_rankings if re.search(r'\b(IIIT|Indian Institute of Information Technology|International Institute of Information Technology)\b', inst["Name"], re.IGNORECASE)]
            elif mode["is_nit"]:
                rankings = [inst for inst in master_rankings if re.search(r'\b(NIT|National Institute of Technology|IIEST)\b', inst["Name"], re.IGNORECASE)]
            elif mode["is_university"]:
                rankings = [
                    inst for inst in master_rankings 
                    if not re.search(r'\b(IIT|Indian Institute of Technology|NIT|National Institute of Technology|IIIT|Indian Institute of Information Technology|International Institute of Information Technology)\b', inst["Name"], re.IGNORECASE)
                ]

            for inst_item in rankings:
                norm_rank_name = self.normalize_name(inst_item["Name"])
                if norm_rank_name not in cutoff_institutes_set:
                    continue

                tier_suffix = str(inst_item.get("Tier", "N/A")).strip().replace('Tier', '').strip()
                short_inst = f"{self.shorten_institute_name(inst_item['Name'])} (Tier {tier_suffix})"
                short_inst=f'{short_inst}'
                location=f'{inst_item["City"]}, {inst_item["State"]}'
                if mode["is_iit"]:
                    institute_matrix = {"": {}}
                else:
                    institute_matrix = {"HOME STATE": {}, "OTHER STATE": {}}

                for item in cutoff_raw:
                    normal_name = self.normalize_name(item.get("Institute", ""))
                    if normal_name != norm_rank_name: continue
                    seat_type = item["Seat Type"]
                    if seat_type not in self.cfg.CATEGORY_MAP: continue
                        
                    program_clean = self.clean_branch_name(item["Academic Program Name"])
                    quota = item.get("Quota", "")
                    gender_offset = 1 if "Female-only" in item["Gender"] else 0

                    if mode["is_iit"]:
                        target_map = institute_matrix[""]
                        if program_clean not in target_map: 
                            target_map[program_clean] = {c: ["-", "-"] for c in self.cfg.CATEGORY_MAP}
                        target_map[program_clean][seat_type][gender_offset] = str(item["Closing Rank"])
                    else:
                        if quota in ["HS", "OS", "AI"]: 
                            quota_key = "HOME STATE" if quota == "HS" else "OTHER STATE"
                            target_map = institute_matrix[quota_key]
                            if program_clean not in target_map: 
                                target_map[program_clean] = {c: ["-", "-"] for c in self.cfg.CATEGORY_MAP}
                            target_map[program_clean][seat_type][gender_offset] = str(item["Closing Rank"])

                for quota_name, matrix_sheet_data in institute_matrix.items():
                    if matrix_sheet_data:
                        sorted_matrix_data = dict(
                            sorted(matrix_sheet_data.items(), key=lambda x: (self._get_sorting_rank(x[1]), x[0]))
                        )
                        rank = int(inst_item["Rank"])
                        tier_value = int(inst_item["Tier"].replace('Tier',''))
                        saved_img_path = self.chart_generator.generate(
                            admission_name, short_inst,location, rank, tier_value, quota_name, 
                            sorted_matrix_data, mode_type, inst_item["Name"]
                        )
                        tier_image_frames.append(saved_img_path)

            # DYNAMIC NAMING LOGIC FOR COMPILATION VIDEOS
            if self.cfg.VIDEO_PER_FOLDER and tier_image_frames:
                folder_video_output_dir = os.path.join(self.cfg.OUTPUT_BASE_FOLDER, "videos", "institute_type_wise")
                os.makedirs(folder_video_output_dir, exist_ok=True)
                
                # Determine dynamic naming aspects
                if mode["is_iit"]:
                    prefix, exam = "IIT", "JEE Advanced"
                elif mode["is_nit"]:
                    prefix, exam = "NIT", "JEE Main"
                elif mode["is_iiit"]:
                    prefix, exam = "IIIT", "JEE Main"
                else:
                    prefix, exam = "University", "JEE Main"

                # Generate clean destination path
                video_filename = f"{prefix} Admission Cutoff in {self.cfg.YEAR} based on IIT {exam} #jossa #nirf #{mode_type}.mp4"
                folder_video_path = os.path.join(folder_video_output_dir, video_filename)
                
                print(f"Compiling tier image directory [{mode_type}] into total sequence video...")
                self.cfg.video_engine.generate_video(tier_image_frames, folder_video_path)

# =====================================================================
# 4. RUNTIME SYSTEM EXECUTION BLOCK
# =====================================================================
if __name__ == "__main__":
    config_blueprint = ProcessingConfig(
        course_name="engineering", 
        target_year=2026,
        video_per_image=False,  # If True, saves to 'outputs/videos/institute_wise/'
        video_per_folder=True   # If True, saves to 'outputs/videos/institute_type_wise/'
    )
    
    pipeline = JossaPipelineManager(config=config_blueprint)
    pipeline.execute()