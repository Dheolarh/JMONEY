import os
import pandas as pd
import pytest
from unittest.mock import Mock

from core.data_fetcher import DataFetcher


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Ensure a consistent threshold
    monkeypatch.setenv('PRICE_MISMATCH_THRESHOLD_PCT', '10')
    yield


def make_df(price: float):
    return pd.DataFrame({'Close': [price]}, index=[pd.Timestamp.now()])


def test_price_mismatch_triggers_alert(monkeypatch):
    """When Yahoo and Polygon disagree beyond threshold, OutputManager.write_price_alert is called."""
    yahoo_df = make_df(100.0)
    poly_df = make_df(150.0)

    # Patch fetcher methods to return our fake frames
    monkeypatch.setattr(DataFetcher, '_fetch_yahoo', lambda self, t, asset_type='stocks': yahoo_df)
    monkeypatch.setattr(DataFetcher, '_fetch_polygon', lambda self, t, asset_type='stocks': poly_df)

    mock_output = Mock()

    df = DataFetcher(output_manager=mock_output).get_data('AAPL', asset_type='stocks', preferred_sources=['yahoo', 'polygon'])

    assert df is not None
    # Should return yahoo data (first source)
    assert float(df['Close'].iloc[-1]) == 100.0
    # Ensure the price alert was attempted because 100 vs 150 is > 10%
    assert mock_output.write_price_alert.called


def test_fallback_to_crypto_when_yahoo_missing(monkeypatch):
    """If Yahoo returns no data, crypto source is used as fallback."""
    yahoo_none = None
    crypto_df = make_df(20000.0)

    monkeypatch.setattr(DataFetcher, '_fetch_yahoo', lambda self, t, asset_type='crypto': yahoo_none)
    monkeypatch.setattr(DataFetcher, '_fetch_crypto', lambda self, t, source: crypto_df)

    df = DataFetcher().get_data('BTC/USD', asset_type='crypto', preferred_sources=['yahoo', 'crypto'])

    assert df is not None
    assert float(df['Close'].iloc[-1]) == 20000.0
