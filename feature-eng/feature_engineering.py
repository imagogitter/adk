"""
Feature Engineering module for crypto trading data.

This module handles calculation of technical indicators using pandas-ta library.
Indicators include:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
"""

import os
from typing import List

import pandas as pd
import pandas_ta as ta
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()


class FeatureEngineering:
    """Handles technical indicator calculations and storage for crypto trading data.

    This class integrates with InfluxDB to fetch OHLCV data, calculate technical indicators,
    and store the results. It supports multiple symbols and timeframes, implementing various
    technical analysis indicators using the pandas-ta library.
    """

    def __init__(self) -> None:
        """Initialize FeatureEngineering with InfluxDB connection."""
        self.client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            token=os.getenv("INFLUXDB_TOKEN"),
            org=os.getenv("INFLUXDB_ORG"),
        )
        self.read_api = self.client.query_api()
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def fetch_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data from InfluxDB.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        query = f"""
        from(bucket: '{os.getenv('INFLUXDB_BUCKET')}')
            |> range(start: -30d)
            |> filter(fn: (r) => r['symbol'] == '{symbol}' and r['timeframe'] == '{timeframe}')
            |> limit(n: {limit})
        """

        result = self.read_api.query_data_frame(query)
        if result.empty:
            return pd.DataFrame()

        df = result.sort_values("_time")
        df = df.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for the given OHLCV data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added technical indicators
        """
        if df.empty:
            return df

        # Simple Moving Averages
        df["SMA_20"] = ta.sma(df["Close"], length=20)
        df["SMA_50"] = ta.sma(df["Close"], length=50)

        # Exponential Moving Averages
        df["EMA_12"] = ta.ema(df["Close"], length=12)
        df["EMA_26"] = ta.ema(df["Close"], length=26)

        # RSI
        df["RSI_14"] = ta.rsi(df["Close"], length=14)

        # MACD
        macd = ta.macd(df["Close"])
        df = pd.concat([df, macd], axis=1)

        # Bollinger Bands
        bbands = ta.bbands(df["Close"], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)

        return df

    def write_features_to_influx(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        Write calculated features back to InfluxDB.

        Args:
            df: DataFrame with calculated features
            symbol: Trading pair symbol
            timeframe: Candlestick timeframe
        """
        feature_columns = [
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

        # Prepare data for InfluxDB
        for _, row in df.iterrows():
            point = {
                "measurement": "technical_features",
                "tags": {"symbol": symbol, "timeframe": timeframe},
                "time": row["_time"],
                "fields": {col: float(row[col]) for col in feature_columns if pd.notna(row[col])},
            }
            self.write_api.write(bucket=os.getenv("INFLUXDB_BUCKET"), record=point)

    def process_historical_data(self, symbols: List[str], timeframes: List[str]) -> None:
        """
        Process historical data for multiple symbols and timeframes.

        Args:
            symbols: List of trading pair symbols
            timeframes: List of timeframes to process
        """
        for symbol in symbols:
            for timeframe in timeframes:
                # Fetch data
                df = self.fetch_ohlcv_data(symbol, timeframe)
                if df.empty:
                    continue

                # Calculate features
                df_features = self.calculate_indicators(df)

                # Write features back to InfluxDB
                self.write_features_to_influx(df_features, symbol, timeframe)


if __name__ == "__main__":
    # Example usage
    feature_eng = FeatureEngineering()
    symbols = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h", "1d"]
    feature_eng.process_historical_data(symbols, timeframes)
