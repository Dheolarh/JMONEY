import yfinance as yf
import ccxt
import pandas as pd
import os
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import concurrent.futures
import time as _time
import math
from utils.logger import logger


class DataFetcher:
    """A unified class to fetch market data from multiple configurable sources.

    Adds structured logging and per-source metrics for retries, failures and successes.
    """

    def __init__(self, config_path: str = "config/data_sources.json", output_manager=None):
        self.config = self._load_config(config_path)
        self.polygon_api_key = os.environ.get("POLYGON_API_KEY")

        # Default network controls (seconds)
        self.default_timeout = int(os.environ.get('FETCH_TIMEOUT_SEC', '10'))
        self.default_retries = int(os.environ.get('FETCH_RETRIES', '2'))
        self.default_backoff = float(os.environ.get('FETCH_BACKOFF', '1.5'))
        # ccxt expects milliseconds
        self.default_timeout_ms = int(self.default_timeout * 1000)
        # Optional OutputManager for alerts
        self.output_manager = output_manager

        # Initialize crypto exchanges if configured
        self.crypto_exchanges = {}
        crypto_sources = self.config.get('asset_type_mapping', {}).get('crypto', [])
        for source in crypto_sources:
            if source in self.config['data_sources']:
                exchange_name = self.config['data_sources'][source].get('exchange')
                if exchange_name:
                    try:
                        exchange_class = getattr(ccxt, exchange_name)
                        try:
                            self.crypto_exchanges[source] = exchange_class({'timeout': self.default_timeout_ms})
                        except Exception:
                            ex = exchange_class()
                            try:
                                ex.timeout = self.default_timeout_ms
                            except Exception:
                                pass
                            self.crypto_exchanges[source] = ex
                        logger.info(f"Initialized crypto exchange: {exchange_name} for source {source}")
                    except Exception as e:
                        logger.fail(f"Could not initialize crypto exchange '{exchange_name}': {e}")

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _load_config(self, path: str) -> Dict:
        """Load data sources configuration from JSON file."""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded data sources config: {len(config.get('data_sources',{}))} sources available")
                return config
        except FileNotFoundError:
            logger.fail(f"Config file {path} not found. Using default configuration.")
            return self._get_default_config()
        except json.JSONDecodeError:
            logger.fail(f"Invalid JSON in {path}. Using default configuration.")
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
        if asset_type == 'crypto' and '-' not in ticker:
            ticker = f"{ticker}-USD"

        logger.info(f"Fetching '{ticker}' from Yahoo Finance...")
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="90d", interval="1h")
            if hist is None or getattr(hist, 'empty', False):
                logger.info(f"No data found for {ticker}")
                return None
            logger.success(f"Successfully fetched {len(hist)} data points for {ticker}")
            return hist
        except Exception as e:
            logger.fail(f"Error fetching {ticker} from Yahoo: {e}")
            return None

    def _fetch_crypto(self, ticker: str, source: str) -> Optional[pd.DataFrame]:
        """Fetches data from the configured crypto exchange."""
        exchange = self.crypto_exchanges.get(source)
        if not exchange:
            logger.fail(f"Crypto exchange for source '{source}' not available")
            return None

        logger.info(f"Fetching '{ticker}' from {exchange.name}...")
        try:
            exchange.load_markets()
            ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1h', limit=500)
            if not ohlcv:
                alt_ticker = ticker.replace('/', '-')
                logger.info(f"Ticker not found, trying alternative format: {alt_ticker}")
                ohlcv = exchange.fetch_ohlcv(alt_ticker, timeframe='1h', limit=500)

            if not ohlcv:
                logger.info(f"No data found for {ticker} on {exchange.name}")
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            logger.success(f"Successfully fetched {len(df)} data points from {exchange.name} for {ticker}")
            return df
        except Exception as e:
            logger.fail(f"Error fetching {ticker} from {exchange.name}: {e}")
            return None

    def _fetch_google_finance(self, ticker: str, asset_type: str) -> Optional[pd.DataFrame]:
        """Fetches data from Google Finance via web scraping."""
        if asset_type == 'forex':
            ticker = ticker.replace('/', '-')

        logger.info(f"Fetching '{ticker}' from Google Finance...")
        try:
            url = f"https://www.google.com/finance/quote/{ticker}"
            response = requests.get(url, headers=self.headers, timeout=self.default_timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            price_element = soup.find('div', {'data-source': 'PRICE'})
            if not price_element:
                logger.info(f"Could not find price data for {ticker}")
                return None
            current_price = float(price_element.text.replace('$', '').replace(',', ''))
            df = pd.DataFrame({
                'Open': [current_price],
                'High': [current_price],
                'Low': [current_price],
                'Close': [current_price],
                'Volume': [0]
            }, index=[pd.Timestamp.now()])
            logger.success(f"Successfully fetched current price: ${current_price} for {ticker}")
            return df
        except Exception as e:
            logger.fail(f"Error fetching {ticker} from Google Finance: {e}")
            return None

    def _run_with_timeout(self, func, timeout: int):
        """Run func() with timeout (seconds). Returns result or raises TimeoutError."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise TimeoutError(f"Operation timed out after {timeout} seconds")

    def _call_with_retries(self, func_callable, timeout: int = None, retries: int = None, backoff: float = None, metric_prefix: str = None):
        """Call a callable with retries and exponential backoff. Returns result or raises last exception."""
        if timeout is None:
            timeout = self.default_timeout
        if retries is None:
            retries = self.default_retries
        if backoff is None:
            backoff = self.default_backoff

        attempt = 0
        last_exc = None
        while attempt <= retries:
            try:
                return self._run_with_timeout(func_callable, timeout)
            except Exception as e:
                last_exc = e
                if metric_prefix:
                    try:
                        logger.increment_metric(f"{metric_prefix}.retry")
                    except Exception:
                        pass
                wait = backoff * (2 ** attempt)
                wait = min(wait, 30)
                logger.info(f"Retry {attempt+1}/{retries} failed: {e}. Backing off {wait:.1f}s")
                _time.sleep(wait)
                attempt += 1
                continue

        if metric_prefix:
            try:
                logger.increment_metric(f"{metric_prefix}.failure")
            except Exception:
                pass
        raise last_exc

    def _fetch_polygon(self, ticker: str, asset_type: str) -> Optional[pd.DataFrame]:
        """Fetches data from Polygon.io (requires API key)."""
        if asset_type == 'forex':
            ticker = f"C:{ticker.replace('/', '')}"

        logger.info(f"Fetching '{ticker}' from Polygon.io...")
        if not self.polygon_api_key:
            logger.info("Polygon API key not available, skipping")
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
                logger.info(f"No data found for {ticker}")
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
            logger.success(f"Successfully fetched {len(df)} days of data from Polygon for {ticker}")
            return df
        except Exception as e:
            logger.fail(f"Error fetching {ticker} from Polygon.io: {e}")
            return None

    def get_data(self, ticker: str, asset_type: str = 'stocks', preferred_sources: List[str] = None) -> Optional[pd.DataFrame]:
        """Main method to fetch data using configurable sources with fallback strategy."""
        if preferred_sources:
            sources_to_try = preferred_sources
        else:
            sources_to_try = self.config.get('asset_type_mapping', {}).get(asset_type, self.config.get('priority_order', ['yahoo']))

        logger.info(f"Trying sources for {asset_type} '{ticker}': {sources_to_try}")

        for source in sources_to_try:
            if source not in self.config['data_sources']:
                logger.info(f"Source '{source}' not configured, skipping")
                continue

            source_config = self.config['data_sources'][source]
            if asset_type not in source_config.get('supported_assets', []):
                logger.info(f"Source '{source}' doesn't support {asset_type}, skipping")
                continue

            if source_config.get('api_key_required', False):
                api_key_var = source_config.get('api_key_env_var')
                if api_key_var and not os.environ.get(api_key_var):
                    logger.info(f"Source '{source}' requires API key ({api_key_var}), skipping")
                    continue

            try:
                fetch_ticker = ticker.replace('/', '-') if source == 'yahoo' and asset_type == 'crypto' else ticker
                source_cfg = self.config['data_sources'].get(source, {})
                timeout = int(source_cfg.get('timeout', self.default_timeout))
                retries = int(source_cfg.get('retries', self.default_retries))
                backoff = float(source_cfg.get('backoff', self.default_backoff))

                metric_prefix = f"fetch.{source}"
                try:
                    data = self._call_with_retries(lambda: self._fetch_from_source(source, fetch_ticker, asset_type), timeout=timeout, retries=retries, backoff=backoff, metric_prefix=metric_prefix)
                    if data is not None and not getattr(data, 'empty', False):
                        logger.success(f"Successfully fetched from {source}")
                        logger.increment_metric(f"{metric_prefix}.success")

                        # Price cross-check: compare yahoo vs polygon when both present
                        try:
                            threshold_pct = float(os.environ.get('PRICE_MISMATCH_THRESHOLD_PCT', '10'))
                        except Exception:
                            threshold_pct = 10.0

                        other_source = None
                        if source == 'yahoo' and 'polygon' in sources_to_try:
                            other_source = 'polygon'
                        elif source == 'polygon' and 'yahoo' in sources_to_try:
                            other_source = 'yahoo'

                        if other_source:
                            try:
                                other_cfg = self.config['data_sources'].get(other_source, {})
                                other_timeout = int(other_cfg.get('timeout', self.default_timeout))
                                other_retries = int(other_cfg.get('retries', self.default_retries))
                                other_backoff = float(other_cfg.get('backoff', self.default_backoff))

                                other_data = self._call_with_retries(lambda: self._fetch_from_source(other_source, fetch_ticker, asset_type), timeout=other_timeout, retries=other_retries, backoff=other_backoff, metric_prefix=f"fetch.{other_source}")
                                if other_data is not None and not getattr(other_data, 'empty', False):
                                    self._maybe_cross_check_prices(ticker, source, data, other_source, other_data, threshold_pct)
                            except Exception as e:
                                logger.info(f"Note: could not fetch {other_source} for cross-check: {e}")

                        return data
                    else:
                        logger.fail(f"No data returned from {source}")
                        logger.increment_metric(f"{metric_prefix}.no_data")
                except Exception as e:
                    logger.fail(f"Error with {source}: {e}")
                    logger.increment_metric(f"{metric_prefix}.exception")
                    continue
            except Exception as e:
                logger.fail(f"Unexpected error iterating sources: {e}")
                continue

        logger.fail(f"Failed to fetch data for '{ticker}' from all available sources")
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

    def _maybe_cross_check_prices(self, ticker: str, src_a: str, data_a: pd.DataFrame, src_b: str, data_b: pd.DataFrame, threshold_pct: float):
        """Compare latest close prices between two dataframes and alert if difference > threshold_pct."""
        try:
            def latest_close(df: pd.DataFrame):
                if df is None or df.empty:
                    return None
                col = 'Close' if 'Close' in df.columns else next((c for c in df.columns if c.lower().startswith('close')), df.columns[-1])
                return float(df[col].iloc[-1])

            price_a = latest_close(data_a)
            price_b = latest_close(data_b)
            if price_a is None or price_b is None:
                return

            diff_pct = abs(price_a - price_b) / max((price_a + price_b) / 2.0, 1e-9) * 100.0
            if diff_pct >= threshold_pct:
                msg = f"Price mismatch for {ticker}: {src_a}={price_a} vs {src_b}={price_b} ({diff_pct:.1f}% diff)"
                logger.fail(f"WARNING: {msg}")
                try:
                    if self.output_manager:
                        alert = {
                            'Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Ticker': ticker,
                            'Source A': src_a,
                            'Price A': price_a,
                            'Source B': src_b,
                            'Price B': price_b,
                            'Diff %': f"{diff_pct:.2f}%",
                            'Note': 'Price mismatch alert (> threshold)'
                        }
                        try:
                            self.output_manager.write_price_alert(alert)
                        except Exception as e:
                            logger.fail(f"Could not write price alert to sheets: {e}")
                except Exception:
                    pass
        except Exception as e:
            logger.fail(f"Error during price cross-check: {e}")