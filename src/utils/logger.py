# src/logger.py

import logging
import coloredlogs
import os
from dotenv import load_dotenv

load_dotenv()

def setup_logging(level: str = None):
    """Configure logging globally."""
    if not level:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()

    fmt = "%(asctime)s %(name)-36s %(levelname)-8s %(message)s"
    date_fmt = "%H:%M:%S"

    coloredlogs.install(level=level, fmt=fmt, datefmt=date_fmt)
    logging.basicConfig(level=level, format=fmt, datefmt=date_fmt)

    # Reduce noise
    logging.getLogger("web3.providers.HTTPProvider").setLevel(logging.WARNING)
    logging.getLogger("web3.RequestManager").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with consistent setup.
    
    Automatically sets up logging on the first call.
    """
    setup_logging()
    return logging.getLogger(name)
