"""ADK Strategy implementation for Backtrader."""

import logging
import os
from datetime import datetime, timedelta

import backtrader as bt


class ADKStrategy(bt.Strategy):
    """Enhanced ADK Strategy with trend following, dynamic position sizing,
    and improved risk management.
    """

    params = (
        ("rsi_period", 14),  # RSI lookback period
        ("rsi_overbought", 65),  # RSI overbought threshold
        ("rsi_oversold", 35),  # RSI oversold threshold
        ("sma_period", 50),  # Trend filter SMA period
        ("atr_period", 14),  # ATR period for position sizing
        ("risk_pct", 0.02),  # Risk per trade (2% of portfolio)
        ("trail_pct", 0.02),  # Trailing stop percentage
        ("position_size", 0.01),  # Default position size (fallback)
        ("max_positions", 2),  # Maximum concurrent positions
        ("timeframe", "1h"),  # Strategy timeframe
        ("debug", False),  # Enable debug output
    )

    def log(self, txt, dt=None):
        """Logging function."""
        if self.p.debug:
            dt = dt or self.data.datetime.datetime()
            print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        """Initialize strategy indicators and variables."""
        # Core indicators
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period, plot=True)

        # Shorter trend filter
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.sma_period, plot=True
        )

        # Volatility indicator for position sizing
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period, plot=True)

        # Additional momentum indicators
        self.macd = bt.indicators.MACD(
            self.data.close, period_me1=12, period_me2=26, period_signal=9, plot=True
        )

        # Price rate of change
        self.roc = bt.indicators.RateOfChange(self.data.close, period=10, plot=True)

        # Track our trades
        self.trades = []
        self.last_trade_time = None
        self.min_trade_interval = timedelta(hours=1)  # Reduced minimum time between trades

        # Trading state
        self.trailing_stop = None
        self.entry_price = None

        # Debug counters
        self.check_count = 0

    def _calculate_position_size(self):
        """Calculate dynamic position size based on ATR and risk percentage."""
        # Get current portfolio value and ATR
        portfolio_value = self.broker.getvalue()
        atr_value = self.atr[0]

        if not atr_value:
            self.log(f"Using default position size (no ATR): {self.p.position_size}")
            return self.p.position_size

        # Calculate position size based on risk
        risk_amount = portfolio_value * self.p.risk_pct
        price = self.data.close[0]

        # Use 1.5x ATR as our stop loss distance (reduced from 2x)
        stop_distance = 1.5 * atr_value

        if stop_distance <= 0:
            self.log(f"Using default position size (zero stop distance): {self.p.position_size}")
            return self.p.position_size

        # Calculate position size that risks risk_amount given the stop distance
        position_size = risk_amount / stop_distance

        # Convert to asset units
        position_units = position_size / price

        # Apply minimum and maximum constraints
        min_size = self.p.position_size
        max_size = 0.1  # Maximum 10% of portfolio per trade

        final_size = max(min_size, min(position_units, max_size))
        self.log(f"Calculated position size: {final_size}")
        return final_size

    def _should_open_long(self) -> bool:
        """Check if we should open a long position."""
        # Basic conditions with more lenient requirements
        conditions = {
            "price_above_sma": self.data.close[0] > self.sma[0],
            "rsi_oversold": self.rsi[0] < self.p.rsi_oversold,
            "macd_positive": self.macd.macd[0] > self.macd.signal[0],
            "roc_positive": self.roc[0] > 0,
        }

        self.log(f"Long conditions: {conditions}")

        # Time-based filters
        can_trade = True
        if self.last_trade_time:
            time_since_last = self.data.datetime.datetime() - self.last_trade_time
            can_trade = time_since_last >= self.min_trade_interval

        # Position limit check
        position_available = len(self.trades) < self.p.max_positions

        # Need at least 2 conditions plus timing and position availability
        conditions_met = sum(conditions.values()) >= 2

        return can_trade and position_available and conditions_met

    def _should_open_short(self) -> bool:
        """Check if we should open a short position."""
        # Basic conditions with more lenient requirements
        conditions = {
            "price_below_sma": self.data.close[0] < self.sma[0],
            "rsi_overbought": self.rsi[0] > self.p.rsi_overbought,
            "macd_negative": self.macd.macd[0] < self.macd.signal[0],
            "roc_negative": self.roc[0] < 0,
        }

        self.log(f"Short conditions: {conditions}")

        # Time-based filters
        can_trade = True
        if self.last_trade_time:
            time_since_last = self.data.datetime.datetime() - self.last_trade_time
            can_trade = time_since_last >= self.min_trade_interval

        # Position limit check
        position_available = len(self.trades) < self.p.max_positions

        # Need at least 2 conditions plus timing and position availability
        conditions_met = sum(conditions.values()) >= 2

        return can_trade and position_available and conditions_met

    def _update_trailing_stop(self):
        """Update trailing stop price for open positions."""
        if not self.position or not self.entry_price:
            return

        price = self.data.close[0]

        if self.position.size > 0:  # Long position
            trail_price = price * (1 - self.p.trail_pct)
            if not self.trailing_stop or trail_price > self.trailing_stop:
                self.trailing_stop = trail_price
                self.log(f"Updated long trailing stop: {self.trailing_stop}")

        else:  # Short position
            trail_price = price * (1 + self.p.trail_pct)
            if not self.trailing_stop or trail_price < self.trailing_stop:
                self.trailing_stop = trail_price
                self.log(f"Updated short trailing stop: {self.trailing_stop}")

    def _should_close_position(self) -> bool:
        """Check if we should close the current position."""
        if not self.position or not self.trailing_stop:
            return False

        price = self.data.close[0]

        if self.position.size > 0:  # Long position
            # Close if price below trailing stop or RSI overbought
            should_close = price < self.trailing_stop or self.rsi[0] > self.p.rsi_overbought
            self.log(
                f"Long position - Price: {price}, Stop: {self.trailing_stop}, "
                f"RSI: {self.rsi[0]}, Close: {should_close}"
            )
            return should_close

        else:  # Short position
            # Close if price above trailing stop or RSI oversold
            should_close = price > self.trailing_stop or self.rsi[0] < self.p.rsi_oversold
            self.log(
                f"Short position - Price: {price}, Stop: {self.trailing_stop}, "
                f"RSI: {self.rsi[0]}, Close: {should_close}"
            )
            return should_close

    def next(self):
        """Execute trading logic for the next candle."""
        self.check_count += 1

        # Skip if not enough data for indicators
        if self.check_count < self.p.sma_period:
            return

        self.log(
            f"Processing bar {self.check_count} - Close: {self.data.close[0]}, "
            f"RSI: {self.rsi[0]}, SMA: {self.sma[0]}"
        )

        if not self.position:  # No position
            size = self._calculate_position_size()

            if self._should_open_long():
                self.log("Opening long position")
                self.buy(size=size)
                self.entry_price = self.data.close[0]
                self.trailing_stop = self.entry_price * (1 - self.p.trail_pct)
                self.last_trade_time = self.data.datetime.datetime()

            elif self._should_open_short():
                self.log("Opening short position")
                self.sell(size=size)
                self.entry_price = self.data.close[0]
                self.trailing_stop = self.entry_price * (1 + self.p.trail_pct)
                self.last_trade_time = self.data.datetime.datetime()

        else:  # Have position
            self._update_trailing_stop()

            if self._should_close_position():
                self.log("Closing position")
                self.close()
                self.trailing_stop = None
                self.entry_price = None

    def notify_trade(self, trade):
        """Track completed trades."""
        if trade.status == trade.Closed:
            self.trades.append(
                {
                    "entry_time": bt.num2date(trade.dtopen),
                    "exit_time": bt.num2date(trade.dtclose),
                    "entry_price": trade.price,
                    "exit_price": trade.pnlcomm,
                    "profit_loss": trade.pnl,
                    "profit_loss_pct": trade.pnlcomm / trade.price * 100,
                }
            )
            self.log(f"Trade closed - P/L: {trade.pnlcomm:.2f}")


class BacktestCommissionScheme(bt.CommInfoBase):
    """Commission scheme that mimics real exchange fees."""

    params = (
        ("commission", 0.001),  # 0.1% commission
        ("mult", 1.0),  # Multiplier
        ("margin", False),  # No margin trading
    )

    def _getcommission(self, size, price, pseudoexec):
        """Calculate commission for trade."""
        return abs(size) * price * self.p.commission
