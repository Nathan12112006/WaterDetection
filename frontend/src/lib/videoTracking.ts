import type { BoundingBoxTuple, Detection } from '../types'
import { BoundingBox } from './detections'

type BoxVector = [
  centerX: number,
  centerY: number,
  width: number,
  height: number,
]

export interface GrayFrame {
  width: number
  height: number
  data: Uint8ClampedArray
}

export interface Flow {
  dx: number
  dy: number
  dt: number
  reliability: number
}

export interface TrackedDetection extends Detection {
  trackId?: number
  temporallyVisible?: boolean
  visibilitySegment?: number
  flowToNext?: Flow
  flowFromPrevious?: Flow
}

export interface VideoEntry {
  time: number
  detections: TrackedDetection[]
}

export interface VideoTrack {
  id: number
  className: string
  startTime: number
  endTime: number
  visibleEndTime: number
  lastFrame: number
  observations: number
  visibleObservations: number
  temporallyVisible: boolean
  everVisible: boolean
  lowConfidenceFrames: number
  visibilitySegment: number
  maxConfidence: number
  lastDetection: TrackedDetection
  representativeTime: number
  representativeDetection: TrackedDetection
}

interface PlaybackObservation {
  time: number
  detection: TrackedDetection
  vector: BoxVector
}

interface PlaybackTrack {
  trackId: number
  observations: PlaybackObservation[]
}

export interface VideoPlayback {
  maximumGap: number
  visibilityWindow: number
  tracks: PlaybackTrack[]
}

export interface FlowOptions {
  gridSize?: number
  patchRadius?: number
  searchRadius?: number
  minimumTexture?: number
}

export interface TrackingOptions {
  enterConfidence?: number
  exitConfidence?: number
  exitPatience?: number
}

export interface PlaybackOptions {
  smoothingTime?: number
  maximumGap?: number
  visibilityWindow?: number
}

function boxVector([x1, y1, x2, y2]: BoundingBoxTuple): BoxVector {
  return [
    (x1 + x2) / 2,
    (y1 + y2) / 2,
    x2 - x1,
    y2 - y1,
  ]
}

function vectorBox([
  centerX,
  centerY,
  width,
  height,
]: BoxVector): BoundingBoxTuple {
  return [
    centerX - width / 2,
    centerY - height / 2,
    centerX + width / 2,
    centerY + height / 2,
  ]
}

function interpolateVector(
  left: BoxVector,
  right: BoxVector,
  amount: number,
): BoxVector {
  return left.map(
    (value, index) => value + (right[index] - value) * amount,
  ) as BoxVector
}

function median(values: readonly number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((left, right) => left - right)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2
}

export function framePercentageCount(
  totalFrames: number,
  percentage: number,
): number {
  const frames = Math.max(0, Math.floor(totalFrames))
  if (frames === 0) return 0
  return Math.max(1, Math.ceil(frames * Math.max(0, percentage)))
}

export function grayscale(imageData: ImageData): GrayFrame {
  const { data: pixels, width, height } = imageData
  if (
    width <= 0 ||
    height <= 0 ||
    pixels.length !== width * height * 4
  ) {
    throw new TypeError('Expected RGBA ImageData.')
  }
  const data = new Uint8ClampedArray(width * height)
  for (let source = 0, target = 0; source < pixels.length; source += 4) {
    data[target] = Math.round(
      pixels[source] * 0.299 +
        pixels[source + 1] * 0.587 +
        pixels[source + 2] * 0.114,
    )
    target += 1
  }
  return { width, height, data }
}

function validateFrames(previous: GrayFrame, current: GrayFrame): void {
  if (
    previous.width !== current.width ||
    previous.height !== current.height ||
    previous.data.length !== previous.width * previous.height ||
    current.data.length !== current.width * current.height
  ) {
    throw new TypeError('Optical-flow frames must have matching dimensions.')
  }
}

function patchAt(
  frame: GrayFrame,
  x: number,
  y: number,
  radius: number,
): number[] {
  const patch: number[] = []
  for (let offsetY = -radius; offsetY <= radius; offsetY += 1) {
    for (let offsetX = -radius; offsetX <= radius; offsetX += 1) {
      patch.push(frame.data[(y + offsetY) * frame.width + x + offsetX])
    }
  }
  return patch
}

function patchTexture(patch: readonly number[]): number {
  const mean =
    patch.reduce((total, value) => total + value, 0) / patch.length
  return Math.sqrt(
    patch.reduce(
      (total, value) => total + (value - mean) ** 2,
      0,
    ) / patch.length,
  )
}

function matchPatch(
  patch: readonly number[],
  current: GrayFrame,
  x: number,
  y: number,
  patchRadius: number,
  searchRadius: number,
): { dx: number; dy: number; error: number } {
  let best = { dx: 0, dy: 0, error: Number.POSITIVE_INFINITY }
  for (let dy = -searchRadius; dy <= searchRadius; dy += 1) {
    for (let dx = -searchRadius; dx <= searchRadius; dx += 1) {
      let error = 0
      let patchIndex = 0
      for (
        let offsetY = -patchRadius;
        offsetY <= patchRadius;
        offsetY += 1
      ) {
        for (
          let offsetX = -patchRadius;
          offsetX <= patchRadius;
          offsetX += 1
        ) {
          const currentValue =
            current.data[
              (y + dy + offsetY) * current.width + x + dx + offsetX
            ]
          error += Math.abs(patch[patchIndex] - currentValue)
          patchIndex += 1
        }
      }
      if (error < best.error) best = { dx, dy, error }
    }
  }
  return { ...best, error: best.error / patch.length }
}

export function estimateFlow(
  previous: GrayFrame,
  current: GrayFrame,
  bbox: BoundingBoxTuple,
  options: FlowOptions = {},
): Omit<Flow, 'dt'> | null {
  validateFrames(previous, current)
  const gridSize = Math.max(2, Math.floor(options.gridSize ?? 4))
  const patchRadius = Math.max(1, Math.floor(options.patchRadius ?? 2))
  const searchRadius = Math.max(1, Math.floor(options.searchRadius ?? 6))
  const minimumTexture = Math.max(0, options.minimumTexture ?? 18)
  const [rawX1, rawY1, rawX2, rawY2] = bbox
  const margin = patchRadius + searchRadius
  const x1 = Math.max(margin, Math.min(previous.width - margin, rawX1))
  const y1 = Math.max(margin, Math.min(previous.height - margin, rawY1))
  const x2 = Math.max(margin, Math.min(previous.width - margin, rawX2))
  const y2 = Math.max(margin, Math.min(previous.height - margin, rawY2))
  if (x2 - x1 < 2 || y2 - y1 < 2) return null

  const flows: { dx: number; dy: number }[] = []
  for (let gridY = 0; gridY < gridSize; gridY += 1) {
    for (let gridX = 0; gridX < gridSize; gridX += 1) {
      const x = Math.round(
        x1 + ((gridX + 0.5) / gridSize) * (x2 - x1),
      )
      const y = Math.round(
        y1 + ((gridY + 0.5) / gridSize) * (y2 - y1),
      )
      const patch = patchAt(previous, x, y, patchRadius)
      if (patchTexture(patch) < minimumTexture) continue
      flows.push(
        matchPatch(
          patch,
          current,
          x,
          y,
          patchRadius,
          searchRadius,
        ),
      )
    }
  }
  const minimumPoints = Math.max(
    2,
    Math.ceil(gridSize * gridSize * 0.2),
  )
  if (flows.length < minimumPoints) return null

  const dx = median(flows.map((flow) => flow.dx))
  const dy = median(flows.map((flow) => flow.dy))
  const deviations = flows.map((flow) =>
    Math.hypot(flow.dx - dx, flow.dy - dy),
  )
  const consistency = 1 / (1 + median(deviations))
  const coverage = flows.length / (gridSize * gridSize)
  return {
    dx,
    dy,
    reliability: Math.max(0, Math.min(1, consistency * coverage)),
  }
}

function smoothingAlpha(deltaTime: number, smoothingTime: number): number {
  if (smoothingTime <= 0 || deltaTime <= 0) return 1
  return 1 - Math.exp(-deltaTime / smoothingTime)
}

function smoothVectors(
  observations: readonly PlaybackObservation[],
  smoothingTime: number,
): BoxVector[] {
  if (observations.length <= 1 || smoothingTime <= 0) {
    return observations.map((observation) => [...observation.vector])
  }
  const forward: BoxVector[] = [[...observations[0].vector]]
  for (let index = 1; index < observations.length; index += 1) {
    const alpha = smoothingAlpha(
      observations[index].time - observations[index - 1].time,
      smoothingTime,
    )
    forward.push(
      interpolateVector(
        forward[index - 1],
        observations[index].vector,
        alpha,
      ),
    )
  }

  const backward = new Array<BoxVector>(observations.length)
  backward[observations.length - 1] = [
    ...observations[observations.length - 1].vector,
  ]
  for (let index = observations.length - 2; index >= 0; index -= 1) {
    const alpha = smoothingAlpha(
      observations[index + 1].time - observations[index].time,
      smoothingTime,
    )
    backward[index] = interpolateVector(
      backward[index + 1],
      observations[index].vector,
      alpha,
    )
  }
  return forward.map(
    (vector, index) =>
      vector.map(
        (value, coordinate) =>
          (value + backward[index][coordinate]) / 2,
      ) as BoxVector,
  )
}

export function createPlayback(
  entries: readonly VideoEntry[],
  options: PlaybackOptions = {},
): VideoPlayback {
  const smoothingTime = Math.max(0, options.smoothingTime ?? 0.12)
  const maximumGap = Math.max(0, options.maximumGap ?? 0.35)
  const visibilityWindow = Math.max(
    0,
    options.visibilityWindow ?? Math.min(0.2, maximumGap),
  )
  const tracks = new Map<number, PlaybackObservation[]>()

  for (const entry of [...entries].sort(
    (left, right) => left.time - right.time,
  )) {
    for (const detection of entry.detections) {
      if (detection.trackId === undefined) continue
      const segment = detection.visibilitySegment ?? 0
      const key = detection.trackId * 1_000_000 + segment
      const observations = tracks.get(key) ?? []
      observations.push({
        time: entry.time,
        detection: { ...detection, bbox: [...detection.bbox] },
        vector: boxVector(detection.bbox),
      })
      tracks.set(key, observations)
    }
  }

  return {
    maximumGap,
    visibilityWindow,
    tracks: [...tracks.values()].map((observations) => {
      observations.sort((left, right) => left.time - right.time)
      const smoothed = smoothVectors(observations, smoothingTime)
      return {
        trackId: observations[0].detection.trackId!,
        observations: observations.map((observation, index) => ({
          ...observation,
          vector: smoothed[index],
        })),
      }
    }),
  }
}

function observationIndexAtOrBefore(
  observations: readonly PlaybackObservation[],
  time: number,
): number {
  let low = 0
  let high = observations.length - 1
  let result = -1
  while (low <= high) {
    const middle = Math.floor((low + high) / 2)
    if (observations[middle].time <= time) {
      result = middle
      low = middle + 1
    } else {
      high = middle - 1
    }
  }
  return result
}

function propagateObservation(
  observation: PlaybackObservation,
  time: number,
): TrackedDetection {
  const vector: BoxVector = [...observation.vector]
  const deltaTime = time - observation.time
  const flow =
    deltaTime >= 0
      ? observation.detection.flowToNext
      : observation.detection.flowFromPrevious
  if (
    flow &&
    flow.dt > 0 &&
    flow.reliability >= 0.15 &&
    Math.abs(deltaTime) <= flow.dt
  ) {
    vector[0] += (flow.dx / flow.dt) * deltaTime
    vector[1] += (flow.dy / flow.dt) * deltaTime
  }
  return { ...observation.detection, bbox: vectorBox(vector) }
}

function sampleTrack(
  track: PlaybackTrack,
  time: number,
  maximumGap: number,
  visibilityWindow: number,
): TrackedDetection | null {
  const { observations } = track
  if (observations.length === 0) return null
  const leftIndex = observationIndexAtOrBefore(observations, time)
  const left = leftIndex >= 0 ? observations[leftIndex] : undefined
  const right = observations[leftIndex + 1]

  if (left && right) {
    const gap = right.time - left.time
    if (gap <= maximumGap && gap > 0) {
      const amount = Math.max(0, Math.min(1, (time - left.time) / gap))
      const vector = interpolateVector(left.vector, right.vector, amount)
      const leftFlow = left.detection.flowToNext
      const rightFlow = right.detection.flowFromPrevious
      if (
        leftFlow &&
        rightFlow &&
        leftFlow.dt > 0 &&
        rightFlow.dt > 0 &&
        leftFlow.reliability >= 0.15 &&
        rightFlow.reliability >= 0.15
      ) {
        const t2 = amount * amount
        const t3 = t2 * amount
        const leftWeight = 2 * t3 - 3 * t2 + 1
        const leftTangentWeight = t3 - 2 * t2 + amount
        const rightWeight = -2 * t3 + 3 * t2
        const rightTangentWeight = t3 - t2
        for (let coordinate = 0; coordinate < 2; coordinate += 1) {
          const leftVelocity =
            (coordinate === 0 ? leftFlow.dx : leftFlow.dy) / leftFlow.dt
          const rightVelocity =
            (coordinate === 0 ? rightFlow.dx : rightFlow.dy) / rightFlow.dt
          vector[coordinate] =
            leftWeight * left.vector[coordinate] +
            leftTangentWeight * leftVelocity * gap +
            rightWeight * right.vector[coordinate] +
            rightTangentWeight * rightVelocity * gap
        }
      }
      return {
        ...left.detection,
        confidence:
          left.detection.confidence +
          (right.detection.confidence - left.detection.confidence) * amount,
        bbox: vectorBox(vector),
      }
    }
    const nearest =
      time - left.time <= right.time - time ? left : right
    return Math.abs(nearest.time - time) <= visibilityWindow
      ? propagateObservation(nearest, time)
      : null
  }

  const nearest = left ?? right
  return nearest && Math.abs(nearest.time - time) <= visibilityWindow
    ? propagateObservation(nearest, time)
    : null
}

export function samplePlayback(
  playback: VideoPlayback | null,
  time: number,
): TrackedDetection[] {
  if (!playback || !Number.isFinite(time)) return []
  return playback.tracks
    .map((track) =>
      sampleTrack(
        track,
        time,
        playback.maximumGap,
        playback.visibilityWindow,
      ),
    )
    .filter((detection): detection is TrackedDetection => detection !== null)
}

export function updateTracks(
  tracks: VideoTrack[],
  detections: TrackedDetection[],
  time: number,
  frameIndex: number,
  maximumFrameGap: number,
  matchIou: number,
  options: TrackingOptions = {},
): void {
  const enterConfidence = Math.max(0, options.enterConfidence ?? 0)
  const exitConfidence = Math.max(
    0,
    options.exitConfidence ?? enterConfidence,
  )
  const exitPatience = Math.max(0, Math.floor(options.exitPatience ?? 0))
  const candidates: {
    trackIndex: number
    detectionIndex: number
    overlap: number
  }[] = []

  tracks.forEach((track, trackIndex) => {
    if (frameIndex - track.lastFrame > maximumFrameGap) return
    detections.forEach((detection, detectionIndex) => {
      if (track.className !== detection.class) return
      const previousBox: BoundingBoxTuple = [...track.lastDetection.bbox]
      const motion = track.lastDetection.flowToNext
      if (motion && motion.reliability >= 0.15) {
        previousBox[0] += motion.dx
        previousBox[1] += motion.dy
        previousBox[2] += motion.dx
        previousBox[3] += motion.dy
      }
      const overlap = BoundingBox.from(previousBox).iou(detection.bbox)
      if (overlap >= matchIou) {
        candidates.push({ trackIndex, detectionIndex, overlap })
      }
    })
  })
  candidates.sort((left, right) => right.overlap - left.overlap)

  const matchedTracks = new Set<number>()
  const matchedDetections = new Set<number>()
  for (const candidate of candidates) {
    if (
      matchedTracks.has(candidate.trackIndex) ||
      matchedDetections.has(candidate.detectionIndex)
    ) {
      continue
    }
    const track = tracks[candidate.trackIndex]
    const detection = detections[candidate.detectionIndex]
    detection.trackId = track.id
    matchedTracks.add(candidate.trackIndex)
    matchedDetections.add(candidate.detectionIndex)
    track.endTime = time
    track.lastFrame = frameIndex
    track.lastDetection = detection
    track.observations += 1
    track.lowConfidenceFrames =
      detection.confidence < exitConfidence
        ? track.lowConfidenceFrames + 1
        : 0
    if (!track.temporallyVisible && detection.confidence >= enterConfidence) {
      track.temporallyVisible = true
      track.visibilitySegment += 1
      track.lowConfidenceFrames = 0
    } else if (
      track.temporallyVisible &&
      track.lowConfidenceFrames > exitPatience
    ) {
      track.temporallyVisible = false
    }
    detection.temporallyVisible = track.temporallyVisible
    detection.visibilitySegment = track.visibilitySegment
    if (track.temporallyVisible) {
      track.visibleObservations += 1
      track.everVisible = true
      track.visibleEndTime = time
    }
    if (detection.confidence > track.maxConfidence) {
      track.maxConfidence = detection.confidence
      track.representativeTime = time
      track.representativeDetection = detection
    }
  }

  detections.forEach((detection, index) => {
    if (
      matchedDetections.has(index) ||
      detection.confidence < enterConfidence
    ) {
      return
    }
    const id = tracks.length + 1
    const track: VideoTrack = {
      id,
      className: detection.class,
      startTime: time,
      endTime: time,
      visibleEndTime: time,
      lastFrame: frameIndex,
      observations: 1,
      visibleObservations: 1,
      temporallyVisible: true,
      everVisible: true,
      lowConfidenceFrames: 0,
      visibilitySegment: 0,
      maxConfidence: detection.confidence,
      lastDetection: detection,
      representativeTime: time,
      representativeDetection: detection,
    }
    detection.trackId = id
    detection.temporallyVisible = true
    detection.visibilitySegment = 0
    tracks.push(track)
  })
}

export function filterVideoEntries(
  entries: readonly VideoEntry[],
  tracks: readonly VideoTrack[],
): VideoEntry[] {
  const survivingTrackIds = new Set(tracks.map((track) => track.id))
  return entries
    .map((entry) => ({
      ...entry,
      detections: entry.detections.filter(
        (detection) =>
          detection.trackId !== undefined &&
          survivingTrackIds.has(detection.trackId) &&
          detection.temporallyVisible !== false,
      ),
    }))
    .filter((entry) => entry.detections.length > 0)
}

