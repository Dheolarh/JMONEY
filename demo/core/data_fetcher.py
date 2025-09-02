import pandas as pd
import os
from typing import Optional

class DataFetcher:
    """
    (DEMO VERSION)
    A unified class to fetch market data from local CSV files.
    """
    def __init__(self, config_path: str = "data/mock_market_data/"):
        """
        Initializes the fetcher with a path to the directory containing mock CSV data.
        """
        self.data_path = config_path
        print(f"Initialized Demo DataFetcher. Reading from: {self.data_path}")

    def get_data(self, ticker: str, asset_type: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        Main method to fetch data from a local CSV file.
        """
        print(f"    Fetching '{ticker}' from local CSV files...")
        file_path = os.path.join(self.data_path, f"{ticker}.csv")

        try:
            if not os.path.exists(file_path):
                print(f"    No mock data file found for {ticker} at {file_path}")
                return None

            df = pd.read_csv(file_path)
            # Ensure the 'Date' column is parsed correctly as datetime objects
            df['Date'] = pd.to_datetime(df['Date'])
            # Set the 'Date' column as the index for compatibility with scoring engine
            df.set_index('Date', inplace=True)
            
            if df.empty:
                print(f"    No data found for {ticker} in {file_path}")
                return None
                
            print(f"    Successfully fetched {len(df)} data points from CSV.")
            return df
        except Exception as e:
            print(f"    Error fetching {ticker} from local file: {e}")
            return None