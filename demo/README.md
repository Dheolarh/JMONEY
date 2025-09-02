# JMONEY - Offline Demo

This folder contains aoffline demo of the JMONEY trading system. It follows the exact same 7-stage workflow as the main application but uses local mock data files instead of live APIs.

**No API keys or internet connection are required to run this demo.**

---

## How to Run

### 1. Install Dependencies
First, ensure you have the required Python libraries installed.

```sh
pip install -r requirements.txt
```

## 2. Run the Main Demo Workflow
This script simulates the core logic: scanning news, analyzing assets,scoring, and generating signals. It will create an output folder with the results.

```sh
cd demo
python demo_main.py
```

## 3. BACKTESTING
### 1. Demo Backtesting (demo/run_backtest.py)
Its goal is to clearly illustrate the system's reporting capabilities.

Illustrative Logic: It uses pre-defined "win" or "loss" outcomes for a balanced set of trades, rather than historical data, to ensure the equity curve is always dynamic and shows both profits and drawdowns.

Purpose: To provide a reliable and clear demonstration of the system's end-to-end workflow without the complexity of live data analysis.

```sh
cd demo
python run_backtest.py
```

### 2. Advanced Backtesting (core/backtester.py)
This is the core engine for rigorously evaluating and optimizing the trading strategy with real-world data.

Data-Driven: It fetches actual historical market data to simulate how each trade would have performed by checking if the price hit the Stop Loss or Take Profit levels.

AI-Powered Optimization: The results are fed into the AI-powered optimizer, which refines the trading rules to improve performance based on historical data.

Purpose: To validate and enhance the trading strategy's profitability and risk profile.
