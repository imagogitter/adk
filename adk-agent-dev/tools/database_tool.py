"""InfluxDB integration tool for storing trading data."""
import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DatabaseTool:
    """Tool for interacting with InfluxDB."""

    def __init__(self):
        """Initialize database connection."""
        load_dotenv()

        self.url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.token = os.getenv('INFLUXDB_TOKEN', '')
        self.org = os.getenv('INFLUXDB_ORG', '')
        self.bucket = os.getenv('INFLUXDB_BUCKET', '')

        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def write_trade_record(self, trade: Dict[str, Any]) -> bool:
        """Write trade record to database."""
        try:
            point = {
                "measurement": "trades",
                "tags": {
                    "symbol": trade['symbol'],
                    "type": trade['type'],
                    "paper_trade": trade.get('paper_trade', False)
                },
                "fields": {
                    "price": float(trade['price']),
                    "size": float(trade['size']),
                    "value": float(trade['price']) * float(trade['size'])
                },
                "time": datetime.fromtimestamp(trade['timestamp'])
            }
            
            self.write_api.write(
                bucket=self.bucket,
                record=point
            )
            return True
            
        except Exception as e:
            logger.error(f"Error writing trade record: {str(e)}")
            return False

    def get_latest_indicators(self, symbol: str, timeframe: str) -> Optional[Dict[str, float]]:
        """Get latest technical indicators for a symbol."""
        try:
            query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r["measurement"] == "indicators")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
                |> last()
            """
            
            result = self.query_api.query(query)
            
            if not result or len(result) == 0:
                return None
                
            # Convert result to dictionary
            record = result[0].records[0]
            return {
                'sma_20': record.get_value('sma_20', 0.0),
                'sma_50': record.get_value('sma_50', 0.0),
                'rsi_14': record.get_value('rsi_14', 50.0),
                'macd': record.get_value('macd', 0.0),
                'macd_signal': record.get_value('macd_signal', 0.0),
                'bb_upper': record.get_value('bb_upper', 0.0),
                'bb_middle': record.get_value('bb_middle', 0.0),
                'bb_lower': record.get_value('bb_lower', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error getting indicators: {str(e)}")
            return None

    def get_trade_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical trades for a symbol."""
        try:
            query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r["measurement"] == "trades")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> limit(n: {limit})
            """
            
            result = self.query_api.query(query)
            
            trades = []
            for table in result:
                for record in table.records:
                    trade = {
                        'symbol': record.get_value('symbol'),
                        'type': record.get_value('type'),
                        'price': record.get_value('price'),
                        'size': record.get_value('size'),
                        'value': record.get_value('value'),
                        'paper_trade': record.get_value('paper_trade'),
                        'timestamp': record.get_time()
                    }
                    trades.append(trade)
                    
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return []

    def close(self):
        """Close database connection."""
        try:
            self.client.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")