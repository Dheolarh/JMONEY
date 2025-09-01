import os
import json
from openai import OpenAI
import google.generativeai as genai
from typing import Optional
import re

from dotenv import load_dotenv
load_dotenv()

class AIAnalyzer:
    """
    Uses an AI model to analyze text content like news headlines.
    Supports both OpenAI and Google Gemini models.
    """
    def __init__(self, api_key: str, prompts_path: str, provider: str = "openai", model_name: str = None):
        import os
        testing_mode = os.getenv("TESTING_MODE", "false").lower() == "true"
        self.prompts = self._load_prompts(prompts_path)
        self.asset_type_cache = {} # Add this line
        if testing_mode:
            if not api_key:
                raise ValueError("Gemini API key is required.")
            self.provider = "gemini"
            genai.configure(api_key=api_key)
            self.model_name = model_name or "gemini-1.5-flash"
            self.client = genai.GenerativeModel(self.model_name)
        else:
            self.provider = provider.lower()
            if self.provider == "openai":
                if not api_key:
                    raise ValueError("OpenAI API key is required.")
                self.client = OpenAI(api_key=api_key)
                self.model_name = model_name or "gpt-4o-mini"
            elif self.provider == "gemini":
                if not api_key:
                    raise ValueError("Gemini API key is required.")
                genai.configure(api_key=api_key)
                self.model_name = model_name or "gemini-1.5-flash"
                self.client = genai.GenerativeModel(self.model_name)
            else:
                raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'gemini'")
        print(f"AI Analyzer initialized with {self.provider.upper()} ({self.model_name})")

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
        """Cleans and extracts JSON from AI responses, handling extra content."""
        import re
        
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
        
        json_pattern = r'\{.*\}|\[.*\]'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            return json_match.group(0).strip()
        
        return response_text.strip()
    
    def _call_ai_provider(self, system_message: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Unified method to call either OpenAI or Gemini"""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=max_tokens   
            )
            return response.choices[0].message.content
        
        elif self.provider == "gemini":
            full_prompt = f"{system_message}\n\n{user_prompt}"
            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=max_tokens
                )
            )
            return response.text
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def identify_assets_from_headlines(self, headlines: list[str]) -> list[dict]:
        if not self.prompts or "identify_assets" not in self.prompts:
            print("Error: 'identify_assets' prompt not found in config.")
            return []
        headlines_text = "\n".join(headlines)
        prompt_config = self.prompts["identify_assets"]
        final_prompt = prompt_config["user_prompt_template"].format(headlines=headlines_text)
        print(f"--> Sending headlines to {self.provider.upper()} for initial analysis...")
        try:
            response_text = self._call_ai_provider(
                prompt_config["system_message"],
                final_prompt,
                max_tokens=2000
            )
            response_text = self._clean_ai_response(response_text)
            print("    ...initial analysis complete.")
            
            assets = json.loads(response_text)
            for asset in assets:
                catalyst = asset.get('catalyst', '')
                source_match = re.match(r'\[(.*?)\]', catalyst)
                if source_match:
                    asset['source'] = source_match.group(1)
            return assets
            
        except Exception as e:
            print(f"    [FAILED] Error during initial AI analysis: {e}")
            return []

    def get_ticker_details(self, ticker: str) -> dict:
        """
        Uses AI to determine the asset type and correct ticker format.
        """
        if not self.prompts or "enrich_ticker" not in self.prompts:
            print("Error: 'enrich_ticker' prompt not found in config.")
            return {}
            
        prompt_config = self.prompts["enrich_ticker"]
        final_prompt = prompt_config["user_prompt_template"].format(ticker=ticker)
        
        try:
            response_text = self._call_ai_provider(
                prompt_config["system_message"],
                final_prompt,
                max_tokens=100
            )
            response_text = self._clean_ai_response(response_text)
            return json.loads(response_text)
        except Exception as e:
            print(f"    [FAILED] AI enrichment failed for '{ticker}': {e}")
            return {}

    def get_detailed_scores(self, ticker: str, catalyst_headline: str) -> dict:
        """
        Performs a detailed AI analysis on a single asset to get specific scores.
        """
        if not self.prompts or "score_asset" not in self.prompts:
            print("Error: 'score_asset' prompt not found in config.")
            return {}

        prompt_config = self.prompts["score_asset"]
        final_prompt = prompt_config["user_prompt_template"].format(
            ticker=ticker, 
            catalyst_headline=catalyst_headline
        )
        
        print(f"    --> Performing detailed {self.provider.upper()} scoring for '{ticker}'...")
        try:
            response_text = self._call_ai_provider(
                prompt_config["system_message"],
                final_prompt,
                max_tokens=1500
            )
            response_text = self._clean_ai_response(response_text)
            print("        ...detailed scoring complete.")
            return json.loads(response_text)
        except Exception as e:
            print(f"        [FAILED] Error during detailed AI scoring: {e}")
            return {}

    def get_asset_type(self, ticker: str) -> Optional[str]:
        """
        Uses AI to determine the asset type of a ticker, with caching.
        """
        if ticker in self.asset_type_cache:
            return self.asset_type_cache[ticker]

        if not self.prompts or "get_asset_type" not in self.prompts:
            print("Error: 'get_asset_type' prompt not found in config.")
            return None
            
        prompt_config = self.prompts["get_asset_type"]
        final_prompt = prompt_config["user_prompt_template"].format(ticker=ticker)
        
        try:
            response_text = self._call_ai_provider(
                prompt_config["system_message"],
                final_prompt,
                max_tokens=20
            )
            asset_type = response_text.strip().lower()
            
            # Cache the result
            self.asset_type_cache[ticker] = asset_type
            return asset_type
        except Exception as e:
            print(f"    [FAILED] AI asset type detection failed for '{ticker}': {e}")
            return None