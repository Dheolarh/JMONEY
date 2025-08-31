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

    def run_backtest(self, signals: list[dict], days_to_backtest: int = 7, 
                     transaction_cost_pct: float = 0.001, slippage_pct: float = 0.0005) -> dict:
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
                # Remove '$' and '(ref)' before converting to float
                if isinstance(entry_price, str):
                    entry_price = float(entry_price.replace('$', '').replace('(ref)', '').strip())
                if isinstance(sl, str):
                    sl = float(sl.replace('$', '').replace('(ref)', '').strip())
                if isinstance(tp, str):
                    tp = float(tp.replace('$', '').replace('(ref)', '').strip())
            except (TypeError, ValueError):
                skipped += 1
                continue
    
            trade_result = self._simulate_trade(data, entry_price, sl, tp, direction, transaction_cost_pct, slippage_pct)
            if trade_result is not None:
                results.append(trade_result)
    
        win_count = sum(1 for r in results if r > 0)  # A win is any result > 0
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

    def _simulate_trade(self, market_data: pd.DataFrame, entry: float, sl: float, tp: float, signal: str, 
                        transaction_cost_pct: float, slippage_pct: float) -> float | None:
        """
        Simulates a single trade against historical data, including transaction costs and slippage.
        Returns the net profit/loss percentage.
        """
        signal = signal.lower()
        
        # Adjust entry price for slippage
        entry_price_with_slippage = entry * (1 + slippage_pct) if signal == 'buy' else entry * (1 - slippage_pct)
        
        for index, row in market_data.iterrows():
            if signal == 'buy':
                # Check for stop loss
                if row['Low'] <= sl:
                    exit_price = sl
                    profit_pct = (exit_price - entry_price_with_slippage) / entry_price_with_slippage * 100
                    return profit_pct - (transaction_cost_pct * 2 * 100) # Costs for entry and exit
                # Check for take profit
                if row['High'] >= tp:
                    exit_price = tp
                    profit_pct = (exit_price - entry_price_with_slippage) / entry_price_with_slippage * 100
                    return profit_pct - (transaction_cost_pct * 2 * 100)

            elif signal == 'sell':
                # Check for stop loss
                if row['High'] >= sl:
                    exit_price = sl
                    profit_pct = (entry_price_with_slippage - exit_price) / entry_price_with_slippage * 100
                    return profit_pct - (transaction_cost_pct * 2 * 100)
                # Check for take profit
                if row['Low'] <= tp:
                    exit_price = tp
                    profit_pct = (entry_price_with_slippage - exit_price) / entry_price_with_slippage * 100
                    return profit_pct - (transaction_cost_pct * 2 * 100)

        # If trade is still open at the end of the data, calculate mark-to-market P/L
        last_close = market_data.iloc[-1]['Close']
        if signal == 'buy':
            profit_pct = (last_close - entry_price_with_slippage) / entry_price_with_slippage * 100
        elif signal == 'sell':
            profit_pct = (entry_price_with_slippage - last_close) / entry_price_with_slippage * 100
        else:
            return None
            
        return profit_pct - (transaction_cost_pct * 100) # Cost for entry only, as trade is not closed