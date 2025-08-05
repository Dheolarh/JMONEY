import os
import json
from openai import OpenAI

class AIAnalyzer:
    """
    Uses an AI model to analyze text content like news headlines.
    """
    def __init__(self, api_key: str, prompts_path: str):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=api_key)
        self.prompts = self._load_prompts(prompts_path)

    def _load_prompts(self, path: str) -> dict:
        print(f"Loading AI prompts from: {path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: The prompts file was not found at '{path}'")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode the JSON from '{path}'")
            return {}

    def _clean_ai_response(self, response_text: str) -> str:
        """Cleans the typical markdown formatting from AI JSON responses."""
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        return response_text.strip()

    def identify_assets_from_headlines(self, headlines: list[str]) -> list[dict]:
        if not self.prompts or "identify_assets" not in self.prompts:
            print("Error: 'identify_assets' prompt not found in config.")
            return []
        headlines_text = "\n".join(headlines)
        prompt_config = self.prompts["identify_assets"]
        final_prompt = prompt_config["user_prompt_template"].format(headlines=headlines_text)
        print("--> Sending headlines to AI for initial analysis...")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": prompt_config["system_message"]},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.1,
                max_tokens=2000   
            )
            response_text = self._clean_ai_response(response.choices[0].message.content)
            print("    ...initial analysis complete.")
            return json.loads(response_text)
        except Exception as e:
            print(f"    [FAILED] Error during initial AI analysis: {e}")
            return []

    def get_detailed_scores(self, ticker: str, catalyst_headline: str) -> dict:
        """
        Performs a detailed AI analysis on a single asset to get specific scores.

        Args:
            ticker: The asset's ticker symbol.
            catalyst_headline: The news headline related to the asset.

        Returns:
            A dictionary containing the macro_score, sentiment_score, and catalyst_type.
        """
        if not self.prompts or "score_asset" not in self.prompts:
            print("Error: 'score_asset' prompt not found in config.")
            return {}

        prompt_config = self.prompts["score_asset"]
        final_prompt = prompt_config["user_prompt_template"].format(
            ticker=ticker, 
            catalyst_headline=catalyst_headline
        )
        
        print(f"    --> Performing detailed AI scoring for '{ticker}'...")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_config["system_message"]},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.1,
                max_tokens=1500   
            )
            response_text = self._clean_ai_response(response.choices[0].message.content)
            print("        ...detailed scoring complete.")
            return json.loads(response_text)
        except Exception as e:
            print(f"        [FAILED] Error during detailed AI scoring: {e}")
            return {}
