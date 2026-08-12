import { describe, expect, it } from 'vitest'
import type { ImageEntry, ReviewDetection } from '../types'
import {
  compareImageFilenames,
  emptyHistory,
  modelReviewDetection,
  manualReviewDetection,
  rankReviewEntries,
  recordHistory,
  redoHistory,
  undoHistory,
} from './review'

const modelDetection = (confidence: number): ReviewDetection =>
  modelReviewDetection(
    {
      class: 'pipe burst',
      confidence,
      bbox: [20, 20, 70, 70],
    },
    1,
  )

function entry(
  id: string,
  confidence: number,
  options: Partial<ImageEntry> = {},
): ImageEntry {
  const reviewDetections = [modelDetection(confidence)]
  return {
    id,
    file: new File(['image'], `${id}.jpg`, { type: 'image/jpeg' }),
    originalIndex: Number(id),
    url: `blob:${id}`,
    width: 100,
    height: 100,
    exportDetections: reviewDetections,
    reviewDetections,
    reviewHistory: emptyHistory(),
    reviewViewport: { zoom: 1, panX: 0, panY: 0 },
    reviewSelected: false,
    reviewEdited: false,
    imageApproved: false,
    error: null,
    ...options,
  }
}

describe('review queue', () => {
  it('ranks untouched uncertain images first and excludes approvals', () => {
    const routine = entry('1', 0.95)
    const uncertain = entry('2', 0.2)
    const reviewed = entry('3', 0.2, { reviewEdited: true })
    const approved = entry('4', 0.9, { imageApproved: true })
    expect(
      rankReviewEntries([approved, routine, reviewed, uncertain]).map(
        (item) => item.entry.id,
      ),
    ).toEqual(['2', '1', '3'])
  })

  it('orders filenames naturally with number-prefixed files first', () => {
    const entries = [
      entry('alpha', 0.8),
      entry('10', 0.8),
      entry('Beta', 0.8),
      entry('2', 0.8),
      entry('1', 0.8),
    ]

    expect(
      entries
        .sort(compareImageFilenames)
        .map(({ file }) => file.name),
    ).toEqual(['1.jpg', '2.jpg', '10.jpg', 'alpha.jpg', 'Beta.jpg'])
  })
})

describe('review history', () => {
  it('undoes and redoes immutable snapshots', () => {
    const original = [modelDetection(0.8)]
    const history = recordHistory(emptyHistory(), original)
    const removed = [{ ...original[0], removed: true }]
    const undone = undoHistory(history, removed)
    expect(undone?.detections[0].removed).toBe(false)
    const redone = undone
      ? redoHistory(undone.history, undone.detections)
      : null
    expect(redone?.detections[0].removed).toBe(true)
  })
})

describe('manual annotations', () => {
  it('uses the class selected by the reviewer', () => {
    const detection = manualReviewDetection(
      [10, 20, 30, 40],
      2,
      'water drop',
    )

    expect(detection.class).toBe('water drop')
  })
})
