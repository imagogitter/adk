"""Tests for the feature engineering module."""

from typing import Any

import numpy as np
import pandas as pd
import pytest
from feature_engineering import FeatureEngineering


@pytest.fixture
def feature_eng() -> FeatureEngineering:
    """Create FeatureEngineering instance for testing."""
    return FeatureEngineering()


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    return pd.DataFrame(
        {
            "_time": pd.date_range(start="2025-01-01", periods=100, freq="H"),
            "Open": [100 + i * 0.1 for i in range(100)],
            "High": [101 + i * 0.1 for i in range(100)],
            "Low": [99 + i * 0.1 for i in range(100)],
            "Close": [100.5 + i * 0.1 for i in range(100)],
            "Volume": [1000 + i * 10 for i in range(100)],
        }
    )


def test_calculate_indicators(
    feature_eng: FeatureEngineering,
    sample_ohlcv_data: pd.DataFrame,
) -> None:
    """Test calculation of technical indicators."""
    df_features = feature_eng.calculate_indicators(sample_ohlcv_data)

    # Check if all expected indicators are present
    expected_columns = [
        "SMA_20",
        "SMA_50",
        "EMA_12",
        "EMA_26",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "MACDh_12_26_9",
        "BBL_20_2.0",
        "BBM_20_2.0",
        "BBU_20_2.0",
        "BBB_20_2.0",
    ]
    for col in expected_columns:
        assert col in df_features.columns

    # Verify SMA calculations
    assert not df_features["SMA_20"].isna().all()
    assert not df_features["SMA_50"].isna().all()
    assert df_features["SMA_20"].iloc[19] is not None  # First valid value
    assert df_features["SMA_50"].iloc[49] is not None  # First valid value

    # Verify EMA calculations
    assert not df_features["EMA_12"].isna().all()
    assert not df_features["EMA_26"].isna().all()

    # Verify RSI calculations
    assert not df_features["RSI_14"].isna().all()
    assert all(0 <= x <= 100 for x in df_features["RSI_14"].dropna())

    # Verify MACD calculations
    assert not df_features["MACD_12_26_9"].isna().all()
    assert not df_features["MACDs_12_26_9"].isna().all()
    assert not df_features["MACDh_12_26_9"].isna().all()

    # Verify Bollinger Bands calculations
    assert not df_features["BBM_20_2.0"].isna().all()  # Middle band
    assert not df_features["BBU_20_2.0"].isna().all()  # Upper band
    assert not df_features["BBL_20_2.0"].isna().all()  # Lower band
    assert not df_features["BBB_20_2.0"].isna().all()  # Bandwidth


def test_empty_dataframe(feature_eng: FeatureEngineering) -> None:
    """Test handling of empty DataFrame."""
    empty_df = pd.DataFrame()
    result = feature_eng.calculate_indicators(empty_df)
    assert result.empty


def test_fetch_ohlcv_data(feature_eng: FeatureEngineering, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetching OHLCV data from InfluxDB."""

    def mock_query_data_frame(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "_time": pd.date_range(start="2025-01-01", periods=10, freq="H"),
                "open": np.random.rand(10) * 100,
                "high": np.random.rand(10) * 100,
                "low": np.random.rand(10) * 100,
                "close": np.random.rand(10) * 100,
                "volume": np.random.rand(10) * 1000,
            }
        )

    monkeypatch.setattr(feature_eng.read_api, "query_data_frame", mock_query_data_frame)

    df = feature_eng.fetch_ohlcv_data("BTC/USDT", "1h", 10)
    assert not df.empty
    assert all(col in df.columns for col in ["Open", "High", "Low", "Close", "Volume"])
    assert len(df) == 10


def test_write_features_to_influx(
    feature_eng: FeatureEngineering,
    sample_ohlcv_data: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test writing features back to InfluxDB."""
    write_points: list[dict[str, Any]] = []

    def mock_write(*args: Any, **kwargs: Any) -> None:
        if record := kwargs.get("record"):
            write_points.append(record)

    monkeypatch.setattr(feature_eng.write_api, "write", mock_write)

    df_features = feature_eng.calculate_indicators(sample_ohlcv_data)
    feature_eng.write_features_to_influx(df_features, "BTC/USDT", "1h")

    assert len(write_points) > 0
    for point in write_points:
        assert point["measurement"] == "technical_features"
        assert point["tags"]["symbol"] == "BTC/USDT"
        assert point["tags"]["timeframe"] == "1h"
        assert isinstance(point["time"], pd.Timestamp)
        assert isinstance(point["fields"], dict)


def test_process_historical_data(
    feature_eng: FeatureEngineering, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test processing historical data for multiple symbols and timeframes."""
    processed_data: list[tuple[str, str]] = []

    def mock_fetch_ohlcv_data(symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        return sample_ohlcv_data()

    def mock_write_features(*args: Any, **kwargs: Any) -> None:
        processed_data.append((args[1], args[2]))  # symbol, timeframe

    monkeypatch.setattr(feature_eng, "fetch_ohlcv_data", mock_fetch_ohlcv_data)
    monkeypatch.setattr(feature_eng, "write_features_to_influx", mock_write_features)

    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h"]

    feature_eng.process_historical_data(symbols, timeframes)

    assert len(processed_data) == len(symbols) * len(timeframes)
    assert all(s in [p[0] for p in processed_data] for s in symbols)
    assert all(t in [p[1] for p in processed_data] for t in timeframes)
