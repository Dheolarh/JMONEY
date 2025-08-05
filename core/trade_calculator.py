import pandas as pd
import numpy as np

class TradeCalculator:
    """
    Calculates dynamic trade parameters like Stop Loss and Take Profit
    based on market volatility (ATR).
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

    def calculate_trade_parameters(self, market_data: pd.DataFrame, signal: str, confidence_score: float = 5.0) -> dict:
        """
        Calculates Entry, Stop Loss, and Take Profit levels.

        Args:
            market_data: A pandas DataFrame with OHLCV data.
            signal: The trading signal ('Buy', 'Sell', 'Neutral', 'Avoid', etc.).
            confidence_score: Signal confidence score (0-10) for dynamic strategy

        Returns:
            A dictionary with the calculated trade parameters and TP strategy.
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
            
            # Calculate dynamic TP strategy for all signals based on confidence
            tp_strategy = self._calculate_tp_strategy(confidence_score, risk_per_share, entry_price)
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
