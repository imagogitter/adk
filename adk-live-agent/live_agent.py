"""Live trading agent implementation with integrated risk management and monitoring."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import ccxt.async_io as ccxt
from adk import Agent
from influxdb_client import InfluxDBClient
from slack_sdk import WebClient
from utils.config import get_config, get_env_bool

from monitoring import MonitoringSystem
from recovery import RecoveryManager, TradeState
from risk_management import RiskLimits, RiskManager

logger = logging.getLogger(__name__)


class LiveTradingAgent(Agent):
    """ADK-based live trading agent with paper trading support."""

    def __init__(
        self,
        exchange_id: Optional[str] = None,
        paper_trading: Optional[bool] = None,
        initial_capital: Optional[Decimal] = None,
        state_file: str = 'agent_state.json',
        prometheus_port: Optional[int] = None,
        slack_token: Optional[str] = None,
    ):
        """Initialize the live trading agent."""
        super().__init__()

        # Load configuration
        config = get_config()

        # Override with parameters if provided
        exchange_id = exchange_id or config['exchange']['id']
        paper_trading = (
            paper_trading
            if paper_trading is not None
            else get_env_bool('PAPER_TRADING', True)
        )
        initial_capital = initial_capital or config['trading']['initial_capital']
        prometheus_port = prometheus_port or config['monitoring']['prometheus_port']
        slack_token = slack_token or config['monitoring']['slack_token']

        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                'apiKey': config['exchange']['api_key'],
                'secret': config['exchange']['api_secret'],
                'enableRateLimit': True,
                'options': {'defaultType': 'future', 'adjustForTimeDifference': True},
            }
        )

        if paper_trading:
            self.exchange.set_sandbox_mode(True)
            logger.info('Running in paper trading mode')

        # Initialize InfluxDB client
        self.influx_client = InfluxDBClient(
            url=config['influxdb']['url'],
            token=config['influxdb']['token'],
            org=config['influxdb']['org'],
        )

        # Initialize risk manager
        self.risk_manager = RiskManager(
            initial_capital=initial_capital,
            risk_limits=RiskLimits(
                max_position_size=initial_capital * Decimal('0.1'),  # 10% max position
                max_drawdown_percent=Decimal('20'),
                daily_loss_limit=initial_capital * Decimal('0.02'),  # 2% daily limit
                max_open_trades=3,
                position_risk_percent=Decimal('2'),
            ),
            slack_client=None if not slack_token else WebClient(token=slack_token),
        )

        # Initialize monitoring system
        self.monitor = MonitoringSystem(
            prometheus_port=prometheus_port, slack_token=slack_token
        )

        # Initialize recovery manager
        self.recovery = RecoveryManager(
            state_file=state_file,
            exchange=self.exchange,
            influx_client=self.influx_client,
        )

        # Register tools
        self.register_tools()

    def register_tools(self):
        """Register ADK tools."""
        # Re-use existing tools from development agent
        from adk_agent_dev.tools.ccxt_info_tool import CCXTInfoTool
        from adk_agent_dev.tools.database_tool import DatabaseTool

        self.register_tool(DatabaseTool(self.influx_client))
        self.register_tool(CCXTInfoTool(self.exchange))

    async def startup(self):
        """Initialize agent state on startup."""
        try:
            # Attempt recovery if needed
            recovered = await self.recovery.recover_from_crash()
            if not recovered:
                logger.error('Failed to recover agent state')
                return False

            # Load markets
            await self.exchange.load_markets()

            # Update initial metrics
            self._update_system_metrics()

            logger.info('Agent startup completed successfully')
            return True

        except Exception as e:
            logger.error(f'Failed to start agent: {e}')
            return False

    async def shutdown(self):
        """Clean shutdown of agent."""
        try:
            # Close all positions if any
            positions = await self.exchange.fetch_positions()
            for position in positions:
                if float(position['size']) != 0:
                    await self._close_position(position['symbol'])

            # Close connections
            await self.exchange.close()
            self.influx_client.close()

            logger.info('Agent shutdown completed')

        except Exception as e:
            logger.error(f'Error during shutdown: {e}')

    async def execute_trade(
        self, symbol: str, side: str, size: Decimal, price: Optional[Decimal] = None
    ):
        """Execute a trade with risk management and monitoring."""
        try:
            # Check risk limits
            if not self.risk_manager.can_open_position(
                symbol, price or await self._get_market_price(symbol), size
            ):
                logger.warning(f'Trade rejected: Risk limits exceeded for {symbol}')
                return False

            # Execute trade
            start_time = datetime.now()
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market' if price is None else 'limit',
                side=side,
                amount=float(size),
                price=float(price) if price else None,
            )

            # Record latency
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self.monitor.update_api_latency(latency)

            # Update state
            trade_state = TradeState(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=Decimal(str(order['price'])),
                timestamp=order['timestamp'] / 1000,
            )
            self.recovery.record_trade(trade_state)
            self.risk_manager.position_opened(symbol, trade_state.entry_price, size)

            # Record metrics
            volume = size * trade_state.entry_price
            self.monitor.record_trade(volume, Decimal('0'))  # PnL calculated on close

            logger.info(f'Trade executed: {order}')
            return True

        except Exception as e:
            self.monitor.record_error('trade_execution', str(e))
            logger.error(f'Trade execution failed: {e}')
            return False

    async def _close_position(self, symbol: str):
        """Close an open position."""
        try:
            position = await self.exchange.fetch_position(symbol)
            if position and float(position['size']) != 0:
                close_side = 'sell' if float(position['size']) > 0 else 'buy'
                await self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=close_side,
                    amount=abs(float(position['size'])),
                )

                # Update state
                self.recovery.remove_trade(symbol)
                pnl = self.risk_manager.position_closed(
                    symbol, Decimal(str(position['price']))
                )
                if pnl:
                    self.monitor.record_trade(Decimal('0'), pnl)

        except Exception as e:
            self.monitor.record_error('position_close', str(e))
            logger.error(f'Failed to close position {symbol}: {e}')

    async def _get_market_price(self, symbol: str) -> Decimal:
        """Get current market price for symbol."""
        ticker = await self.exchange.fetch_ticker(symbol)
        return Decimal(str(ticker['last']))

    def _update_system_metrics(self):
        """Update system metrics."""
        try:
            import psutil

            process = psutil.Process()
            memory_percent = process.memory_percent()
            self.monitor.update_memory_usage(memory_percent)
        except Exception as e:
            logger.error(f'Failed to update system metrics: {e}')
