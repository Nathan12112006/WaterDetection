"""Parse command-line arguments into application configuration."""

import argparse
from collections.abc import Sequence

from config import AppConfig
from utils import ConfigurationError


def parse_args(argv: Sequence[str] | None = None) -> AppConfig:
    """Parse and validate command-line options.

    Args:
        argv: Arguments to parse without the executable name. When omitted,
            arguments are read from ``sys.argv``.

    Returns:
        A validated configuration containing the selected inference options.

    Raises:
        SystemExit: If argument syntax or a configuration value is invalid.
    """
    defaults = AppConfig()
    parser = argparse.ArgumentParser(
        description="Run YOLO object detection on an image.",
    )
    parser.add_argument(
        "--image",
        default=defaults.image,
        help=f"Image to process (default: {defaults.image}).",
    )
    parser.add_argument(
        "--model",
        choices=["water_accumulation", "water_detection"],
        default=defaults.model,
        help="Model to run (default: water_detection; best.pt only).",
    )
    parser.add_argument(
        "--conf",
        dest="confidence",
        type=float,
        default=defaults.confidence,
        help=f"Minimum confidence (default: {defaults.confidence}).",
    )
    parser.add_argument(
        "--device",
        default=defaults.device,
        help=f"Inference device (default: {defaults.device}).",
    )

    args = parser.parse_args(argv)

    try:
        return AppConfig(**vars(args))
    except ConfigurationError as error:
        parser.error(str(error))
