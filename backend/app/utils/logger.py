"""
Structured logging configuration
Sets up logging for the entire application
"""

import logging
import logging.config
import sys
import io
from pathlib import Path
from app.utils.config import settings, LOG_DIR


def _get_utf8_stream():
    """Return a UTF-8 safe wrapper around stdout for Windows compatibility."""
    if hasattr(sys.stdout, 'buffer'):
        return io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    return sys.stdout


class UTF8StreamHandler(logging.StreamHandler):
    """StreamHandler that always writes in UTF-8 to avoid cp1252 errors on Windows."""
    def __init__(self):
        super().__init__(stream=_get_utf8_stream())

    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback: strip non-ASCII characters and try again
            record.msg = record.msg.encode('ascii', 'replace').decode('ascii')
            super().emit(record)


def setup_logging():
    """
    Configure logging for the application
    Creates both file and console handlers
    """
    
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    log_file = str(LOG_DIR / "app.log")
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    if not root_logger.handlers:
        # Console handler (UTF-8 safe)
        console_handler = UTF8StreamHandler()
        console_handler.setLevel(settings.log_level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (UTF-8)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(settings.log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    Usage: logger = get_logger(__name__)
    """
    setup_logging()
    return logging.getLogger(name)