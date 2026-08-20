"""Apply service-owned suppression rules to backend detections."""

from models import Detection

_CONTAINMENT_THRESHOLD = 0.95
_SAME_CLASS_IOU_THRESHOLD = 0.4


def suppress_contained_lower_confidence(
    detections: list[Detection],
) -> list[Detection]:
    """Discard the lower-confidence member of same-class contained pairs."""

    survivors: list[tuple[int, Detection]] = []
    ranked = sorted(
        enumerate(detections),
        key=lambda item: item[1].confidence,
        reverse=True,
    )
    for index, candidate in ranked:
        suppressed = any(
            kept.class_name == candidate.class_name
            and (
                _iou(kept.bbox, candidate.bbox)
                >= _SAME_CLASS_IOU_THRESHOLD
                or (
                    kept.confidence > candidate.confidence
                    and _containment(kept.bbox, candidate.bbox)
                    >= _CONTAINMENT_THRESHOLD
                )
            )
            for _, kept in survivors
        )
        if not suppressed:
            survivors.append((index, candidate))

    survivor_indices = {index for index, _ in survivors}
    return [
        detection
        for index, detection in enumerate(detections)
        if index in survivor_indices
    ]


def _containment(left: list[float], right: list[float]) -> float:
    """Return intersection area as a fraction of the smaller box area."""

    left_area = _area(left)
    right_area = _area(right)
    smaller_area = min(left_area, right_area)
    if smaller_area <= 0.0:
        return 0.0

    return _intersection_area(left, right) / smaller_area


def _area(box: list[float]) -> float:
    """Return a non-negative bounding-box area."""

    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(left: list[float], right: list[float]) -> float:
    """Return intersection over union for two bounding boxes."""

    intersection = _intersection_area(left, right)
    union = _area(left) + _area(right) - intersection
    return intersection / union if union > 0.0 else 0.0


def _intersection_area(left: list[float], right: list[float]) -> float:
    """Return the overlapping area of two bounding boxes."""

    intersection_width = max(
        0.0,
        min(left[2], right[2]) - max(left[0], right[0]),
    )
    intersection_height = max(
        0.0,
        min(left[3], right[3]) - max(left[1], right[1]),
    )
    return intersection_width * intersection_height
