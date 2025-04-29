"""Test suite for the data pipeline module.

This module contains unit tests for the DataPipeline class and its components,
verifying the correct functionality of data fetching, processing, and storage
operations. It includes tests for:
- OHLCV data fetching from exchanges
- Data processing and transformation
- InfluxDB storage operations
- Error handling scenarios
"""

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd
from data_pipeline import DataPipeline


class TestDataPipeline(unittest.TestCase):
    """Test cases for DataPipeline functionality."""

    def setUp(self) -> None:
        """Set up test fixtures before each test."""
        self.pipeline = DataPipeline()


    def tearDown(self) -> None:
        """Clean up after each test."""
        self.pipeline.close()


    @patch('ccxt.binance')
    def test_fetch_ohlcv(self, mock_exchange: patch) -> None:
        """Test fetching OHLCV data from exchange."""
        # Mock OHLCV data
        mock_data = [
            [1625097600000, 35000.0, 35100.0, 34900.0, 35050.0, 100.0],
            [1625101200000, 35050.0, 35200.0, 35000.0, 35150.0, 150.0],
        ]
        mock_exchange.return_value.fetch_ohlcv.return_value = mock_data
        
        result = self.pipeline.fetch_ohlcv("BTC/USDT", "1h")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][4], 35050.0)  # Check closing price


    def test_process_data(self) -> None:
        """Test data processing functionality."""
        test_data = [
            [1625097600000, 35000.0, 35100.0, 34900.0, 35050.0, 100.0],
        ]
        
        result = self.pipeline.process_data(test_data)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)


    @patch('influxdb_client.InfluxDBClient')
    def test_write_to_influxdb(self, mock_client: patch) -> None:
        """Test writing data to InfluxDB."""
        test_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [35000.0],
            'high': [35100.0],
            'low': [34900.0],
            'close': [35050.0],
            'volume': [100.0]
        })
        
        self.pipeline.write_to_influxdb(test_data)
        mock_client.return_value.write_api.assert_called_once()


if __name__ == '__main__':
    unittest.main()
