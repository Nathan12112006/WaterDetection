import { describe, expect, it } from 'vitest'
import type { ImageEntry } from '../types'
import { buildDatasetArchive } from './archive'
import { emptyHistory, modelReviewDetection } from './review'

describe('dataset archive', () => {
  it('contains an image, YOLO label, data file, and review summary', async () => {
    const reviewDetection = modelReviewDetection(
      {
        class: 'pipe burst',
        confidence: 0.8,
        bbox: [10, 10, 50, 60],
      },
      1,
    )
    const entry: ImageEntry = {
      id: '1',
      file: new File(['jpeg'], 'leak.jpg', { type: 'image/jpeg' }),
      originalIndex: 0,
      url: 'blob:1',
      width: 100,
      height: 100,
      exportDetections: [reviewDetection],
      reviewDetections: [reviewDetection],
      reviewHistory: emptyHistory(),
      reviewViewport: { zoom: 1, panX: 0, panY: 0 },
      reviewSelected: false,
      reviewEdited: false,
      imageApproved: false,
      error: null,
    }
    const archive = await buildDatasetArchive([entry])
    const bytes = new Uint8Array(await archive.arrayBuffer())
    const text = new TextDecoder().decode(bytes)
    expect(archive.type).toBe('application/zip')
    expect(text).toContain('images/train/00001-leak.jpg')
    expect(text).toContain('labels/train/00001-leak.txt')
    expect(text).toContain('data.yaml')
    expect(text).toContain('review-summary.json')
    expect(text).toContain('pipe burst')
    expect(text).toContain('water accumulation')
    expect(text).toContain('water drop')
    expect(text).not.toContain('water damage')
  })
})
