"""Measure the fixed water-detection ensemble through its public runtime."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean, median
from time import perf_counter

from models import Detection
from service import DetectionRuntime
from utils import YoloServiceError, configure_logging


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing and detection output collected for the fixed ensemble."""

    cold_detection_ms: float
    cached_inference_times_ms: list[float]
    detections: list[Detection]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse benchmark controls without exposing model choices."""

    parser = argparse.ArgumentParser(
        description="Measure the fixed water-detection ensemble.",
    )
    parser.add_argument("--image", default="test1.jpg")
    parser.add_argument(
        "--model",
        choices=["water_accumulation", "water_detection"],
        default="water_detection",
    )
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--runs", type=int, default=10)

    args = parser.parse_args(argv)

    if not 0.0 <= args.conf <= 1.0:
        parser.error("Confidence must be between 0.0 and 1.0.")
    if not args.device.strip():
        parser.error("Device must not be empty.")
    if args.warmup < 0:
        parser.error("Warm-up runs cannot be negative.")
    if args.runs < 1:
        parser.error("Runs must be at least 1.")

    return args


def benchmark_runtime(
    runtime: DetectionRuntime,
    args: argparse.Namespace,
) -> BenchmarkResult:
    """Measure one cold call and repeated cached calls on the ensemble."""

    cold_start = perf_counter()
    detections = runtime.detect(args.image, model=args.model, confidence=args.conf)
    cold_detection_ms = (perf_counter() - cold_start) * 1000

    for _ in range(args.warmup):
        runtime.detect(args.image, model=args.model, confidence=args.conf)

    cached_inference_times_ms: list[float] = []
    for _ in range(args.runs):
        inference_start = perf_counter()
        detections = runtime.detect(args.image, model=args.model, confidence=args.conf)
        elapsed_ms = (perf_counter() - inference_start) * 1000
        cached_inference_times_ms.append(elapsed_ms)

    return BenchmarkResult(
        cold_detection_ms=cold_detection_ms,
        cached_inference_times_ms=cached_inference_times_ms,
        detections=detections,
    )


def print_timing(result: BenchmarkResult) -> None:
    """Print cold and cached timings for the fixed ensemble."""

    times = result.cached_inference_times_ms
    print("\nFixed ensemble")
    print(f"  Cold detection: {result.cold_detection_ms:.2f} ms")
    print(f"  Average cached inference: {mean(times):.2f} ms")
    print(f"  Median cached inference: {median(times):.2f} ms")
    print(f"  Fastest cached inference: {min(times):.2f} ms")
    print(f"  Slowest cached inference: {max(times):.2f} ms")
    print(f"  Detections: {len(result.detections)}")


def main(argv: Sequence[str] | None = None) -> int:
    """Benchmark the fixed ensemble and print its timing summary."""

    configure_logging()
    args = parse_args(argv)

    print("Benchmark configuration")
    print(f"  Image: {args.image}")
    print(f"  Confidence: {args.conf}")
    print(f"  Model: {args.model}")
    print(f"  Device: {args.device}")
    print(f"  Warm-up runs: {args.warmup}")
    print(f"  Measured runs: {args.runs}")

    try:
        runtime = DetectionRuntime(device=args.device)
        result = benchmark_runtime(runtime, args)
    except (OSError, YoloServiceError) as error:
        print(f"Benchmark failed: {error}")
        return 1

    print_timing(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
