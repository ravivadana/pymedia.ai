import os
import shutil
import re
import unicodedata
import pandas as pd
from tqdm import tqdm

class AssetScraper:
    def __init__(self, json_path, source_folder, target_folder):
        self.json_path = json_path
        self.source_folder = source_folder
        self.target_folder = target_folder
        
        # --- HARDCODED EXCEPTIONS ---
        # Format: {"Cleaned JSON Name": "Exact Logo Filename in Downloads folder"}
        self.manual_mappings = {
            "Galgotias University": "galgotia_logo.png"  # Update with your actual filename if needed
        }
        
        # Ensure target assets folder exists
        os.makedirs(self.target_folder, exist_ok=True)

    def clean_name(self, name):
        """
        Cleans the institution name to make file-matching robust.
        """
        if pd.isna(name):
            return ""
        name = str(name)
        name = re.sub(r'\(.*?\)', '', name)
        name = re.sub(r'\[.*?\]', '', name)
        name = name.replace("’", "'").replace("`", "'").replace("“", '"').replace("”", '"')
        name = unicodedata.normalize('NFKD', name)
        name = "".join([c for c in name if not unicodedata.combining(c)])
        name = re.sub(r'[\\/:*?"<>|]', '', name)
        name = " ".join(name.split())
        return name.strip()

    def find_and_copy_logos(self):
        try:
            df = pd.read_json(self.json_path)
            institution_column = 'Name'
            index_column = 'Index'
            df_cleaned = df.dropna(subset=[institution_column])
        except Exception as e:
            print(f"X Error reading JSON file: {e}")
            return

        print(f"Found {len(df_cleaned)} institution rows in JSON.")
        
        try:
            source_files = os.listdir(self.source_folder)
        except Exception as e:
            print(f"X Error accessing source directory: {e}")
            return

        print(f"Scanning source directory... Found {len(source_files)} available files.")

        copied_count = 0
        missing_count = 0

        for seq_num, (idx, row) in enumerate(tqdm(df_cleaned.iterrows(), total=len(df_cleaned), desc="Processing Logos"), start=1):
            uni_raw = row[institution_column]
            uni_clean = self.clean_name(uni_raw)
            if not uni_clean:
                continue

            if index_column in row and not pd.isna(row[index_column]):
                try:
                    sequence_str = f"{int(row[index_column]):03d}"
                except (ValueError, TypeError):
                    sequence_str = str(row[index_column]).strip()
            else:
                sequence_str = f"{seq_num:03d}"

            matched_files = []

            # --- PRE-CHECK STRATEGY: Manual Overrides ---
            if uni_clean in self.manual_mappings:
                forced_filename = self.manual_mappings[uni_clean]
                if forced_filename in source_files:
                    matched_files = [forced_filename]
                else:
                    tqdm.write(f" ⚠ Manual mapping file '{forced_filename}' not found in source folder for {uni_clean}")

            # Execute standard automated fallbacks if no manual match
            if not matched_files:
                # --- STRATEGY 1: Flexible Containment Match ---
                matched_files = [f for f in source_files if uni_clean.lower() in f.lower()]
                
                # --- STRATEGY 1b: Apostrophe-free Fallback ---
                if not matched_files and "'" in uni_clean:
                    uni_no_apostrophe = uni_clean.replace("'", "")
                    matched_files = [f for f in source_files if uni_no_apostrophe.lower() in f.lower()]
                
                # --- STRATEGY 2: Smart Specific Fallback ---
                name_parts = uni_clean.split()
                if not matched_files and len(name_parts) > 1:
                    specific_keyword = name_parts[-1].lower()
                    if specific_keyword not in ["university", "institute", "college", "technology", "of", "and", "science"]:
                        matched_files = [
                            f for f in source_files 
                            if specific_keyword in f.lower() and name_parts[0].lower().replace("'", "") in f.lower()
                        ]

                # --- STRATEGY 3: Final Sequential Reduction ---
                if not matched_files:
                    for i in range(len(name_parts), 0, -1):
                        search_query = " ".join(name_parts[:i]).lower()
                        
                        # FIXED: Added "university of", "university", and "college" to prevent duplicate matching
                        if search_query in [
                            "massachusetts institute", "institute of technology", "indian institute", 
                            "university of", "university", "college of", "college", "institute"
                        ]:
                            continue
                            
                        matched_files = [f for f in source_files if search_query in f.lower()]
                        if matched_files:
                            break

            # 4. Copy file workflow if assets matched
            if matched_files:
                file_name = matched_files[0]
                source_file_path = os.path.join(self.source_folder, file_name)
                
                safe_target_name = uni_clean.replace(" ", "_").replace("'", "") + os.path.splitext(file_name)[1]
                target_file_path = os.path.join(self.target_folder, f'{sequence_str}_{safe_target_name}')

                try:
                    shutil.copy2(source_file_path, target_file_path)
                    copied_count += 1
                except Exception as e:
                    tqdm.write(f"  X Failed to copy {file_name}: {e}")
            else:
                missing_count += 1

        print("\n=== Pipeline Execution Summary ===")
        print(f"✓ Total assets successfully matched and copied: {copied_count}")
        print(f"⚠ Total universities missing source assets: {missing_count}")


# if __name__ == "__main__":
#     JSON_FILE_PATH = r"02_videos_processing\002_QS\assets\data\qs_rankings_2027.json" 
#    browse and save as https://www.topuniversities.com/world-university-rankings
#     SOURCE_DIR = r"C:\Users\ravik\Downloads\QS World University Rankings 2027_ Top Global Universities _ TopUniversities_files"
#     ASSETS_DIR = r"C:\Ravi\Python\2025\Media\02_videos_processing\002_QS\assets\images\logos"

#     organizer = AssetOrganizer(
#         json_path=JSON_FILE_PATH, 
#         source_folder=SOURCE_DIR, 
#         target_folder=ASSETS_DIR
#     )
#     organizer.find_and_copy_logos()