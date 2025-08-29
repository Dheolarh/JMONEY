import pandas as pd
from .data_fetcher import DataFetcher
from .output_manager import OutputManager
from datetime import datetime, timedelta

class Backtester:
    """
    Backtests past trading signals to evaluate performance.
    """
    def __init__(self, output_manager: OutputManager):
        self.output_manager = output_manager
        self.data_fetcher = DataFetcher()

    def run_backtest(self, signals: list[dict], days_to_backtest: int = 7) -> dict:
        """
        Runs a backtest on a given list of signals.

        Args:
            signals: A list of signal dictionaries to backtest.
            days_to_backtest: The number of days of historical data to check for each signal.

        Returns:
            A dictionary with backtesting results.
        """
        print(f"--- Running Backtest on {len(signals)} signals ---")
        
        results = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_profit_loss": 0.0
        }

        for signal in signals:
            if signal.get('Signal') not in ['Buy', 'Sell']:
                continue

            ticker = signal.get('Ticker')
            entry_price = float(str(signal.get('Entry')).replace('$', ''))
            stop_loss = float(str(signal.get('Stop Loss')).replace('$', ''))
            take_profit = float(str(signal.get('TP1')).replace('$', ''))
            
            # Fetch historical data for the backtest period
            market_data = self.data_fetcher.get_data(ticker, asset_type='stocks') # Assuming stocks for simplicity
            
            if market_data is None or market_data.empty:
                continue

            # Simulate the trade
            outcome = self._simulate_trade(market_data, entry_price, stop_loss, take_profit, signal['Signal'])

            if outcome is not None:
                results["total_trades"] += 1
                if outcome > 0:
                    results["wins"] += 1
                else:
                    results["losses"] += 1
                results["total_profit_loss"] += outcome
        
        if results["total_trades"] > 0:
            results["win_rate"] = (results["wins"] / results["total_trades"]) * 100

        print("--- Backtest Complete ---")
        return results

    def _simulate_trade(self, market_data: pd.DataFrame, entry: float, sl: float, tp: float, signal: str) -> float | None:
        """
        Simulates a single trade against historical data.
        Returns the profit/loss percentage, or None if the trade is still open.
        """
        for index, row in market_data.iterrows():
            if signal == 'Buy':
                if row['Low'] <= sl:
                    return -abs((entry - sl) / entry) * 100  # Loss
                if row['High'] >= tp:
                    return abs((tp - entry) / entry) * 100  # Win
            elif signal == 'Sell':
                if row['High'] >= sl:
                    return -abs((sl - entry) / entry) * 100  # Loss
                if row['Low'] <= tp:
                    return abs((entry - tp) / entry) * 100  # Win
        return None 