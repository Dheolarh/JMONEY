import pandas as pd
import numpy as np
from .ai_analyzer import AIAnalyzer
import os

from dotenv import load_dotenv
load_dotenv()

class ScoringEngine:
    """
    Calculates various scores for a given asset based on its market data and catalyst.
    Uses simple technical analysis functions for better compatibility.
    """
    def __init__(self, analyzer=None):
        import os
        if analyzer:
            self.analyzer = analyzer
        else:
            # This block preserves the original logic for non-demo use,
            # but in the demo, the analyzer is always provided directly.
            testing_mode = os.getenv("TESTING_MODE", "false").lower() == "true"
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            openai_api_key = os.getenv("OPENAI_KEY")
            if testing_mode:
                if not gemini_api_key:
                    raise ValueError("TESTING_MODE is enabled but no GEMINI_API_KEY found for scoring engine")
                self.analyzer = AIAnalyzer(
                    api_key=gemini_api_key,
                    prompts_path=os.getenv("PROMPTS_PATH", "config/prompts.json"),
                    provider="gemini"
                )
            else:
                if openai_api_key:
                    self.analyzer = AIAnalyzer(
                        api_key=openai_api_key,
                        prompts_path=os.getenv("PROMPTS_PATH", "config/prompts.json"),
                        provider="openai"
                    )
                elif gemini_api_key:
                    self.analyzer = AIAnalyzer(
                        api_key=gemini_api_key,
                        prompts_path=os.getenv("PROMPTS_PATH", "config/prompts.json"),
                        provider="gemini"
                    )
                else:
                    raise ValueError("No AI API key found for scoring engine")

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def _calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return prices.rolling(window=period).mean()

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return {'upper': upper_band, 'middle': sma, 'lower': lower_band}

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    def calculate_technical_score(self, market_data: pd.DataFrame, ticker: str) -> int:
        """
        (DEMO-MODIFIED)
        Calculate a technical score that guarantees confirmation for our balanced portfolio.
        """
        # For any tickers that are part of our confirmed trades pool, assign a high score.
        if ticker in ["NVDA", "TSLA", "BTC", "PFE", "AMD", "XRP"]:
            return 8
        
        # For the original static tickers, provide varied scores.
        if ticker == "AAPL": return 8
        if ticker == "PFE": return 6
        if ticker == "SHOP": return 4
        if ticker == "GME": return 5
        return 5

    def calculate_zs10_score(self, market_data: pd.DataFrame, ticker: str) -> int:
        """
        (DEMO-MODIFIED)
        Calculate a ZS-10+ score that guarantees confirmation for our balanced portfolio.
        """
        # For any tickers that are part of our confirmed trades pool, assign a low-risk score.
        if ticker in ["NVDA", "TSLA", "BTC", "PFE", "AMD", "XRP"]:
            return 2
            
        # For the original static tickers, provide varied scores.
        if ticker == "GME": return 8 # High score for Avoid signal
        return 4

    def calculate_all_scores(self, enriched_assets: list[dict]) -> list[dict]:
        """Calculates all scores for a list of enriched assets."""
        scored_assets = []
        for asset in enriched_assets:
            print(f"--> Scoring asset: {asset.get('ticker')}")
            market_data = asset.get('market_data')

            asset['technical_score'] = self.calculate_technical_score(market_data, asset.get('ticker'))
            asset['zs10_score'] = self.calculate_zs10_score(market_data, asset.get('ticker'))

            ai_scores = self.analyzer.get_detailed_scores(
                ticker=asset.get('ticker'),
                catalyst_headline=asset.get('catalyst')
            )
            
            asset.update(ai_scores)
            scored_assets.append(asset)
        
        return scored_assets