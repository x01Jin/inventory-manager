"""
Centralized logging configuration for the inventory application.
All modules should import and use this logger instance.
"""

import logging
from pathlib import Path


def setup_logger():
    """
    Sets up centralized logging for the application.
    Creates logs directory if it doesn't exist and configures logging to logs/logs.txt.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure logger
    logger = logging.getLogger("inventory_app")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler for logs/logs.txt
    log_file = logs_dir / "logs.txt"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # Console handler for development (optional, can be disabled for production)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)

    # Only add console handler if not in executable mode
    # This prevents console window from appearing in standalone exe
    import sys
    if not getattr(sys, 'frozen', False):
        logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logger()
