# Data Pipeline

This component is responsible for fetching OHLCV (Open, High, Low, Close, Volume) data from cryptocurrency exchanges using the ccxt library and storing it in InfluxDB.

## Features

- Fetch historical OHLCV data from any exchange supported by ccxt
- Store data in InfluxDB with appropriate tags and fields
- Robust error handling and retry logic
- Comprehensive logging
- Containerized for easy deployment

## Schema

See [SCHEMA.md](SCHEMA.md) for details on the InfluxDB schema used.

## Configuration

The data pipeline is configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| INFLUXDB_URL | InfluxDB server URL | http://localhost:8086 |
| INFLUXDB_TOKEN | InfluxDB authentication token | - |
| INFLUXDB_ORG | InfluxDB organization | - |
| INFLUXDB_BUCKET | InfluxDB bucket | - |
| EXCHANGE_ID | Exchange ID (e.g., 'binance') | binance |
| EXCHANGE_API_KEY | Exchange API key | - |
| EXCHANGE_SECRET | Exchange API secret | - |

## Usage

### Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the data pipeline:
   ```bash
   python data_pipeline.py
   ```

### Running with Docker Compose

1. Start the services:
   ```bash
   docker-compose up -d
   ```

2. View logs:
   ```bash
   docker-compose logs -f data-pipeline
   ```

### Testing

Run the test script to verify the data pipeline:

```bash
python test_data_pipeline.py
```

## Development

### Adding Support for New Exchanges

The data pipeline uses ccxt, which supports numerous cryptocurrency exchanges. To use a different exchange:

1. Set the `EXCHANGE_ID` environment variable to the desired exchange ID.
2. Provide the appropriate API credentials via environment variables.

### Adding New Timeframes

To fetch data for additional timeframes, modify the `timeframes` list in the main script:

```python
timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
```

## Troubleshooting

### Common Issues

1. **Rate Limiting**: If you encounter rate limiting issues, the pipeline will automatically retry with exponential backoff.

2. **Missing Data**: Check the logs for any warnings about missing data. You may need to adjust the date range.

3. **Connection Issues**: Ensure your network can reach both the exchange API and InfluxDB.

### Logs

Logs are stored in the `logs` directory with the following files:

- Daily logs: `YYYY-MM-DD.log`
- Error logs: `error_YYYY-MM-DD.log`
```

Now, let's create a script to run the data pipeline on a schedule:

```python:/data-pipeline/scheduled_pipeline.py
#!/usr/bin/env python3
"""
Scheduled data pipeline for fetching OHLCV data on a regular basis.
"""

import os
import time
import schedule
from datetime import datetime, timedelta

from data_pipeline import DataPipeline
from logger import configure_logger

# Configure logger
logger = configure_logger('scheduled_pipeline')

# Symbols to fetch
SYMBOLS = ['BTC/USDT', 'ETH/USDT']
# Timeframes to fetch
TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
# How far back to fetch data (in days)
LOOKBACK_DAYS = {
    '1m': 1,    # 1 day for 1-minute data
    '5m': 3,    # 3 days for 5-minute data
    '15m': 7,   # 7 days for 15-minute data
    '1h': 30,   # 30 days for 1-hour data
    '4h': 90,   # 90 days for 4-hour data
    '1d': 365,  # 365 days for 1-day data
}


def run_pipeline():
    """Run the data pipeline for all symbols and timeframes."""
    logger.info("Starting scheduled data pipeline run")

    pipeline = DataPipeline()

    try:
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                # Calculate start date based on timeframe
                lookback = LOOKBACK_DAYS.get(timeframe, 1)
                start_date = datetime.now() - timedelta(days=lookback)

                logger.info(f"Fetching {timeframe} data for {symbol} from {start_date}")

                try:
                    pipeline.fetch_and_store(symbol, timeframe, start_date)
                except Exception as e:
                    logger.error(f"Failed to fetch and store {timeframe} data for {symbol}: {e}")
                    # Continue with next symbol/timeframe

                # Small delay between requests
                time.sleep(1)

        logger.info("Completed scheduled data pipeline run")
    except Exception as e:
        logger.error(f"Scheduled pipeline run failed: {e}")
    finally:
        pipeline.close()


def schedule_jobs():
    """Schedule data pipeline jobs."""
    # Schedule different timeframes at different intervals
    schedule.every(1).minutes.do(run_pipeline_for_timeframe, timeframe='1m')
    schedule.every(5).minutes.do(run_pipeline_for_timeframe, timeframe='5m')
    schedule.every(15).minutes.do(run_pipeline_for_timeframe, timeframe='15m')
    schedule.every(1).hours.do(run_pipeline_for_timeframe, timeframe='1h')
    schedule.every(4).hours.do(run_pipeline_for_timeframe, timeframe='4h')
    schedule.every(1).days.at("00:05").do(run_pipeline_for_timeframe, timeframe='1d')

    # Also run a full update once a day
    schedule.every(1).days.at("01:00").do(run_pipeline)

    logger.info("Scheduled all data pipeline jobs")


def run_pipeline_for_timeframe(timeframe):
    """Run the data pipeline for a specific timeframe."""
    logger.info(f"Starting scheduled data pipeline run for {timeframe} timeframe")

    pipeline = DataPipeline()

    try:
        for symbol in SYMBOLS:
            # Calculate start date based on timeframe
            lookback = LOOKBACK_DAYS.get(timeframe, 1)
            start_date = datetime.now() - timedelta(days=lookback)

            logger.info(f"Fetching {timeframe} data for {symbol} from {start_date}")

            try:
                pipeline.fetch_and_store(symbol, timeframe, start_date)
            except Exception as e:
                logger.error(f"Failed to fetch and store {timeframe} data for {symbol}: {e}")
                # Continue with next symbol

            # Small delay between requests
            time.sleep(1)

        logger.info(f"Completed scheduled data pipeline run for {timeframe} timeframe")
    except Exception as e:
        logger.error(f"Scheduled pipeline run for {timeframe} failed: {e}")
    finally:
        pipeline.close()


if __name__ == "__main__":
    # Run once at startup
    run_pipeline()

    # Schedule future runs
    schedule_jobs()

    # Keep the script running
    logger.info("Starting scheduler loop")
    while True:
        schedule.run_pending()
        time.sleep(1)
