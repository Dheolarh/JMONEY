# JMONEY Trading System

An intelligent automated trading signal system that scans financial news, identifies trading opportunities using AI, and provides real-time notifications via Telegram with comprehensive Google Sheets tracking.

## 📁 Project Structure

```
/JMONEY/
|
|-- config/
|   |-- data_sources.json         # ← Market data source priorities & API configs
|   |-- sources.json             # ← Financial news website URLs for scanning
|   |-- prompts.json             # ← AI prompts for GPT-4o asset identification
|   |-- scoring_metrics.json     # ← Scoring thresholds & confirmation criteria
|
├── core/                         # ← Main system modules (all essential)
│   ├── __init__.py              # ← Python package marker (required for imports)
│   ├── ai_analyzer.py           # ← GPT-4o integration for asset identification
│   ├── data_enricher.py         # ← Determines asset types & enriches with data
│   ├── data_fetcher.py          # ← Multi-source data fetching (Yahoo, Google, etc.)
│   ├── decision_engine.py       # ← Strategy mapping & final signal generation
│   ├── news_scanner.py          # ← Web scraping for financial headlines
│   ├── output_manager.py        # ← Google Sheets export functionality
│   ├── scoring_engine.py        # ← Technical, ZS-10+, and AI scoring algorithms
│   ├── telegram_bot.py          # ← Telegram bot commands & message formatting
│   ├── telegram_manager.py      # ← Telegram notification orchestration
│   └── trade_calculator.py      # ← Entry/exit price & risk management calculations
|
|-- .env                         # ← API keys, tokens & sensitive configuration
|-- google_service_account.json  # ← Google Sheets API credentials
|-- main.py                      # ← Main execution script (runs 7-stage pipeline)
|-- requirements.txt             # ← Python dependencies with version specifications
```

## ⭐ Key Features

- **Multi-source news scanning** (7 financial websites)
- **Flexible data sources** (Yahoo Finance, Google Finance, Polygon.io, Binance)
- **Advanced scoring algorithms** (Technical, Macro, AI, ZS-10+ trap detection)
- **Google Sheets export** for tracking with Source column and $ formatting
- **Interactive Telegram bot** with rich formatting and confirmation reasoning

## 🔄 7-Stage Processing Pipeline

### Stage 1: News Scanning
**Location:** `core/news_scanner.py`  
**Sources:** `config/sources.json`

**Process:**
1. Scans 7 financial news websites simultaneously
2. Extracts headlines using web scraping (BeautifulSoup)
3. Preserves source information for each headline
4. Filters for relevant financial content
5. Removes duplicates and noise

**Default Sources:**
- Yahoo Finance
- Finviz  
- GlobeNewswire
- CNBC
- FXStreet
- Business Insider
- MarketWatch

**Output:** Dictionary of headlines organized by source

### Stage 2: AI Asset Identification
**Location:** `core/ai_analyzer.py`  
**Model:** GPT-4o

**Process:**
1. Receives headlines with source prefixes [Source] Headline
2. Sends to GPT-4o with specialized prompts
3. AI identifies relevant asset symbols (stocks, crypto, forex, indices)
4. Extracts catalyst information preserving source tags
5. Returns structured list of assets with catalysts and sources

**AI Prompts Used:**
- System message for financial expertise
- User prompt template for asset extraction with source preservation
- JSON format requirements for consistency

**Output:** List of identified assets with catalysts and source information

### Stage 3: Data Enrichment
**Location:** `core/data_enricher.py`, `core/data_fetcher.py`  
**Configuration:** `config/data_sources.json`

**Process:**
1. Determines asset type (stocks, crypto, forex, indices)
2. Maps symbols to correct formats (e.g., SPX → ^GSPC)
3. Attempts data fetching from multiple sources with fallback:
   - **Primary:** Yahoo Finance (yfinance)
   - **Secondary:** Google Finance (web scraping)
   - **Tertiary:** Polygon.io (requires API key) - FULLY IMPLEMENTED
   - **Crypto:** Binance via CCXT

**Asset Type Detection:**
- **FX Pairs:** EUR/USD → EURUSD=X (Yahoo format)
- **Crypto Pairs:** BTC/USDT → Direct symbol
- **Indices:** SPX → ^GSPC, NDX → ^NDX
- **Stocks:** Direct symbol (AAPL, MSFT, etc.)

**Output:** Assets with OHLCV market data (up to 90 days)

### Stage 4: Scoring Calculation
**Location:** `core/scoring_engine.py`

#### Four-Dimensional Scoring System:

#### A) Technical Score (1-10)
**Indicators Used:**
- **RSI (14-period):** Oversold (+2), Overbought (-2), Neutral (+1)
- **MACD:** Bullish crossover (+1.5), Bearish (-1.5)
- **Moving Averages:** 50 > 200 MA (+1), Golden cross (+1.5)
- **Price vs MA:** Above 50MA (+0.5), Above 200MA (+0.5)

#### B) ZS-10+ Score (Smart Trap Detection) (1-10)
**Purpose:** Detect potential "smart money traps"

**Volume Analysis (when available):**
- Volume Ratio = Recent 5-day avg / Historical 20-day avg
- **Score 8:** Volume ↓60% + Price ↑3% (High trap risk)
- **Score 6:** Volume ↓20% + Price ↑2% (Medium risk)
- **Score 2:** Volume ↑50% + Price ↑1% (Low risk - good confirmation)
- **Score 4:** Sideways price action (Neutral)

**Price-Only Analysis (no volume):**
- **Score 7:** High volatility (>5%) + big moves (>3%)
- **Score 3:** Low volatility (<2%) - stable
- **Score 5:** Moderate volatility - default

#### C) Macro Score (AI-Generated)
**Location:** AI analysis in scoring_engine.py  
**Factors:** Economic indicators, sector trends, market sentiment

#### D) AI Catalyst Score
Evaluates news catalyst strength and relevance

**Output:** Each asset gets 4 scores (Technical, ZS-10+, Macro, AI)

### Stage 5: Decision Engine
**Location:** `core/decision_engine.py`  
**Configuration:** `config/scoring_metrics.json`

**Strategy Mapping Logic:**
1. **BOOST Strategy:** High technical (≥6) + catalyst present
2. **ZEN Strategy:** High technical (≥8) + good macro (≥6) + low trap risk (<4)
3. **NEUTRAL Strategy:** Weak scores across board
4. **CAUTION Strategy:** High retail sentiment + moderate trap risk

**Signal Generation:**
- **BUY:** Strong bullish indicators
- **SELL:** Strong bearish indicators  
- **NEUTRAL:** Mixed or weak signals

**Trade Parameters Calculated:**
- **Entry:** Current market price or pullback level
- **Stop Loss:** ATR-based or support/resistance
- **TP1/TP2:** Risk-reward ratio ≥ 2.0
- **Position sizing recommendations**

**JMoney Confirmation Logic:**
- Assigns confirmation_reason for each signal
- "Ticker doesn't meet confirmation requirements" for unconfirmed signals
- Detailed reasoning for confirmed signals

**Output:** Trading signals with strategy classification and confirmation reasoning

### Stage 6: Google Sheets Export
**Location:** `core/output_manager.py`  
**Configuration:** Google API credentials

#### Enhanced Structure (20 columns):
1. **Timestamp** - When signal was generated
2. **Ticker** - Asset symbol
3. **Source** - News source (Yahoo Finance, CNBC, etc.)
4. **Signal** - Buy/Sell/Neutral decision
5. **Strategy** - Boost/Zen/Caution/Neutral
6. **Direction** - Long/Short/Neutral position
7. **Entry** - Suggested entry price ($formatted)
8. **Stop Loss** - Risk management level ($formatted)
9. **TP1** - First target price ($formatted)
10. **TP2** - Second target price ($formatted)
11. **TP Strategy** - Dynamic position sizing strategy
12. **Technical Score** - Technical analysis (1-10)
13. **ZS-10+ Score** - Trap detection (1-10)
14. **Macro Score** - Economic context (1-10)
15. **Sentiment Score** - Market sentiment (1-10)
16. **Confidence Score** - Overall confidence (1-10)
17. **Catalyst** - Simple category (JOBS, EARNINGS, etc.)
18. **Summary** - Detailed headline description
19. **JMoney Confirmed** - YES/NO confirmation
20. **Reasoning** - JMoney confirmation reasoning

**Features:**
- Duplicate detection based on ticker + headline (allows same ticker with different headlines)
- Source tracking from headline to final export
- Enhanced error handling
- Reference levels for neutral signals with "(ref)" notation

### Stage 7: Telegram Notifications
**Location:** `core/telegram_bot.py`, `core/telegram_manager.py`

#### Message Format:
- **Ticker:** Asset symbol
- **Source:** News source
- **Strategy:** Boost/Zen/Caution/Neutral strategy type
- **Score:** Confidence score (1–10)
- **Direction:** Long/Short/Neutral
- **Entry:** Suggested entry zone ($formatted)
- **Stop Loss:** Risk management level ($formatted)
- **TP1/TP2:** Target levels ($formatted) with "(ref)" for neutral signals
- **TP Strategy:** Dynamic profit-taking approach based on confidence
- **Macro Score:** Economic context
- **Sentiment Score:** Market sentiment
- **Catalyst:** News catalyst category
- **ZS-10+ Score:** Trap detection
- **Confirmation:** JMoney confirmation status with reason

#### Bot Commands:
- 📊 `/signals` - View recent trading signals (all strategies)
- ✅ `/confirmed` - Show confirmed trade setups (reads from Google Sheets)
- ⚡ `/boost` - View only Boost strategy signals  
- 🧘 `/zen` - View only Zen strategy signals
- ⚠️ `/caution` - View only Caution strategy signals
- ⚪ `/neutral` - View only Neutral strategy signals
- 🔄 `/fetch` - Manually trigger new workflow analysis
- 📈 `/status` - Check system status (real-time Google Sheets data)
- ❓ `/help` - Show help message

## 📊 Detailed Scoring System

### Confidence Score Calculation
**Formula:** `(Technical Score + Macro Score + ZS-10+ Score) / 3`

**Example:**
- Technical Score: 7/10 (Strong RSI + MACD bullish)
- Macro Score: 6/10 (Positive economic backdrop)
- ZS-10+ Score: 3/10 (Low trap risk, good volume)
- **Confidence Score:** (7 + 6 + 3) / 3 = 5.3/10

### Technical Score Breakdown
**Base Score:** 5/10

**RSI Analysis:**
- Current RSI > 70: -2 points (Overbought risk)
- Current RSI < 30: +2 points (Oversold opportunity)
- RSI 40-60: +1 point (Neutral momentum)

**MACD Analysis:**
- MACD > Signal Line: +1.5 points (Bullish momentum)
- MACD < Signal Line: -1.5 points (Bearish momentum)

**Moving Average Analysis:**
- 50-day MA > 200-day MA: +1 point (Bullish trend)
- Recent golden cross: +1.5 points (Strong bullish)
- Price > 50-day MA: +0.5 points (Short-term bullish)
- Price > 200-day MA: +0.5 points (Long-term bullish)

**Final Technical Score:** Clamped between 0-10

### ZS-10+ Trap Detection Logic
**Concept:** Smart money often creates false breakouts to trap retail traders

**High Trap Risk Scenarios:**
- Price increases significantly but volume decreases
- High volatility with erratic price movements
- Unusual price spikes without fundamental support

**Scoring Logic:**
- **Score 2-3:** Low trap risk (good volume confirmation)
- **Score 4-5:** Neutral/moderate risk
- **Score 6-8:** High trap risk (suspicious price/volume divergence)

### AI Scoring Integration
The AI Analyzer provides additional scoring based on:
- Catalyst strength and relevance
- Market sentiment analysis
- Sector-specific factors
- Economic context evaluation

## ✅ JMoney Confirmation Logic

### Confirmation Criteria
**Location:** `core/decision_engine.py`  
**Configuration:** `config/scoring_metrics.json`

A signal becomes "JMoney Confirmed" when it meets ALL requirements:

#### Required Conditions:
1. **Minimum Confidence Score:** ≥ 7.0/10
2. **Strategy Must Be:** "Boost" or "Zen" (not Neutral/Caution)
3. **Technical Score:** ≥ 6/10
4. **ZS-10+ Score:** ≤ 5/10 (low trap risk)
5. **Valid Trade Parameters:** Entry, SL, TP1 all defined

#### Boost Strategy Confirmation:
- Technical Score ≥ 6/10
- Strong catalyst present
- Reasonable risk-reward ratio (≥ 2.0)

#### Zen Strategy Confirmation:
- Technical Score ≥ 8/10
- Macro Score ≥ 6/10
- ZS-10+ Score < 4/10 (very low trap risk)
- Clean technical setup

### Confirmation Reasoning
Enhanced reasoning system provides detailed explanations:

**For CONFIRMED signals:**
- "Boost strategy: Technical score: 8/10, Strong catalyst: EARNINGS"
- "Zen strategy: Technical score: 9/10, Low trap risk: 2/10"

**For NOT CONFIRMED signals:**
- "Technical score too low: 4/10 (need ≥6)"
- "High trap risk: 7/10 (need <4)"
- "No significant catalyst detected"
- "Ticker doesn't meet confirmation requirements" (default)

## ⚙️ Enhanced TP Strategy System

### Dynamic TP Strategy Based on Confidence
The system now calculates dynamic position sizing strategies for ALL signals:

#### For Actionable Signals (Buy/Sell):
- **High confidence (≥8.5):** "TP1 30% / TP2 70%" (let winners run)
- **Medium confidence (≥7.5):** "TP1 50% / TP2 50%"
- **Lower confidence (≥6.0):** "TP1 70% / TP2 30%" (more conservative)
- **Very low confidence:** "TP1 80% / TP2 20%"

#### For Neutral Signals:
- Shows reference TP1/TP2 levels with "(ref)" notation
- Strategy: "Monitor for signals (confidence: X.X/10)"
- Provides breakout scenarios for potential trades

**Trade Parameter Dependencies:**
- **Entry Point:** Latest closing price from market data (NOT score-dependent)
- **Stop Loss:** ATR-based volatility calculation (NOT score-dependent)
- **TP1/TP2:** Risk-reward ratio based (NOT score-dependent)
- **TP Strategy:** Confidence score dependent (score-dependent)

## 🛠️ Editable Configuration Files

### A) `config/sources.json` - News Sources
**Purpose:** Define which financial news websites to scan

**Editable Fields:**
- Add/remove news sources
- Change URLs for existing sources
- Modify source names

```json
{
  "Yahoo Finance": "https://finance.yahoo.com/",
  "Custom Source": "https://your-news-site.com/markets"
}
```

### B) `config/data_sources.json` - Market Data Sources
**Purpose:** Configure data fetching priorities and sources

**Editable Fields:**
- Source priority order
- Asset type mappings
- API configurations
- Fallback strategies

### C) `config/prompts.json` - AI Prompts
**Purpose:** Customize AI behavior and responses

Enhanced prompts include:
- Source preservation instructions
- Asset identification criteria
- Output format requirements with source tags

**Key Enhancement:**
"IMPORTANT: Keep the [Source] prefix in the catalyst field exactly as provided in the headlines"

### D) `config/scoring_metrics.json` - Scoring Thresholds
**Purpose:** Adjust scoring sensitivity and confirmation rules

**Editable Parameters:**
- Technical indicator thresholds
- Confirmation criteria weights
- Strategy classification rules
- Risk management parameters

### E) `.env` - Environment Variables
**Purpose:** Store sensitive configuration data

**Required Variables:**
- `OPENAI_KEY`: GPT-4o API access
- `TELEGRAM_BOT_TOKEN`: Bot authentication
- `TELEGRAM_CHAT_ID`: Target chat for notifications
- `POLYGON_API_KEY`: Premium data access (optional, now working)
- `SHEET_NAME`: Google Sheets target name
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON

## 🚀 System Operation Modes

### 1. Complete System Mode (Recommended)
```bash
python main.py
```
- Runs initial workflow immediately
- Starts Telegram bot for interactive commands
- Schedules automatic workflow every 4 hours
- Keeps system running continuously
- All Telegram commands work with Google Sheets integration

### 2. Workflow Only Mode
```bash
python main.py --workflow-only
```
- Runs workflow once and exits
- Exports to Google Sheets with enhanced structure
- Good for testing or scheduled runs

### 3. Bot Only Mode
```bash
python main.py --bot-only
```
- Starts only Telegram bot with Google Sheets access
- All commands read real-time data from sheets
- Manual workflow trigger via /fetch command

### 4. Test Telegram
```bash
python main.py --test-telegram
```
- Sends test notification to verify setup
- Tests Google Sheets connectivity

## 📋 System Requirements

### Python Dependencies
- `python-telegram-bot==13.15` (exact version for compatibility)
- `openai>=1.0.0` (for GPT-4o support)
- `yfinance>=0.2.0` (market data)
- `ccxt>=4.0.0` (crypto data)
- `gspread>=5.7.0` (Google Sheets)
- `schedule>=1.2.0` (workflow automation)
- `polygon-api-client>=1.0.0` (premium data - now working)
- `requests`, `beautifulsoup4`, `pandas`, `numpy`

### API Requirements
- **OpenAI API key** (GPT-4o access)
- **Telegram Bot Token & Chat ID**
- **Google Service Account** (for Sheets)
- **Polygon.io API key** (optional, premium data)

### Runtime Requirements
- Stable internet connection
- Continuous server/computer operation
- Sufficient API quota limits
- 24/7 availability for best results

## 📝 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd JMONEY
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your API keys and tokens

4. **Set up Google Sheets:**
   - Create a Google Service Account
   - Download credentials JSON file
   - Share your target sheet with the service account email

5. **Run the system:**
   ```bash
   python main.py
   ```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**⚠️ Disclaimer:** This system is for educational and informational purposes only. Always conduct your own research and consult with financial advisors before making trading decisions.
