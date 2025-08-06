import pandas as pd
import numpy as np
import os
import json
from openai import OpenAI
import google.generativeai as genai

class TradeCalculator:
    """
    Calculates dynamic trade parameters like Stop Loss and Take Profit
    based on market volatility (ATR) with AI-driven TP strategy optimization.
    """
    def __init__(self, atr_multiplier: float = 2.0, tp1_rr: float = 2.0, tp2_rr: float = 4.0):
        """
        Initializes the TradeCalculator.

        Args:
            atr_multiplier: The multiplier for ATR to set the Stop Loss distance.
            tp1_rr: The Reward/Risk ratio for the first Take Profit level.
            tp2_rr: The Reward/Risk ratio for the second Take Profit level.
        """
        self.atr_multiplier = atr_multiplier
        self.tp1_rr = tp1_rr
        self.tp2_rr = tp2_rr
        
        # Initialize AI client for dynamic TP strategy - try OpenAI first
        self.ai_enabled = False
        self.ai_provider = None
        self.ai_client = None
        
        try:
            openai_api_key = os.environ.get("OPENAI_KEY")
            if openai_api_key:
                self.ai_client = OpenAI(api_key=openai_api_key)
                self.ai_provider = "openai"
                self.ai_enabled = True
                print("    AI-driven TP strategy enabled with OpenAI")
            else:
                # Fallback to Gemini
                gemini_api_key = os.environ.get("GEMINI_API_KEY")
                if gemini_api_key:
                    genai.configure(api_key=gemini_api_key)
                    self.ai_client = genai.GenerativeModel("gemini-1.5-flash") 
                    self.ai_provider = "gemini"
                    self.ai_enabled = True
                    print("    AI-driven TP strategy enabled with Gemini")
                else:
                    self.ai_client = None
                    self.ai_enabled = False
                    print("    No AI API key available, using fallback TP strategy")
        except Exception as e:
            print(f"    AI initialization failed: {e}")
            self.ai_client = None
            self.ai_enabled = False

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range."""
        try:
            high_low = high - low
            high_close = np.abs(high - close.shift())
            low_close = np.abs(low - close.shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            return atr if not pd.isna(atr) else 0.0
        except Exception as e:
            print(f"    Error calculating ATR: {e}")
            return 0.0

    def calculate_trade_parameters(self, market_data: pd.DataFrame, signal: str, confidence_score: float = 5.0, 
                                 ticker: str = "UNKNOWN", catalyst: str = "", scores: dict = None) -> dict:
        """
        Calculates Entry, Stop Loss, and Take Profit levels with AI-driven TP strategy.

        Args:
            market_data: A pandas DataFrame with OHLCV data.
            signal: The trading signal ('Buy', 'Sell', 'Neutral', 'Avoid', etc.).
            confidence_score: Signal confidence score (0-10) for dynamic strategy
            ticker: Asset ticker symbol for AI context
            catalyst: News catalyst for AI analysis
            scores: Dictionary containing technical, macro, zs10, sentiment scores

        Returns:
            A dictionary with the calculated trade parameters and AI-optimized TP strategy.
        """
        params = {
            "entry": "N/A", 
            "stop_loss": "N/A", 
            "tp1": "N/A", 
            "tp2": "N/A",
            "tp_strategy": "Manual exit required"
        }

        if market_data is None or len(market_data) < 20:
            return params # Not enough data

        try:
            high_col = 'High' if 'High' in market_data.columns else 'high'
            low_col = 'Low' if 'Low' in market_data.columns else 'low'
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            
            # Calculate ATR (Average True Range) for volatility
            atr = self._calculate_atr(
                market_data[high_col], 
                market_data[low_col], 
                market_data[close_col],
                period=14
            )
            
            if atr == 0:
                print("    [WARNING] ATR calculation failed, using 2% of price as fallback")
                entry_price = market_data[close_col].iloc[-1]
                atr = entry_price * 0.02  # 2% fallback
            
            # Use the latest closing price as the entry point (reference for all signals)
            entry_price = market_data[close_col].iloc[-1]
            risk_per_share = atr * self.atr_multiplier
            
            # Format to a reasonable number of decimal places
            decimals = 4 if entry_price < 10 else 2
            
            # Always show entry price as reference
            params["entry"] = round(entry_price, decimals)
            
            # For actionable signals (Buy/Sell), calculate full trade parameters
            if signal in ["Buy", "Sell"]:
                if signal == "Buy":
                    stop_loss = entry_price - risk_per_share
                    tp1 = entry_price + (risk_per_share * self.tp1_rr)
                    tp2 = entry_price + (risk_per_share * self.tp2_rr)
                elif signal == "Sell":
                    stop_loss = entry_price + risk_per_share
                    tp1 = entry_price - (risk_per_share * self.tp1_rr)
                    tp2 = entry_price - (risk_per_share * self.tp2_rr)
                
                params.update({
                    "stop_loss": round(stop_loss, decimals),
                    "tp1": round(tp1, decimals),
                    "tp2": round(tp2, decimals)
                })
            
            else:
                # Calculate hypothetical Buy levels for reference
                hypothetical_stop_loss = entry_price - risk_per_share
                hypothetical_tp1 = entry_price + (risk_per_share * self.tp1_rr)
                hypothetical_tp2 = entry_price + (risk_per_share * self.tp2_rr)
                
                params.update({
                    "stop_loss": f"${round(hypothetical_stop_loss, decimals)} (ref)",
                    "tp1": f"${round(hypothetical_tp1, decimals)} (ref)",
                    "tp2": f"${round(hypothetical_tp2, decimals)} (ref)"
                })
            
            # Calculate AI-driven TP strategy for all signals
            market_context = self._prepare_market_context(market_data, ticker, catalyst, confidence_score, scores or {})
            tp_strategy = self._calculate_ai_tp_strategy(market_context, confidence_score, risk_per_share, entry_price)
            params["tp_strategy"] = tp_strategy
        
        except Exception as e:
            print(f"    [WARNING] Could not calculate trade parameters: {e}")

        return params

    def _calculate_atr(self, high, low, close, period=14):
        """
        Calculate Average True Range (ATR) for volatility measurement.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            period: Look-back period for ATR calculation
            
        Returns:
            Current ATR value (float)
        """
        try:
            if len(high) < period or len(low) < period or len(close) < period:
                return 0
                
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            # True Range is the maximum of the three
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR is the simple moving average of True Range
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return atr if not pd.isna(atr) else 0
            
        except Exception as e:
            print(f"    [WARNING] ATR calculation failed: {e}")
            return 0

    def _prepare_market_context(self, market_data: pd.DataFrame, ticker: str, catalyst: str, 
                              confidence_score: float, scores: dict) -> dict:
        """
        Prepare comprehensive market context for AI analysis.
        
        Args:
            market_data: OHLCV market data
            ticker: Asset ticker symbol
            catalyst: News catalyst
            confidence_score: Overall confidence score
            scores: Dictionary of technical, macro, zs10, sentiment scores
            
        Returns:
            Dictionary with market context for AI analysis
        """
        try:
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            volume_col = 'Volume' if 'Volume' in market_data.columns else 'volume'
            
            # Recent price performance
            recent_prices = market_data[close_col].tail(10)
            price_change_5d = ((recent_prices.iloc[-1] - recent_prices.iloc[-5]) / recent_prices.iloc[-5]) * 100
            price_change_1d = ((recent_prices.iloc[-1] - recent_prices.iloc[-2]) / recent_prices.iloc[-2]) * 100
            
            # Volatility analysis
            price_returns = recent_prices.pct_change().dropna()
            volatility = price_returns.std() * 100
            
            # Volume analysis (if available)
            volume_trend = "unknown"
            if volume_col in market_data.columns:
                recent_volume = market_data[volume_col].tail(10)
                avg_volume = recent_volume.mean()
                latest_volume = recent_volume.iloc[-1]
                volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
                
                if volume_ratio > 1.5:
                    volume_trend = "high"
                elif volume_ratio < 0.7:
                    volume_trend = "low"
                else:
                    volume_trend = "normal"
            
            # Determine asset type for context
            asset_type = "stock"
            if "USD" in ticker or "/" in ticker:
                asset_type = "forex"
            elif "BTC" in ticker or "ETH" in ticker or ticker.endswith("USDT"):
                asset_type = "crypto"
            elif ticker.startswith("^"):
                asset_type = "index"
            
            return {
                "ticker": ticker,
                "asset_type": asset_type,
                "catalyst": catalyst,
                "confidence_score": confidence_score,
                "technical_score": scores.get("technical", 5),
                "macro_score": scores.get("macro", 5),
                "zs10_score": scores.get("zs10", 5),
                "sentiment_score": scores.get("sentiment", 5),
                "price_change_1d": round(price_change_1d, 2),
                "price_change_5d": round(price_change_5d, 2),
                "volatility": round(volatility, 2),
                "volume_trend": volume_trend,
                "current_price": round(recent_prices.iloc[-1], 4)
            }
            
        except Exception as e:
            print(f"    [WARNING] Error preparing market context: {e}")
            return {
                "ticker": ticker,
                "asset_type": "unknown",
                "catalyst": catalyst,
                "confidence_score": confidence_score,
                "technical_score": 5,
                "macro_score": 5,
                "zs10_score": 5,
                "sentiment_score": 5,
                "price_change_1d": 0,
                "price_change_5d": 0,
                "volatility": 2,
                "volume_trend": "unknown",
                "current_price": 100
            }

    def _calculate_ai_tp_strategy(self, market_context: dict, confidence_score: float, 
                                risk_amount: float, entry_price: float) -> str:
        """
        Use AI to calculate dynamic TP strategy based on comprehensive market analysis.
        
        Args:
            market_context: Comprehensive market data and context
            confidence_score: Signal confidence (0-10)
            risk_amount: Risk per share (ATR-based)
            entry_price: Entry price
            
        Returns:
            AI-optimized TP strategy string
        """
        if not self.ai_enabled:
            return self._calculate_tp_strategy_fallback(confidence_score, risk_amount, entry_price)
        
        try:
            risk_percentage = (risk_amount / entry_price) * 100
            
            signal_strength = "Strong" if confidence_score >= 7 else "Moderate" if confidence_score >= 5 else "Weak"
            volatility_regime = "High" if market_context.get('volatility', 0) > 3 else "Medium" if market_context.get('volatility', 0) > 1.5 else "Low"
            momentum_direction = "Bullish" if market_context.get('price_change_1d', 0) > 0 else "Bearish"
            
            prompt = f"""
You are an expert quantitative trader specializing in adaptive profit-taking strategies. Each trade requires a unique approach based on comprehensive market analysis.

ASSET PROFILE:
- Symbol: {market_context['ticker']} ({market_context['asset_type']})
- Entry Price: ${market_context['current_price']}
- Signal Strength: {signal_strength} ({confidence_score}/10)
- Market Regime: {volatility_regime} Volatility, {momentum_direction} Momentum

CATALYST ANALYSIS:
- News Event: {market_context['catalyst']}
- Catalyst Type: {market_context.get('catalyst_type', 'Unknown')}
- Timing: Recent development requiring adaptive response

MARKET DYNAMICS:
- Recent Performance: {market_context['price_change_1d']}% (1D), {market_context['price_change_5d']}% (5D)
- Volatility Environment: {market_context['volatility']}% (Current ATR-based)
- Volume Pattern: {market_context['volume_trend']}
- Risk Exposure: ${round(risk_amount, 4)} ({round(risk_percentage, 2)}% of entry)

MULTI-FACTOR SCORING:
- Technical Setup: {market_context['technical_score']}/10
- Macro Environment: {market_context['macro_score']}/10  
- Sentiment Reading: {market_context['sentiment_score']}/10
- Trap Risk Assessment: {market_context['zs10_score']}/10

STRATEGY OPTIMIZATION FACTORS:
- Analyze all provided data points to determine optimal profit-taking allocation
- Consider volatility patterns and their impact on holding periods
- Evaluate catalyst strength and market sentiment for risk/reward balance
- Factor in asset class characteristics and typical behavior patterns
- Assess volume trends and momentum sustainability
- Balance trap risk against potential upside based on technical setup

IMPORTANT: Analyze the complete data set and determine the optimal TP1/TP2 allocation. 
Do NOT use preset ranges or generic splits. Base your decision entirely on the provided market data.
Use precise decimal percentages that reflect your analytical conclusions.

Respond with ONLY: "TP1 X.X% / TP2 Y.Y%" where X.X+Y.Y=100.0
"""

            # Make AI call based on provider
            if self.ai_provider == "openai":
                response = self.ai_client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[
                        {"role": "system", "content": "You are a quantitative trading expert focused on optimal profit-taking strategies. Provide concise, data-driven recommendations."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.9, 
                    max_tokens=50     
                )
                ai_strategy = response.choices[0].message.content.strip()
                
            elif self.ai_provider == "gemini":
                full_prompt = "You are a quantitative trading expert focused on optimal profit-taking strategies. Provide concise, data-driven recommendations.\n\n" + prompt
                response = self.ai_client.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.9,
                        max_output_tokens=50
                    )
                )
                ai_strategy = response.text.strip()
                
            else:
                raise ValueError(f"Unknown AI provider: {self.ai_provider}")
            
            # Validate AI response format and percentages
            if "TP1" in ai_strategy and "TP2" in ai_strategy and "%" in ai_strategy:
                try:
                    import re
                    percentages = re.findall(r'(\d+(?:\.\d+)?)%', ai_strategy)
                    if len(percentages) == 2:
                        tp1_pct = float(percentages[0])
                        tp2_pct = float(percentages[1])
                        total = tp1_pct + tp2_pct
                        if 99.5 <= total <= 100.5 and 5.0 <= tp1_pct <= 95.0:
                            print(f"    🤖 AI TP Strategy: {ai_strategy}")
                            return ai_strategy
                        else:
                            if not (99.5 <= total <= 100.5):
                                print(f"    [WARNING] AI percentages don't add to 100 ({total}%), using fallback")
                            else:
                                print(f"    [WARNING] AI TP1 percentage out of reasonable range ({tp1_pct}%), using fallback")
                    else:
                        print(f"    [WARNING] Could not parse percentages from: {ai_strategy}, using fallback")
                except Exception as parse_error:
                    print(f"    [WARNING] Error parsing AI response: {parse_error}, using fallback")
                
                return self._calculate_tp_strategy_fallback(confidence_score, risk_amount, entry_price)
            else:
                print(f"    [WARNING] Invalid AI response format: {ai_strategy}, using fallback")
                return self._calculate_tp_strategy_fallback(confidence_score, risk_amount, entry_price)
                
        except Exception as e:
            print(f"    [WARNING] AI TP strategy failed: {e}, using fallback")
            return self._calculate_tp_strategy_fallback(confidence_score, risk_amount, entry_price)

    def _calculate_tp_strategy_fallback(self, confidence_score: float, risk_amount: float, entry_price: float) -> str:
        """
        Fallback TP strategy calculation when AI is unavailable - data-driven approach.
        """
        import random
        
        try:
            risk_percentage = (risk_amount / entry_price) * 100
            
            # Base calculation on actual risk and confidence data
            # Higher confidence = willing to hold longer (lower TP1)
            # Higher risk = take profits sooner (higher TP1)
            
            confidence_factor = (10 - confidence_score) / 10  # 0-1, higher when confidence is lower
            risk_factor = min(risk_percentage / 5.0, 1.0)     # 0-1, higher when risk is higher
            
            # Calculate base TP1 from data
            base_tp1 = 30 + (confidence_factor * 40) + (risk_factor * 20)
            
            random_offset = random.uniform(-8.0, 8.0)
            tp1 = base_tp1 + random_offset
            
            tp1 = max(10.0, min(90.0, tp1))
            tp1 = round(tp1, 1)
            tp2 = round(100.0 - tp1, 1)
            
            return f"TP1 {tp1}% / TP2 {tp2}%"
                
        except Exception:
            # True random fallback
            random_tp1 = round(random.uniform(15.0, 85.0), 1)
            random_tp2 = round(100.0 - random_tp1, 1)
            return f"TP1 {random_tp1}% / TP2 {random_tp2}%"

    def _calculate_tp_strategy(self, confidence_score: float, risk_amount: float, entry_price: float) -> str:
        """
        Calculate dynamic TP strategy based on confidence score and risk-reward metrics.
        
        Args:
            confidence_score: Signal confidence (0-10)
            risk_amount: Risk per share (ATR-based)
            entry_price: Entry price
            
        Returns:
            Dynamic TP strategy string
        """
        try:
            # Calculate risk percentage relative to entry price
            risk_percentage = (risk_amount / entry_price) * 100
            
            # Dynamic strategy based on confidence and risk
            if confidence_score >= 8.5:
                # Very high confidence (aggressive)
                if risk_percentage < 3:  # Low risk
                    return "TP1 30% / TP2 70%" 
                else:  # Higher risk
                    return "TP1 40% / TP2 60%"
                    
            elif confidence_score >= 7.5:
                # High confidence (balanced approach)
                if risk_percentage < 2:  # Very low risk
                    return "TP1 40% / TP2 60%"
                else:
                    return "TP1 50% / TP2 50%"
                    
            elif confidence_score >= 6.0:
                # Medium confidence (conservative)
                if risk_percentage < 2:
                    return "TP1 60% / TP2 40%"
                else:
                    return "TP1 70% / TP2 30%"
                    
            else:
                # Lower confidence (very conservative)
                return "TP1 80% / TP2 20%"
                
        except Exception:
            if confidence_score > 7.5:
                return "TP1 50% / TP2 50%"
            elif confidence_score > 6.0:
                return "TP1 70% / TP2 30%"
            else:
                return "TP1 100%"
