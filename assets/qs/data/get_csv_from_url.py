import csv
import json
import urllib.request
from pathlib import Path

def load_country_iso_map(countries_json_path):
    """Loads the countries_ISO_codes.json file for mapping full country names to ISO codes."""
    country_to_iso = {}
    
    if not countries_json_path.exists():
        print(f"Warning: Country ISO reference file '{countries_json_path}' not found. Country resolution might fail.")
        return country_to_iso

    try:
        with open(countries_json_path, "r", encoding="utf-8") as f:
            country_data = json.load(f)
            # FIX: Convert keys to lowercase to match the comment's intent and handle CSV variations safely
            country_to_iso = {name.strip().lower(): code.strip().lower() for name, code in country_data.items()}
        print(f"Loaded {len(country_to_iso)} country ISO mappings.")
    except Exception as e:
        print(f"Error reading countries_ISO_codes.json file: {e}")
        
    return country_to_iso

def load_cities_reference_map(cities_json_path):
    """Loads the cities.json file and maps a composite key of 'countrycode_cityname' to 'admin2' (state)."""
    composite_city_map = {}
    
    if not cities_json_path.exists():
        print(f"Warning: Cities reference file '{cities_json_path}' not found. Fallback lookup unavailable.")
        return composite_city_map

    try:
        with open(cities_json_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
            for item in cities_data:
                city_name = item.get("name")
                country_code = item.get("country")
                state_name = item.get("admin1")
                
                if city_name and country_code and state_name:
                    # FIX: Enforce absolute lowercase on both parts of the key to guarantee matching
                    composite_key = f"{country_code.strip().lower()}_{city_name.strip().lower()}"
                    composite_city_map[composite_key] = state_name.strip()
                    
                city_name =  item.get("admin2")
                if city_name and country_code and state_name:
                    # FIX: Enforce absolute lowercase on both parts of the key to guarantee matching
                    composite_key = f"{country_code.strip().lower()}_{city_name.strip().lower()}"
                    if composite_key not in composite_city_map:
                        composite_city_map[composite_key] = state_name.strip()

        print(f"Loaded {len(composite_city_map)} unique country-city mapping keys from cities.json.")
    except Exception as e:
        print(f"Error reading cities.json file: {e}")
        
    return composite_city_map

def download_and_transform_qs_data(url, countries_json_path, cities_json_path, output_json_path):
    print("Connecting to GitHub to fetch the 2027 dataset...")
    
    country_to_iso_map = load_country_iso_map(countries_json_path)
    city_to_state_map = load_cities_reference_map(cities_json_path)
    
    try:
        response = urllib.request.urlopen(url)
        lines = [line.decode('utf-8') for line in response.readlines()]
        
        reader = csv.DictReader(lines)
        transformed_records = []
        city_ref_fallback_count = 0
        
        for index, row in enumerate(reader, start=1):
            inst_name = row.get("institution_name", "").strip()
            country_val = row.get("country/territory", "").strip()
            city_val = row.get("city", "").strip()
            state_val = row.get("state")
            
            if not state_val or state_val.strip() == "":
                # FIX: Lowercase the incoming CSV country name for safe map querying
                country_code = country_to_iso_map.get(country_val.lower(), "")
                
                # FIX: Construct lookup key matching the lowercase structure of our reference map
                lookup_key = f"{country_code}_{city_val.lower()}"
                
                state_val = city_to_state_map.get(lookup_key, "")
                if state_val=="Unknown":
                    if country_val=="United Kingdom":
                        country_code="gb"
                        lookup_key = f"{country_code}_{city_val.lower()}"
                        state_val = city_to_state_map.get(lookup_key, "Unknown")
                if state_val != "Unknown":
                    city_ref_fallback_count += 1
                else:
                    print(f'not found for {country_val} and {city_val}')
            else:
                state_val = state_val.strip()

            transformed_record = {
                "index": index,
                "rank": row.get("2027_rank"),
                "previous_year_rank": row.get("previous_year_rank"),
                "institution_name": inst_name,
                "country_territory": country_val,
                "region": row.get("region"),
                "size": row.get("size"),
                "focus": row.get("focus"),
                "research": row.get("research"),
                "status": row.get("status"),
                "overall_score": row.get("overall_score"),
                "city": city_val,
                "state": state_val
            }
            transformed_records.append(transformed_record)
            
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(transformed_records, f, indent=4, ensure_ascii=False)
            
        print(f"Success! Processed {len(transformed_records)} records.")
        print(f"-> Safely resolved {city_ref_fallback_count} missing states using precise Country + City keys.")
        print(f"File saved to: {output_json_path}")
        
    except Exception as e:
        print(f"An error occurred during extraction: {e}")

if __name__ == "__main__":
    year = 2027
    target_url = f"https://raw.githubusercontent.com/reshmaharidhas/Data-Analysis-of-QS-World-University-Rankings-2027/refs/heads/main/data/cleaned_qs_world_rankings_{year}.csv"
    
    QS_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/qs/data")
    COMMON_ASSETS = Path("C:/Ravi/Python/2025/Media/assets/common/data")
    COUNTRIES_ISO_PATH = COMMON_ASSETS / 'countries_abbreviations.json'
    CITIES_REF_PATH = COMMON_ASSETS / 'cities.json'
    JSON_DATA_PATH = QS_ASSETS / f'qs_{year}_ranking.json'
    
    download_and_transform_qs_data(target_url, COUNTRIES_ISO_PATH, CITIES_REF_PATH, JSON_DATA_PATH)