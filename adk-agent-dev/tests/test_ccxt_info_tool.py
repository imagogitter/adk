"""Tests for CCXTInfoTool."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from tools.ccxt_info_tool import CCXTInfoTool

@pytest.fixture
def mock_exchange():
    """Create mock CCXT exchange."""
    exchange = MagicMock()
    exchange.load_markets = MagicMock()
    exchange.fetch_ticker = MagicMock()
    exchange.fetch_order_book = MagicMock()
    exchange.timeframes = {'1m': '1m', '5m': '5m', '1h': '1h', '4h': '4h', '1d': '1d'}
    return exchange

@pytest.fixture
def ccxt_tool(mock_exchange):
    """Create CCXTInfoTool with mocked exchange."""
    with patch('ccxt.binanceus') as mock_ccxt:
        mock_ccxt.return_value = mock_exchange
        return CCXTInfoTool()

def test_get_symbols(ccxt_tool, mock_exchange):
    """Test retrieving available trading pairs."""
    mock_exchange.symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
    
    symbols = ccxt_tool.get_symbols()
    
    assert isinstance(symbols, list)
    assert len(symbols) == 3
    assert 'BTC/USDT' in symbols
    assert 'ETH/USDT' in symbols
    mock_exchange.load_markets.assert_called_once()

def test_get_ticker(ccxt_tool, mock_exchange):
    """Test retrieving current ticker information."""
    mock_ticker = {
        'symbol': 'BTC/USDT',
        'bid': 45000.0,
        'ask': 45100.0,
        'last': 45050.0,
        'baseVolume': 100.0,
        'quoteVolume': 4505000.0,
        'timestamp': datetime.now().timestamp() * 1000
    }
    mock_exchange.fetch_ticker.return_value = mock_ticker
    
    ticker = ccxt_tool.get_ticker('BTC/USDT')
    
    assert isinstance(ticker, dict)
    assert all(k in ticker for k in ['bid', 'ask', 'last', 'volume', 'quote_volume'])
    assert ticker['bid'] == 45000.0
    assert ticker['ask'] == 45100.0
    mock_exchange.fetch_ticker.assert_called_once_with('BTC/USDT')

def test_get_market_info(ccxt_tool, mock_exchange):
    """Test retrieving detailed market information."""
    mock_market = {
        'id': 'BTCUSDT',
        'base': 'BTC',
        'quote': 'USDT',
        'active': True,
        'precision': {'price': 2, 'amount': 6},
        'limits': {
            'amount': {'min': 0.0001, 'max': 1000.0},
            'price': {'min': 0.01, 'max': 1000000.0}
        },
        'maker': 0.001,
        'taker': 0.001
    }
    mock_exchange.market.return_value = mock_market
    
    market_info = ccxt_tool.get_market_info('BTC/USDT')
    
    assert isinstance(market_info, dict)
    assert market_info['base'] == 'BTC'
    assert market_info['quote'] == 'USDT'
    assert market_info['active'] is True
    assert 'precision' in market_info
    assert 'limits' in market_info
    mock_exchange.load_markets.assert_called_once()

def test_get_order_book(ccxt_tool, mock_exchange):
    """Test retrieving order book data."""
    mock_order_book = {
        'bids': [[45000.0, 1.5], [44900.0, 2.0]],
        'asks': [[45100.0, 1.0], [45200.0, 2.5]],
        'timestamp': datetime.now().timestamp() * 1000,
        'datetime': datetime.now().isoformat()
    }
    mock_exchange.fetch_order_book.return_value = mock_order_book
    
    order_book = ccxt_tool.get_order_book('BTC/USDT', 2)
    
    assert isinstance(order_book, dict)
    assert 'bids' in order_book
    assert 'asks' in order_book
    assert len(order_book['bids']) == 2
    assert len(order_book['asks']) == 2
    mock_exchange.fetch_order_book.assert_called_once_with('BTC/USDT', 2)

def test_get_trading_timeframes(ccxt_tool, mock_exchange):
    """Test retrieving available timeframes."""
    timeframes = ccxt_tool.get_trading_timeframes()
    
    assert isinstance(timeframes, list)
    assert len(timeframes) == 5
    assert '1h' in timeframes
    assert '4h' in timeframes
    assert '1d' in timeframes

def test_check_connection(ccxt_tool, mock_exchange):
    """Test exchange connection check."""
    mock_exchange.fetch_ticker.return_value = {'last': 45000.0}
    
    assert ccxt_tool.check_connection() is True
    mock_exchange.fetch_ticker.assert_called_once_with('BTC/USDT')

def test_error_handling(ccxt_tool, mock_exchange):
    """Test error handling in CCXT operations."""
    # Test symbol fetch error
    mock_exchange.load_markets.side_effect = Exception("API error")
    assert ccxt_tool.get_symbols() == []
    
    # Test ticker fetch error
    mock_exchange.fetch_ticker.side_effect = Exception("Network error")
    assert ccxt_tool.get_ticker('BTC/USDT') == {}
    
    # Test order book fetch error
    mock_exchange.fetch_order_book.side_effect = Exception("Timeout")
    assert ccxt_tool.get_order_book('BTC/USDT') == {}
    
    # Test connection check with error
    assert ccxt_tool.check_connection() is False