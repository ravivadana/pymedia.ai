import os
import pandas as pd

# Define paths
input_file_path = r"C:\Ravi\Python\2025\Media\assets\common\data\cities.json"
output_dir = os.path.dirname(input_file_path)

print("Reading cities.json...")

try:
    # Load the entire 26 MB file at once
    # Try reading as a standard JSON array first
    df = pd.read_json(input_file_path)
except ValueError:
    # If it fails, it might be formatted as JSON Lines (one JSON per line)
    df = pd.read_json(input_file_path, lines=True)

print(f"Loaded {len(df)} cities. Splitting by country...")

# Group by the 'country' column
grouped = df.groupby("country")

# Loop through each country group and save it
for country, group_df in grouped:
    output_file_path = os.path.join(output_dir, f"{country}_Cities.json")

    # Save as a clean, traditional JSON array [...]
    group_df.to_json(
        output_file_path,
        orient="records",
        indent=4,  # Makes it beautiful and readable
        force_ascii=False,
    )

print("Done! All country files have been created successfully.")