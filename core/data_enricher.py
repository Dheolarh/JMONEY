from .data_fetcher import DataFetcher
import re

class DataEnricher:
    """
    Takes a list of identified assets and enriches them with market data
    using a dynamic, multi-source fetching strategy.
    """
    def __init__(self):
        """Initializes the DataEnricher."""
        self.fetcher = DataFetcher()
        # Define patterns for asset type detection
        self.asset_patterns = [
            {'type': 'forex', 'pattern': re.compile(r'^[A-Z]{3}/[A-Z]{3}$')},
            # Corrected crypto pattern to handle "/"
            {'type': 'crypto', 'pattern': re.compile(r'^[A-Z0-9]+/(USDT|BUSD|BTC|ETH|USDC|DAI)$')},
            {'type': 'indices', 'pattern': re.compile(r'^(SPY|QQQ|DJI|IXIC|RUT|VIX)$')},
            {'type': 'stocks', 'pattern': re.compile(r'^[A-Z]{1,5}$')} # Default for stocks
        ]

    def _determine_asset_type(self, ticker: str) -> tuple[str, str, str]:
        """
        Intelligently determines the asset type and the ticker format needed for fetching.

        Args:
            ticker: The original ticker symbol from the AI.

        Returns:
            A tuple containing the asset type, formatted ticker string, and raw ticker.
        """
        upper_ticker = ticker.upper()

        for asset_pattern in self.asset_patterns:
            if asset_pattern['pattern'].match(upper_ticker):
                asset_type = asset_pattern['type']
                print(f"    ...identified as {asset_type.title()}.")
                
                # Format ticker for Yahoo Finance if it's a forex pair
                if asset_type == 'forex':
                    formatted_ticker = f"{upper_ticker.replace('/', '')}=X"
                    return asset_type, formatted_ticker, upper_ticker
                
                # For crypto, the ticker is already in the correct format for ccxt
                if asset_type == 'crypto':
                    return asset_type, upper_ticker, upper_ticker

                return asset_type, upper_ticker, upper_ticker
        
        # Default to stocks if no other pattern matches
        print("    ...no specific pattern matched, defaulting to Stock.")
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