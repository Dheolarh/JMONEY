from .data_fetcher import DataFetcher

class DataEnricher:
    """
    Takes a list of identified assets and enriches them with market data
    using a dynamic, multi-source fetching strategy.
    """
    def __init__(self):
        """Initializes the DataEnricher."""
        self.fetcher = DataFetcher()
        # Define known FIAT and CRYPTO currencies to help identify asset types
        self.FIAT_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF']
        self.CRYPTO_CURRENCIES = ['USDT', 'BUSD', 'BTC', 'ETH', 'USDC', 'DAI']

    def _determine_asset_type(self, ticker: str) -> tuple[str, str, str]:
        """
        Intelligently determines the asset type and the ticker format needed for fetching.

        Args:
            ticker: The original ticker symbol from the AI.

        Returns:
            A tuple containing the asset type, formatted ticker string, and raw ticker.
        """
        upper_ticker = ticker.upper()

        # 1. Check for FX Pairs (e.g., EUR/USD)
        if "/" in upper_ticker and len(upper_ticker) == 7:
            base, quote = upper_ticker.split('/')
            if base in self.FIAT_CURRENCIES and quote in self.FIAT_CURRENCIES:
                print(f"    ...identified as FX Pair.")
                # Format for Yahoo Finance: 'EURUSD=X'
                return 'forex', f"{base}{quote}=X", upper_ticker

        # 2. Check for Crypto Pairs (e.g., BTC/USDT)
        if "/" in upper_ticker:
            base, quote = upper_ticker.split('/')
            if quote in self.CRYPTO_CURRENCIES:
                print(f"    ...identified as Crypto Pair.")
                return 'crypto', upper_ticker, upper_ticker

        # 3. Check for common indices (e.g., SPY, QQQ, DJI)
        common_indices = ['SPY', 'QQQ', 'DJI', 'IXIC', 'RUT', 'VIX']
        if upper_ticker in common_indices:
            print(f"    ...identified as Index/ETF.")
            return 'indices', upper_ticker, upper_ticker

        # 4. Default to Stocks/ETFs (e.g., AAPL, MSFT)
        print(f"    ...identified as Stock.")
        return 'stocks', upper_ticker, upper_ticker

    def enrich_assets(self, assets: list[dict]) -> list[dict]:
        """
        Enriches each asset with its corresponding market data using the flexible fetching strategy.
        """
        enriched_assets = []
        for asset in assets:
            original_ticker = asset.get('ticker')
            if not original_ticker:
                continue

            print(f"--> Enriching '{original_ticker}' with market data...")
            
            asset_type, ticker_to_fetch, raw_ticker = self._determine_asset_type(original_ticker)
            
            # Use the new flexible fetching system
            market_data = self.fetcher.get_data(
                ticker=ticker_to_fetch, 
                asset_type=asset_type
            )
            
            if market_data is not None and not market_data.empty:
                asset['market_data'] = market_data
                asset['asset_type'] = asset_type
                asset['formatted_ticker'] = ticker_to_fetch
                enriched_assets.append(asset)
                print(f"    ...SUCCESS, {len(market_data)} data points found.")
            else:
                print(f"    ...FAILED to retrieve market data for '{original_ticker}'.")

        return enriched_assets
