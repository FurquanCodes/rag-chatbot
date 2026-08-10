"""
Structured logging configuration
Sets up logging for the entire application
"""

import logging
import logging.config
from pathlib import Path
from app.utils.config import settings, LOG_DIR


def setup_logging():
    """
    Configure logging for the application
    Creates both file and console handlers
    """
    
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filename": str(LOG_DIR / "app.log"),
                "mode": "a",
                "encoding": "utf-8"
            }
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file"]
        },
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    Usage: logger = get_logger(__name__)
    """
    setup_logging()
    return logging.getLogger(name)