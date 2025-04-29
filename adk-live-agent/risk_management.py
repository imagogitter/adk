'' 'Risk management module for live trading agent.' ''

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from prometheus_client import Counter, Gauge
from slack_sdk import WebClient

logger = logging.getLogger(__name__)

# Prometheus metrics
RISK_EXPOSURE = Gauge('risk_exposure_percent', 'Current risk exposure as percentage')
STOP_LOSS_TRIGGERED = Counter(
    'stop_loss_triggered_total', 'Number of stop losses triggered'
)


@dataclass
class RiskLimits:
    '' 'Risk limits configuration.' ''

    max_position_size: Decimal  # Maximum size of any single position
    max_drawdown_percent: Decimal  # Maximum allowable drawdown
    daily_loss_limit: Decimal  # Maximum daily loss allowed
    max_open_trades: int  # Maximum number of concurrent open trades
    position_risk_percent: Decimal  # Risk per position as % of capital


class RiskManager:
    '' 'Manages trading risk limits and controls.' ''

    def __init__(
        self,
        initial_capital: Decimal,
        risk_limits: RiskLimits,
        slack_client: Optional[WebClient] = None,
    ):
        '' 'Initialize risk manager.' ''
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_limits = risk_limits
        self.slack_client = slack_client
        self.open_positions: Dict[str, Dict] = {}

        # Initialize metrics
        RISK_EXPOSURE.set(0)

    def can_open_position(self, symbol: str, price: Decimal, size: Decimal) -> bool:
        '' 'Check if opening a new position is within risk limits.' ''
        # Check number of open positions
        if len(self.open_positions) >= self.risk_limits.max_open_trades:
            logger.warning('Maximum number of open trades reached')
            return False

        # Calculate position value
        position_value = price * size

        # Check position size limit
        if position_value > self.risk_limits.max_position_size:
            logger.warning(
                f'Position size {position_value} exceeds limit '
                f'{self.risk_limits.max_position_size}'
            )
            return False

        # Calculate total exposure with new position
        total_exposure = (
            sum(pos['value'] for pos in self.open_positions.values()) + position_value
        )

        exposure_percent = (total_exposure / self.current_capital) * 100
        if exposure_percent > 100:
            logger.warning(f'Total exposure {exposure_percent}% would exceed 100%')
            return False

        return True

    def position_opened(self, symbol: str, price: Decimal, size: Decimal):
        '' 'Record new position opening.' ''
        position_value = price * size
        self.open_positions[symbol] = {
            'size': size,
            'entry_price': price,
            'value': position_value,
        }

        # Update metrics
        exposure = (
            sum(pos['value'] for pos in self.open_positions.values())
            / self.current_capital
            * 100
        )
        RISK_EXPOSURE.set(exposure)

    def position_closed(self, symbol: str, price: Decimal) -> Optional[Decimal]:
        '' 'Handle position closing and return realized PnL.' ''
        if symbol not in self.open_positions:
            logger.error(f'Attempted to close non-existent position {symbol}')
            return None

        position = self.open_positions[symbol]
        pnl = (price - position['entry_price']) * position['size']

        # Update capital
        self.current_capital += pnl

        # Remove position
        del self.open_positions[symbol]

        # Update metrics
        exposure = (
            sum(pos['value'] for pos in self.open_positions.values())
            / self.current_capital
            * 100
        )
        RISK_EXPOSURE.set(exposure)

        # Check drawdown
        drawdown = (
            (self.initial_capital - self.current_capital) / self.initial_capital * 100
        )
        if drawdown > self.risk_limits.max_drawdown_percent:
            self._alert_max_drawdown(drawdown)

        return pnl

    def check_stop_loss(self, symbol: str, current_price: Decimal) -> bool:
        '' 'Check if position should be stopped out based on risk limits.' ''
        if symbol not in self.open_positions:
            return False

        position = self.open_positions[symbol]
        unrealized_pnl = (current_price - position['entry_price']) * position['size']

        # Check position risk limit
        position_risk = abs(unrealized_pnl / self.current_capital * 100)
        if position_risk > self.risk_limits.position_risk_percent:
            STOP_LOSS_TRIGGERED.inc()
            return True

        return False

    def _alert_max_drawdown(self, drawdown: Decimal):
        '' 'Send alert when max drawdown is exceeded.' ''
        message = f'WARNING: Max drawdown exceeded! Current drawdown: {drawdown}%'
        logger.error(message)

        if self.slack_client:
            try:
                self.slack_client.chat_postMessage(
                    channel='#trading-alerts', text=message
                )
            except Exception as e:
                logger.error(f'Failed to send Slack alert: {e}')
