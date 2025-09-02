import pandas as pd
import json
import matplotlib.pyplot as plt
import os

def run_backtest_and_generate_outputs():
    """
    Runs a simple backtest on the generated signals and creates summary files.
    """
    print("\n--- Running Backtest on Demo Signals ---")
    
    output_dir = "output"
    signals_path = os.path.join(output_dir, "signals.csv")
    summary_path = os.path.join(output_dir, "summary.json")
    trades_path = os.path.join(output_dir, "trades.csv")
    equity_curve_path = os.path.join(output_dir, "equity_curve.png")

    os.makedirs(output_dir, exist_ok=True)

    try:
        signals_df = pd.read_csv(signals_path)
    except FileNotFoundError:
        print(f"❌ Error: '{signals_path}' not found. Run 'demo_main.py' first.")
        return

    initial_capital = 10000
    equity = [initial_capital]
    trades = []
    win_count = 0
    loss_count = 0

    # Load simulated outcomes from the confirmed trades pool
    try:
        with open("data/confirmed_trades_pool.json", 'r') as f:
            trades_pool = json.load(f)
        
        # Create a dictionary to easily look up the simulated outcome for each ticker
        outcomes = {trade['ticker']: trade['simulated_outcome'] for trade in trades_pool}
        print(f"✅ Loaded outcomes for {len(outcomes)} tickers from confirmed trades pool.")
        
    except FileNotFoundError:
        print("❌ Warning: confirmed_trades_pool.json not found. Using fallback logic.")
        # Fallback: alternate wins and losses
        outcomes = {}

    for _, row in signals_df.iterrows():
        pnl = 0
        current_equity = equity[-1] 
        
        if row['JMoney Confirmed'] == 'YES':
            ticker = row['Ticker']
            
            if ticker in outcomes:
                # Use the predefined outcome from the trades pool
                outcome = outcomes[ticker]
            else:
                # Fallback: alternate between win and loss
                outcome = 'win' if len(trades) % 2 == 0 else 'loss'
            
            # Generate a win or loss based on the outcome
            if outcome == 'win':
                pnl = current_equity * 0.015  # 1.5% win
                print(f"  📈 {ticker}: WIN (+{pnl:.2f})")
            else:
                pnl = -current_equity * 0.01  # 1% loss
                print(f"  📉 {ticker}: LOSS ({pnl:.2f})")

        if pnl > 0:
            win_count += 1
        elif pnl < 0:
            loss_count += 1
            
        new_equity = current_equity + pnl
        equity.append(new_equity)
        
        if pnl != 0: 
            trades.append({
                "ticker": row['Ticker'],
                "direction": row['Direction'],
                "pnl": round(pnl, 2),
                "equity": round(new_equity, 2)
            })

    total_trades = win_count + loss_count
    summary = {
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate": f"{((win_count / total_trades) * 100 if total_trades > 0 else 0):.2f}%",
        "final_equity": round(equity[-1], 2),
        "net_profit": round(equity[-1] - initial_capital, 2),
        "net_profit_pct": f"{(((equity[-1] - initial_capital) / initial_capital) * 100):.2f}%"
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ {summary_path} created.")

    if trades: 
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv(trades_path, index=False)
        print(f"✅ {trades_path} created.")

        plt.figure(figsize=(10, 6))
        plt.plot(equity, marker='o', linestyle='-', color='b')
        plt.title('Demo Backtest Equity Curve')
        plt.xlabel('Trade Number')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True)
        plt.savefig(equity_curve_path)
        plt.close()
        print(f"✅ {equity_curve_path} created.")
        
    print(f"\n--- Backtest Summary ---")
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {win_count} | Losses: {loss_count}")
    print(f"Win Rate: {summary['win_rate']}")
    print(f"Final Equity: ${summary['final_equity']}")
    print(f"Net P&L: ${summary['net_profit']} ({summary['net_profit_pct']})")
    print("\n--- Backtest Complete ---")


if __name__ == "__main__":
    run_backtest_and_generate_outputs()