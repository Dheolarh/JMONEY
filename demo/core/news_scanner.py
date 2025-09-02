import json

class NewsScanner:
    """
    (DEMO VERSION)
    Scrapes headlines from a local mock data file instead of live websites.
    """
    def __init__(self, sources_path: str):
        """
        Initializes the scanner with the path to the mock headlines JSON file.
        """
        self.sources_path = sources_path

    def _load_sources(self) -> dict:
        """Loads mock news sources from a JSON file."""
        print(f"Loading mock news sources from: {self.sources_path}")
        try:
            with open(self.sources_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load mock headlines file: {e}")
            return {}

    def scan_headlines(self) -> dict:
        """
        Scans the mock source file and returns the headlines.
        """
        all_headlines = self._load_sources()
        if not all_headlines:
            print("No mock headlines loaded.")
        return all_headlines