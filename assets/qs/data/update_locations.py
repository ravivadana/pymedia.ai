import json
import os

def update_locations(json_filepath, output_filepath):
    # Load the original ranking data
    if not os.path.exists(json_filepath):
        print(f"Error: File {json_filepath} not found.")
        return
        
    with open(json_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Dictionary Map: "University Name": ("City", "State/Region")
    # Add your targeted university location map mappings here
    location_map = {
        "Massachusetts Institute of Technology (MIT)": ("Cambridge", "Massachusetts"),
        "Imperial College London": ("London", "England"),
        "Stanford University": ("Stanford", "California"),
        "University of Oxford": ("Oxford", "England"),
        "Harvard University": ("Cambridge", "Massachusetts"),
        "University of Cambridge": ("Cambridge", "England"),
        "California Institute of Technology (Caltech)": ("Pasadena", "California"),
        "ETH Zurich": ("Zurich", "Zurich"),
        "UCL": ("London", "England"),
        "National University of Singapore (NUS)": ("Singapore", "Singapore"),
        "The University of Hong Kong": ("Hong Kong", "Hong Kong"),
        "Nanyang Technological University, Singapore (NTU Singapore)": ("Singapore", "Singapore"),
        "Peking University": ("Beijing", "Beijing"),
        "Tsinghua University": ("Beijing", "Beijing"),
        "University of Pennsylvania": ("Philadelphia", "Pennsylvania"),
        "Cornell University": ("Ithaca", "New York"),
        "Yale University": ("New Haven", "Connecticut"),
    }

    updated_count = 0
    for record in data:
        name = record.get("Name")
        
        # If matching map configuration exists, append it dynamically
        if name in location_map:
            city, state = location_map[name]
            record["City"] = city
            record["State"] = state
            updated_count += 1
        else:
            # Fallback defaults so the keys always exist structurally
            record["City"] = record.get("City", "Unknown")
            record["State"] = record.get("State", record.get("Country/Territory", "Unknown"))

    # Save out the structural changes to a new file
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully processed {len(data)} records!")
    print(f"Explicitly updated map locations for {updated_count} specific items.")

# Execution
if __name__ == "__main__":
    # Adjust paths if your file sits inside 'QS_ASSETS/data/' or your current folder
    input_file = r"C:\Ravi\Python\2025\Media\assets\qs\data\QS_2027_RANKING.json"
    output_file = r"C:\Ravi\Python\2025\Media\assets\qs\data\QS_2027_RANKING_UPDATED.json"
    
    update_locations(input_file, output_file)