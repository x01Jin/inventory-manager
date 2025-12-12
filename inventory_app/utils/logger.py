"""
Centralized logging configuration for the inventory application.
All modules should import and use this logger instance.
"""

import logging
import os
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler


class SanitizeFilter(logging.Filter):
    """
    Logging filter that sanitizes messages to avoid leaking PII and trims long free-form text.
    Modifies the final formatted message by replacing emails/phones/SSNs and truncating long strings.
    """

    EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CC_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
    PHONE_RE = re.compile(r"\+?\d[\d\-() ]{6,}\d")

    def __init__(self, max_length=256):
        super().__init__()
        self.max_length = max_length

    def sanitize(self, text: str) -> str:
        if not text:
            return text

        # Replace common PII with placeholders
        text = self.EMAIL_RE.sub("<REDACTED_EMAIL>", text)
        text = self.SSN_RE.sub("<REDACTED_SSN>", text)
        text = self.CC_RE.sub("<REDACTED_CARD>", text)
        text = self.PHONE_RE.sub("<REDACTED_PHONE>", text)

        # Truncate long free-form messages
        if len(text) > self.max_length:
            return text[: self.max_length - 3] + "..."
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Format message once to capture args expansion then sanitize
            formatted = record.getMessage()
            sanitized = self.sanitize(formatted)
            # Replace the msg with sanitized message and clear args
            record.msg = sanitized
            record.args = None
        except Exception:
            # Fail-safe: don't block logging if sanitization fails
            pass
        return True


def setup_logger(
    logs_dir: str | os.PathLike | None = None,
    *,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    redact_max_length: int = 256,
):
    """
    Sets up centralized logging for the application.
    Creates logs directory if it doesn't exist and configures logging to logs/logs.txt.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path(logs_dir) if logs_dir else Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure logger
    logger = logging.getLogger("inventory_app")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler for logs/logs.txt: use rotating file handler with size-based rotation
    log_file = logs_dir / "logs.txt"
    # Ensure the logs directory exists and a file is created with restrictive permissions
    try:
        log_file.touch(exist_ok=True)
        # Set restrictive permissions on Unix-like systems
        if os.name != "nt":
            os.chmod(log_file, 0o600)
    except Exception:
        pass

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler for development (optional, can be disabled for production)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(SanitizeFilter(max_length=redact_max_length))
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)

    # Only add console handler if not in executable mode
    # This prevents console window from appearing in standalone exe
    import sys

    if not getattr(sys, "frozen", False):
        logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logger()
