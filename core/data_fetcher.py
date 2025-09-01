import yfinance as yf
import ccxt
import pandas as pd
import os
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List

class DataFetcher:
    """
    A unified class to fetch market data from multiple configurable sources.
    """
    def __init__(self, config_path: str = "config/data_sources.json"):
        """
        Initializes the fetcher with configuration from JSON file.
        """
        self.config = self._load_config(config_path)
        self.polygon_api_key = os.environ.get("POLYGON_API_KEY")
        
        # Initialize crypto exchange based on config
        self.crypto_exchanges = {}
        crypto_sources = self.config.get('asset_type_mapping', {}).get('crypto', [])
        for source in crypto_sources:
            if source in self.config['data_sources']:
                exchange_name = self.config['data_sources'][source].get('exchange')
                if exchange_name:
                    try:
                        exchange_class = getattr(ccxt, exchange_name)
                        self.crypto_exchanges[source] = exchange_class()
                        print(f"Initialized crypto exchange: {exchange_name} for source {source}")
                    except Exception as e:
                        print(f"Warning: Could not initialize crypto exchange '{exchange_name}': {e}")

        # Headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _load_config(self, path: str) -> Dict:
        """Load data sources configuration from JSON file."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                print(f"Loaded data sources config: {len(config['data_sources'])} sources available")
                return config
        except FileNotFoundError:
            print(f"Warning: Config file {path} not found. Using default configuration.")
            return self._get_default_config()
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {path}. Using default configuration.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Fallback configuration if config file is not available."""
        return {
            "data_sources": {
                "yahoo": {"supported_assets": ["stocks", "etfs", "forex", "crypto"]},
                "crypto": {"supported_assets": ["crypto"], "exchange": "binance"}
            },
            "priority_order": ["yahoo", "crypto"],
            "asset_type_mapping": {
                "stocks": ["yahoo"],
                "crypto": ["crypto", "yahoo"]
            }
        }

    def _fetch_yahoo(self, ticker: str, asset_type: str = 'stocks') -> Optional[pd.DataFrame]:
        """Fetches data from Yahoo Finance."""
        
        # Add this block to format crypto tickers
        if asset_type == 'crypto' and '-' not in ticker:
            ticker = f"{ticker}-USD"

        print(f"    Fetching '{ticker}' from Yahoo Finance...")
        
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="90d", interval="1h")
            if hist.empty:
                print(f"    No data found for {ticker}")
                return None
            print(f"    Successfully fetched {len(hist)} data points")
            return hist
        except Exception as e:
            print(f"    Error fetching {ticker} from Yahoo: {e}")
            return None

    def _fetch_crypto(self, ticker: str, source: str) -> Optional[pd.DataFrame]:
        """Fetches data from the configured crypto exchange."""
        exchange = self.crypto_exchanges.get(source)
        if not exchange:
            print(f"    Crypto exchange for source '{source}' not available")
            return None
            
        print(f"    Fetching '{ticker}' from {exchange.name}...")
        
        try:
            exchange.load_markets()
            
            ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1h', limit=500)
            
            if not ohlcv:
                alt_ticker = ticker.replace('/', '-')
                print(f"    ...ticker not found, trying alternative format: {alt_ticker}")
                ohlcv = exchange.fetch_ohlcv(alt_ticker, timeframe='1h', limit=500)

            if not ohlcv:
                print(f"    No data found for {ticker}")
                return None
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            print(f"    Successfully fetched {len(df)} data points")
            return df
        except Exception as e:
            print(f"    Error fetching {ticker} from {exchange.name}: {e}")
            return None

    def _fetch_google_finance(self, ticker: str, asset_type: str) -> Optional[pd.DataFrame]:
        """Fetches data from Google Finance via web scraping."""
        
        if asset_type == 'forex':
            ticker = ticker.replace('/', '-')
        
        print(f"    Fetching '{ticker}' from Google Finance...")
        try:
            url = f"https://www.google.com/finance/quote/{ticker}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_element = soup.find('div', {'data-source': 'PRICE'})
            if not price_element:
                print(f"    Could not find price data for {ticker}")
                return None
                
            current_price = float(price_element.text.replace('$', '').replace(',', ''))
            
            df = pd.DataFrame({
                'Open': [current_price],
                'High': [current_price], 
                'Low': [current_price],
                'Close': [current_price],
                'Volume': [0]
            }, index=[pd.Timestamp.now()])
            
            print(f"    Successfully fetched current price: ${current_price}")
            return df
            
        except Exception as e:
            print(f"    Error fetching {ticker} from Google Finance: {e}")
            return None

    def _fetch_polygon(self, ticker: str, asset_type: str) -> Optional[pd.DataFrame]:
        """Fetches data from Polygon.io (requires API key)."""
        
        if asset_type == 'forex':
            ticker = f"C:{ticker.replace('/', '')}"
            
        print(f"    Fetching '{ticker}' from Polygon.io...")
        if not self.polygon_api_key:
            print("    Polygon API key not available, skipping")
            return None
        
        try:
            from polygon import RESTClient
            
            client = RESTClient(api_key=self.polygon_api_key)
            
            from datetime import datetime, timedelta
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            aggs = list(client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date,
                to=end_date,
                limit=90
            ))
            
            if not aggs:
                print(f"    No data found for {ticker}")
                return None
            
            data = []
            for agg in aggs:
                data.append({
                    'Date': datetime.fromtimestamp(agg.timestamp / 1000).date(),
                    'Open': agg.open,
                    'High': agg.high,
                    'Low': agg.low,
                    'Close': agg.close,
                    'Volume': agg.volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('Date', inplace=True)
            df.index = pd.to_datetime(df.index)
            
            print(f"    Successfully fetched {len(df)} days of data")
            return df
            
        except Exception as e:
            print(f"    Error fetching {ticker} from Polygon.io: {e}")
            return None

    def get_data(self, ticker: str, asset_type: str = 'stocks', preferred_sources: List[str] = None) -> Optional[pd.DataFrame]:
        """
        Main method to fetch data using configurable sources with fallback strategy.
        """
        if preferred_sources:
            sources_to_try = preferred_sources
        else:
            sources_to_try = self.config.get('asset_type_mapping', {}).get(
                asset_type, 
                self.config.get('priority_order', ['yahoo'])
            )
        
        print(f"    Trying sources for {asset_type} '{ticker}': {sources_to_try}")
        
        for source in sources_to_try:
            if source not in self.config['data_sources']:
                print(f"    Source '{source}' not configured, skipping")
                continue
                
            source_config = self.config['data_sources'][source]
            
            if asset_type not in source_config.get('supported_assets', []):
                print(f"    Source '{source}' doesn't support {asset_type}, skipping")
                continue
                
            if source_config.get('api_key_required', False):
                api_key_var = source_config.get('api_key_env_var')
                if api_key_var and not os.environ.get(api_key_var):
                    print(f"    Source '{source}' requires API key ({api_key_var}), skipping")
                    continue
            
            try:
                if source == 'yahoo' and asset_type == 'crypto':
                    fetch_ticker = ticker.replace('/', '-')
                else:
                    fetch_ticker = ticker
                
                data = self._fetch_from_source(source, fetch_ticker, asset_type)
                if data is not None and not data.empty:
                    print(f"    ✅ Successfully fetched from {source}")
                    return data
                else:
                    print(f"    ❌ No data returned from {source}")
            except Exception as e:
                print(f"    ❌ Error with {source}: {e}")
                continue
        
        print(f"    ❌ Failed to fetch data for '{ticker}' from all available sources")
        return None

    def _fetch_from_source(self, source: str, ticker: str, asset_type: str) -> Optional[pd.DataFrame]:
        """Route to the appropriate fetcher method based on source name."""
        source_methods = {
            'yahoo': lambda t: self._fetch_yahoo(t, asset_type), # Pass asset_type here
            'polygon': lambda t: self._fetch_polygon(t, asset_type),
            'crypto': lambda t: self._fetch_crypto(t, source),
            'google_finance': lambda t: self._fetch_google_finance(t, asset_type),
            'coinbase': lambda t: self._fetch_crypto(t, source),
            'kucoin': lambda t: self._fetch_crypto(t, source),
            'kraken': lambda t: self._fetch_crypto(t, source),
            'bybit': lambda t: self._fetch_crypto(t, source),
            'gateio': lambda t: self._fetch_crypto(t, source),
            'mexc': lambda t: self._fetch_crypto(t, source)
        }
        
        method = source_methods.get(source)
        if not method:
            raise ValueError(f"No fetch method implemented for source: {source}")
            
        return method(ticker)