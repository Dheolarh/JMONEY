import json
import pandas as pd
from datetime import datetime
from .data_fetcher import DataFetcher
from .ai_analyzer import AIAnalyzer # Add this import
import os

class PortfolioTracker:
    """
    Tracks the performance of trading signals over time.
    """
    def __init__(self, portfolio_path: str = "data/portfolio.json"):
        """
        Initializes the PortfolioTracker.
        """
        self.portfolio_path = portfolio_path
        self.data_fetcher = DataFetcher()
        
        # Add these lines to initialize the AI Analyzer
        api_key = os.getenv("OPENAI_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("AI API key not found for PortfolioTracker")
        self.ai_analyzer = AIAnalyzer(
            api_key=api_key,
            prompts_path=os.getenv("PROMPTS_PATH", "config/prompts.json"),
            provider="openai" if os.getenv("OPENAI_KEY") else "gemini"
        )

        # Ensure the data directory exists
        portfolio_dir = os.path.dirname(self.portfolio_path)
        if portfolio_dir:
            os.makedirs(portfolio_dir, exist_ok=True)
        
        self.portfolio = self._load_portfolio()

    def _load_portfolio(self) -> dict:
        """Loads the portfolio from a JSON file, creating it if it doesn't exist."""
        try:
            with open(self.portfolio_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file doesn't exist or is empty, create a default structure
            print(f"    '{self.portfolio_path}' not found or invalid. Creating a new one.")
            default_portfolio = {"trades": [], "summary": {}}
            self._save_portfolio(default_portfolio)
            return default_portfolio

    def _save_portfolio(self, data_to_save=None):
        """Saves the portfolio to a JSON file."""
        if data_to_save is None:
            data_to_save = self.portfolio
            
        with open(self.portfolio_path, 'w') as f:
            json.dump(data_to_save, f, indent=2)

    def add_trade(self, signal: dict):
        """Adds a new trade to the portfolio."""
        try:
            # Clean monetary values before processing
            entry_price_str = str(signal.get('entry', '0')).split(' ')[0].replace('$', '').strip()
            stop_loss_str = str(signal.get('stop_loss', '0')).split(' ')[0].replace('$', '').strip()
            take_profit_str = str(signal.get('tp1', '0')).split(' ')[0].replace('$', '').strip()

            entry_price = float(entry_price_str)
            stop_loss = float(stop_loss_str)
            take_profit = float(take_profit_str)
            
        except (ValueError, TypeError):
            print(f"    ...skipping adding trade for {signal.get('ticker')} due to invalid price format.")
            return

        trade = {
            "ticker": signal.get('ticker'),
            "asset_type": signal.get('asset_type'), # Add this line
            "direction": "Long" if signal.get('signal') == "Buy" else "Short",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "open",
            "open_date": datetime.now().isoformat(),
            "close_date": None,
            "pnl_pct": 0.0
        }
        self.portfolio["trades"].append(trade)
        self._save_portfolio()
        print(f"    ...added trade for {trade['ticker']} to portfolio.")

    def update_open_trades(self):
        """Updates the status of all open trades."""
        print("--> Updating status of open trades...")
        trades_to_check = [trade for trade in self.portfolio.get("trades", []) if trade.get("status") == "open"]
        
        if not trades_to_check:
            print("    ...no open trades to update.")
            return

        for trade in trades_to_check:
            # Use AI to get the asset type
            asset_type = self.ai_analyzer.get_asset_type(trade["ticker"])
            if not asset_type:
                print(f"    ...could not determine asset type for {trade['ticker']}. Skipping.")
                continue

            market_data = self.data_fetcher.get_data(trade["ticker"], asset_type=asset_type)
            if market_data is not None and not market_data.empty:
                self._check_trade_status(trade, market_data)
        
        self._calculate_performance_summary()
        self._save_portfolio()

    def _check_trade_status(self, trade: dict, market_data: pd.DataFrame):
        """Checks if an open trade has hit its SL or TP."""
        latest_candle = market_data.iloc[-1]
        
        if trade["direction"] == "Long":
            if latest_candle['Low'] <= trade["stop_loss"]:
                self._close_trade(trade, trade["stop_loss"])
            elif latest_candle['High'] >= trade["take_profit"]:
                self._close_trade(trade, trade["take_profit"])
        elif trade["direction"] == "Short":
            if latest_candle['High'] >= trade["stop_loss"]:
                self._close_trade(trade, trade["stop_loss"])
            elif latest_candle['Low'] <= trade["take_profit"]:
                self._close_trade(trade, trade["take_profit"])

    def _close_trade(self, trade: dict, exit_price: float):
        """Closes a trade and calculates the P/L."""
        trade["status"] = "closed"
        trade["close_date"] = datetime.now().isoformat()
        
        if trade["direction"] == "Long":
            trade["pnl_pct"] = (exit_price - trade["entry_price"]) / trade["entry_price"] * 100
        else: # Short
            trade["pnl_pct"] = (trade["entry_price"] - exit_price) / trade["entry_price"] * 100
        
        print(f"    ...closing trade for {trade['ticker']} with P/L of {trade['pnl_pct']:.2f}%")

    def _calculate_performance_summary(self):
        """Calculates and updates the performance summary."""
        closed_trades = [t for t in self.portfolio.get("trades", []) if t.get("status") == "closed"]
        if not closed_trades:
            return

        total_pnl = sum(t["pnl_pct"] for t in closed_trades)
        wins = [t for t in closed_trades if t["pnl_pct"] > 0]
        losses = [t for t in closed_trades if t["pnl_pct"] <= 0]
        
        win_rate = (len(wins) / len(closed_trades)) * 100 if closed_trades else 0
        avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0

        self.portfolio["summary"] = {
            "total_pnl_pct": total_pnl,
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "average_win_pct": avg_win,
            "average_loss_pct": avg_loss
        }

    def get_summary(self) -> dict:
        """Returns the latest performance summary."""
        return self.portfolio.get("summary", {})