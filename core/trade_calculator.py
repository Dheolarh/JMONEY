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

    def calculate_trade_parameters(self, market_data: pd.DataFrame, signal: str) -> dict:
        """
        Calculates Entry, Stop Loss, and Take Profit levels.

        Args:
            market_data: A pandas DataFrame with OHLCV data.
            signal: The trading signal ('Buy', 'Sell', 'Avoid', etc.).

        Returns:
            A dictionary with the calculated trade parameters.
        """
        params = {"entry": "N/A", "stop_loss": "N/A", "tp1": "N/A", "tp2": "N/A"}

        if signal not in ["Buy", "Sell"] or market_data is None or len(market_data) < 20:
            return params # Not enough data or no valid signal

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
            
            # Use the latest closing price as the entry point
            entry_price = market_data[close_col].iloc[-1]
            
            risk_per_share = atr * self.atr_multiplier

            if signal == "Buy":
                stop_loss = entry_price - risk_per_share
                tp1 = entry_price + (risk_per_share * self.tp1_rr)
                tp2 = entry_price + (risk_per_share * self.tp2_rr)
            elif signal == "Sell":
                stop_loss = entry_price + risk_per_share
                tp1 = entry_price - (risk_per_share * self.tp1_rr)
                tp2 = entry_price - (risk_per_share * self.tp2_rr)

            # Format to a reasonable number of decimal places
            decimals = 4 if entry_price < 10 else 2
            params = {
                "entry": round(entry_price, decimals),
                "stop_loss": round(stop_loss, decimals),
                "tp1": round(tp1, decimals),
                "tp2": round(tp2, decimals)
            }
        
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
