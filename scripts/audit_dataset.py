"""Validate and safely repair the checked-in three-class YOLO dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / "dataset"
QUARANTINE_ROOT = PROJECT_ROOT / ".scratch" / "dataset-quarantine"
SPLITS = ("train", "valid", "test")
CLASS_NAMES = ("pipe burst", "water accumulation", "water drop")
IMAGE_SUFFIXES = {".avif", ".bmp", ".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class Annotation:
    class_id: int
    center_x: float
    center_y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    def is_valid(self) -> bool:
        tolerance = 1e-9
        left = self.center_x - self.width / 2
        top = self.center_y - self.height / 2
        right = self.center_x + self.width / 2
        bottom = self.center_y + self.height / 2
        return (
            self.class_id in range(len(CLASS_NAMES))
            and self.width > 0
            and self.height > 0
            and left >= -tolerance
            and top >= -tolerance
            and right <= 1 + tolerance
            and bottom <= 1 + tolerance
        )

    def clamped(self) -> Annotation:
        left = max(0.0, self.center_x - self.width / 2)
        top = max(0.0, self.center_y - self.height / 2)
        right = min(1.0, self.center_x + self.width / 2)
        bottom = min(1.0, self.center_y + self.height / 2)
        return Annotation(
            class_id=self.class_id,
            center_x=(left + right) / 2,
            center_y=(top + bottom) / 2,
            width=right - left,
            height=bottom - top,
        )

    def to_yolo(self) -> str:
        values = (
            self.center_x,
            self.center_y,
            self.width,
            self.height,
        )
        coordinates = " ".join(f"{value:.10f}".rstrip("0").rstrip(".") for value in values)
        return f"{self.class_id} {coordinates}"


def parse_label(path: Path) -> list[Annotation]:
    annotations: list[Annotation] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"{path}:{line_number} must contain five fields")
        try:
            annotation = Annotation(
                class_id=int(fields[0]),
                center_x=float(fields[1]),
                center_y=float(fields[2]),
                width=float(fields[3]),
                height=float(fields[4]),
            )
        except ValueError as error:
            raise ValueError(
                f"{path}:{line_number} contains a non-numeric value"
            ) from error
        annotations.append(annotation)
    return annotations


def image_paths() -> list[Path]:
    return sorted(
        path
        for split in SPLITS
        for path in (DATASET_ROOT / split / "images").iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def paired_label(image_path: Path) -> Path:
    return (
        image_path.parent.parent
        / "labels"
        / f"{image_path.stem}.txt"
    )


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_name(path: Path) -> str:
    return path.relative_to(DATASET_ROOT).parts[0]


def keeper_score(path: Path) -> tuple[int, int, int, float, str]:
    annotations = parse_label(paired_label(path))
    split_priority = {"train": 0, "valid": 1, "test": 2}[split_name(path)]
    valid_count = sum(annotation.is_valid() for annotation in annotations)
    total_area = sum(annotation.area for annotation in annotations)
    return (
        split_priority,
        valid_count,
        len(annotations),
        -total_area,
        path.name,
    )


def quarantine(path: Path, category: str) -> Path:
    relative_path = path.relative_to(PROJECT_ROOT)
    destination = QUARANTINE_ROOT / category / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Quarantine target already exists: {destination}")
    shutil.move(str(path), str(destination))
    return destination


def backup(path: Path, category: str) -> Path:
    relative_path = path.relative_to(PROJECT_ROOT)
    destination = QUARANTINE_ROOT / category / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup target already exists: {destination}")
    shutil.copy2(path, destination)
    return destination


def remove_exact_duplicates() -> list[dict[str, object]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in image_paths():
        groups[file_digest(path)].append(path)

    changes: list[dict[str, object]] = []
    for digest, paths in sorted(groups.items()):
        if len(paths) < 2:
            continue
        keeper = max(paths, key=keeper_score)
        removed: list[str] = []
        for duplicate in paths:
            if duplicate == keeper:
                continue
            label = paired_label(duplicate)
            quarantine(duplicate, "exact-duplicates")
            quarantine(label, "exact-duplicates")
            removed.append(str(duplicate.relative_to(PROJECT_ROOT)))
        changes.append(
            {
                "sha256": digest,
                "keeper": str(keeper.relative_to(PROJECT_ROOT)),
                "quarantined": removed,
            }
        )
    return changes


def clamp_annotations() -> list[str]:
    changed: list[str] = []
    for path in sorted(
        label
        for split in SPLITS
        for label in (DATASET_ROOT / split / "labels").glob("*.txt")
    ):
        annotations = parse_label(path)
        repaired = [
            annotation if annotation.is_valid() else annotation.clamped()
            for annotation in annotations
        ]
        if repaired == annotations:
            continue
        backup(path, "annotation-originals")
        text = "\n".join(annotation.to_yolo() for annotation in repaired)
        path.write_text(f"{text}\n" if text else "", encoding="utf-8")
        changed.append(str(path.relative_to(PROJECT_ROOT)))
    return changed


def normalize_images() -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for path in image_paths():
        with Image.open(path) as source:
            orientation = source.getexif().get(274, 1)
            needs_orientation = orientation not in (None, 1)
            needs_container = source.format == "MPO"
            if not needs_orientation and not needs_container:
                continue
            backup(path, "image-originals")
            normalized = ImageOps.exif_transpose(source).convert("RGB")
            normalized.save(
                path,
                format="JPEG",
                quality=95,
                subsampling=0,
                exif=b"",
            )
            changes.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "reason": ",".join(
                        reason
                        for condition, reason in (
                            (needs_orientation, "baked EXIF orientation"),
                            (needs_container, "converted MPO to JPEG"),
                        )
                        if condition
                    ),
                }
            )
    return changes


def expected_yaml_is_present() -> bool:
    text = (DATASET_ROOT / "data.yaml").read_text(encoding="utf-8")
    required_lines = {
        "train: train/images",
        "val: valid/images",
        "test: test/images",
        "nc: 3",
        "names: ['pipe burst', 'water accumulation', 'water drop']",
    }
    return required_lines.issubset(set(text.splitlines()))


def audit() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, object] = {}
    digests: dict[str, list[str]] = defaultdict(list)

    if not expected_yaml_is_present():
        errors.append("dataset/data.yaml does not match the three-class contract")

    for split in SPLITS:
        images = [
            path
            for path in image_paths()
            if split_name(path) == split
        ]
        labels = sorted((DATASET_ROOT / split / "labels").glob("*.txt"))
        image_stems = {path.stem for path in images}
        label_stems = {path.stem for path in labels}
        for stem in sorted(image_stems - label_stems):
            errors.append(f"{split} image {stem!r} has no label")
        for stem in sorted(label_stems - image_stems):
            errors.append(f"{split} label {stem!r} has no image")

        class_annotations: Counter[int] = Counter()
        null_images = 0
        for image_path in images:
            try:
                with Image.open(image_path) as image:
                    image.load()
                    orientation = image.getexif().get(274, 1)
                    if orientation not in (None, 1):
                        errors.append(
                            f"{image_path.relative_to(PROJECT_ROOT)} retains "
                            f"EXIF orientation {orientation}"
                        )
                    if image.format == "MPO":
                        errors.append(
                            f"{image_path.relative_to(PROJECT_ROOT)} is MPO"
                        )
                    if min(image.size) < 256:
                        warnings.append(
                            f"{image_path.relative_to(PROJECT_ROOT)} has "
                            f"low resolution {image.width}x{image.height}"
                        )
            except OSError as error:
                errors.append(f"{image_path}: cannot decode: {error}")
                continue

            digest = file_digest(image_path)
            digests[digest].append(str(image_path.relative_to(PROJECT_ROOT)))
            label_path = paired_label(image_path)
            try:
                annotations = parse_label(label_path)
            except (OSError, ValueError) as error:
                errors.append(
                    f"{label_path.relative_to(PROJECT_ROOT)} cannot be parsed: "
                    f"{error}"
                )
                continue
            if not annotations:
                null_images += 1
            for annotation in annotations:
                if not annotation.is_valid():
                    errors.append(
                        f"{paired_label(image_path).relative_to(PROJECT_ROOT)} "
                        "contains an invalid annotation"
                    )
                class_annotations[annotation.class_id] += 1

        counts[split] = {
            "images": len(images),
            "annotations": sum(class_annotations.values()),
            "null_images": null_images,
            "class_annotations": {
                CLASS_NAMES[class_id]: class_annotations[class_id]
                for class_id in range(len(CLASS_NAMES))
            },
        }

    for paths in digests.values():
        if len(paths) > 1:
            errors.append(f"exact duplicate images remain: {paths}")

    return {
        "ok": not errors,
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
    }


def fix() -> dict[str, object]:
    if QUARANTINE_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse existing quarantine: {QUARANTINE_ROOT}"
        )
    duplicates = remove_exact_duplicates()
    annotations = clamp_annotations()
    images = normalize_images()
    result = {
        "exact_duplicate_groups": duplicates,
        "clamped_annotation_files": annotations,
        "normalized_images": images,
    }
    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    (QUARANTINE_ROOT / "changes.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply recoverable fixes and write originals to .scratch.",
    )
    arguments = parser.parse_args()

    if arguments.fix:
        changes = fix()
        print(json.dumps(changes, indent=2))

    report = audit()
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
