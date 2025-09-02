# JMONEY - Offline Demo

This folder contains a self-contained, offline demo of the JMONEY trading system. It follows the exact same 7-stage workflow as the main application but uses local mock data files instead of live APIs.

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
python run_backtest.py
```

