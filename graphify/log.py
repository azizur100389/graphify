# Centralized logging for graphify
#
# Every module should use:
#     from graphify.log import logger
#
# Log levels follow standard Python semantics:
#   DEBUG    - internal detail (e.g. per-file extraction timing)
#   INFO     - user-facing status (e.g. "Rebuilt: 42 nodes, 15 edges")
#   WARNING  - recoverable issue (e.g. extraction schema warning)
#   ERROR    - failure that stops a pipeline stage
#
# The CLI controls verbosity via --verbose (DEBUG) and --quiet (WARNING only).
# Default level is INFO.
from __future__ import annotations

import logging
import sys


def _create_logger() -> logging.Logger:
    """Create and configure the graphify logger.

    Returns a logger with a stderr StreamHandler using a clean format:
        [graphify] message            (INFO)
        [graphify] WARNING: message   (WARNING and above)
    """
    _logger = logging.getLogger("graphify")
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_GraphifyFormatter())
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
    return _logger


class _GraphifyFormatter(logging.Formatter):
    """Custom formatter that matches the existing [graphify] prefix style.

    INFO messages:     [graphify] Rebuilt: 42 nodes
    WARNING messages:  [graphify] WARNING: extraction schema issue
    ERROR messages:    [graphify] ERROR: graph.json is corrupted
    DEBUG messages:    [graphify] DEBUG: parsing sample.py
    """

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            return f"[graphify] {record.getMessage()}"
        level = record.levelname
        return f"[graphify] {level}: {record.getMessage()}"


def set_level(level: int) -> None:
    """Set the graphify log level.

    Args:
        level: A logging level constant (e.g. logging.DEBUG, logging.WARNING).
    """
    logger.setLevel(level)


def set_verbosity(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configure log verbosity from CLI flags.

    Args:
        verbose: If True, set level to DEBUG.
        quiet: If True, set level to WARNING. Ignored if verbose is also True.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)


logger = _create_logger()
