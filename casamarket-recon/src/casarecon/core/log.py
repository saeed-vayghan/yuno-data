"""Stdlib logging to stderr, one `key=value` line per step."""

import logging
import sys

LOGGER_NAME = "casarecon"


def setup(verbose: bool = False) -> logging.Logger:
    """Configure the casarecon logger once (idempotent). Side effect: adds a stderr handler."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def get(name: str = "") -> logging.Logger:
    """Child logger, e.g. get('build') -> 'casarecon.build'."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


def kv(**fields: object) -> str:
    """Format fields as one line: kv(step='build', rows=10) -> 'step=build rows=10'."""
    return " ".join(f"{k}={v}" for k, v in fields.items())
