"""Logging configuration and setup module."""

import logging
import sys


def setup_logging(log_level: str | None = None) -> None:
    """Configure root and application loggers with formatted output."""
    from src.core.config import get_settings

    settings = get_settings()
    level_name = (log_level or settings.LOG_LEVEL).upper()
    numeric_level = getattr(logging, level_name, logging.INFO)

    log_format = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # Silence chatty third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("telegram.ext").setLevel(logging.INFO)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return configured logger instance for a given module."""
    return logging.getLogger(name)
