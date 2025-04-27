#!/usr/bin/env python3
"""Data pipeline for fetching OHLCV data from exchanges using ccxt and writing to InfluxDB."""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional, cast

import ccxt
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", ".env.binance"))

# InfluxDB configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

# Exchange configuration
EXCHANGE_ID = os.getenv("EXCHANGE_ID", "binance")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_SECRET = os.getenv("EXCHANGE_SECRET", "")


class DataPipeline:
    """Pipeline for fetching OHLCV data and writing to InfluxDB."""

    def __init__(self, exchange_id: str = EXCHANGE_ID):
        """Initialize the data pipeline with exchange and database connections.

        Args:
            exchange_id: The ID of the exchange to use (default: from env var)
        """
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": EXCHANGE_API_KEY,
                "secret": EXCHANGE_SECRET,
                "enableRateLimit": True,
            }
        )

        # Initialize InfluxDB client
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG,
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

        logger.info(f"Initialized DataPipeline with exchange: {exchange_id}")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 1000,
    ) -> List[List[float]]:
        """Fetch OHLCV data from the exchange.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '1h', '1d')
            since: Timestamp in milliseconds to fetch data from
            limit: Maximum number of candles to fetch

        Returns:
            List of OHLCV candles with [timestamp, open, high, low, close, volume]
        """
        try:
            logger.info(f"Fetching {timeframe} OHLCV data for {symbol} since {since}")
            ohlcv = cast(
                List[List[float]],
                self.exchange.fetch_ohlcv(symbol, timeframe, since, limit),
            )
            logger.info(f"Fetched {len(ohlcv)} candles for {symbol}")
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise

    def fetch_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data for a specified date range.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '1h', '1d')
            start_date: Start date for historical data
            end_date: End date for historical data (defaults to now)

        Returns:
            DataFrame with OHLCV data
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Convert dates to millisecond timestamps
        since = int(start_date.timestamp() * 1000)
        until = int(end_date.timestamp() * 1000)

        all_ohlcv = []
        current_since = since

        # Fetch data in chunks until we reach the end date
        while current_since < until:
            ohlcv_chunk = self.fetch_ohlcv(symbol, timeframe, current_since)
            if not ohlcv_chunk:
                break

            all_ohlcv.extend(ohlcv_chunk)

            # Update the since timestamp for the next iteration
            current_since = int(ohlcv_chunk[-1][0] + 1)

            # Rate limiting
            time.sleep(self.exchange.rateLimit / 1000)

        # Convert to DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        return df

    def write_to_influxdb(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> None:
        """Write OHLCV data to InfluxDB.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '1h', '1d')
        """
        try:
            # Reset index to access the timestamp column
            df = df.reset_index()

            # Clean symbol for use as a tag (replace / with _)
            clean_symbol = symbol.replace("/", "_")

            points = []
            for _, row in df.iterrows():
                point = (
                    Point("ohlcv")
                    .tag("symbol", clean_symbol)
                    .tag("timeframe", timeframe)
                    .field("open", float(row["open"]))
                    .field("high", float(row["high"]))
                    .field("low", float(row["low"]))
                    .field("close", float(row["close"]))
                    .field("volume", float(row["volume"]))
                    .time(row["timestamp"])
                )
                points.append(point)

            self.write_api.write(bucket=INFLUXDB_BUCKET, record=points)
            logger.info(
                f"Successfully wrote {len(points)} points to InfluxDB for {symbol} ({timeframe})"
            )
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            raise

    def fetch_and_store(
        self,
        symbol: str,
        timeframe: str = "1h",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> None:
        """Fetch OHLCV data and store it in InfluxDB.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '1h', '1d')
            start_date: Start date for historical data
            end_date: End date for historical data
        """
        df = self.fetch_historical_ohlcv(symbol, timeframe, start_date, end_date)
        self.write_to_influxdb(df, symbol, timeframe)

    def close(self) -> None:
        """Close all connections."""
        self.influx_client.close()


if __name__ == "__main__":
    # Example usage
    pipeline = DataPipeline()

    try:
        # Fetch and store data for BTC/USDT and ETH/USDT
        symbols = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["1h", "4h", "1d"]

        # Start date: 30 days ago
        start_date = datetime.now() - timedelta(days=30)

        for symbol in symbols:
            for timeframe in timeframes:
                pipeline.fetch_and_store(symbol, timeframe, start_date)

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
    finally:
        pipeline.close()
