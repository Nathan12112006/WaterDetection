"""Validate the Torch checkpoints owned by the service.

Runtime startup depends only on ``best.pt`` and ``waterAccubest.pt``.  The
former is the three-class general detector and the latter is the legacy
``water damage`` specialist. ``last.pt`` is an optional selectable general
checkpoint. A JSON manifest and ONNX exports are not part of this runtime
contract.

``verify_model_manifest`` is retained as a deprecated helper for repository
tools that still import it.  It is intentionally not called by runtime
startup; :func:`verify_runtime_models` only validates the two fixed files.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils import ModelManifestError


PROJECT_ROOT = Path(__file__).resolve().parent.parent

GENERAL_MODEL_FILENAME = "best.pt"
LAST_MODEL_FILENAME = "last.pt"
SPECIALIST_MODEL_FILENAME = "waterAccubest.pt"
GENERAL_MODEL_PATH = PROJECT_ROOT / GENERAL_MODEL_FILENAME
LAST_MODEL_PATH = PROJECT_ROOT / LAST_MODEL_FILENAME
SPECIALIST_MODEL_PATH = PROJECT_ROOT / SPECIALIST_MODEL_FILENAME
RUNTIME_MODEL_FILENAMES = {
    "general": GENERAL_MODEL_FILENAME,
    "specialist": SPECIALIST_MODEL_FILENAME,
}
RUNTIME_MODEL_PATHS = {
    "general": GENERAL_MODEL_PATH,
    "specialist": SPECIALIST_MODEL_PATH,
}

EXPECTED_GENERAL_CLASS_NAMES = (
    "pipe burst",
    "water accumulation",
    "water drop",
)
EXPECTED_SPECIALIST_CLASS_NAMES = ("water damage",)

_CLASS_NAME_ALIASES = {
    "dripping water": "water drop",
}

# Deprecated manifest-era exports.  They are kept so maintenance scripts can
# report a useful error instead of failing at import time.  Runtime code does
# not consume this four-artifact matrix.
MANIFEST_PATH = PROJECT_ROOT / "model-manifest.json"
MODEL_FILENAMES = {
    "best": {"torch": "best.pt", "onnx": "best.onnx"},
    "last": {"torch": "last.pt", "onnx": "last.onnx"},
}
EXPECTED_CLASS_NAMES = EXPECTED_GENERAL_CLASS_NAMES

# Public runtime paths include the two required models and the optional
# selectable general checkpoint.
MODEL_PATHS = {
    **RUNTIME_MODEL_PATHS,
    "last": LAST_MODEL_PATH,
}

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    """Return a lowercase SHA-256 digest without loading the file in memory."""

    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_class_names(value: object) -> tuple[str, ...]:
    """Normalize an Ultralytics class map while enforcing indexed integrity."""

    if isinstance(value, Mapping):
        indexed: dict[int, str] = {}
        for raw_index, raw_name in value.items():
            if isinstance(raw_index, bool):
                raise ModelManifestError("Model class indices must be integers.")
            if isinstance(raw_index, int):
                index = raw_index
            elif isinstance(raw_index, str) and raw_index.isdecimal():
                index = int(raw_index)
            else:
                raise ModelManifestError("Model class indices must be integers.")

            if index < 0 or index in indexed:
                raise ModelManifestError(
                    "Model class indices must be unique non-negative integers."
                )
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise ModelManifestError(
                    "Model class names must be non-empty strings."
                )
            indexed[index] = raw_name

        if set(indexed) != set(range(len(indexed))):
            raise ModelManifestError(
                "Model class indices must be contiguous from zero."
            )
        return tuple(indexed[index] for index in range(len(indexed)))

    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        names = tuple(value)
        if not names or not all(
            isinstance(name, str) and name.strip() for name in names
        ):
            raise ModelManifestError("Model class names must be non-empty strings.")
        return names

    raise ModelManifestError("Model class map must be a list or dictionary.")


def canonical_class_name(value: str) -> str:
    """Convert supported checkpoint labels to the public application names."""

    normalized = " ".join(value.strip().lower().replace("_", " ").split())
    return _CLASS_NAME_ALIASES.get(normalized, normalized)


def expected_class_names(model_role: str) -> tuple[str, ...]:
    """Return the exact class map required for a fixed model role."""

    try:
        return {
            "general": EXPECTED_GENERAL_CLASS_NAMES,
            "last": EXPECTED_GENERAL_CLASS_NAMES,
            "specialist": EXPECTED_SPECIALIST_CLASS_NAMES,
        }[model_role]
    except KeyError as error:
        raise ModelManifestError(
            f"Unknown runtime model role: {model_role!r}."
        ) from error


def validate_loaded_class_names(model_role: str, value: object) -> tuple[str, ...]:
    """Validate a loaded Torch class map against its fixed model role."""

    names = normalize_class_names(value)
    canonical_names = tuple(canonical_class_name(name) for name in names)
    expected = expected_class_names(model_role)
    if canonical_names != expected:
        raise ModelManifestError(
            f"Loaded {model_role} model classes must be {list(expected)!r}; "
            f"got {list(names)!r}."
        )
    return canonical_names


def _verify_runtime_file(path: Path) -> None:
    """Reject missing, non-regular, or empty runtime model files."""

    try:
        stat = path.stat()
    except OSError as error:
        raise ModelManifestError(f"Runtime model is missing: {path}") from error
    if not path.is_file() or stat.st_size <= 0:
        raise ModelManifestError(
            f"Runtime model must be a non-empty regular file: {path}"
        )


def verify_runtime_models(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Path]:
    """Verify both fixed runtime files without consulting a manifest."""

    root = Path(project_root).resolve()
    paths = {
        role: root / filename
        for role, filename in RUNTIME_MODEL_FILENAMES.items()
    }
    for path in paths.values():
        _verify_runtime_file(path)
    return paths


def verify_model_manifest(
    manifest_path: Path = MANIFEST_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Deprecated validation for the old four-artifact manifest format.

    This function exists only for the manifest-generation tool and historical
    callers.  Runtime startup deliberately calls :func:`verify_runtime_models`
    instead.
    """

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ModelManifestError(
            f"Model manifest is missing: {manifest_path}"
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise ModelManifestError(f"Model manifest is invalid: {error}") from error

    if manifest.get("schema_version") != 1:
        raise ModelManifestError("Model manifest schema_version must be 1.")

    checkpoints = manifest.get("checkpoints")
    if not isinstance(checkpoints, dict) or set(checkpoints) != set(
        MODEL_FILENAMES
    ):
        raise ModelManifestError(
            "Model manifest must contain exactly the best and last checkpoints."
        )

    for checkpoint, expected_files in MODEL_FILENAMES.items():
        entry = checkpoints[checkpoint]
        if not isinstance(entry, dict):
            raise ModelManifestError(
                f"Manifest checkpoint {checkpoint!r} must be an object."
            )

        classes = entry.get("classes")
        if (
            not isinstance(classes, list)
            or not classes
            or not all(isinstance(name, str) and name for name in classes)
        ):
            raise ModelManifestError(
                f"Manifest checkpoint {checkpoint!r} has invalid classes."
            )
        if classes != list(EXPECTED_CLASS_NAMES):
            raise ModelManifestError(
                f"Manifest checkpoint {checkpoint!r} classes must be "
                f"{list(EXPECTED_CLASS_NAMES)!r} in dataset order."
            )
        input_size = entry.get("input_size")
        if (
            not isinstance(input_size, list)
            or len(input_size) != 2
            or not all(isinstance(value, int) and value > 0 for value in input_size)
        ):
            raise ModelManifestError(
                f"Manifest checkpoint {checkpoint!r} has invalid input_size."
            )

        verified_digests: dict[str, str] = {}
        for backend, expected_filename in expected_files.items():
            artifact = entry.get(backend)
            if not isinstance(artifact, dict):
                raise ModelManifestError(
                    f"Manifest {checkpoint}/{backend} artifact is missing."
                )
            if artifact.get("file") != expected_filename:
                raise ModelManifestError(
                    f"Manifest {checkpoint}/{backend} must use "
                    f"{expected_filename}."
                )

            expected_digest = artifact.get("sha256")
            if (
                not isinstance(expected_digest, str)
                or _SHA256_PATTERN.fullmatch(expected_digest) is None
            ):
                raise ModelManifestError(
                    f"Manifest {checkpoint}/{backend} has an invalid SHA-256."
                )

            model_path = project_root / expected_filename
            try:
                actual_size = model_path.stat().st_size
            except OSError as error:
                raise ModelManifestError(
                    f"Runtime model is missing: {model_path}"
                ) from error

            if artifact.get("size_bytes") != actual_size:
                raise ModelManifestError(
                    "Runtime model size does not match the manifest: "
                    f"{expected_filename}"
                )

            actual_digest = sha256_file(model_path)
            if actual_digest != expected_digest:
                raise ModelManifestError(
                    "Runtime model SHA-256 does not match the manifest: "
                    f"{expected_filename}"
                )
            verified_digests[backend] = actual_digest

        source_digest = entry["onnx"].get("exported_from_sha256")
        if source_digest != verified_digests["torch"]:
            raise ModelManifestError(
                f"Manifest {checkpoint}/onnx is not paired with "
                f"{expected_files['torch']}."
            )

    return manifest

