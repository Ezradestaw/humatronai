import logging
import sys
import re
from typing import Any

# Patterns for sensitive data that should NEVER be logged
SENSITIVE_PATTERNS = [
    re.compile(r'(token[:=]\s*)[a-zA-Z0-9_\-:]+', re.IGNORECASE),
    re.compile(r'(password[:=]\s*)[^\s,]+', re.IGNORECASE),
    re.compile(r'(key[:=]\s*)[a-zA-Z0-9_\-]+', re.IGNORECASE),
    re.compile(r'(secret[:=]\s*)[a-zA-Z0-9_\-]+', re.IGNORECASE),
    re.compile(r'(\d{8,11}:[a-zA-Z0-9_\-]{20,})'), # Telegram bot token regex
]

class SanitizedFormatter(logging.Formatter):
    """Logging formatter that scrubs API tokens, passwords, and sensitive keys from log output."""
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r'\1[REDACTED]', sanitized)
        return sanitized

def setup_logger(name: str = "humatron", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = SanitizedFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

logger = setup_logger()
