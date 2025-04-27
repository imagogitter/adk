# InfluxDB Schema for Trading Data

## OHLCV Data

### Measurement: `ohlcv`

This measurement stores candlestick (OHLCV) data from cryptocurrency exchanges.

#### Tags
- `symbol` (string): Trading pair with '/' replaced by '_' (e.g., 'BTC_USDT')
- `timeframe` (string): Candle timeframe (e.g., '1m', '5m', '15m', '1h', '4h', '1d')
- `exchange` (string): Exchange name (e.g., 'binance', 'coinbase')

#### Fields
- `open` (float): Opening price
- `high` (float): Highest price
- `low` (float): Lowest price
- `close` (float): Closing price
- `volume` (float): Trading volume

#### Timestamp
- Timestamp of the candle open time

### Retention Policy
- Default retention policy: infinite
- Consider creating additional downsampled retention policies for long-term storage

## Example Point
```
ohlcv,symbol=BTC_USDT,timeframe=1h,exchange=binance open=50000.0,high=51000.0,low=49500.0,close=50500.0,volume=1250.5 1620000000000000000
```

## Query Examples

### Get the latest BTC/USDT hourly candle:
```flux
from(bucket: "trading")
  |> range(start: -2h)
  |> filter(fn: (r) => r._measurement == "ohlcv")
  |> filter(fn: (r) => r.symbol == "BTC_USDT")
  |> filter(fn: (r) => r.timeframe == "1h")
  |> last()
```

### Get daily candles for ETH/USDT for the last 30 days:
```flux
from(bucket: "trading")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "ohlcv")
  |> filter(fn: (r) => r.symbol == "ETH_USDT")
  |> filter(fn: (r) => r.timeframe == "1d")
```
```

Now, let's create a test script to test the data pipeline with historical data load:

```python:/data-pipeline/test_data_pipeline.py
#!/usr/bin/env python3
"""
Test script for data pipeline with historical data load for BTC/USDT and ETH/USDT.
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv

from data_pipeline import DataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secrets', '.env.binance'))

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')


def verify_data_in_influxdb(symbol: str, timeframe: str, start_date: datetime) -> bool:
    """
    Verify that data was successfully written to InfluxDB.

    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '1h')
        start_date: Start date for verification

    Returns:
        bool: True if data exists, False otherwise
    """
    clean_symbol = symbol.replace('/', '_')

    # Create InfluxDB client
    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

    query_api = client.query_api()

    # Convert start_date to RFC3339 format
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Query to check if data exists
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: {start_date_str})
        |> filter(fn: (r) => r._measurement == "ohlcv")
        |> filter(fn: (r) => r.symbol == "{clean_symbol}")
        |> filter(fn: (r) => r.timeframe == "{timeframe}")
        |> count()
    '''

    try:
        result = query_api.query(query)

        # Check if we have any results
        if result and len(result) > 0 and len(result[0].records) > 0:
            count = result[0].records[0].get_value()
            logger.info(f"Found {count} records for {symbol} ({timeframe})")
            return count > 0
        else:
            logger.warning(f"No data found for {symbol} ({timeframe})")
            return False
    except Exception as e:
        logger.error(f"Error querying InfluxDB: {e}")
        return False
    finally:
        client.close()


def main():
    """Run test for data pipeline with historical data load."""
    logger.info("Starting data pipeline test")

    # Initialize data pipeline
    pipeline = DataPipeline()

    try:
        # Define test parameters
        symbols = ['BTC/USDT', 'ETH/USDT']
        timeframes = ['1h', '4h', '1d']

        # Start date: 7 days ago (for testing, we use a shorter period)
        start_date = datetime.now() - timedelta(days=7)

        # Fetch and store data
        for symbol in symbols:
            for timeframe in timeframes:
                logger.info(f"Testing data pipeline for {symbol} ({timeframe})")

                # Fetch and store data
                pipeline.fetch_and_store(symbol, timeframe, start_date)

                # Verify data was written to InfluxDB
                if verify_data_in_influxdb(symbol, timeframe, start_date):
                    logger.info(f"✅ Test passed for {symbol} ({timeframe})")
                else:
                    logger.error(f"❌ Test failed for {symbol} ({timeframe})")

        logger.info("Data pipeline test completed")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
```

Finally, let's enhance the error handling and logging in the data pipeline by creating a dedicated logger module:

```python:/data-pipeline/logger.py
#!/usr/bin/env python3
"""
Logger configuration for the data pipeline.
"""

import os
import logging
import logging.handlers
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure root logger
def configure_logger(name=None):
    """
    Configure and return a logger with file and console handlers.

    Args:
        name: Logger name (default: None for root logger)

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create file handler for info+ logs
    log_filename = f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(logs_dir, log_filename),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Create file handler for error+ logs
    error_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(logs_dir, f"error_{log_filename}"),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)

    return logger
```

Now, let's update the `data_pipeline.py` file to use our enhanced logger and improve error handling:

```python:/data-pipeline/data_pipeline.py
#!/usr/bin/env python3
"""
Data pipeline for fetching OHLCV data from exchanges using ccxt and writing to InfluxDB.
"""

import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import ccxt
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

from logger import configure_logger

# Configure logger
logger = configure_logger('data_pipeline')

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secrets', '.env.binance'))

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

# Exchange configuration
EXCHANGE_ID = os.getenv('EXCHANGE_ID', 'binance')
EXCHANGE_API_KEY = os.getenv('EXCHANGE_API_KEY', '')
EXCHANGE_SECRET = os.getenv('EXCHANGE_SECRET', '')

# Maximum retry attempts
MAX_RETRIES = 3
# Retry delay in seconds
RETRY_DELAY = 5


class DataPipelineError(Exception):
    """Base exception for data pipeline errors."""
    pass


class ExchangeError(DataPipelineError):
    """Exception for exchange-related errors."""
    pass


class DatabaseError(DataPipelineError):
    """Exception for database-related errors."""
    pass


class DataPipeline:
    """
    Pipeline for fetching OHLCV data and writing to InfluxDB.
    """

    def __init__(self, exchange_id: str = EXCHANGE_ID):
        """
        Initialize the data pipeline with exchange and database connections.

        Args:
            exchange_id: The ID of the exchange to use (default: from env var)
        """
        try:
            # Initialize exchange
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'apiKey': EXCHANGE_API_KEY,
                'secret': EXCHANGE_SECRET,
                'enableRateLimit': True,
            })

            # Initialize InfluxDB client
            self.influx_client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

            logger.info(f"Initialized DataPipeline with exchange: {exchange_id}")
        except AttributeError as e:
            logger.error(f"Invalid exchange ID: {exchange_id}")
            raise ExchangeError(f"Invalid exchange ID: {exchange_id}") from e
        except Exception as e:
            logger.error(f"Failed to initialize DataPipeline: {e}")
            logger.debug(traceback.format_exc())
            raise DataPipelineError(f"Failed to initialize DataPipeline: {e}") from e

    def fetch_ohlcv(self,
                   symbol: str,
                   timeframe: str = '1h',
                   since: Optional[int] = None,
                   limit: int = 1000,
                   retry_count: int = 0) -> List[List]:
        """
        Fetch OHLCV data from the exchange with retry logic.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '1h', '1d')
            since: Timestamp in milliseconds to fetch data from
            limit: Maximum number of candles to fetch
            retry_count: Current retry attempt

        Returns:
            List of OHLCV candles
        """
        try:
            logger.info(f"Fetching {timeframe} OHLCV data for {symbol} since {since}")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            logger.info(f"Fetched {len(ohlcv)} candles for {symbol}")
            return ohlcv
        except ccxt.NetworkError as e:
            if retry_count < MAX_RETRIES:
                retry_count += 1
                wait_time = RETRY_DELAY * retry_count
                logger.warning(f"Network error, retrying in {wait_time}s (attempt {retry_count}/{MAX_RETRIES}): {e}")
                time.sleep(wait_time)
                return self.fetch_ohlcv(symbol, timeframe, since, limit, retry_count)
            else:
                logger.error(f"Failed to fetch OHLCV data after {MAX_RETRIES} attempts: {e}")
                raise ExchangeError(f"Failed to fetch OHLCV data: {e}") from e
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            raise ExchangeError(f"Exchange error: {e}") from e
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            logger.debug(traceback.format_exc())
            raise DataPipelineError(f"Error fetching O
