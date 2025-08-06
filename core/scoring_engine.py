import pandas as pd
import numpy as np
from .ai_analyzer import AIAnalyzer
import os

class ScoringEngine:
    """
    Calculates various scores for a given asset based on its market data and catalyst.
    Uses simple technical analysis functions for better compatibility.
    """
    def __init__(self, analyzer=None):
        """Initializes the ScoringEngine. Accepts an existing AIAnalyzer or creates one."""
        if analyzer:
            self.analyzer = analyzer
        else:
            # Fallback: try OpenAI first, then Gemini
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            openai_api_key = os.getenv("OPENAI_KEY")
            
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

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    def calculate_technical_score(self, market_data: pd.DataFrame) -> int:
        """
        Calculate technical score using indicators.
        """
        if market_data is None or len(market_data) < 50:
            print("    ...insufficient data for technical analysis")
            return 0
        
        try:
            score = 5  # Base score
            
            # Determine correct column name for close prices
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            close_prices = market_data[close_col]
            
            # RSI Analysis
            rsi = self._calculate_rsi(close_prices)
            current_rsi = rsi.iloc[-1]
            
            if not pd.isna(current_rsi):
                if current_rsi > 70:  # Overbought
                    score -= 2
                elif current_rsi < 30:  # Oversold
                    score += 2
                elif 40 <= current_rsi <= 60:  # Neutral zone
                    score += 1
            
            # MACD Analysis
            macd_data = self._calculate_macd(close_prices)
            if not pd.isna(macd_data['macd'].iloc[-1]) and not pd.isna(macd_data['signal'].iloc[-1]):
                if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1]:  # Bullish
                    score += 1.5
                else:  # Bearish
                    score -= 1.5
            
            # Moving Average Analysis
            if len(close_prices) >= 200:
                ma_50 = self._calculate_sma(close_prices, 50).iloc[-1]
                ma_200 = self._calculate_sma(close_prices, 200).iloc[-1]
                
                if not pd.isna(ma_50) and not pd.isna(ma_200):
                    if ma_50 > ma_200:  # Bullish trend
                        score += 1.5
                    else:  # Bearish trend
                        score -= 1.5
            
            # Price momentum (last 5 periods)
            if len(close_prices) >= 5:
                recent_change = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5]
                if recent_change > 0.02:  # 2% gain
                    score += 1
                elif recent_change < -0.02:  # 2% loss
                    score -= 1
            
            final_score = max(0, min(10, round(score)))
            print(f"    ...calculated Technical Score: {final_score}/10")
            return final_score
            
        except Exception as e:
            print(f"    ...error calculating technical score: {e}")
            return 5  # Return neutral score on error

    def calculate_zs10_score(self, market_data: pd.DataFrame) -> int:
        """
        Calculate ZS-10+ score for trap detection.
        Enhanced implementation with better volume/price divergence analysis.
        """
        if market_data is None or len(market_data) < 20:
            print("    ...insufficient data for ZS-10+ analysis")
            return 5
        
        try:
            # Find volume and close columns (handle different naming conventions)
            volume_col = None
            close_col = None
            
            for col in market_data.columns:
                if col.lower() in ['volume', 'vol']:
                    volume_col = col
                if col.lower() in ['close', 'close_price', 'adj close']:
                    close_col = col
            
            if not close_col:
                close_col = market_data.columns[-1] # Fallback to last column if no close found
            
            close_prices = market_data[close_col]
            
            if volume_col and volume_col in market_data.columns:
                volume = market_data[volume_col]
                
                # Enhanced volume analysis
                recent_volume_avg = volume.tail(5).mean()
                historical_volume_avg = volume.tail(20).mean()
                volume_ratio = recent_volume_avg / historical_volume_avg if historical_volume_avg > 0 else 1
                
                # Price momentum analysis
                recent_price_change = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5]
                
                # More nuanced scoring
                if volume_ratio < 0.6 and recent_price_change > 0.03:
                    score = 8  # High trap risk - price up, volume down significantly
                elif volume_ratio < 0.8 and recent_price_change > 0.02:
                    score = 6  # Medium-high trap risk
                elif volume_ratio > 1.5 and recent_price_change > 0.01:
                    score = 2  # Low trap risk - good volume confirmation
                elif volume_ratio > 1.2 and recent_price_change > 0:
                    score = 3  # Low-medium trap risk
                elif abs(recent_price_change) < 0.01:
                    score = 4  # Neutral - sideways movement
                else:
                    score = 5  # Default moderate risk
                    
                print(f"    ...calculated ZS-10+ Score: {score}/10 (Volume ratio: {volume_ratio:.2f}, Price change: {recent_price_change:.3f})")
            else:
                # Price-only analysis when volume not available
                price_volatility = close_prices.tail(10).std() / close_prices.tail(10).mean()
                recent_price_change = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5]
                
                if price_volatility > 0.05 and abs(recent_price_change) > 0.03:
                    score = 7  # High volatility suggests potential trap
                elif price_volatility < 0.02:
                    score = 3  # Low volatility suggests stability
                else:
                    score = 5  # Moderate volatility
                    
                print(f"    ...calculated ZS-10+ Score: {score}/10 (Price-only analysis, volatility: {price_volatility:.3f})")
            
            return score
            
        except Exception as e:
            print(f"    ...error calculating ZS-10+ score: {e}")
            return 5

    def calculate_all_scores(self, enriched_assets: list[dict]) -> list[dict]:
        """
        Calculates all scores for a list of enriched assets, now including AI scores.
        """
        scored_assets = []
        for asset in enriched_assets:
            print(f"--> Scoring asset: {asset.get('ticker')}")
            market_data = asset.get('market_data')

            # --- Technical Score Calculations ---
            asset['technical_score'] = self.calculate_technical_score(market_data)
            asset['zs10_score'] = self.calculate_zs10_score(market_data)

            # --- AI-based Score Calculations ---
            ai_scores = self.analyzer.get_detailed_scores(
                ticker=asset.get('ticker'),
                catalyst_headline=asset.get('catalyst')
            )
            
            # Update the asset with the new, real scores from the AI
            asset['macro_score'] = ai_scores.get('macro_score', 5) # Default to 5 if AI fails
            asset['sentiment_score'] = ai_scores.get('sentiment_score', 5)
            asset['catalyst_type'] = ai_scores.get('catalyst_type', 'None')
            
            scored_assets.append(asset)
        
        return scored_assets
