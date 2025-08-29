from unittest import signals
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
        results = []
        skipped = 0
        processed = 0
    
        for signal in signals:
            ticker = signal.get('Ticker') or signal.get('ticker')
            data = self.data_fetcher.get_data(ticker)
            if data is None or data.empty:
                skipped += 1
                continue
    
            processed += 1
    
            entry_price = signal.get('Entry') or signal.get('entry_price')
            sl = signal.get('Stop Loss') or signal.get('stop_loss')
            tp = signal.get('TP1') or signal.get('take_profit')
            direction = signal.get('Signal') or signal.get('Direction') or signal.get('signal')

            print(f"Signal: {ticker}, Entry: {entry_price}, SL: {sl}, TP: {tp}, Dir: {direction}")

            if not all([ticker, entry_price, sl, tp, direction]):
                skipped += 1
                continue

            data = self.data_fetcher.get_data(ticker)
            if data is None or data.empty:
                skipped += 1
                continue

            processed += 1

            try:
                entry_price = float(entry_price)
                sl = float(sl)
                tp = float(tp)
            except (TypeError, ValueError):
                skipped += 1
                continue
    
            trade_result = self._simulate_trade(data, entry_price, sl, tp, direction)
            if trade_result is not None:
                results.append(trade_result)
    
        win_count = sum(1 for r in results if r == 1)
        total = len(results)
        win_rate = (win_count / total * 100) if total > 0 else 0
    
        print(f"Backtest: Skipped {skipped} unsupported tickers or invalid signals, processed {processed} signals, {total} trades evaluated.")
    
        return {
            "win_rate": win_rate,
            "total_trades": total,
            "wins": win_count,
            "losses": total - win_count,
            "skipped": skipped
        }

    def _simulate_trade(self, market_data: pd.DataFrame, entry: float, sl: float, tp: float, signal: str) -> float | None:
        """
        Simulates a single trade against historical data.
        Returns the profit/loss percentage, or the mark-to-market P/L if trade is still open at the end.
        """
        signal = signal.lower()
        for index, row in market_data.iterrows():
            if signal == 'buy':
                if row['Low'] <= sl:
                    return -abs((entry - sl) / entry) * 100 
                if row['High'] >= tp:
                    return abs((tp - entry) / entry) * 100
            elif signal == 'sell':
                if row['High'] >= sl:
                    return -abs((sl - entry) / entry) * 100 
                if row['Low'] <= tp:
                    return abs((entry - tp) / entry) * 100

        last_close = market_data.iloc[-1]['Close']
        if signal == 'buy':
            return (last_close - entry) / entry * 100
        elif signal == 'sell':
            return (entry - last_close) / entry * 100
        return None