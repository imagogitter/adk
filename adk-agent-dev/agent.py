"""ADK Trading Agent implementation."""
import os
import time
import logging
import json
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from tools.database_tool import DatabaseTool
from tools.ccxt_info_tool import CCXTInfoTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingAgent:
    """Trading agent that analyzes market data and executes trades."""
    
    def __init__(self):
        """Initialize the trading agent with configuration and tools."""
        load_dotenv()
        
        self.db_tool = DatabaseTool()
        self.market_tool = CCXTInfoTool(paper_trading=True)  # Enable paper trading mode
        
        # Trading parameters
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        self.timeframes = ['1h', '4h', '1d']
        self.position_size = float(os.getenv('POSITION_SIZE', '0.01'))
        self.max_positions = int(os.getenv('MAX_POSITIONS', '2'))
        self.active_positions = {}
        
        logger.info(f"Starting trading agent with {len(self.symbols)} symbols...")

    def analyze_market(self, symbol, timeframe):
        """Analyze market data and generate trading signals."""
        try:
            # Get latest indicators from database
            indicators = self.db_tool.get_latest_indicators(symbol, timeframe)
            if not indicators:
                return {'signal': 'neutral', 'reason': 'no_data'}
            
            # Get current market data
            market_data = self.market_tool.get_ticker(symbol)
            if not market_data:
                return {'signal': 'error', 'reason': 'no_market_data'}
            
            # Simple trend-following strategy
            sma_20 = indicators.get('sma_20', 0)
            sma_50 = indicators.get('sma_50', 0)
            rsi_14 = indicators.get('rsi_14', 50)
            current_price = market_data['last']
            
            analysis = {
                'signal': 'neutral',
                'reason': 'no_clear_signal',
                'indicators': indicators,
                'market_data': market_data
            }
            
            # Generate trading signals
            if (current_price > sma_20 > sma_50 and rsi_14 < 70):
                analysis['signal'] = 'buy'
                analysis['reason'] = 'bullish_trend'
            elif (current_price < sma_20 < sma_50 and rsi_14 > 30):
                analysis['signal'] = 'sell'
                analysis['reason'] = 'bearish_trend'
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            return {'signal': 'error', 'reason': str(e)}

    def _execute_trade(self, symbol, analysis):
        """Execute a trade based on analysis."""
        try:
            if analysis['signal'] == 'buy':
                if len(self.active_positions) >= self.max_positions:
                    logger.info(f"Max positions ({self.max_positions}) reached")
                    return None
                    
                market_info = self.market_tool.get_market_info(symbol)
                if not market_info:
                    return None
                    
                min_amount = market_info['limits']['amount']['min']
                ticker = self.market_tool.get_ticker(symbol)
                
                # Paper trade simulation
                trade = {
                    'symbol': symbol,
                    'type': 'buy',
                    'price': ticker['ask'],
                    'size': max(min_amount, 0.1),  # Simulated position size
                    'timestamp': datetime.now().timestamp(),
                    'paper_trade': True
                }
                
                self.active_positions[symbol] = {
                    'side': 'long',
                    'entry_price': trade['price'],
                    'size': trade['size']
                }
                
                logger.info(f"Paper trade executed: {json.dumps(trade)}")
                return trade
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
        return None

    def execute_trades(self):
        """Execute trades based on market analysis."""
        trades = []
        for symbol in self.symbols:
            try:
                analysis = self.analyze_market(symbol, '1h')
                if analysis['signal'] in ['buy', 'sell']:
                    trade = self._execute_trade(symbol, analysis)
                    if trade:
                        trades.append(trade)
                        # Record trade in database
                        self.db_tool.write_trade_record(trade)
            except Exception as e:
                logger.error(f"Error in trade execution loop: {e}")
        return trades

    def run(self, interval=3600):
        """Run the trading agent continuously."""
        while True:
            try:
                if not self.market_tool.check_connection():
                    logger.error("Unable to connect to exchange")
                    time.sleep(60)  # Wait before retrying
                    continue
                    
                self.execute_trades()
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

if __name__ == "__main__":
    agent = TradingAgent()
    agent.run()