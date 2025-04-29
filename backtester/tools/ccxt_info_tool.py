'''CCXT integration tool for market data and trading operations.'''
import logging
import os
from typing import Any, Dict, Optional

import ccxt
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CCXTInfoTool:
    '''Tool for interacting with crypto exchanges using CCXT.'''

    def __init__(self, paper_trading: bool = False):
        '''Initialize exchange connection.'''
        load_dotenv()

        self.exchange_id = 'binanceus'
        self.paper_trading = paper_trading

        # Initialize exchange with or without authentication
        if paper_trading:
            self.exchange = ccxt.binanceus(
                {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}
            )
        else:
            self.exchange = ccxt.binanceus(
                {
                    'apiKey': os.getenv('BINANCEUS_API_KEY'),
                    'secret': os.getenv('BINANCEUS_API_SECRET'),
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'},
                }
            )

    def check_connection(self) -> bool:
        '''Test exchange connectivity.'''
        try:
            if self.paper_trading:
                # In paper trading mode, just check public endpoints
                self.exchange.fetch_ticker('BTC/USDT')
                return True

            # In live mode, check authenticated endpoints
            self.exchange.fetch_balance()
            return True
        except Exception as e:
            logger.error(f'Connection test failed: {self.exchange_id} {str(e)}')
            return False

    def get_ticker(self, symbol: str) -> Optional[Dict[str, float]]:
        '''Get current ticker data for a symbol.'''
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'volume': ticker['baseVolume'],
            }
        except Exception as e:
            logger.error(f'Error fetching ticker: {str(e)}')
            return None

    def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        '''Get market information for a symbol.'''
        try:
            return self.exchange.market(symbol)
        except Exception as e:
            logger.error(f'Error fetching market info: {str(e)}')
            return None

    def get_account_balance(self) -> Optional[Dict[str, float]]:
        '''Get account balances.'''
        if self.paper_trading:
            # Return simulated balance for paper trading
            return {'USDT': 10000.0, 'BTC': 0.0, 'ETH': 0.0}  # Simulated USDT balance

        try:
            balance = self.exchange.fetch_balance()
            return {
                currency: float(data['free'])
                for currency, data in balance['free'].items()
                if float(data['free']) > 0
            }
        except Exception as e:
            logger.error(f'Error fetching balance: {str(e)}')
            return None

    def create_order(
        self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        '''Create a new order.'''
        if self.paper_trading:
            # Simulate order creation for paper trading
            ticker = self.get_ticker(symbol)
            if not ticker:
                return None

            return {
                'id': 'paper_order',
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount,
                'price': price or ticker['last'],
                'status': 'closed',
                'filled': amount,
                'remaining': 0.0,
                'paper_trade': True,
            }

        try:
            return self.exchange.create_order(symbol, order_type, side, amount, price)
        except Exception as e:
            logger.error(f'Error creating order: {str(e)}')
            return None

    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[list]:
        '''Get OHLCV data for a symbol.'''
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f'Error fetching OHLCV data: {str(e)}')
            return None
