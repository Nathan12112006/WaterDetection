"""Application entry point."""

import json
import logging
from collections.abc import Sequence

from cli import parse_args
from service import DetectionRuntime
from utils import YoloServiceError, configure_logging

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run object detection from command-line arguments.

    Args:
        argv: Arguments to parse without the executable name. When omitted,
            arguments are read from ``sys.argv``.

    Returns:
        ``0`` when detection succeeds or ``1`` when the application encounters
        an error. Argument parsing errors exit directly with status ``2``.
    """
    configure_logging()

    try:
        config = parse_args(argv)
        runtime = DetectionRuntime(device=config.device)
        detections = runtime.detect(
            config.image,
            model=config.model,
            confidence=config.confidence,
        )
        print(
            json.dumps(
                [detection.to_dict() for detection in detections],
                indent=2,
            )
        )
        return 0
    except YoloServiceError as error:
        logger.error("%s", error)
        return 1
    except Exception:
        logger.exception("Unexpected application error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
