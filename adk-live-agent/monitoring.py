'' 'Performance monitoring and alerting system for live trading agent.' ''

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from slack_sdk import WebClient

logger = logging.getLogger(__name__)

# Prometheus metrics
TRADE_COUNT = Counter('trades_total', 'Total number of trades executed')
TRADE_VOLUME = Counter('trade_volume_total', 'Total trading volume in USDT')
TRADE_PNL = Histogram('trade_pnl_usdt', 'Trade PnL distribution in USDT')
AGENT_UPTIME = Gauge('agent_uptime_seconds', 'Trading agent uptime in seconds')
SYSTEM_HEALTH = Gauge(
    'system_health', 'Overall system health status (1=healthy, 0=unhealthy)'
)
ERROR_COUNT = Counter('errors_total', 'Total number of errors encountered', ['type'])


@dataclass
class HealthCheck:
    '' 'Health check configuration.' ''

    name: str
    threshold: float  # Threshold for check to pass
    current_value: float = 0.0
    status: bool = True
    last_check: float = 0.0


class MonitoringSystem:
    '' 'System for monitoring trading performance and health.' ''

    def __init__(
        self,
        prometheus_port: int = 8000,
        slack_token: Optional[str] = None,
        alert_channel: str = '#trading-alerts',
    ):
        '' 'Initialize monitoring system.' ''
        self.start_time = time.time()
        self.health_checks: Dict[str, HealthCheck] = {
            'api_latency': HealthCheck(name='API Latency', threshold=1000.0),  # ms
            'error_rate': HealthCheck(
                name='Error Rate', threshold=0.1  # 10% error rate
            ),
            'memory_usage': HealthCheck(
                name='Memory Usage', threshold=0.9  # 90% usage
            ),
        }

        # Initialize Prometheus metrics server
        start_http_server(prometheus_port)

        # Initialize Slack client if token provided
        self.slack_client = WebClient(token=slack_token) if slack_token else None
        self.alert_channel = alert_channel

        # Initialize scheduler for periodic health checks
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._update_health_metrics, 'interval', minutes=5)
        self.scheduler.start()

        # Set initial health status
        SYSTEM_HEALTH.set(1)

    def record_trade(self, volume: Decimal, pnl: Decimal):
        '' 'Record trade metrics.' ''
        TRADE_COUNT.inc()
        TRADE_VOLUME.inc(float(volume))
        TRADE_PNL.observe(float(pnl))

    def record_error(self, error_type: str, error_msg: str):
        '' 'Record error metrics and send alert if needed.' ''
        ERROR_COUNT.labels(type=error_type).inc()

        # Update error rate health check
        total_ops = sum(c._value.get() for c in ERROR_COUNT._metrics.values())
        error_rate = total_ops / max(TRADE_COUNT._value.get(), 1)

        check = self.health_checks['error_rate']
        check.current_value = error_rate
        check.last_check = time.time()
        check.status = error_rate <= check.threshold

        if not check.status:
            self._send_alert(
                f'High error rate detected: {error_rate:.2%}\n'
                f'Latest error ({error_type}): {error_msg}'
            )

    def update_api_latency(self, latency_ms: float):
        '' 'Update API latency health check.' ''
        check = self.health_checks['api_latency']
        check.current_value = latency_ms
        check.last_check = time.time()
        check.status = latency_ms <= check.threshold

        if not check.status:
            self._send_alert(
                f'High API latency detected: {latency_ms:.2f}ms\n'
                f'Threshold: {check.threshold}ms'
            )

    def update_memory_usage(self, usage_percent: float):
        '' 'Update memory usage health check.' ''
        check = self.health_checks['memory_usage']
        check.current_value = usage_percent
        check.last_check = time.time()
        check.status = usage_percent <= check.threshold

        if not check.status:
            self._send_alert(
                f'High memory usage detected: {usage_percent:.2%}\n'
                f'Threshold: {check.threshold:.2%}'
            )

    def get_system_status(self) -> Dict:
        '' 'Get current system status summary.' ''
        return {
            'uptime': time.time() - self.start_time,
            'trade_count': TRADE_COUNT._value.get(),
            'total_volume': TRADE_VOLUME._value.get(),
            'health_checks': {
                name: {
                    'status': check.status,
                    'current_value': check.current_value,
                    'threshold': check.threshold,
                    'last_check': check.last_check,
                }
                for name, check in self.health_checks.items()
            },
        }

    def _update_health_metrics(self):
        '' 'Update system health metrics periodically.' ''
        # Update uptime
        AGENT_UPTIME.set(time.time() - self.start_time)

        # Check overall system health
        all_healthy = all(check.status for check in self.health_checks.values())
        SYSTEM_HEALTH.set(1 if all_healthy else 0)

        # Log current status
        status = self.get_system_status()
        logger.info(f'System status update: {json.dumps(status, indent=2)}')

    def _send_alert(self, message: str):
        '' 'Send alert message.' ''
        logger.warning(message)

        if self.slack_client:
            try:
                self.slack_client.chat_postMessage(
                    channel=self.alert_channel,
                    text=message,
                    blocks=[
                        {
                            'type': 'section',
                            'text': {
                                'type': 'mrkdwn',
                                'text': f'*Trading Alert*\n{message}',
                            },
                        }
                    ],
                )
            except Exception as e:
                logger.error(f'Failed to send Slack alert: {e}')
