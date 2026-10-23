import os
import re
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from config import Config

class AssetScraper:
    def __init__(self):
        Config.initialize_dirs()
        self.processed_states = set()

    @staticmethod
    def clean_country_name(name):
        name = name.split('[')[0]
        name = name.split('(')[0]
        return name.strip()

    @staticmethod
    def download_and_save_as_png(url, filename, force_replace=False):
        """Downloads, smart crops, and resizes background image to target size portrait PNG."""
        if os.path.exists(filename):
            if force_replace:
                try:
                    os.remove(filename)
                except Exception as e:
                    print(f"    Failed to remove old file {filename}: {e}")
            else:
                return True
            
        try:
            response = requests.get(url, headers=Config.HEADERS, timeout=30)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                
                if img.mode in ("CMYK", "P"):
                    img = img.convert("RGB")
                
                target_w, target_h = Config.TARGET_SIZE
                orig_w, orig_h = img.size
                target_aspect = target_w / target_h
                orig_aspect = orig_w / orig_h
                
                if orig_aspect > target_aspect:
                    new_h = target_h
                    new_w = int(target_h * orig_aspect)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    left = (new_w - target_w) // 2
                    img = img.crop((left, 0, left + target_w, target_h))
                else:
                    new_w = target_w
                    new_h = int(target_w / orig_aspect)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    top = (new_h - target_h) // 2
                    img = img.crop((0, top, target_w, top + target_h))
                
                img.save(filename, "PNG")
                return True
            return False
        except Exception as e:
            print(f"    Download or Image processing workflow exception: {e}")
            return False

    @staticmethod
    def get_4k_background_url(country_name, google_search_base_url, bing_search_base_url):
        """Scrapes base engines dynamically using parameters injected cleanly from main driver."""
        query = f"capital of {country_name} wallpaper"
        encoded_query = urllib.parse.quote_plus(query)
        
        # Engine 1 Parsing Logic
        if google_search_base_url:
            google_url = f"{google_search_base_url}{encoded_query}&tbm=isch"
            try:
                res = requests.get(google_url, headers=Config.HEADERS, timeout=15)
                if res.status_code == 200:
                    urls = re.findall(r'(https?://[^\s\"\']+\.(?:jpg|jpeg|png|webp)[^\s\"\']*)', res.text)
                    for url in urls:
                        url = url.replace("\\u003d", "=").replace("\\u0026", "&").split('\\')[0]
                        if any(x in url for x in ["gstatic.com", "googleusercontent.com", "encrypted", "tbn:"]):
                            continue
                        return url
            except Exception as e:
                print(f"    Google Engine Scraper Exception: {e}")

        # Engine 2 Parsing Logic
        if bing_search_base_url:
            bing_url = f"{bing_search_base_url}{encoded_query}&qft=+filterui:aspect-tall"
            try:
                res = requests.get(bing_url, headers=Config.HEADERS, timeout=15)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", class_="iusc")
                    for link in links:
                        m_attr = link.get("m")
                        if m_attr:
                            murl_match = re.search(r'"murl"\s*:\s*(?:"([^"]+)"|\'([^\']+)\')', m_attr)
                            if murl_match:
                                img_url = murl_match.group(1) or murl_match.group(2)
                                if img_url and img_url.startswith("http"):
                                    return img_url
            except Exception as e:
                print(f"    Bing Engine Scraper Exception: {e}")
                
        return None

    def download_wikipedia_assets(self, wiki_url, google_base_url, bing_base_url, force_replace_list=None):
        """Finds missing flags and auto-resolves backgrounds using purely injected control endpoints."""
        if force_replace_list is None:
            force_replace_list = []
            
        # Convert list items to lowercase for safe checking
        force_replace_lower = [c.lower() for c in force_replace_list]

        try:
            print(f"Fetching structural matrices directly from index: {wiki_url}")
            response = requests.get(wiki_url, headers=Config.HEADERS, timeout=30)
            if response.status_code != 200:
                print(f"Failed to access Wikipedia index. Code: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table", class_="wikitable")
            
            for table in tables:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    
                    img_tag = cells[0].find("img")
                    state_link = cells[1].find("a")
                    
                    if not img_tag or not state_link or not state_link.text:
                        continue
                        
                    raw_country = state_link.text
                    country_name = self.clean_country_name(raw_country)
                    
                    if not country_name or country_name in ["Flag", "State", "Aspect ratio", "Date", "Sovereign state"] or country_name in self.processed_states:
                        continue
                    
                    safe_name = country_name.replace("/", "_").replace("\\", "_")
                    flag_filename = os.path.join(Config.FLAG_DIR, f"{safe_name}_flag.png")
                    bg_filename = os.path.join(Config.BG_DIR, f"{safe_name}.png")
                    
                    # Evaluate dynamic substitution execution flags
                    should_force = country_name.lower() in force_replace_lower
                    
                    # --- Global Asset Skip Check with Force Bypass ---
                    if os.path.exists(flag_filename) and os.path.exists(bg_filename) and not should_force:
                        self.processed_states.add(country_name)
                        continue
                    
                    src = img_tag.get("src") or img_tag.get("data-src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        if "/thumb/" in src:
                            parts = src.split("/")
                            last_segment = parts[-1]
                            if "px-" in last_segment:
                                dimension_split = last_segment.split("px-", 1)
                                parts[-1] = f"500px-{dimension_split[1]}"
                                src = "/".join(parts)
                        
                        print(f"-> Verification step for base assets: {country_name}")
                        
                        # --- Flag File Replacement Strategy ---
                        if not os.path.exists(flag_filename) or should_force:
                            if should_force and os.path.exists(flag_filename):
                                try: os.remove(flag_filename)
                                except Exception: pass
                            try:
                                res_flag = requests.get(src, headers=Config.HEADERS, timeout=30)
                                if res_flag.status_code == 200:
                                    with open(flag_filename, 'wb') as f:
                                        f.write(res_flag.content)
                                    print(f"    ✓ Flag saved: {flag_filename}")
                            except Exception as e:
                                print(f"    Failed pulling flag asset: {e}")
                        else:
                            print(f"    ↳ Skipping Flag download: Already exists.")
                        
                        # --- Background File Replacement Strategy ---
                        if not os.path.exists(bg_filename) or should_force:
                            bg_url = self.get_4k_background_url(country_name, google_base_url, bing_base_url)
                            if bg_url:
                                self.download_and_save_as_png(bg_url, bg_filename, force_replace=should_force)
                                print(f"    ✓ Background wallpaper verified/saved for: {country_name}")
                        else:
                            print(f"    ↳ Skipping Background search: Already exists.")
                        
                        self.processed_states.add(country_name)
                        time.sleep(1.2)
        except Exception as e:
            print(f"Asset Scraping Pipeline Exception: {e}")