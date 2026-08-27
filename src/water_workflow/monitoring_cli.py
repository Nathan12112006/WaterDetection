from __future__ import annotations

import argparse
import time

from .config import load_config
from .monitoring.engine import MonitoringEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-camera water monitoring")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--camera-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = MonitoringEngine(load_config(args.config))
    engine.start(args.camera_id)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        engine.close()


if __name__ == "__main__":
    main()
