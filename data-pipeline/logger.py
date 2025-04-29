"""Logging configuration module for the data pipeline.

This module provides a centralized logging setup for the data pipeline system,
ensuring consistent log formatting and handling across all pipeline components.
It configures the root logger with appropriate formatting and level settings.
"""

import logging

# Configure root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create logger for this module
logger = logging.getLogger(__name__)
