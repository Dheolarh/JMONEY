import pandas as pd
import numpy as np
import os
import json
from openai import OpenAI
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv()

class TradeCalculator:
    """
    Calculates dynamic trade parameters like Stop Loss, Take Profit, and Position Size.
    """
    def __init__(self):
        """Initializes the TradeCalculator."""
        try:
            with open("config/trading_config.json", 'r') as f:
                self.trading_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.trading_config = {"account_balance": 10000, "risk_per_trade_pct": 1.5}
        
        self.ai_client = None # Simplified for brevity, AI TP strategy remains

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range."""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        return atr if not pd.isna(atr) else (close.iloc[-1] * 0.02)

    def calculate_trade_parameters(self, market_data: pd.DataFrame, signal: str, confidence_score: float) -> dict:
        """Calculates Entry, SL, TP, and Position Size for all signals."""
        params = {"entry": "N/A", "stop_loss": "N/A", "tp1": "N/A", "tp2": "N/A", "position_size": "N/A", "tp_strategy": "N/A"}
        if market_data is None or len(market_data) < 20: return params

        try:
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            entry_price = market_data[close_col].iloc[-1]
            atr = self._calculate_atr(market_data['High'], market_data['Low'], market_data['Close'])
            
            # Dynamic ATR multiplier based on confidence
            atr_multiplier = 1.5 + (confidence_score / 10.0) # Ranges from 1.5 to 2.5
            risk_per_share = atr * atr_multiplier
            
            decimals = 4 if entry_price < 10 else 2
            params["entry"] = round(entry_price, decimals)
            
            # Always calculate reference levels, even for Neutral signals
            stop_loss_long = entry_price - risk_per_share
            stop_loss_short = entry_price + risk_per_share

            tp1_rr = 1.0 + (confidence_score / 10.0) # Ranges from 1.0 to 2.0
            tp2_rr = 2.0 + (confidence_score / 5.0)  # Ranges from 2.0 to 4.0

            tp1_long = entry_price + (risk_per_share * tp1_rr)
            tp2_long = entry_price + (risk_per_share * tp2_rr)
            tp1_short = entry_price - (risk_per_share * tp1_rr)
            tp2_short = entry_price - (risk_per_share * tp2_rr)

            if signal == "Buy":
                tp1_pct = (tp1_long - entry_price) / entry_price * 100
                tp2_pct = (tp2_long - entry_price) / entry_price * 100
                params.update({
                    "stop_loss": round(stop_loss_long, decimals),
                    "tp1": f"{round(tp1_long, decimals)} ({tp1_pct:.1f}%)",
                    "tp2": f"{round(tp2_long, decimals)} ({tp2_pct:.1f}%)",
                    "position_size": self.calculate_position_size(entry_price, stop_loss_long)
                })
            elif signal == "Sell":
                tp1_pct = (entry_price - tp1_short) / entry_price * 100
                tp2_pct = (entry_price - tp2_short) / entry_price * 100
                params.update({
                    "stop_loss": round(stop_loss_short, decimals),
                    "tp1": f"{round(tp1_short, decimals)} ({tp1_pct:.1f}%)",
                    "tp2": f"{round(tp2_short, decimals)} ({tp2_pct:.1f}%)",
                    "position_size": self.calculate_position_size(entry_price, stop_loss_short)
                })
            else: # For "Hold", "Avoid", "Neutral"
                params.update({
                    "stop_loss": f"{round(stop_loss_long, decimals)} (ref)",
                    "tp1": f"{round(tp1_long, decimals)} (ref)",
                    "tp2": f"{round(tp2_long, decimals)} (ref)",
                    "position_size": "N/A" # No position for neutral
                })
            
            params["tp_strategy"] = self._get_tp_strategy(confidence_score, signal)

        except Exception as e:
            print(f"    [WARNING] Could not calculate trade parameters: {e}")

        return params
        
    def _get_tp_strategy(self, confidence_score: float, signal: str) -> str:
        """Determines the TP allocation strategy based on confidence."""
        if signal not in ["Buy", "Sell"]:
            return f"Monitor for signals (confidence: {confidence_score:.1f}/10)"

        if confidence_score >= 8.5: return "TP1 30% / TP2 70%"
        if confidence_score >= 7.5: return "TP1 50% / TP2 50%"
        if confidence_score >= 6.0: return "TP1 70% / TP2 30%"
        return "TP1 80% / TP2 20%"

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculates the position size based on risk parameters."""
        account_balance = self.trading_config.get("account_balance", 10000)
        risk_per_trade_pct = self.trading_config.get("risk_per_trade_pct", 1.5) / 100
        
        risk_amount_per_trade = account_balance * risk_per_trade_pct
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0: return 0.0
        
        position_size = risk_amount_per_trade / risk_per_share
        return round(position_size, 4)