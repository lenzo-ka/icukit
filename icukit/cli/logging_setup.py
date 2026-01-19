"""Logging configuration for icukit CLI."""

import logging
import sys

logger = logging.getLogger("icukit")


def setup_logging(verbose: int = 0) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
    """
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if verbose >= 2:
        formatter = logging.Formatter("%(levelname)s [%(name)s]: %(message)s")
    else:
        formatter = logging.Formatter("%(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
