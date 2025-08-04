import json
import requests
from bs4 import BeautifulSoup

class NewsScanner:
    """
    Scrapes headlines from a list of news sources defined in a config file.
    """
    def __init__(self, sources_path: str):
        """
        Initializes the scanner with the path to the news sources JSON file.

        Args:
            sources_path: The file path to 'sources.json'.
        """
        self.sources = self._load_sources(sources_path)
        self.scrape_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _load_sources(self, path: str) -> dict:
        """Loads news sources from a JSON file."""
        print(f"Loading news sources from: {path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: The sources file was not found at '{path}'")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode the JSON from '{path}'")
            return {}

    def scan_headlines(self) -> dict:
        """
        Scans all configured sources and returns the headlines.

        Returns:
            A dictionary where keys are source names and values are lists of headlines.
        """
        all_headlines = {}
        failed_sources = []
        if not self.sources:
            print("No sources loaded, cannot scan for headlines.")
            return all_headlines

        for source_name, url in self.sources.items():
            print(f"--> Scanning {source_name}...")
            try:
                response = requests.get(url, headers=self.scrape_headers, timeout=15)
                response.raise_for_status()  # Checks for HTTP errors like 404 or 500

                soup = BeautifulSoup(response.content, 'html.parser')
                
                headlines = [
                    a.get_text(strip=True) for a in soup.find_all('a') 
                    if a.get_text() and len(a.get_text(strip=True)) > 40
                ]
                
                unique_headlines = list(dict.fromkeys(headlines))
                all_headlines[source_name] = unique_headlines[:10]
                print(f"    ...found {len(unique_headlines[:10])} headlines.")

            except requests.RequestException as e:
                print(f"    [FAILED] Could not fetch {url}. Error: {e}")
                failed_sources.append(source_name)
            except Exception as e:
                print(f"    [FAILED] An error occurred while parsing {source_name}: {e}")
                failed_sources.append(source_name)
        
        if failed_sources:
            print("\n--------------------------------------------------")
            print("WARNING: Some news sources could not be scraped.")
            print("This is common for sites with anti-scraping measures.")
            print("Failed sources:", ", ".join(failed_sources))
            print("Consider removing them from 'config/sources.json' for cleaner output.")
            print("--------------------------------------------------")

        return all_headlines
        