import json
import re

class AIAnalyzer:
    """
    (DEMO VERSION)
    Uses pre-canned responses from a JSON file instead of a live AI model.
    The 'prompts_path' now points to 'mock_ai_responses.json'.
    """
    def __init__(self, api_key: str, prompts_path: str, **kwargs):
        self.mock_responses = self._load_mock_responses(prompts_path)
        print("AI Analyzer initialized in DEMO mode.")

    def _load_mock_responses(self, path: str) -> dict:
        print(f"Loading mock AI responses from: {path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load mock AI responses file: {e}")
            return {}

    def identify_assets_from_headlines(self, headlines: list[str]) -> list[dict]:
        print("--> Retrieving mock asset identification...")
        assets = self.mock_responses.get("identify_assets", [])
        for asset in assets:
            catalyst = asset.get('catalyst', '')
            source_match = re.match(r'\[(.*?)\]', catalyst)
            if source_match:
                asset['source'] = source_match.group(1)
        return assets

    def get_ticker_details(self, ticker: str) -> dict:
        print(f"    ...getting mock enrichment details for '{ticker}'.")
        return self.mock_responses.get("enrich_ticker", {}).get(ticker, {})

    def get_detailed_scores(self, ticker: str, catalyst_headline: str) -> dict:
        print(f"    --> Performing mock detailed scoring for '{ticker}'...")
        return self.mock_responses.get("score_asset", {}).get(ticker, {})