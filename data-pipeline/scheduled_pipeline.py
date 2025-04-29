"""Scheduled execution module for the data pipeline system.

This module implements a scheduled execution system for the data pipeline,
managing periodic data fetching and processing according to configured intervals.
It orchestrates the following operations:
- Running the pipeline at specified intervals
- Fetching OHLCV data for configured trading pairs
- Processing and storing data in InfluxDB
- Error handling and logging of pipeline operations
"""

import time
from datetime import datetime, timedelta

from data_pipeline import DataPipeline
from logger import logger


def run_scheduled_pipeline(interval_minutes: int = 60) -> None:
    """Run the data pipeline on a schedule.
    
    Args:
        interval_minutes: Time between pipeline runs in minutes
    """
    pipeline = DataPipeline()
    
    try:
        while True:
            start_time = datetime.now()
            logger.info(f"Starting scheduled pipeline run at {start_time}")
            
            # Fetch last 24 hours of data
            start_date = datetime.now() - timedelta(days=1)
            
            # Run pipeline for major pairs
            for symbol in ["BTC/USDT", "ETH/USDT"]:
                for timeframe in ["1h", "4h"]:
                    try:
                        pipeline.fetch_and_store(symbol, timeframe, start_date)
                    except Exception as e:
                        logger.error(f"Error processing {symbol} {timeframe}: {e}")
            
            # Calculate sleep time for next run
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0, (interval_minutes * 60) - elapsed)
            logger.info(f"Sleeping for {sleep_time:.1f} seconds until next run")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Scheduled pipeline stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in scheduled pipeline: {e}")
    finally:
        pipeline.close()


if __name__ == "__main__":
    run_scheduled_pipeline()
