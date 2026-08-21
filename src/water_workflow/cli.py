from __future__ import annotations

import argparse

from .config import load_config
from .models import create_model
from .pipeline import Workflow
from .video import OpenCVVideoSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the water-leak video workflow")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source", choices=("camera", "file"), help="Override video.source")
    parser.add_argument("--camera-index", type=int, help="Override video.camera_index")
    parser.add_argument("--file", dest="file_path", help="Override video.file_path")
    parser.add_argument("--model", choices=("noop", "yolo"), help="Override model.backend")
    parser.add_argument("--weights", help="Override model.weights")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.source:
        config.video.source = args.source
    if args.camera_index is not None:
        config.video.camera_index = args.camera_index
    if args.file_path:
        config.video.file_path = args.file_path
    if args.model:
        config.model.backend = args.model
    if args.weights:
        config.model.weights = args.weights

    source = OpenCVVideoSource(config.video)
    model = create_model(config.model)
    Workflow(config, source, model).run()
