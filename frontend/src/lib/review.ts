import type {
  BoundingBoxTuple,
  Detection,
  ImageEntry,
  ReviewDetection,
  ReviewHistory,
  ReviewSignals,
} from '../types'
import type { ModelClass } from '../modelClasses'
import { BoundingBox } from './detections'

const HISTORY_LIMIT = 100
const FILENAME_COLLATOR = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: 'base',
})

export interface ReviewStatus {
  active: number
  confirmed: number
  imageApproved: boolean
  allBoxesConfirmed: boolean
}

export interface RankedReviewEntry {
  entry: ImageEntry
  uncertainty: number
  signals: ReviewSignals
}

export function compareImageFilenames(
  left: ImageEntry,
  right: ImageEntry,
): number {
  const leftStartsWithNumber = /^\d/.test(left.file.name)
  const rightStartsWithNumber = /^\d/.test(right.file.name)
  if (leftStartsWithNumber !== rightStartsWithNumber) {
    return leftStartsWithNumber ? -1 : 1
  }
  return (
    FILENAME_COLLATOR.compare(left.file.name, right.file.name) ||
    left.originalIndex - right.originalIndex
  )
}

export function cloneReviewDetections(
  detections: readonly ReviewDetection[],
): ReviewDetection[] {
  return detections.map((detection) => ({
    ...detection,
    bbox: [...detection.bbox],
  }))
}

export function modelReviewDetection(
  detection: Detection,
  id: number,
): ReviewDetection {
  return {
    ...detection,
    bbox: BoundingBox.from(detection.bbox).toArray(),
    id,
    confirmed: false,
    removed: false,
    source: 'model',
  }
}

export function manualReviewDetection(
  bbox: BoundingBoxTuple,
  id: number,
  className: ModelClass,
): ReviewDetection {
  return {
    class: className,
    confidence: 1,
    bbox: BoundingBox.from(bbox).toArray(),
    id,
    confirmed: true,
    removed: false,
    source: 'manual',
  }
}

export function activeDetections(
  detections: readonly ReviewDetection[],
): Detection[] {
  return detections
    .filter((detection) => !detection.removed)
    .map(({ class: className, confidence, bbox }) => ({
      class: className,
      confidence,
      bbox: [...bbox],
    }))
}

export function reviewStatus(
  detections: readonly ReviewDetection[],
  imageApproved: boolean,
): ReviewStatus {
  const active = detections.filter((detection) => !detection.removed)
  const confirmed = active.filter((detection) => detection.confirmed).length
  return {
    active: active.length,
    confirmed,
    imageApproved,
    allBoxesConfirmed: active.length > 0 && confirmed === active.length,
  }
}

export function statusLabel(status: ReviewStatus): string {
  if (status.imageApproved) {
    return status.active === 0
      ? 'Approved · no detections'
      : `Approved · ${status.confirmed} of ${status.active} boxes confirmed`
  }
  if (status.active === 0) return 'No active detections · approval needed'
  if (status.confirmed === status.active) {
    return `All ${status.active} confirmed`
  }
  return `${status.confirmed} of ${status.active} confirmed`
}

function geometryUncertainty(
  detections: readonly ReviewDetection[],
  width: number,
  height: number,
): number {
  if (detections.length === 0 || width <= 0 || height <= 0) return 1
  const imageArea = width * height
  return detections.reduce((highest, detection) => {
    const box = BoundingBox.from(detection.bbox)
    const boxWidth = box.x2 - box.x1
    const boxHeight = box.y2 - box.y1
    const ratio = Math.max(boxWidth / boxHeight, boxHeight / boxWidth)
    const areaRatio = box.area() / imageArea
    const shapeScore =
      ratio >= 6 ? 1 : ratio >= 4 ? 0.65 : ratio >= 3 ? 0.3 : 0
    const areaScore =
      areaRatio < 0.002
        ? 1
        : areaRatio < 0.006
          ? 0.6
          : areaRatio > 0.8
            ? 0.8
            : areaRatio > 0.6
              ? 0.4
              : 0
    return Math.max(highest, shapeScore, areaScore)
  }, 0)
}

export function reviewSignals(entry: ImageEntry): ReviewSignals {
  const detections = (entry.reviewDetections ?? []).filter(
    (detection) => !detection.removed,
  )
  return {
    confidence:
      detections.length === 0
        ? 1
        : Math.max(
            ...detections.map((detection) => 1 - detection.confidence),
          ),
    geometry: geometryUncertainty(detections, entry.width, entry.height),
    empty: detections.length === 0,
  }
}

export function reviewScore(signals: ReviewSignals): number {
  return Number(
    (
      signals.confidence * 0.7 + signals.geometry * 0.3
    ).toFixed(6),
  )
}

export function rankReviewEntries(
  entries: readonly ImageEntry[],
): RankedReviewEntry[] {
  return entries
    .filter(
      (entry) =>
        entry.reviewDetections !== null && !entry.imageApproved,
    )
    .map((entry) => {
      const signals = reviewSignals(entry)
      return {
        entry,
        signals,
        uncertainty: reviewScore(signals),
      }
    })
    .sort(
      (left, right) =>
        Number(left.entry.reviewEdited) -
          Number(right.entry.reviewEdited) ||
        right.uncertainty - left.uncertainty ||
        left.entry.originalIndex - right.entry.originalIndex,
    )
}

export function reviewReasons(signals: ReviewSignals): string[] {
  const reasons: string[] = []
  if (signals.empty) reasons.push('no detections')
  else if (signals.confidence >= 0.5) reasons.push('low confidence')
  if (signals.geometry >= 0.4) reasons.push('unusual box')
  return reasons.length > 0 ? reasons : ['routine']
}

export function emptyHistory(): ReviewHistory {
  return { past: [], future: [] }
}

export function recordHistory(
  history: ReviewHistory,
  detections: readonly ReviewDetection[],
): ReviewHistory {
  const past = [...history.past, cloneReviewDetections(detections)]
  return {
    past: past.slice(-HISTORY_LIMIT),
    future: [],
  }
}

export function undoHistory(
  history: ReviewHistory,
  current: readonly ReviewDetection[],
): { history: ReviewHistory; detections: ReviewDetection[] } | null {
  const previous = history.past.at(-1)
  if (!previous) return null
  return {
    history: {
      past: history.past.slice(0, -1),
      future: [cloneReviewDetections(current), ...history.future],
    },
    detections: cloneReviewDetections(previous),
  }
}

export function redoHistory(
  history: ReviewHistory,
  current: readonly ReviewDetection[],
): { history: ReviewHistory; detections: ReviewDetection[] } | null {
  const next = history.future[0]
  if (!next) return null
  return {
    history: {
      past: [...history.past, cloneReviewDetections(current)],
      future: history.future.slice(1),
    },
    detections: cloneReviewDetections(next),
  }
}
