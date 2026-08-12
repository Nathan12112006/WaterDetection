import { describe, expect, it } from 'vitest'
import type {
  GrayFrame,
  TrackedDetection,
  VideoTrack,
} from './videoTracking'
import {
  createPlayback,
  estimateFlow,
  filterVideoEntries,
  framePercentageCount,
  samplePlayback,
  updateTracks,
} from './videoTracking'

const trackedDetection = (
  trackId: number | undefined,
  bbox: TrackedDetection['bbox'],
  confidence = 0.8,
): TrackedDetection => ({
  trackId,
  class: 'water accumulation',
  confidence,
  bbox,
})

function shiftedFrame(shiftX: number): GrayFrame {
  const width = 24
  const height = 20
  const data = new Uint8ClampedArray(width * height)
  for (let y = 2; y < height - 2; y += 1) {
    for (let x = 2; x < width - 4; x += 1) {
      data[y * width + x + shiftX] = (x * 37 + y * 61 + x * y * 3) % 256
    }
  }
  return { width, height, data }
}

describe('video playback', () => {
  it('interpolates coordinates without mixing track IDs', () => {
    const playback = createPlayback(
      [
        {
          time: 0,
          detections: [
            trackedDetection(1, [0, 0, 10, 10]),
            trackedDetection(2, [100, 0, 110, 10]),
          ],
        },
        {
          time: 1,
          detections: [
            trackedDetection(1, [10, 0, 20, 10]),
            trackedDetection(2, [80, 0, 90, 10]),
          ],
        },
      ],
      { smoothingTime: 0, maximumGap: 1.1, visibilityWindow: 0.1 },
    )
    const detections = samplePlayback(playback, 0.5)
    expect(detections.find((item) => item.trackId === 1)?.bbox[0]).toBe(5)
    expect(detections.find((item) => item.trackId === 2)?.bbox[0]).toBe(90)
  })

  it('does not bridge long missing-detection gaps', () => {
    const playback = createPlayback(
      [
        { time: 0, detections: [trackedDetection(1, [0, 0, 10, 10])] },
        { time: 1, detections: [trackedDetection(1, [10, 0, 20, 10])] },
      ],
      { smoothingTime: 0, maximumGap: 0.2, visibilityWindow: 0.1 },
    )
    expect(samplePlayback(playback, 0.5)).toEqual([])
  })
})

describe('optical flow', () => {
  it('recovers a known frame translation', () => {
    const flow = estimateFlow(
      shiftedFrame(0),
      shiftedFrame(2),
      [3, 3, 18, 17],
      { gridSize: 4, patchRadius: 1, searchRadius: 4 },
    )
    expect(flow?.dx).toBeCloseTo(2)
    expect(flow?.dy).toBeCloseTo(0)
  })
})

describe('temporal confidence', () => {
  it('scales patience by total frame count', () => {
    expect(framePercentageCount(1_200, 0.01)).toBe(12)
    expect(framePercentageCount(100, 0.01)).toBe(1)
  })

  it('keeps an established track visible through its patience window', () => {
    const tracks: VideoTrack[] = []
    const options = {
      enterConfidence: 0.5,
      exitConfidence: 0.3,
      exitPatience: 2,
    }
    const high = trackedDetection(undefined, [0, 0, 10, 10], 0.8)
    updateTracks(tracks, [high], 0, 0, 2, 0.3, options)
    const low = [1, 2, 3].map((frameIndex) => {
      const detection = trackedDetection(
        undefined,
        [0, 0, 10, 10],
        0.2,
      )
      updateTracks(
        tracks,
        [detection],
        frameIndex * 0.1,
        frameIndex,
        2,
        0.3,
        options,
      )
      return detection
    })
    expect(low.map((item) => item.temporallyVisible)).toEqual([
      true,
      true,
      false,
    ])
  })
})

describe('final filtering', () => {
  it('removes detections belonging to discarded tracks', () => {
    const entries = [
      {
        time: 0,
        detections: [
          trackedDetection(1, [0, 0, 10, 10]),
          trackedDetection(2, [20, 20, 30, 30]),
        ],
      },
    ]
    const surviving = [{ id: 1 }] as VideoTrack[]
    expect(filterVideoEntries(entries, surviving)[0].detections).toHaveLength(1)
  })
})
