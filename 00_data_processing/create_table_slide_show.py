import os
import json
import cv2
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import math
import re

# ------------------- CONFIG -------------------
INPUT_FOLDER = "data_processing/data/SeatAllotmentResult2025"
SLIDES_FOLDER = "data_processing/outputs/slides_videos"
BACKGROUND_IMAGE = "data_processing/assets/background.jpg"

os.makedirs(SLIDES_FOLDER, exist_ok=True)

MAX_ROWS_PER_SLIDE = 20
FPS = 1
SECONDS_PER_SLIDE = 3

# ------------------- HELPERS -------------------
def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

# ------------------- PROCESS FILES -------------------
for filename in os.listdir(INPUT_FOLDER):
    if not filename.endswith(".json"):
        continue

    image_paths = []

    input_path = os.path.join(INPUT_FOLDER, filename)
    base_name = os.path.splitext(filename)[0]
    video_file = os.path.join(SLIDES_FOLDER, f"{base_name}.mp4")
    slide_folder = os.path.join(SLIDES_FOLDER, base_name)
    os.makedirs(slide_folder, exist_ok=True)

    # Load JSON safely
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠ Skipping invalid file: {filename} ({e})")
        continue

    if not data:
        continue

    # ------------------- COLLECT INSTITUTE DATA -------------------
    institute_data = {}
    for row in data:
        institute = row.get("Institute")
        program = row.get("Academic Program Name")
        if institute and program:
            institute = institute.strip()
            entry = (
                program.strip(),
                str(row.get("Quota", "")).strip(),
                str(row.get("Seat Type", "")).strip(),
                str(row.get("Gender", "")).strip(),
                str(row.get("Opening Rank", "")).strip(),
                str(row.get("Closing Rank", "")).strip(),
            )
            institute_data.setdefault(institute, []).append(entry)

    # ------------------- CREATE SLIDES -------------------
    for institute_idx, (institute, programs) in enumerate(sorted(institute_data.items()), start=1):
        programs = sorted(programs, key=lambda x: x[0])  # sort by program
        total_rows = len(programs)
        num_splits = math.ceil(total_rows / MAX_ROWS_PER_SLIDE)

        for split_num in range(num_splits):
            start = split_num * MAX_ROWS_PER_SLIDE
            end = start + MAX_ROWS_PER_SLIDE
            chunk = programs[start:end]

            fig_height = max(6, len(chunk) * 0.5)
            fig = plt.figure(figsize=(19.2, 10.8))  # HD 1080p

            # ------------------- BACKGROUND -------------------
            if os.path.exists(BACKGROUND_IMAGE):
                img = mpimg.imread(BACKGROUND_IMAGE)
                plt.imshow(img, extent=[0, 1, 0, 1], aspect='auto', zorder=0)
            else:
                fig.patch.set_facecolor("#E5E7EB")  # fallback light gray

            plt.axis('off')

            # ------------------- TITLE -------------------
            title_text = institute
            if num_splits > 1:
                title_text += f" (Slide {split_num+1}/{num_splits})"

            plt.text(
                0.5, 0.93,
                title_text,
                fontsize=28,
                fontweight='bold',
                ha='center',
                va='center',
                color="white",
                bbox=dict(
                    boxstyle="round,pad=0.6",
                    facecolor="#0F172A",
                    edgecolor="white",
                    linewidth=1.5
                ),
                zorder=2
            )

            # ------------------- TABLE -------------------
            col_labels = [
                "Academic Program Name",
                "Quota",
                "Seat Type",
                "Gender",
                "Opening Rank",
                "Closing Rank"
            ]

            # Group rows by Academic Program Name
            grouped_programs = {}
            for entry in chunk:
                program = entry[0]
                grouped_programs.setdefault(program, []).append(entry)

            # Sort each program by Closing Rank ascending
            for program in grouped_programs:
                grouped_programs[program] = sorted(
                    grouped_programs[program],
                    key=lambda x: int(x[5]) if x[5].isdigit() else 9999999
                )

            cell_text = []
            program_start_rows = []
            current_row_index = 1  # header is row 0

            for program, rows in grouped_programs.items():
                program_start_rows.append(current_row_index)
                for idx, row in enumerate(rows):
                    row_list = list(row)
                    if idx != 0:
                        row_list[0] = ""  # remove duplicate program name
                    cell_text.append(row_list)
                    current_row_index += 1

            table = plt.table(
                cellText=cell_text,
                colLabels=col_labels,
                cellLoc='center',
                loc='center',
                bbox=[0.05, 0.12, 0.90, 0.75]  # [left, bottom, width, height]
            )

            table.auto_set_font_size(False)
            table.set_fontsize(max(10, 16 - len(chunk)//2))  # general text
            header_font_size = max(16, 20 - len(chunk)//2)   # header bigger

            cells = table.get_celld()
            col_widths = [0.30, 0.08, 0.12, 0.15, 0.09, 0.09]

            # Closing ranks for color-coding
            all_closing_ranks = [int(r[5]) for r in cell_text if r[5].isdigit()]
            min_rank = min(all_closing_ranks) if all_closing_ranks else 0
            max_rank = max(all_closing_ranks) if all_closing_ranks else 1

            for (row, col), cell in cells.items():
                if col < len(col_widths):
                    cell.set_width(col_widths[col])

                # Header styling
                if row == 0:
                    cell.set_facecolor("#0F172A")
                    cell.set_text_props(color="white", weight="bold", fontsize=header_font_size)
                    cell.set_height(0.05)
                else:
                    # Program block subtle background
                    if row in program_start_rows:
                        base_color = "#E0F2FE"
                    else:
                        base_color = "#FFFFFF" if row % 2 else "#F8FAFC"
                    cell.set_facecolor(base_color)
                    cell.set_text_props(color="#111827", weight="bold",fontsize=max(10, 16 - len(chunk)//2))

                    # Left align program column
                    if col == 0:
                        cell.get_text().set_ha('left')

                    # Bold Opening Rank
                    if col == 4:
                        cell.get_text().set_weight('bold')

                    # Color-coded Closing Rank
                    if col == 5 and cell.get_text().get_text().isdigit():
                        rank = int(cell.get_text().get_text())
                        ratio = (rank - min_rank) / (max_rank - min_rank + 1)
                        if ratio < 0.33:
                            cell.set_text_props(color="#15803D", weight='bold')  # green
                        elif ratio < 0.66:
                            cell.set_text_props(color="#B45309", weight='bold')  # amber
                        else:
                            cell.set_text_props(color="#B91C1C", weight='bold')  # red

                    # Thick separator line at start of program
                    if row in program_start_rows:
                        cell.set_linewidth(2.2)
                        cell.set_edgecolor("#1E3A8A")

            table.scale(1, 1.5)
            table.set_zorder(2)
            plt.tight_layout()

            # ------------------- SAVE SLIDE -------------------
            slide_filename = f"{institute_idx}) {clean_filename(institute)}"
            if num_splits > 1:
                slide_filename += f" - {split_num+1}"

            slide_path = os.path.join(slide_folder, f"{slide_filename}.png")
            plt.savefig(slide_path, bbox_inches='tight')
            plt.close()
            image_paths.append(slide_path)

    # ------------------- CREATE VIDEO -------------------
    if image_paths:
        frame = cv2.imread(image_paths[0])
        if frame is None:
            continue

        height, width, _ = frame.shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(video_file, fourcc, FPS, (width, height))

        for image_path in image_paths:
            frame = cv2.imread(image_path)
            if frame is not None:
                for _ in range(SECONDS_PER_SLIDE * FPS):
                    video.write(frame)

        video.release()
        print(f"🎬 Video created: {video_file}")
