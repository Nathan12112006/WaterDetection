"""Run the three-class and accumulation-specialist models together."""

import argparse
import json
from collections.abc import Sequence

from service import DetectionRuntime
from utils import YoloServiceError, configure_logging


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect water damage with the fixed model ensemble."
    )
    parser.add_argument("--image", required=True, help="Image to process.")
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Minimum confidence for all detections (default: 0.25).",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Inference device such as cpu, 0, or cuda:0 (default: cpu).",
    )
    parser.add_argument(
        "--model",
        choices=["water_accumulation", "water_detection"],
        default="water_detection",
        help="Runtime model role (default: water_detection).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)

    try:
        runtime = DetectionRuntime(device=args.device)
        detections = runtime.detect(
            args.image,
            model=args.model,
            confidence=args.conf,
        )
    except (OSError, YoloServiceError) as error:
        print(f"Detection failed: {error}")
        return 1

    print(
        json.dumps(
            [detection.to_dict() for detection in detections],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
