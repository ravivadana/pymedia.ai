import os
import json
from bs4 import BeautifulSoup

# 📁 Input and Output folders
INPUT_FOLDER = "00_data_processing/pages/SeatAllotmentResult2026"
OUTPUT_FOLDER = "00_data_processing/data/nrif_ranking/2026/engineering\Cutoff"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def parse_table(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    table = soup.find("table", id="ctl00_ContentPlaceHolder1_GridView1")
    if not table:
        return []

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    data = []

    # Extract all rows except header
    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) != len(headers):
            continue

        row_data = {}
        for header, col in zip(headers, cols):
            value = col.get_text(strip=True)

            # Optional: convert ranks to integers
            if header in ["Opening Rank", "Closing Rank"] and value.isdigit():
                value = int(value)

            row_data[header] = value

        data.append(row_data)

    return data


# 🔄 Process all HTML files
for filename in os.listdir(INPUT_FOLDER):
    if filename.endswith(".html"):
        input_path = os.path.join(INPUT_FOLDER, filename)

        with open(input_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        table_data = parse_table(html_content)

        output_filename = os.path.splitext(filename)[0] + ".json"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(table_data, f, indent=4, ensure_ascii=False)

        print(f"Converted: {filename} → {output_filename}")

print("✅ All files converted successfully.")
