"""Standardized logging configuration for all components."""

import logging
import logging.handlers
import os
from datetime import datetime


def configure_logger(name=None, log_dir=None):
    """
    Configure and return a logger with file and console handlers.

    Args:
        name: Logger name (default: None for root logger)
        log_dir: Directory for log files (default: 'logs' in current directory)

    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create file handler for info+ logs
    log_filename = f'{datetime.now().strftime("%Y-%m-%d")}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, log_filename),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Create file handler for error+ logs
    error_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, f'error_{log_filename}'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)

    return logger