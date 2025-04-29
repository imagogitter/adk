from datetime import datetime, timezone
from typing import Optional, Dict, Any

import backtrader as bt
import pandas as pd
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxTable


class InfluxDBData(bt.feeds.DataBase):
    """Custom Backtrader data feed for InfluxDB OHLCV data."""
    
    params = (
        ('bucket', ''),        # InfluxDB bucket name
        ('org', ''),          # InfluxDB organization
        ('url', ''),          # InfluxDB URL
        ('token', ''),        # InfluxDB API token
        ('symbol', ''),       # Trading pair symbol (e.g. 'BTC/USDT')
        ('timeframe', '1h'),  # Data timeframe as string (e.g. '1h', '4h')
    )
    
    def __init__(self):
        super().__init__()
        
        # Initialize InfluxDB client - ensure we're using localhost instead of influxdb
        url = self.p.url.replace('influxdb', 'localhost')
        self._client = InfluxDBClient(
            url=url,
            token=self.p.token,
            org=self.p.org
        )
        
        # Store original timeframe string for InfluxDB queries
        self._timeframe_str = self.p.timeframe
        
        # Set timeframe values in base class
        timeframe_map = {
            '1m': (bt.TimeFrame.Minutes, 1),
            '5m': (bt.TimeFrame.Minutes, 5),
            '15m': (bt.TimeFrame.Minutes, 15),
            '30m': (bt.TimeFrame.Minutes, 30),
            '1h': (bt.TimeFrame.Minutes, 60),
            '4h': (bt.TimeFrame.Minutes, 240),
            '1d': (bt.TimeFrame.Days, 1),
            '1w': (bt.TimeFrame.Weeks, 1),
        }
        
        if self._timeframe_str not in timeframe_map:
            raise ValueError(f"Unsupported timeframe: {self._timeframe_str}")
            
        # Set timeframe values for backtrader
        self._timeframe = timeframe_map[self._timeframe_str][0]
        self.timeframe = timeframe_map[self._timeframe_str][0]
        self._compression = timeframe_map[self._timeframe_str][1]
        self.compression = timeframe_map[self._timeframe_str][1]
        
        # Override p.timeframe with the integer value for proper name lookup
        self.p.timeframe = self._timeframe
        
        # Store queried data
        self._data: Optional[pd.DataFrame] = None
        
    def _load_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Query OHLCV data from InfluxDB and return as DataFrame."""
        # Convert timestamps to RFC3339 format
        start_ts = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_ts = end.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        query = f'''
        from(bucket: "{self.p.bucket}")
            |> range(start: time(v: "{start_ts}"), stop: time(v: "{end_ts}"))
            |> filter(fn: (r) => r["_measurement"] == "ohlcv")
            |> filter(fn: (r) => r["symbol"] == "{self.p.symbol}")
            |> filter(fn: (r) => r["timeframe"] == "{self._timeframe_str}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
        '''
        
        print(f"\nExecuting InfluxDB query for {self.p.symbol}:")
        print(query)
        
        results = self._client.query_api().query(query)
        if not results:
            raise ValueError(f"No data found for {self.p.symbol}")
        
        # Convert FluxTable records to dictionary format
        records = []
        for table in results:
            for record in table.records:
                values = record.values
                row = {
                    'datetime': values['_time'],
                    'open': values.get('open'),
                    'high': values.get('high'),
                    'low': values.get('low'),
                    'close': values.get('close'),
                    'volume': values.get('volume', 0.0)
                }
                records.append(row)
        
        if not records:
            raise ValueError(f"No data records for {self.p.symbol}")
        
        # Convert to DataFrame and handle missing values
        df = pd.DataFrame(records)
        df = df.set_index('datetime')
        df = df.sort_index()
        
        # Handle missing or NaN values
        df = df.ffill().bfill()
        
        print(f"\nFirst 5 rows of data:")
        print(df.head())
        print(f"\nDataFrame shape: {df.shape}")
        
        return df
        
    def start(self) -> None:
        """Called when Backtrader starts the backtesting process."""
        # Convert dates to UTC for InfluxDB query
        start = self.p.fromdate.replace(tzinfo=timezone.utc)
        end = self.p.todate.replace(tzinfo=timezone.utc)
        
        # Load the data
        self._data = self._load_data(start, end)
        
        # Initialize data iteration
        self._idx = 0
        super().start()
        
    def _load(self) -> bool:
        """Load the next data point into the feed."""
        if self._idx >= len(self._data):
            return False
            
        # Get current row
        row = self._data.iloc[self._idx]
        
        # Update lines
        self.lines.datetime[0] = bt.date2num(row.name.to_pydatetime())
        self.lines.open[0] = float(row['open'])
        self.lines.high[0] = float(row['high'])
        self.lines.low[0] = float(row['low'])
        self.lines.close[0] = float(row['close'])
        self.lines.volume[0] = float(row['volume'])
        
        self._idx += 1
        return True

    def stop(self) -> None:
        """Called when Backtrader stops the backtesting process."""
        self._client.close()
        super().stop()