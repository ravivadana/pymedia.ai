import os
import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
import time
import re

# Define paths
JSON_FILE_PATH = (
    f"assets/nrif/data/NIRF_medical_2025_Ranking"
)
ASSETS_DIR = "assets/nrif/images/medical"

# Ensure assets subdirectories exist
os.makedirs(os.path.join(ASSETS_DIR, "logos"), exist_ok=True)
os.makedirs(os.path.join(ASSETS_DIR, "campus"), exist_ok=True)

# Headers to mimic a browser request (crucial for Google Search scraping)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def download_image(url, save_path):
    """Downloads an image from a URL and saves it to the specified path."""
    if not url:
        return False
    try:
        # Check if file already exists to avoid redundant downloads
        if os.path.exists(save_path):
            print(f"File already exists: {save_path}")
            return True

        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"Successfully saved: {save_path}")
            return True
    except Exception as e:
        print(f"Failed to download from {url}. Error: {e}")
    return False


def get_image_from_google(query):
    """Queries Google Images and returns the URL of the first image result."""
    try:
        print(f"Falling back to Google Search for: '{query}'")
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch"
        response = requests.get(search_url, headers=HEADERS, timeout=20)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Look for image tags. Google Images often stores sources in specific structures or scripts,
            # but standard image tags with encryption or direct links can be extracted.
            img_tags = soup.find_all("img")
            
            for img in img_tags:
                src = img.get("src") or img.get("data-src")
                # Skip the tiny transparent structural gifs or Google logos
                if src and not src.startswith("data:image/gif") and "google" not in src:
                    return src
    except Exception as e:
        print(f"Google search failed for query '{query}': {e}")
    return None


def scrape_from_official_site(site_url, image_type="logo"):
    """Fallback 1: Scrapes the official website for a logo or generic image."""
    try:
        print(f"Falling back to official website: {site_url}")
        response = requests.get(site_url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        all_imgs = soup.find_all("img")

        for img in all_imgs:
            src = img.get("src")
            if src:
                src_lower = src.lower()
                # If looking for a logo
                if image_type == "logo" and ("logo" in src_lower or "brand" in src_lower):
                    return urllib.parse.urljoin(site_url, src)
                # If looking for a campus/banner
                elif image_type == "campus" and any(x in src_lower for x in ["campus", "banner", "hero", "building"]):
                    return urllib.parse.urljoin(site_url, src)
        
        # Absolute fallback: Just return the first non-empty image link if specific matches aren't found
        if all_imgs:
            for img in all_imgs:
                src = img.get("src")
                if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png"]):
                    return urllib.parse.urljoin(site_url, src)

    except Exception as e:
        print(f"Error scraping official site {site_url}: {e}")
    return None


def scrape_images_from_site(site_url, wikilink, institute_id, rank, raw_name):
    """Scrapes Wikipedia, falls back to official site, then falls back to Google Search."""
    logo_url = None
    campus_url = None

    # ------------------ STAGE 1: WIKIPEDIA ------------------
    try:
        print(f"Attempting Wikipedia: {wikilink}")
        response = requests.get(wikilink, headers=HEADERS, timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            infobox = soup.find(class_="infobox")
            
            # Extract Logo from Infobox
            if infobox:
                first_img = infobox.find("img")
                if first_img and first_img.get("src"):
                    logo_url = urllib.parse.urljoin(wikilink, first_img.get("src"))

            # Extract Campus Image
            campus_img = soup.find("img", alt=lambda x: x and "campus" in x.lower()) or \
                         soup.find("img", class_=lambda x: x and ("banner" in x.lower() or "hero" in x.lower()))
            
            if campus_img and campus_img.get("src"):
                campus_url = urllib.parse.urljoin(wikilink, campus_img["src"])
            else:
                # Fallback within Wikipedia to find any jpg/jpeg
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if src and any(ext in src.lower() for ext in [".jpg", ".jpeg"]):
                        if logo_url and logo_url in src:
                            continue
                        campus_url = urllib.parse.urljoin(wikilink, src)
                        break
        else:
            print(f"Wikipedia page not found (Status {response.status_code})")
    except Exception as e:
        print(f"Error reading Wikipedia: {e}")

    # ------------------ PROCESS LOGO DOWNLOAD & FALLBACKS ------------------
    logo_name = os.path.join(ASSETS_DIR, f"logos/{rank}_{institute_id}.png")
    logo_downloaded = False

    if logo_url:
        print(f"Found Wiki Logo URL: {logo_url}")
        logo_downloaded = download_image(logo_url, logo_name)

    if not logo_downloaded:
        # Try official website fallback
        official_logo_url = scrape_from_official_site(site_url, "logo")
        logo_downloaded = download_image(official_logo_url, logo_name)

    if not logo_downloaded:
        # Try Google Search fallback
        google_logo_url = get_image_from_google(f"{raw_name} logo png")
        logo_downloaded = download_image(google_logo_url, logo_name)

    if not logo_downloaded:
        print(f"❌ Failed to download logo for {raw_name} via all methods.")

    # ------------------ PROCESS CAMPUS DOWNLOAD & FALLBACKS ------------------
    campus_name = os.path.join(ASSETS_DIR, f"campus/{rank}_{institute_id}.png")
    campus_downloaded = False

    if campus_url:
        print(f"Found Wiki Campus URL: {campus_url}")
        campus_downloaded = download_image(campus_url, campus_name)

    if not campus_downloaded:
        # Try official website fallback
        official_campus_url = scrape_from_official_site(site_url, "campus")
        campus_downloaded = download_image(official_campus_url, campus_name)

    if not campus_downloaded:
        # Try Google Search fallback
        google_campus_url = get_image_from_google(f"{raw_name} campus building png")
        campus_downloaded = download_image(google_campus_url, campus_name)

    if not campus_downloaded:
        print(f"❌ Failed to download campus image for {raw_name} via all methods.")


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


def main():
    # Load the JSON data
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            institutes = json.load(f)
    except FileNotFoundError:
        print(f"JSON file not found at {JSON_FILE_PATH}. Please check the path.")
        return

    # Loop through each institute and attempt to fetch images
    for inst in institutes:
        raw_name = inst.get("Name")
        inst_id = inst.get("Institute ID")
        website = inst.get("Official Website")
        
        short_name = short_institute_name(raw_name)
        wiki_formatted_name = short_name.replace(' ', '_')
        wikilink = f"https://en.wikipedia.org/wiki/{wiki_formatted_name}"

        # Clean Rank string (e.g., 1 -> '001')
        try:
            rank = f'{int(inst.get("Rank")):03d}'
        except (ValueError, TypeError):
            rank = "000"

        print(f"\n" + "="*50)
        print(f"Processing: {short_name} ({inst_id}) | Rank: {rank}")
        print(f"="*50)
        
        scrape_images_from_site(website, wikilink, wiki_formatted_name, rank, raw_name)
        
        # Polite spacing delay between targets to mitigate rate limiting
        time.sleep(2)

if __name__ == "__main__":
    main()