# JMONEY Trading System

An intelligent, automated trading signal system that scans financial news, identifies trading opportunities using AI, and provides real-time notifications via Telegram with comprehensive Google Sheets tracking.

---

## 📁 Project Structure

```
/JMONEY/
│
├── config/
│   ├── data_sources.json         # Market data source priorities & API configs
│   ├── sources.json              # Financial news website URLs for scanning
│   ├── prompts.json              # AI prompts for GPT-4o asset identification
│   ├── scoring_metrics.json      # Scoring thresholds & confirmation criteria
│   └── trading_config.json       # Risk and account settings
│
├── core/                         # Main system modules
│   ├── __init__.py
│   ├── ai_analyzer.py            # GPT-4o/Gemini integration for asset identification & scoring
│   ├── data_enricher.py          # Determines asset types & enriches with data
│   ├── data_fetcher.py           # Multi-source data fetching (Yahoo, Google, Polygon, Binance, etc.)
│   ├── decision_engine.py        # Strategy mapping & final signal generation
│   ├── news_scanner.py           # Web scraping for financial headlines
│   ├── output_manager.py         # Google Sheets export functionality
│   ├── scoring_engine.py         # Technical, ZS-10+, and AI scoring algorithms
│   ├── telegram_bot.py           # Telegram bot commands & message formatting
│   ├── telegram_manager.py       # Telegram notification orchestration
│   ├── trade_calculator.py       # Entry/exit price & risk management calculations
│   ├── portfolio_tracker.py      # Portfolio and trade tracking
│   └── backtester.py             # Signal backtesting
│
├── utils/
│   ├── __init__.py
│   └── logger.py                 # Logging utility
│
├── data/
│   └── portfolio.json            # Portfolio/trade history
│
├── logs/
│   └── jmoney.log                # System logs
│
├── test/
│   ├── __init__.py
│   └── ai_provider_check.py      # Test scripts
│
├── main.py                       # Main execution script (runs 7-stage pipeline)
├── requirements.txt              # Python dependencies
├── .env                          # API keys, tokens & sensitive configuration
└── README.md                     # Project documentation
```

---

## ⭐ Key Features

- **Multi-source news scanning** (configurable financial/news/crypto sites)
- **Flexible, multi-source market data** (Yahoo Finance, Google Finance, Polygon.io, Binance, Coinbase, KuCoin, Kraken, etc.)
- **AI-powered asset identification** (OpenAI GPT-4o or Gemini, with prompt templates)
- **Advanced scoring algorithms** (Technical, Macro, Sentiment, ZS-10+ trap detection)
- **Dynamic trade parameter calculation** (ATR-based SL/TP, position sizing)
- **Google Sheets export** for tracking with duplicate detection and rich formatting
- **Interactive Telegram bot** with rich formatting, commands, and scheduled notifications
- **Portfolio tracking** with P/L, win rate, and trade status
- **Backtesting and optimization** for strategy parameters

---

## 🔄 7-Stage Processing Pipeline

### 1. News Scanning
- **Location:** `core/news_scanner.py`
- **Sources:** `config/sources.json`
- Scrapes headlines from multiple financial and crypto news sites.
- Returns a dictionary of headlines by source.

### 2. AI Asset Identification
- **Location:** `core/ai_analyzer.py`
- **Model:** OpenAI GPT-4o or Gemini (configurable)
- Identifies tradeable assets (stocks, forex, crypto, indices) from headlines.
- Returns a list of assets with tickers and catalyst descriptions.

### 3. Data Enrichment
- **Location:** `core/data_enricher.py`, `core/data_fetcher.py`
- **Config:** `config/data_sources.json`
- Uses AI to determine asset type and correct ticker formatting.
- Fetches historical OHLCV data from prioritized sources (Yahoo, Google, Polygon, Binance, etc.).
- Supports stocks, forex, crypto, and indices.

### 4. Scoring Calculation
- **Location:** `core/scoring_engine.py`
- Calculates:
  - **Technical Score:** RSI, MACD, MAs, Bollinger Bands
  - **ZS-10+ Score:** Trap detection (volume/price analysis)
  - **Macro & Sentiment Scores:** AI-generated from catalyst
  - **Catalyst Type:** AI-classified

### 5. Decision Engine
- **Location:** `core/decision_engine.py`
- Maps scores to strategies (Boost, Zen, Caution, Neutral).
- Calculates confidence score and trade parameters (entry, SL, TP1/TP2, position size).
- Applies confirmation logic (configurable in `scoring_metrics.json`).

### 6. Output & Google Sheets Export
- **Location:** `core/output_manager.py`
- Exports signals to Google Sheets with duplicate detection and rich formatting.
- 20+ columns including all scores, catalyst, confirmation, and reasoning.

### 7. Telegram Notifications
- **Location:** `core/telegram_manager.py`, `core/telegram_bot.py`
- Sends formatted notifications for new signals, daily summaries, and market open/close.
- Supports interactive commands: `/signals`, `/confirmed`, `/boost`, `/zen`, `/caution`, `/neutral`, `/fetch`, `/status`, `/portfolio`, `/help`.

---

## ⚙️ Market Data Source Logic

- **Stocks:** Yahoo, Google, Polygon
- **Forex:** Yahoo (`EURUSD=X`), Google, Polygon
- **Crypto:** Yahoo (`BTC-USD`), Binance, Coinbase, KuCoin, Kraken, etc.
- **Indices:** Yahoo, Google

All sources and priorities are configurable in `config/data_sources.json`.

---

## 🧠 AI Integration

- **OpenAI GPT-4o** (default) or **Gemini** (fallback/testing)
- Prompts for asset extraction, ticker enrichment, and catalyst scoring are in `config/prompts.json`.
- AI is used for:
  - Asset extraction from headlines
  - Ticker formatting and asset type detection
  - Macro/sentiment/catalyst scoring

---

## 📊 Scoring & Confirmation

- **Technical Score:** 0–10 (RSI, MACD, MAs, Bollinger Bands)
- **ZS-10+ Score:** 0–10 (trap detection)
- **Macro & Sentiment:** 0–10 (AI)
- **Catalyst Type:** AI-classified
- **Strategy Mapping:** Boost, Zen, Caution, Neutral
- **Confirmation:** Configurable rules in `scoring_metrics.json` (min scores, catalyst required, etc.)

---

## 📈 Portfolio Tracking

- **Location:** `core/portfolio_tracker.py`
- Tracks open/closed trades, calculates P/L, win rate, and summary stats.
- Updates trade status based on latest market data.

---

## 🧪 Backtesting & Optimization

- **Backtester:** `core/backtester.py` simulates historical trade performance.
- **Optimizer:** `core/optimizer.py` uses AI to suggest better scoring parameters.

---

## 🚀 Running the System

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Configure your `.env` file** with API keys and settings.
3. **Run the main pipeline:**
   ```sh
   python main.py
   ```
4. **Interact via Telegram** using your bot token and chat ID.

---

## 📝 Customization

- **Add/remove news sources:** Edit `config/sources.json`
- **Change data source priorities:** Edit `config/data_sources.json`
- **Adjust scoring/confirmation:** Edit `config/scoring_metrics.json`
- **Modify prompts:** Edit `config/prompts.json`

---

## 🛠️ Troubleshooting

- **Market data errors:** Check ticker formatting and data source availability.
- **Google Sheets issues:** Ensure correct credentials and sheet name/ID.
- **Telegram issues:** Verify bot token and chat ID in `.env`.
- **AI errors:** Ensure valid OpenAI or Gemini API key.