import type {
  BoundingBoxTuple,
  Detection,
} from '../types'

export function displayDetectionClass(className: string): string {
  return className.trim().toLowerCase() === 'water damage'
    ? 'water accumulation'
    : className
}

export class BoundingBox {
  readonly x1: number
  readonly y1: number
  readonly x2: number
  readonly y2: number

  constructor(x1: number, y1: number, x2: number, y2: number) {
    if (![x1, y1, x2, y2].every(Number.isFinite)) {
      throw new TypeError('Bounding-box coordinates must be finite numbers.')
    }
    if (x2 <= x1 || y2 <= y1) {
      throw new RangeError(
        'Bounding-box right/bottom coordinates must exceed left/top.',
      )
    }
    this.x1 = x1
    this.y1 = y1
    this.x2 = x2
    this.y2 = y2
  }

  static from(value: readonly number[]): BoundingBox {
    if (value.length !== 4) {
      throw new TypeError('A bounding box must contain four coordinates.')
    }
    return new BoundingBox(value[0], value[1], value[2], value[3])
  }

  toArray(): BoundingBoxTuple {
    return [this.x1, this.y1, this.x2, this.y2]
  }

  area(): number {
    return (this.x2 - this.x1) * (this.y2 - this.y1)
  }

  intersectionArea(otherValue: readonly number[]): number {
    const other = BoundingBox.from(otherValue)
    return (
      Math.max(0, Math.min(this.x2, other.x2) - Math.max(this.x1, other.x1)) *
      Math.max(0, Math.min(this.y2, other.y2) - Math.max(this.y1, other.y1))
    )
  }

  iou(otherValue: readonly number[]): number {
    const other = BoundingBox.from(otherValue)
    const intersection = this.intersectionArea(other.toArray())
    const union = this.area() + other.area() - intersection
    return union > 0 ? intersection / union : 0
  }

  containment(otherValue: readonly number[]): number {
    const other = BoundingBox.from(otherValue)
    const smallerArea = Math.min(this.area(), other.area())
    return smallerArea > 0
      ? this.intersectionArea(other.toArray()) / smallerArea
      : 0
  }

  clamp(width: number, height: number): BoundingBox {
    const x1 = Math.max(0, Math.min(width, this.x1))
    const y1 = Math.max(0, Math.min(height, this.y1))
    const x2 = Math.max(0, Math.min(width, this.x2))
    const y2 = Math.max(0, Math.min(height, this.y2))
    return new BoundingBox(x1, y1, x2, y2)
  }

  toYolo(width: number, height: number): BoundingBoxTuple {
    const box = this.clamp(width, height)
    return [
      (box.x1 + box.x2) / 2 / width,
      (box.y1 + box.y2) / 2 / height,
      (box.x2 - box.x1) / width,
      (box.y2 - box.y1) / height,
    ]
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function parseDetection(value: unknown): Detection {
  if (!isRecord(value)) {
    throw new TypeError('Each detection must be an object.')
  }
  if (typeof value.class !== 'string' || value.class.length === 0) {
    throw new TypeError('Each detection must have a class name.')
  }
  if (
    typeof value.confidence !== 'number' ||
    !Number.isFinite(value.confidence) ||
    value.confidence < 0 ||
    value.confidence > 1
  ) {
    throw new TypeError('Each detection must have a valid confidence.')
  }
  if (
    !Array.isArray(value.bbox) ||
    !value.bbox.every((coordinate) => typeof coordinate === 'number')
  ) {
    throw new TypeError('Each detection must have a bounding box.')
  }
  return {
    class: value.class,
    confidence: value.confidence,
    bbox: BoundingBox.from(value.bbox).toArray(),
  }
}

export function normalizeDetections(value: unknown): Detection[] {
  if (!Array.isArray(value)) {
    throw new TypeError('Detection response must be an array.')
  }
  return value.map(parseDetection)
}

export function suppressContainedDetections(
  detections: readonly Detection[],
  threshold = 0.95,
): Detection[] {
  const survivors: { detection: Detection; index: number }[] = []
  const ranked = detections
    .map((detection, index) => ({ detection, index }))
    .sort(
      (left, right) =>
        right.detection.confidence - left.detection.confidence,
    )

  for (const candidate of ranked) {
    const suppressed = survivors.some(
      ({ detection: kept }) =>
        kept.class === candidate.detection.class &&
        kept.confidence > candidate.detection.confidence &&
        BoundingBox.from(kept.bbox).containment(candidate.detection.bbox) >=
          threshold,
    )
    if (!suppressed) survivors.push(candidate)
  }

  const survivorIndexes = new Set(survivors.map(({ index }) => index))
  return detections.filter((_detection, index) => survivorIndexes.has(index))
}

export function classSummary(detections: readonly Detection[]): string {
  const counts = new Map<string, number>()
  for (const detection of detections) {
    counts.set(detection.class, (counts.get(detection.class) ?? 0) + 1)
  }
  if (counts.size === 0) return 'no detections'
  return [...counts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, count]) => `${displayDetectionClass(name)}: ${count}`)
    .join(', ')
}
