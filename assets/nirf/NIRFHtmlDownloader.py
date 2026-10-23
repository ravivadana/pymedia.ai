import json
from bs4 import BeautifulSoup
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import requests
from bs4 import BeautifulSoup
from pathlib import Path

class NIRFHtmlDownloader:
    """
    A reusable utility class to pull table layouts from the NIRF portal
    and isolate the raw `#tbl_overall` table matrix directly into a local file.
    """
    def __init__(self, course_name: str, year: int = 2025, output_dir: str = "."):
        self.course_name = course_name
        self.year = year
        self.output_dir = Path(output_dir).resolve()

    @property
    def filename(self) -> str:
        """Dynamically computes the exact requested target filename format."""
        return f"NIRF_{self.course_name}_{self.year}_Ranking.html"

    def download_and_isolate_table(self, url: str) -> Path:
        """
        Connects to the NIRF target URL, isolates the target `#tbl_overall` 
        table layout markup, and streams it to your local file path.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        
        # Resolve target fully structured filepath
        destination_path = self.output_dir / self.filename
        
        try:
            print(f"Streaming content from URL: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # Check for common streaming failures (404, 500)
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Grab table matching targeted component ID
            target_table = soup.find("table", id="tbl_overall")
            
            if not target_table:
                print("Warning: table with id='tbl_overall' missing. Trying fallback standard <table>...")
                target_table = soup.find("table")
                
            if not target_table:
                print("Error: Could not locate any HTML structural tables.")
                return None
                
            # Create local storage folders if missing
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Commit isolated table fragment directly to storage disk
            with open(destination_path, "w", encoding="utf-8") as file:
                file.write(str(target_table))
                
            print(f"Successfully created isolated matrix: {destination_path.name}")
            return destination_path
            
        except requests.exceptions.RequestException as e:
            print(f"Network transport level connection failure: {e}")
            return None

class NIRFTableExtractor:
    """A reusable utility to extract NIRF ranking tables from local HTML files

    and export them to structured JSON format.
    """

    def __init__(self, course_name: str, year: int = 2025, project: str = "nirf"):
        self.course_name = course_name
        self.year = year
        self.project = project

        # Define headers to normalize the output JSON structure
        self.headers = [
            "Institute ID",
            "Name",
            "City",
            "State",
            "Score",
            "Rank",
        ]

    def _get_default_paths(self) -> tuple[Path, Path]:
        """Dynamically computes the default input and output file paths."""
        base_dir = Path(__file__).resolve().parent
        html_path = base_dir / f"{self.course_name}.html"

        # Using pathlib for cleaner, platform-independent path management
        assets_base = Path(f"C:/Ravi/Python/2025/Media/assets/{self.project}")
        json_path = (
            assets_base
            / "data"
            / f"{self.course_name}.json"
        )

        return html_path, json_path

    def extract(self, html_path: Path = None, json_path: Path = None) -> None:
        """Executes the HTML parsing and saves the extracted table to a JSON file."""
        # Fall back to defaults if custom paths are not provided
        default_html, default_json = self._get_default_paths()
        html_path = Path(html_path) if html_path else default_html
        json_path = Path(json_path) if json_path else default_json

        # 1. Read the local HTML file
        if not html_path.exists():
            print(f"Error: The file {html_path} does not exist.")
            return

        with open(html_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")

        # 2. Find the target table
        table = soup.find("table")
        if not table:
            print("Error: No table found in the HTML file.")
            return

        # 3. Extract Row Data
        data_list = []
        tbody = table.find("tbody")
        rows = (
            tbody.find_all("tr", recursive=False)
            if tbody
            else table.find_all("tr", recursive=False)
        )

        for row in rows:
            cells = row.find_all("td", recursive=False)
            if not cells or len(cells) < 6:
                continue

            # Target-extract just the raw text node for the Name column
            name_text = cells[1].find(text=True)
            name_value = (
                name_text.strip()
                if name_text
                else cells[1].get_text(strip=True)
            )

            row_data = {
                self.headers[0]: cells[0].get_text(strip=True),
                self.headers[1]: name_value,
                self.headers[2]: cells[2].get_text(strip=True),
                self.headers[3]: cells[3].get_text(strip=True),
                self.headers[4]: cells[4].get_text(strip=True),
                self.headers[5]: cells[5].get_text(strip=True),
            }

            data_list.append(row_data)

        # 4. Ensure target directory exists and save JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(data_list, json_file, indent=4, ensure_ascii=False)

        print(
            f"Successfully extracted {len(data_list)} records to {json_path}"
        )


# --- Example Usage ---
if __name__ == "__main__":
    coursename="SDGInstitutions"
    year=2025
    target_url=f"https://www.nirfindia.org/Rankings/{year}/{coursename}Ranking.html"
    BASE_DIR = Path(__file__).resolve().parent
    downloader = NIRFHtmlDownloader(
        course_name=coursename, 
        year=year,
        output_dir=BASE_DIR # Set your target structural directory here
    )
    saved_file_path = downloader.download_and_isolate_table(target_url) 
    extractor = NIRFTableExtractor(course_name=f"NIRF_{coursename}_{year}_Ranking", year=year)
    extractor.extract()