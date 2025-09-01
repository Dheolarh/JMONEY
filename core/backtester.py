import pandas as pd
from .data_fetcher import DataFetcher
from .output_manager import OutputManager
import numpy as np

class Backtester:
    """
    Backtests past trading signals to evaluate performance, including ROI and drawdown,
    using a fixed risk-per-trade model for realistic results.
    """
    def __init__(self, output_manager: OutputManager, initial_capital: float = 10000, risk_per_trade_pct: float = 1.5):
        self.output_manager = output_manager
        self.data_fetcher = DataFetcher()
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct

    def run_backtest(self, signals: list[dict], days_to_backtest: int = 7,
                     transaction_cost_pct: float = 0.001, slippage_pct: float = 0.0005) -> dict:
        results = []
        skipped = 0
        processed = 0
        
        portfolio_values = [self.initial_capital]
        current_capital = self.initial_capital
        
        risk_amount_per_trade = self.initial_capital * (self.risk_per_trade_pct / 100)

        for signal in signals:
            ticker = signal.get('Ticker') or signal.get('ticker')
            asset_type = signal.get('asset_type', 'stocks')
            
            data = self.data_fetcher.get_data(ticker, asset_type=asset_type)
            if data is None or data.empty:
                skipped += 1
                continue
    
            processed += 1
    
            entry_price = signal.get('Entry') or signal.get('entry_price')
            sl = signal.get('Stop Loss') or signal.get('stop_loss')
            tp = signal.get('TP1') or signal.get('take_profit')
            direction = signal.get('Signal') or signal.get('Direction') or signal.get('signal')

            if not all([ticker, entry_price, sl, tp, direction]):
                skipped += 1
                continue

            try:
                if isinstance(entry_price, str): entry_price = float(entry_price.replace('$', '').replace('(ref)', '').strip())
                if isinstance(sl, str): sl = float(sl.replace('$', '').replace('(ref)', '').strip())
                if isinstance(tp, str): tp = float(tp.split(' ')[0].replace('$', '').strip())
            except (TypeError, ValueError):
                skipped += 1
                continue
    
            pnl_pct = self._simulate_trade(data, entry_price, sl, tp, direction, transaction_cost_pct, slippage_pct)
            
            if pnl_pct is not None:
                results.append(pnl_pct)
                trade_pnl = risk_amount_per_trade * (pnl_pct / 100)
                current_capital += trade_pnl
                portfolio_values.append(current_capital)
    
        # --- Performance Calculations ---
        win_count = sum(1 for r in results if r > 0)
        total_trades = len(results)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        
        final_portfolio_value = portfolio_values[-1]
        roi_pct = ((final_portfolio_value - self.initial_capital) / self.initial_capital) * 100
        
        portfolio_series = pd.Series(portfolio_values)
        peak = portfolio_series.expanding(min_periods=1).max()
        drawdown = (portfolio_series - peak) / peak
        max_drawdown_pct = drawdown.min() * 100 if not drawdown.empty else 0.0
    
        print(f"Backtest: Skipped {skipped} signals, processed {processed}, evaluated {total_trades} trades.")
    
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "wins": win_count,
            "losses": total_trades - win_count,
            "return_on_investment": roi_pct,
            "max_drawdown": max_drawdown_pct,
            "skipped_signals": skipped
        }

    def _simulate_trade(self, market_data: pd.DataFrame, entry: float, sl: float, tp: float, signal: str, 
                        transaction_cost_pct: float, slippage_pct: float) -> float | None:
        signal = signal.lower()
        entry_price_with_slippage = entry * (1 + slippage_pct) if signal == 'buy' else entry * (1 - slippage_pct)
        risk_per_share = abs(entry_price_with_slippage - sl)
        
        if risk_per_share == 0: return 0.0

        for index, row in market_data.iterrows():
            if signal == 'buy':
                if row['Low'] <= sl:
                    return -100.0
                if row['High'] >= tp:
                    reward_per_share = abs(tp - entry_price_with_slippage)
                    return (reward_per_share / risk_per_share) * 100
            elif signal == 'sell':
                if row['High'] >= sl:
                    return -100.0
                if row['Low'] <= tp:
                    reward_per_share = abs(entry_price_with_slippage - tp)
                    return (reward_per_share / risk_per_share) * 100
        return 0.0