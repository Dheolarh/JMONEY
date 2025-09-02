import pandas as pd
import json
import matplotlib.pyplot as plt

def run_backtest_and_generate_outputs():
    """
    Runs a simple backtest on the generated signals and creates summary files.
    """
    print("\n--- Running Backtest on Demo Signals ---")
    try:
        signals_df = pd.read_csv("demo/output/signals.csv")
    except FileNotFoundError:
        print("❌ Error: 'demo/output/signals.csv' not found. Run 'demo_main.py' first.")
        return

    initial_capital = 10000
    equity = [initial_capital]
    trades = []
    win_count = 0
    loss_count = 0

    for _, row in signals_df.iterrows():
        # Simplified P&L simulation for demo purposes
        pnl = 0
        if row['Signal'] == 'Buy' and row['JMoney Confirmed'] == 'YES':
            # Simulate a 1.5% gain for a win, 1% loss for a loss
            pnl = initial_capital * 0.015 if row['Confidence Score'] > 7 else -initial_capital * 0.01
        elif row['Signal'] == 'Sell' and row['JMoney Confirmed'] == 'YES':
            pnl = initial_capital * 0.015 if row['Confidence Score'] > 7 else -initial_capital * 0.01

        if pnl > 0:
            win_count += 1
        elif pnl < 0:
            loss_count += 1
            
        new_equity = equity[-1] + pnl
        equity.append(new_equity)
        trades.append({
            "ticker": row['Ticker'],
            "direction": row['Direction'],
            "pnl": round(pnl, 2),
            "equity": round(new_equity, 2)
        })

    # --- Generate Outputs ---

    # 1. Summary JSON
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
    with open("demo/output/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print("✅ summary.json created.")

    # 2. Trades CSV
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv("demo/output/trades.csv", index=False)
    print("✅ trades.csv created.")

    # 3. Equity Curve PNG
    plt.figure(figsize=(10, 6))
    plt.plot(equity, marker='o', linestyle='-', color='b')
    plt.title('Demo Backtest Equity Curve')
    plt.xlabel('Trade Number')
    plt.ylabel('Portfolio Value ($)')
    plt.grid(True)
    plt.savefig("demo/output/equity_curve.png")
    plt.close()
    print("✅ equity_curve.png created.")
    print("\n--- Backtest Complete ---")


if __name__ == "__main__":
    run_backtest_and_generate_outputs()