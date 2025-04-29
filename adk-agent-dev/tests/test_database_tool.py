"""Tests for DatabaseTool."""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from influxdb_client import InfluxDBClient
from tools.database_tool import DatabaseTool


@pytest.fixture
def mock_influxdb():
    """Mock InfluxDB client and APIs."""
    with patch("influxdb_client.InfluxDBClient") as mock_client:
        client = mock_client.return_value
        client.query_api.return_value = MagicMock()
        client.write_api.return_value = MagicMock()
        yield client


@pytest.fixture
def database_tool(mock_influxdb):
    """Create DatabaseTool instance with mocked client."""
    return DatabaseTool()


@pytest.fixture
def sample_indicators_df():
    """Create sample technical indicators DataFrame."""
    return pd.DataFrame(
        {
            "_time": [datetime.now()],
            "SMA_20": [45000.0],
            "SMA_50": [43000.0],
            "EMA_12": [46000.0],
            "EMA_26": [44000.0],
            "RSI_14": [65.0],
            "MACD_12_26_9": [500.0],
            "MACDs_12_26_9": [450.0],
            "MACDh_12_26_9": [50.0],
            "BBL_20_2.0": [42000.0],
            "BBM_20_2.0": [45000.0],
            "BBU_20_2.0": [48000.0],
        }
    )


@pytest.fixture
def sample_ohlcv_df():
    """Create sample OHLCV DataFrame."""
    return pd.DataFrame(
        {
            "_time": pd.date_range(start="2025-01-01", periods=100, freq="H"),
            "open": np.random.uniform(40000, 50000, 100),
            "high": np.random.uniform(41000, 51000, 100),
            "low": np.random.uniform(39000, 49000, 100),
            "close": np.random.uniform(40000, 50000, 100),
            "volume": np.random.uniform(100, 1000, 100),
        }
    )


def test_get_latest_indicators(database_tool, mock_influxdb, sample_indicators_df):
    """Test retrieving latest technical indicators."""
    # Setup mock return value
    query_api = mock_influxdb.query_api.return_value
    query_api.query_data_frame.return_value = sample_indicators_df

    # Test function
    result = database_tool.get_latest_indicators("BTC/USDT", "1h")

    # Verify results
    assert isinstance(result, dict)
    assert "sma_20" in result
    assert "rsi_14" in result
    assert "macd" in result
    assert len(result) == 11  # All indicators present
    assert result["sma_20"] == 45000.0
    assert result["rsi_14"] == 65.0


def test_get_latest_indicators_empty(database_tool, mock_influxdb):
    """Test handling empty result from database."""
    query_api = mock_influxdb.query_api.return_value
    query_api.query_data_frame.return_value = pd.DataFrame()

    result = database_tool.get_latest_indicators("BTC/USDT", "1h")
    assert result == {}


def test_get_ohlcv_history(database_tool, mock_influxdb, sample_ohlcv_df, sample_indicators_df):
    """Test retrieving historical OHLCV and indicator data."""
    # Setup mock returns
    query_api = mock_influxdb.query_api.return_value
    query_api.query_data_frame.side_effect = [sample_ohlcv_df, sample_indicators_df]

    # Test function
    ohlcv_df, indicators = database_tool.get_ohlcv_history("BTC/USDT", "1h", 100)

    # Verify OHLCV data
    assert isinstance(ohlcv_df, pd.DataFrame)
    assert not ohlcv_df.empty
    assert len(ohlcv_df) == 100
    assert all(col in ohlcv_df.columns for col in ["open", "high", "low", "close", "volume"])

    # Verify indicators
    assert isinstance(indicators, dict)
    assert "moving_averages" in indicators
    assert "oscillators" in indicators
    assert "macd" in indicators
    assert "bollinger" in indicators


def test_write_trade_record(database_tool, mock_influxdb):
    """Test writing trade records to database."""
    write_api = mock_influxdb.write_api.return_value

    result = database_tool.write_trade_record(
        symbol="BTC/USDT", timeframe="1h", trade_type="buy", entry_price=45000.0, size=1.0
    )

    assert result is True
    write_api.write.assert_called_once()


def test_get_trade_history(database_tool, mock_influxdb):
    """Test retrieving trade history."""
    # Setup mock data
    trade_history = pd.DataFrame(
        {
            "_time": pd.date_range(start="2025-01-01", periods=5, freq="H"),
            "price": [45000.0, 46000.0, 44000.0, 47000.0, 45500.0],
            "size": [1.0, 0.5, 1.0, 0.8, 1.2],
            "type": ["buy", "sell", "buy", "sell", "buy"],
        }
    )

    query_api = mock_influxdb.query_api.return_value
    query_api.query_data_frame.return_value = trade_history

    # Test function
    result = database_tool.get_trade_history("BTC/USDT")

    # Verify results
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert len(result) == 5
    assert all(col in result.columns for col in ["_time", "price", "size", "type"])


def test_error_handling(database_tool, mock_influxdb):
    """Test error handling in database operations."""
    query_api = mock_influxdb.query_api.return_value
    query_api.query_data_frame.side_effect = Exception("Database error")

    # Test error handling in different methods
    assert database_tool.get_latest_indicators("BTC/USDT", "1h") == {}

    ohlcv_df, indicators = database_tool.get_ohlcv_history("BTC/USDT", "1h")
    assert ohlcv_df.empty
    assert indicators == {}

    history_df = database_tool.get_trade_history("BTC/USDT")
    assert history_df.empty
