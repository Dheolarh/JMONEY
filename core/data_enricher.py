from .data_fetcher import DataFetcher
from .ai_analyzer import AIAnalyzer
import os

class DataEnricher:
    """
    Takes a list of identified assets and enriches them with market data
    using an AI-driven, multi-source fetching strategy.
    """
    def __init__(self, analyzer: AIAnalyzer):
        """Initializes the DataEnricher with an AIAnalyzer instance."""
        self.fetcher = DataFetcher()
        self.analyzer = analyzer

    def enrich_assets(self, assets: list[dict]) -> list[dict]:
        """
        Enriches each asset with its corresponding market data using AI for formatting.
        """
        enriched_assets = []
        for asset in assets:
            original_ticker = asset.get('ticker')
            if not original_ticker:
                continue

            print(f"--> Enriching '{original_ticker}' with market data...")
            
            # Use AI to get asset type and formatted ticker
            ticker_details = self.analyzer.get_ticker_details(original_ticker)
            
            if not ticker_details:
                print(f"    ...FAILED to get enrichment details from AI for '{original_ticker}'.")
                continue

            asset_type = ticker_details.get('asset_type')
            ticker_to_fetch = ticker_details.get('formatted_ticker')

            if not all([asset_type, ticker_to_fetch]):
                print(f"    ...FAILED, AI returned incomplete data for '{original_ticker}'.")
                continue

            print(f"    ...AI identified as {asset_type.title()} with ticker '{ticker_to_fetch}'.")
            
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