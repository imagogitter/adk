#!/usr/bin/env python3
"""Main entry point for the ADK Live Trading Agent."""

import asyncio
import os
import signal
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import get_config, get_env_bool
from utils.logger import configure_logger

from live_agent import LiveTradingAgent

# Configure logger
logger = configure_logger('live_agent', os.path.join(os.path.dirname(__file__), 'logs'))

# Global agent instance
agent = None


async def shutdown(signal_received=None):
    """Handle graceful shutdown."""
    if signal_received:
        logger.info(f"Received exit signal {signal_received.name}...")

    logger.info("Shutting down...")
    if agent:
        await agent.shutdown()

    logger.info("Shutdown complete.")


async def main():
    """Initialize and run the live trading agent."""
    global agent

    try:
        logger.info("Starting ADK Live Trading Agent...")

        # Load configuration
        config = get_config()

        # Initialize agent
        agent = LiveTradingAgent(
            exchange_id=config['exchange']['id'],
            paper_trading=get_env_bool('PAPER_TRADING', True),
            initial_capital=config['trading']['initial_capital'],
            state_file=os.path.join(
                os.path.dirname(__file__), 'state', 'agent_state.json'
            ),
            prometheus_port=config['monitoring']['prometheus_port'],
            slack_token=config['monitoring']['slack_token'],
        )

        # Start agent
        success = await agent.startup()
        if not success:
            logger.error("Failed to start agent. Exiting.")
            await shutdown()
            return 1

        logger.info("Agent started successfully. Running until interrupted...")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
        await shutdown()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        await shutdown()
        return 1

    return 0


if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda sig, _: asyncio.create_task(shutdown(sig)))

    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
