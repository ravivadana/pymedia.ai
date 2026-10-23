import os
import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
import time

class AssetCreater:
    def __init__(self, json_file_path=None, assets_dir=None):
        """
        Initializes the asset creator with configurable paths.
        """
        # Fallback defaults if no parameters are explicitly passed
        self.json_file_path = json_file_path or "C:/Ravi/Python/2025/Media/assets/nirf/data/NIRF_medical_2025_Ranking.json"
        self.assets_dir = assets_dir or "C:/Ravi/Python/2025/Media/assets/nirf/images/medical"
        
        # Build out workspace architecture safely
        os.makedirs(os.path.join(self.assets_dir, "logos"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "campus"), exist_ok=True)
        from pathlib import Path
        directory_path = Path(os.path.join(self.assets_dir, "logos"))
        # Change "*.jpg" to matches your target extension
        self.existed_logos_count = sum(1 for item in directory_path.rglob('*.png') if item.is_file())
        # Class configuration properties
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = 20

    def download_image(self, url, save_path):
        """Downloads an image from a URL and saves it to the specified path."""
        if not url:
            return False
        try:
            if os.path.exists(save_path):
                print(f"File already exists: {save_path}")
                return True

            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
                with open(save_path, "wb") as f:
                    f.write(response.content)
                print(f"Successfully saved: {save_path}")
                return True
        except Exception as e:
            print(f"Failed to download from {url}. Error: {e}")
        return False

    def get_image_from_google(self, query):
        """Queries Google Images and returns the URL of the first image result."""
        try:
            print(f"Falling back to Google Search for: '{query}'")
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch"
            response = requests.get(search_url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                img_tags = soup.find_all("img")
                
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and not src.startswith("data:image/gif") and "google" not in src:
                        return src
        except Exception as e:
            print(f"Google search failed for query '{query}': {e}")
        return None

    def scrape_from_official_site(self, site_url, image_type="logo"):
        """Fallback 1: Scrapes the official website for a logo or generic image."""
        if not site_url:
            return None
        try:
            print(f"Falling back to official website: {site_url}")
            response = requests.get(site_url, headers=self.headers, timeout=self.timeout)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            all_imgs = soup.find_all("img")

            for img in all_imgs:
                src = img.get("src")
                if src:
                    src_lower = src.lower()
                    if image_type == "logo" and ("logo" in src_lower or "brand" in src_lower):
                        return urllib.parse.urljoin(site_url, src)
                    elif image_type == "campus" and any(x in src_lower for x in ["campus", "banner", "hero", "building"]):
                        return urllib.parse.urljoin(site_url, src)
            
            if all_imgs:
                for img in all_imgs:
                    src = img.get("src")
                    if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png"]):
                        return urllib.parse.urljoin(site_url, src)
        except Exception as e:
            print(f"Error scraping official site {site_url}: {e}")
        return None

    def scrape_images_from_site(self, site_url, wikilink, original_name, rank):
        """Scrapes Wikipedia, falls back to official site, then falls back to Google Search."""
        logo_url = None
        campus_url = None

        # ------------------ STAGE 1: WIKIPEDIA ------------------
        try:
            print(f"Attempting Wikipedia: {wikilink}")
            response = requests.get(wikilink, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                infobox = soup.find(class_="infobox")
                
                if infobox:
                    first_img = infobox.find("img")
                    if first_img and first_img.get("src"):
                        logo_url = urllib.parse.urljoin(wikilink, first_img.get("src"))

                campus_img = soup.find("img", alt=lambda x: x and "campus" in x.lower()) or \
                             soup.find("img", class_=lambda x: x and ("banner" in x.lower() or "hero" in x.lower()))
                
                if campus_img and campus_img.get("src"):
                    campus_url = urllib.parse.urljoin(wikilink, campus_img["src"])
                else:
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
        logo_name = os.path.join(self.assets_dir, f"logos/{rank}_{original_name}.png")
        logo_downloaded = False

        if logo_url:
            print(f"Found Wiki Logo URL: {logo_url}")
            logo_downloaded = self.download_image(logo_url, logo_name)

        if not logo_downloaded and site_url:
            official_logo_url = self.scrape_from_official_site(site_url, "logo")
            logo_downloaded = self.download_image(official_logo_url, logo_name)

        if not logo_downloaded:
            google_logo_url = self.get_image_from_google(f"{original_name} logo png")
            logo_downloaded = self.download_image(google_logo_url, logo_name)

        if not logo_downloaded:
            print(f"❌ Failed to download logo for {original_name} via all methods.")

        # ------------------ PROCESS CAMPUS DOWNLOAD & FALLBACKS ------------------
        campus_name = os.path.join(self.assets_dir, f"campus/{rank}_{original_name}.png")
        campus_downloaded = False

        if campus_url:
            print(f"Found Wiki Campus URL: {campus_url}")
            campus_downloaded = self.download_image(campus_url, campus_name)

        if not campus_downloaded and site_url:
            official_campus_url = self.scrape_from_official_site(site_url, "campus")
            campus_downloaded = self.download_image(official_campus_url, campus_name)

        if not campus_downloaded:
            google_campus_url = self.get_image_from_google(f"{original_name} campus building")
            campus_downloaded = self.download_image(google_campus_url, campus_name)

        if not campus_downloaded:
            print(f"❌ Failed to download campus image for {original_name} via all methods.")

    def short_institute_name(self, name):
        """Cleans strings and strips spaces/characters to build searchable criteria."""
        name = name.replace("`", "'")
        name = name.replace(",", "").replace(" ", "_")
        name = name.replace("_&_", "_and_")
        mapping = {
            "Indian_Institute_of_Technology": "IIT",
            "National_Institute_of_Technology": "NIT",
            "Indian_Institute_of_Information_Technology": "IIIT",
        }
        for k, v in mapping.items():
            if name.startswith(k):
                return name.replace(k, v)
        return name

    def run_scraper(self):
        """Main operational execution sequence loop."""
        try:
            with open(self.json_file_path, "r", encoding="utf-8") as f:
                institutes = json.load(f)
        except FileNotFoundError:
            print(f"JSON file not found at {self.json_file_path}. Please verify configuration paths.")
            return
        if len(institutes)>0:
            return
        for inst in institutes:
            original_name = self.short_institute_name(inst.get("Name"))
            inst_id = inst.get("Institute ID")
            website = inst.get("Official Website")
            
            wiki_clean_name = self.short_institute_name(original_name)
            wiki_encoded_name = urllib.parse.quote(wiki_clean_name)
            wikilink = f"https://en.wikipedia.org/wiki/{wiki_encoded_name}"

            try:
                rank = f'{int(inst.get("Rank")):03d}'
            except (ValueError, TypeError):
                rank = "000"

            print("\n" + "="*50)
            print(f"Processing: {original_name} ({original_name}) | Rank: {rank}")
            print("="*50)
            
            self.scrape_images_from_site(website, wikilink, original_name, rank)
            time.sleep(2)