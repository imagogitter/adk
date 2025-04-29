'' 'Failover and recovery procedures for live trading agent.' ''

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict

import ccxt
from influxdb_client import InfluxDBClient

logger = logging.getLogger(__name__)


@dataclass
class TradeState:
    '' 'Current state of a trade.' ''

    symbol: str
    side: str
    size: Decimal
    entry_price: Decimal
    timestamp: float


class RecoveryManager:
    '' 'Manages system recovery and trade state persistence.' ''

    def __init__(
        self,
        state_file: str,
        exchange: ccxt.Exchange,
        influx_client: InfluxDBClient,
        backup_dir: str = './backups',
    ):
        '' 'Initialize recovery manager.' ''
        self.state_file = state_file
        self.exchange = exchange
        self.influx_client = influx_client
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or load state
        self.active_trades: Dict[str, TradeState] = {}
        self._load_state()

    def _load_state(self):
        '' 'Load trading state from file.' ''
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)

                self.active_trades = {
                    symbol: TradeState(
                        symbol=trade['symbol'],
                        side=trade['side'],
                        size=Decimal(str(trade['size'])),
                        entry_price=Decimal(str(trade['entry_price'])),
                        timestamp=trade['timestamp'],
                    )
                    for symbol, trade in state_data.items()
                }
                logger.info(
                    f'Loaded {len(self.active_trades)} active trades from state'
                )
        except Exception as e:
            logger.error(f'Failed to load state: {e}')
            self._backup_corrupted_state()

    def _save_state(self):
        '' 'Save current trading state to file.' ''
        try:
            state_data = {
                symbol: {
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'size': str(trade.size),
                    'entry_price': str(trade.entry_price),
                    'timestamp': trade.timestamp,
                }
                for symbol, trade in self.active_trades.items()
            }

            # Write to temporary file first
            temp_file = f'{self.state_file}.tmp'
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            # Atomic rename for consistency
            Path(temp_file).rename(self.state_file)

        except Exception as e:
            logger.error(f'Failed to save state: {e}')

    def _backup_corrupted_state(self):
        '' 'Backup potentially corrupted state file.' ''
        if Path(self.state_file).exists():
            backup_path = self.backup_dir / f'state_backup_{int(time.time())}.json'
            try:
                Path(self.state_file).rename(backup_path)
                logger.info(f'Backed up corrupted state to {backup_path}')
            except Exception as e:
                logger.error(f'Failed to backup corrupted state: {e}')

    def record_trade(self, trade: TradeState):
        '' 'Record new trade state.' ''
        self.active_trades[trade.symbol] = trade
        self._save_state()

    def remove_trade(self, symbol: str):
        '' 'Remove completed/closed trade.' ''
        if symbol in self.active_trades:
            del self.active_trades[symbol]
            self._save_state()

    async def recover_from_crash(self) -> bool:
        '' 'Recover system state after crash.' ''
        try:
            # Verify exchange connection and database connection
            await self._verify_exchange_connection()
            if not self._verify_database_connection():
                raise RuntimeError('Failed to connect to InfluxDB')

            # Reconcile trades
            await self._reconcile_trades()
            logger.info('System recovery completed successfully')
            return True

        except Exception as e:
            logger.error(f'Recovery failed: {e}')
            return False

    async def _verify_exchange_connection(self):
        '' 'Verify exchange API connection and permissions.' ''
        try:
            await self.exchange.load_markets()
            balance = await self.exchange.fetch_balance()

            if not balance:
                raise RuntimeError('Failed to fetch balance')

        except Exception as e:
            logger.error(f'Exchange connection verification failed: {e}')
            raise

    def _verify_database_connection(self) -> bool:
        '' 'Verify InfluxDB connection.' ''
        try:
            health = self.influx_client.health()
            return health.status == 'pass'
        except Exception as e:
            logger.error(f'Database connection verification failed: {e}')
            return False

    async def _reconcile_trades(self):
        '' 'Reconcile recorded trades with exchange state.' ''
        try:
            # Fetch open positions from exchange
            positions = await self.exchange.fetch_positions()
            exchange_positions = {
                pos['symbol']: pos for pos in positions if float(pos['size']) != 0
            }

            # Check each recorded trade
            for symbol, trade in list(self.active_trades.items()):
                if symbol not in exchange_positions:
                    logger.warning(f'Trade {symbol} not found in exchange positions')
                    # Query recent trades to check if it was closed
                    trades = await self.exchange.fetch_my_trades(
                        symbol, int(trade.timestamp)
                    )

                    closed = any(
                        t['side'] != trade.side
                        and float(t['amount']) == float(trade.size)
                        for t in trades
                    )

                    if closed:
                        logger.info(f'Trade {symbol} was closed, removing from state')
                        self.remove_trade(symbol)
                    else:
                        logger.error(
                            f'Inconsistent state for {symbol}, manual review needed'
                        )

            # Check for any positions not in our state
            for symbol, pos in exchange_positions.items():
                if symbol not in self.active_trades:
                    logger.warning(f'Found unexpected position {symbol}')
                    # Record the position in our state
                    self.record_trade(
                        TradeState(
                            symbol=symbol,
                            side='long' if float(pos['size']) > 0 else 'short',
                            size=Decimal(str(abs(float(pos['size'])))),
                            entry_price=Decimal(str(pos['entryPrice'])),
                            timestamp=time.time(),
                        )
                    )

        except Exception as e:
            logger.error(f'Trade reconciliation failed: {e}')
            raise
