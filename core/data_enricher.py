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
        self.asset_patterns = [
            {'type': 'crypto_pair', 'pattern': re.compile(r'^(BTC|ETH|XRP|SOL|DOGE|ADA|AVAX|LTC|BCH|XLM|TRX|MATIC|DOT|LINK|TON|SHIB|LEO|OKB|ATOM|UNI|XMR|ETC|FIL|ICP|LDO|HBAR|APT|CRO|VET|NEAR|QNT|OP|IMX|GRT|AAVE|ALGO|EGLD|STX|MANA|SAND|AXS|EOS|XTZ|THETA|FTM|APE|CHZ|ZEC|FLOW|SNX|KCS|BTT|CRV|GALA|MKR|KLAY|DASH|RUNE|CAKE|ENJ|LRC|BAT|WAVES|CVX|TWT|ZIL|PAXG|HOT|1INCH|COMP|KAVA|NEXO|ANKR|QTUM|BNB)[/-](USDT|BUSD|BTC|ETH|USDC|DAI|USD)$')},            
            {'type': 'crypto_standalone', 'pattern': re.compile(r'^(BTC|ETH|XRP|SOL|DOGE|ADA|AVAX|LTC|BCH|XLM|TRX|MATIC|DOT|LINK|TON|SHIB|LEO|OKB|ATOM|UNI|XMR|ETC|FIL|ICP|LDO|HBAR|APT|CRO|VET|NEAR|QNT|OP|IMX|GRT|AAVE|ALGO|EGLD|STX|MANA|SAND|AXS|EOS|XTZ|THETA|FTM|APE|CHZ|ZEC|FLOW|SNX|KCS|BTT|CRV|GALA|MKR|KLAY|DASH|RUNE|CAKE|ENJ|LRC|BAT|WAVES|CVX|TWT|ZIL|PAXG|HOT|1INCH|COMP|KAVA|NEXO|ANKR|QTUM|BNB)$')},
            {'type': 'forex', 'pattern': re.compile(r'^[A-Z]{3}/[A-Z]{3}$')},
            {'type': 'indices', 'pattern': re.compile(r'^(SPY|QQQ|DJI|IXIC|RUT|VIX)$')},
            {'type': 'stocks', 'pattern': re.compile(r'^[A-Z]{1,5}$')} # Default for stocks
        ]

    def _determine_asset_type(self, ticker: str) -> tuple[str, str, str]:
        """
        Intelligently determines the asset type and the ticker format needed for fetching.
        """
        upper_ticker = ticker.upper()

        for asset_pattern in self.asset_patterns:
            if asset_pattern['pattern'].match(upper_ticker):
                asset_type = asset_pattern['type']
                
                if asset_type == 'forex':
                    print("    ...identified as Forex.")
                    formatted_ticker = f"{upper_ticker.replace('/', '')}=X"
                    return 'forex', formatted_ticker, upper_ticker
                
                if asset_type in ['crypto_pair', 'crypto_standalone']:
                    print("    ...identified as Crypto.")
                    # For standalone tickers, append '-USD' for fetching compatibility
                    if asset_type == 'crypto_standalone':
                        formatted_ticker = f"{upper_ticker}-USD"
                    else:
                        formatted_ticker = upper_ticker.replace('/', '-')
                    return 'crypto', formatted_ticker, upper_ticker

                print(f"    ...identified as {asset_type.title()}.")
                return asset_type, upper_ticker, upper_ticker
        
        print("    ...no specific pattern matched, defaulting to Stock.")
        return 'stocks', upper_ticker, upper_ticker

    def enrich_assets(self, assets: list[dict]) -> list[dict]:
        """
        Enriches each asset with its corresponding market data.
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