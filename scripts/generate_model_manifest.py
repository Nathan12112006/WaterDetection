"""Generate the checked-in manifest for the four runtime-owned models."""

from __future__ import annotations

import json
import os
from ast import literal_eval
from datetime import datetime, timezone
from pathlib import Path

import onnxruntime as ort
import torch
import ultralytics
from ultralytics import YOLO

from service.model_manifest import (
    EXPECTED_CLASS_NAMES,
    MANIFEST_PATH,
    MODEL_FILENAMES,
    PROJECT_ROOT,
)
from service.model_manifest import sha256_file


def normalized_names(value: object) -> list[str]:
    """Convert indexed model names to a stable ordered list."""

    if isinstance(value, dict):
        return [str(value[index]) for index in sorted(value)]
    if isinstance(value, (list, tuple)):
        return [str(name) for name in value]
    raise RuntimeError(f"Unsupported model names value: {value!r}")


def load_torch_names(path: Path) -> list[str]:
    """Load trusted runtime weights and return their embedded class names."""

    variable = "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"
    previous = os.environ.get(variable)
    os.environ[variable] = "1"
    try:
        return normalized_names(YOLO(str(path)).names)
    finally:
        if previous is None:
            os.environ.pop(variable, None)
        else:
            os.environ[variable] = previous


def onnx_metadata(path: Path) -> tuple[list[str], list[int]]:
    """Return class names and fixed input size from an ONNX export."""

    session = ort.InferenceSession(
        str(path),
        providers=["CPUExecutionProvider"],
    )
    names_text = session.get_modelmeta().custom_metadata_map.get("names")
    if names_text is None:
        raise RuntimeError(f"{path.name} is missing names metadata.")
    names = normalized_names(literal_eval(names_text))
    input_shape = session.get_inputs()[0].shape
    if (
        len(input_shape) != 4
        or not isinstance(input_shape[2], int)
        or not isinstance(input_shape[3], int)
    ):
        raise RuntimeError(f"{path.name} has invalid input shape {input_shape}.")
    return names, [input_shape[2], input_shape[3]]


def artifact(path: Path) -> dict[str, object]:
    """Describe one immutable runtime artifact."""

    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> int:
    checkpoints: dict[str, object] = {}
    for checkpoint, filenames in MODEL_FILENAMES.items():
        torch_path = PROJECT_ROOT / filenames["torch"]
        onnx_path = PROJECT_ROOT / filenames["onnx"]
        torch_names = load_torch_names(torch_path)
        onnx_names, input_size = onnx_metadata(onnx_path)
        if torch_names != onnx_names:
            raise RuntimeError(
                f"{checkpoint} class names differ between Torch and ONNX."
            )
        if torch_names != list(EXPECTED_CLASS_NAMES):
            raise RuntimeError(
                f"{checkpoint} classes must be "
                f"{list(EXPECTED_CLASS_NAMES)!r}, got {torch_names!r}."
            )

        torch_artifact = artifact(torch_path)
        onnx_artifact = artifact(onnx_path)
        onnx_artifact["exported_from_sha256"] = torch_artifact["sha256"]
        checkpoints[checkpoint] = {
            "classes": torch_names,
            "input_size": input_size,
            "torch": torch_artifact,
            "onnx": onnx_artifact,
        }

    manifest = {
        "schema_version": 1,
        "project": "water-leak-detection-service",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_versions": {
            "torch": torch.__version__,
            "ultralytics": ultralytics.__version__,
            "onnxruntime": ort.__version__,
        },
        "checkpoints": checkpoints,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
