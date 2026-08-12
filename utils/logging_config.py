"""Configure consistent application log output."""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging to write formatted messages to stderr.

    Sending logs to stderr keeps stdout available for machine-readable JSON.
    Python applies ``basicConfig`` only when the root logger has no handlers.

    Args:
        level: Minimum severity emitted by the root logger.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
