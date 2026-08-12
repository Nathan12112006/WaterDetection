import { describe, expect, it } from 'vitest'
import type { Detection } from '../types'
import {
  BoundingBox,
  displayDetectionClass,
  normalizeDetections,
  suppressContainedDetections,
} from './detections'

const detection = (
  confidence: number,
  bbox: Detection['bbox'],
): Detection => ({
  class: 'water accumulation',
  confidence,
  bbox,
})

describe('detection display names', () => {
  it('keeps the ensemble class mapping canonical', () => {
    expect(displayDetectionClass('water accumulation')).toBe('water accumulation')
    expect(displayDetectionClass('water damage')).toBe('water accumulation')
    expect(displayDetectionClass('pipe leak')).toBe('pipe leak')
  })
})

describe('BoundingBox', () => {
  it('computes area and YOLO coordinates', () => {
    const box = BoundingBox.from([10, 20, 50, 80])
    expect(box.area()).toBe(2_400)
    expect(box.toYolo(100, 100)).toEqual([0.3, 0.5, 0.4, 0.6])
  })

  it('rejects inverted coordinates', () => {
    expect(() => BoundingBox.from([50, 20, 10, 80])).toThrow(RangeError)
  })
})

describe('detection normalization', () => {
  it('validates unknown API data at runtime', () => {
    expect(
      normalizeDetections([
        {
          class: 'water accumulation',
          confidence: 0.7,
          bbox: [1, 2, 3, 4],
        },
      ]),
    ).toEqual([detection(0.7, [1, 2, 3, 4])])
    expect(() => normalizeDetections({})).toThrow(TypeError)
  })
})

describe('contained detection suppression', () => {
  it('does not let a discarded box suppress an unrelated box', () => {
    const outer = detection(0.8, [0, 0, 100, 100])
    const left = detection(0.9, [0, 0, 40, 100])
    const right = detection(0.7, [60, 0, 100, 100])
    expect(suppressContainedDetections([outer, left, right])).toEqual([
      left,
      right,
    ])
  })
})
