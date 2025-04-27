"""Crypto market data pipeline for fetching and storing OHLCV data.

This module implements a data pipeline that:
1. Fetches historical OHLCV (Open, High, Low, Close, Volume) data from Binance.us
2. Cleans and processes the data using pandas
3. Stores the processed data in InfluxDB for time-series analysis
"""

import logging
import os
import sys
import time

import ccxt
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import WriteApi

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def init_binance() -> ccxt.Exchange:
    """Initialize Binance.us exchange with ccxt."""
    return ccxt.binanceus(
        {
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_SECRET_KEY"),
            "enableRateLimit": True,
        }
    )


def fetch_ohlcv(
    exchange: ccxt.Exchange, symbol: str, timeframe: str, since: int, limit: int = 1000
) -> list:
    """Fetch OHLCV data with pagination."""
    ohlcv = []
    while True:
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not data:
                break
            ohlcv.extend(data)
            since = data[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
        except ccxt.NetworkError as e:
            logger.error(f"Network error: {e}")
            time.sleep(5)
            continue
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            break
    return ohlcv


def clean_ohlcv(ohlcv_data: list) -> pd.DataFrame:
    """Clean OHLCV data using pandas."""
    df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.fillna(method="ffill", limit=None)  # type: ignore
    df.drop_duplicates(inplace=True)
    return df


def write_to_influxdb(
    df: pd.DataFrame, symbol: str, timeframe: str, write_api: WriteApi, bucket: str
) -> None:
    """Write OHLCV data to InfluxDB."""
    for index, row in df.iterrows():
        point = (
            Point("market_data")
            .tag("symbol", symbol)
            .tag("timeframe", timeframe)
            .field("open", row["open"])
            .field("high", row["high"])
            .field("low", row["low"])
            .field("close", row["close"])
            .field("volume", row["volume"])
            .time(index, WritePrecision.NS)
        )
        try:
            write_api.write(bucket=bucket, record=point)
        except Exception as e:
            logger.error(f"Failed to write point to InfluxDB: {e}")


def main() -> None:
    """Execute the data pipeline to fetch and store crypto market data.

    Fetches hourly BTC/USDT data from 2023-01-01 onwards from Binance.us,
    processes it, and writes it to InfluxDB. Uses environment variables
    for all sensitive configuration.
    """
    # Configuration
    symbol = "BTC/USDT"
    timeframe = "1h"
    since = int(pd.Timestamp("2023-01-01").timestamp() * 1000)

    # Get InfluxDB config
    influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    influx_token = os.getenv("INFLUXDB_TOKEN")
    influx_org = os.getenv("INFLUXDB_ORG")
    influx_bucket = os.getenv("INFLUXDB_BUCKET")

    if not all([influx_token, influx_org, influx_bucket]):
        logger.error("Missing required InfluxDB configuration")
        sys.exit(1)

    # Initialize clients
    exchange = init_binance()
    influx_client = InfluxDBClient(
        url=influx_url,
        token=influx_token,  # type: ignore
        org=influx_org,  # type: ignore
    )
    write_api = influx_client.write_api()

    # Fetch and process data
    logger.info(f"Fetching OHLCV for {symbol} ({timeframe})")
    ohlcv_data = fetch_ohlcv(exchange, symbol, timeframe, since)
    if ohlcv_data:
        df = clean_ohlcv(ohlcv_data)
        logger.info(f"Writing {len(df)} records to InfluxDB")
        write_to_influxdb(df, symbol, timeframe, write_api, influx_bucket)  # type: ignore
        logger.info("Data pipeline completed")
    else:
        logger.warning("No data fetched")


if __name__ == "__main__":
    main()
