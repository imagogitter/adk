"""Tests for TradingAgent implementation."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from agent import TradingAgent

@pytest.fixture
def mock_db_tool():
    """Create mock DatabaseTool."""
    db_tool = MagicMock()
    db_tool.get_latest_indicators.return_value = {
        'sma_20': 45000.0,
        'sma_50': 44000.0,
        'rsi_14': 65.0,
        'macd': 100.0,
        'macd_signal': 50.0
    }
    db_tool.write_trade_record.return_value = True
    return db_tool

@pytest.fixture
def mock_market_tool():
    """Create mock CCXTInfoTool."""
    market_tool = MagicMock()
    market_tool.get_ticker.return_value = {
        'bid': 45000.0,
        'ask': 45100.0,
        'last': 45050.0,
        'volume': 100.0,
        'quote_volume': 4505000.0
    }
    market_tool.get_order_book.return_value = {
        'bids': [[45000.0, 1.0], [44900.0, 2.0]],
        'asks': [[45100.0, 1.0], [45200.0, 2.0]]
    }
    market_tool.get_market_info.return_value = {
        'limits': {
            'amount': {'min': 0.001, 'max': 100.0}
        }
    }
    market_tool.check_connection.return_value = True
    return market_tool

@pytest.fixture
def agent(mock_db_tool, mock_market_tool):
    """Create TradingAgent with mocked dependencies."""
    with patch('agent.DatabaseTool') as mock_db, \
         patch('agent.CCXTInfoTool') as mock_market:
        mock_db.return_value = mock_db_tool
        mock_market.return_value = mock_market_tool
        return TradingAgent()

def test_analyze_market_bullish(agent, mock_db_tool, mock_market_tool):
    """Test market analysis with bullish conditions."""
    # Setup bullish conditions
    mock_db_tool.get_latest_indicators.return_value = {
        'sma_20': 45000.0,
        'sma_50': 44000.0,
        'rsi_14': 65.0,
        'macd': 100.0,
        'macd_signal': 50.0
    }
    mock_market_tool.get_ticker.return_value['last'] = 46000.0

    analysis = agent.analyze_market('BTC/USDT', '1h')
    
    assert analysis['signal'] == 'buy'
    assert analysis['reason'] == 'bullish_trend'
    assert 'indicators' in analysis
    assert 'market_data' in analysis

def test_analyze_market_bearish(agent, mock_db_tool, mock_market_tool):
    """Test market analysis with bearish conditions."""
    # Setup bearish conditions
    mock_db_tool.get_latest_indicators.return_value = {
        'sma_20': 45000.0,
        'sma_50': 46000.0,
        'rsi_14': 35.0,
        'macd': -100.0,
        'macd_signal': 50.0
    }
    mock_market_tool.get_ticker.return_value['last'] = 44000.0

    analysis = agent.analyze_market('BTC/USDT', '1h')
    
    assert analysis['signal'] == 'sell'
    assert analysis['reason'] == 'bearish_trend'

def test_analyze_market_neutral(agent, mock_db_tool, mock_market_tool):
    """Test market analysis with neutral conditions."""
    # Setup neutral conditions
    mock_db_tool.get_latest_indicators.return_value = {
        'sma_20': 45000.0,
        'sma_50': 45000.0,
        'rsi_14': 50.0,
        'macd': 0.0,
        'macd_signal': 0.0
    }
    mock_market_tool.get_ticker.return_value['last'] = 45000.0

    analysis = agent.analyze_market('BTC/USDT', '1h')
    
    assert analysis['signal'] == 'neutral'
    assert analysis['reason'] == 'no_clear_signal'

def test_execute_trades(agent):
    """Test trade execution logic."""
    agent.analyze_market = MagicMock(return_value={
        'signal': 'buy',
        'reason': 'bullish_trend'
    })
    
    trades = agent.execute_trades()
    
    assert len(trades) > 0
    assert trades[0]['type'] == 'buy'
    assert trades[0]['symbol'] in agent.symbols
    assert isinstance(trades[0]['price'], (int, float))
    assert isinstance(trades[0]['size'], (int, float))

def test_execute_trade_position_limit(agent):
    """Test trade execution respects position limits."""
    # Fill up max positions
    agent.max_positions = 1
    agent.active_positions = {'ETH/USDT': {'side': 'long', 'entry_price': 3000.0, 'size': 1.0}}
    
    analysis = {'signal': 'buy', 'reason': 'bullish_trend'}
    trade = agent._execute_trade('BTC/USDT', analysis)
    
    assert trade is None

def test_error_handling(agent, mock_db_tool, mock_market_tool):
    """Test error handling in agent operations."""
    # Simulate database error
    mock_db_tool.get_latest_indicators.side_effect = Exception("Database error")
    
    analysis = agent.analyze_market('BTC/USDT', '1h')
    assert analysis['signal'] == 'error'
    
    # Simulate market data error
    mock_market_tool.get_ticker.side_effect = Exception("Market error")
    
    trade = agent._execute_trade('BTC/USDT', {'signal': 'buy'})
    assert trade is None

def test_run_initialization(agent, mock_market_tool):
    """Test agent initialization and connection checking."""
    # Mock time.sleep to avoid waiting
    with patch('time.sleep'):
        # Test successful connection
        mock_market_tool.check_connection.return_value = True
        agent.execute_trades = MagicMock(return_value=[])
        
        # Should run without errors
        try:
            agent.run(interval=1)
        except Exception as e:
            pytest.fail(f"Agent run failed: {e}")
        
        # Test failed connection
        mock_market_tool.check_connection.return_value = False
        agent.run(interval=1)  # Should handle error gracefully