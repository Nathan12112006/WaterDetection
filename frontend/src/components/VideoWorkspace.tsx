import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import {
  canvasBlob,
  canvasDimensions,
  drawDetections,
} from '../lib/canvas'
import { requestDetections } from '../lib/api'
import { displayDetectionClass } from '../lib/detections'
import { formatVideoTime, videoSampleRates } from '../lib/media'
import {
  createPlayback,
  estimateFlow,
  filterVideoEntries,
  framePercentageCount,
  grayscale,
  samplePlayback,
  updateTracks,
} from '../lib/videoTracking'
import type {
  GrayFrame,
  TrackedDetection,
  VideoEntry,
  VideoPlayback,
  VideoTrack,
} from '../lib/videoTracking'
import type { ClassConfidences, ModelSelection } from '../types'
import {
  VideoTimeline,
  type VideoTimelineItem,
} from './VideoTimeline'

const MAX_VIDEO_SAMPLES = 2_000
const MAX_ANALYSIS_DIMENSION = 1_280
const TRACK_IOU_THRESHOLD = 0.3
const BOX_SMOOTHING_SECONDS = 0.12
const CONFIDENCE_EXIT_FRAME_PERCENTAGE = 0.01
const MAX_REPRESENTATIVE_TRACKS = 12

export interface VideoAnalysisRequest {
  model: ModelSelection
  confidence: number
  classConfidences: ClassConfidences
  sampleRate: number
}

export interface VideoAnalysisResult {
  summary: string[]
  persistentTracks: number
  analyzedFrames: number
}

export interface VideoWorkspaceHandle {
  analyze: (request: VideoAnalysisRequest) => Promise<VideoAnalysisResult>
}

interface VideoWorkspaceProps {
  file: File
  url: string
  onRatesChange: (rates: number[]) => void
  onStatus: (message: string, error?: boolean) => void
}

function waitForEvent(
  element: HTMLMediaElement,
  eventName: 'seeked',
): Promise<void> {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      element.removeEventListener(eventName, success)
      element.removeEventListener('error', failure)
    }
    const success = () => {
      cleanup()
      resolve()
    }
    const failure = () => {
      cleanup()
      reject(new Error('The selected media could not be decoded.'))
    }
    element.addEventListener(eventName, success, { once: true })
    element.addEventListener('error', failure, { once: true })
  })
}

async function seekVideo(
  video: HTMLVideoElement,
  time: number,
): Promise<void> {
  if (Math.abs(video.currentTime - time) < 0.001) return
  const seeked = waitForEvent(video, 'seeked')
  video.currentTime = time
  await seeked
}

function visibleObservationCount(track: VideoTrack): number {
  return track.visibleObservations
}

export const VideoWorkspace = forwardRef<
  VideoWorkspaceHandle,
  VideoWorkspaceProps
>(function VideoWorkspace(
  { file, url, onRatesChange, onStatus },
  forwardedRef,
) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const analysisRef = useRef<HTMLCanvasElement>(null)
  const playbackRef = useRef<VideoPlayback | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const [duration, setDuration] = useState(0)
  const [note, setNote] = useState(`${file.name} · loading metadata…`)
  const [timeline, setTimeline] = useState<VideoTimelineItem[]>([])

  const renderOverlay = () => {
    const video = videoRef.current
    const overlay = overlayRef.current
    if (!video || !overlay) return
    const context = overlay.getContext('2d')
    if (!context) return
    context.clearRect(0, 0, overlay.width, overlay.height)
    const detections = samplePlayback(playbackRef.current, video.currentTime)
    if (detections.length > 0) {
      drawDetections(
        context,
        overlay,
        video.videoWidth,
        video.videoHeight,
        detections,
      )
    }
  }

  const stopAnimation = () => {
    if (animationFrameRef.current === null) return
    cancelAnimationFrame(animationFrameRef.current)
    animationFrameRef.current = null
  }

  const startAnimation = () => {
    stopAnimation()
    const renderFrame = () => {
      const video = videoRef.current
      renderOverlay()
      if (video && !video.paused && !video.ended) {
        animationFrameRef.current = requestAnimationFrame(renderFrame)
      } else {
        animationFrameRef.current = null
      }
    }
    animationFrameRef.current = requestAnimationFrame(renderFrame)
  }

  useEffect(() => {
    playbackRef.current = null
    setTimeline([])
    setDuration(0)
    setNote(`${file.name} · loading metadata…`)
    return stopAnimation
  }, [file.name, url])

  const captureTrackThumbnail = async (
    track: VideoTrack,
  ): Promise<string> => {
    const video = videoRef.current
    if (!video) throw new Error('Video preview is unavailable.')
    await seekVideo(video, track.representativeTime)
    const dimensions = canvasDimensions(
      video.videoWidth,
      video.videoHeight,
      320,
    )
    const canvas = document.createElement('canvas')
    canvas.width = dimensions.width
    canvas.height = dimensions.height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas rendering is unavailable.')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    drawDetections(
      context,
      canvas,
      video.videoWidth,
      video.videoHeight,
      [track.representativeDetection],
    )
    return canvas.toDataURL('image/jpeg', 0.78)
  }

  useImperativeHandle(
    forwardedRef,
    () => ({
      analyze: async (
        request: VideoAnalysisRequest,
      ): Promise<VideoAnalysisResult> => {
        const video = videoRef.current
        const analysisCanvas = analysisRef.current
        if (
          !video ||
          !analysisCanvas ||
          !Number.isFinite(video.duration) ||
          video.duration <= 0 ||
          video.videoWidth <= 0 ||
          video.videoHeight <= 0
        ) {
          throw new Error('Wait for the video metadata before detecting.')
        }

        video.pause()
        stopAnimation()
        playbackRef.current = null
        setTimeline([])
        const tracks: VideoTrack[] = []
        let entries: VideoEntry[] = []
        const sampleInterval = 1 / request.sampleRate
        const sampleCount = Math.max(
          1,
          Math.ceil(video.duration / sampleInterval),
        )
        if (sampleCount > MAX_VIDEO_SAMPLES) {
          throw new Error('Video is too long.')
        }
        const detectionWindow = Math.max(0.35, sampleInterval * 0.75)
        const maximumTrackGap = Math.max(
          1,
          Math.ceil(request.sampleRate * 0.75),
        )
        const enterConfidence = Math.max(
          0.01,
          Math.min(1, request.confidence),
        )
        const exitConfidence = Math.max(0.01, enterConfidence * 0.65)
        const trackingOptions = {
          enterConfidence,
          exitConfidence,
          exitPatience: framePercentageCount(
            sampleCount,
            CONFIDENCE_EXIT_FRAME_PERCENTAGE,
          ),
        }

        const analysisSize = canvasDimensions(
          video.videoWidth,
          video.videoHeight,
          MAX_ANALYSIS_DIMENSION,
        )
        analysisCanvas.width = analysisSize.width
        analysisCanvas.height = analysisSize.height
        const analysisContext = analysisCanvas.getContext('2d')
        if (!analysisContext) {
          throw new Error('Canvas rendering is unavailable.')
        }

        let previousGrayFrame: GrayFrame | null = null
        let previousEntry: VideoEntry | null = null
        let previousFrameTime: number | null = null
        for (let index = 0; index < sampleCount; index += 1) {
          const time = Math.min(
            Math.max(0, video.duration - 0.001),
            index * sampleInterval,
          )
          onStatus(
            `Analyzing video frame ${index + 1} of ${sampleCount} at ${time.toFixed(1)}s…`,
          )
          await seekVideo(video, time)
          analysisContext.drawImage(
            video,
            0,
            0,
            analysisCanvas.width,
            analysisCanvas.height,
          )
          const currentGrayFrame = grayscale(
            analysisContext.getImageData(
              0,
              0,
              analysisCanvas.width,
              analysisCanvas.height,
            ),
          )
          const blob = await canvasBlob(analysisCanvas)
          const detections = await requestDetections({
            media: blob,
            filename: `frame-${String(index + 1).padStart(4, '0')}.jpg`,
            model: request.model,
            confidence: exitConfidence,
            classConfidences: request.classConfidences,
          })
          const scaleX = video.videoWidth / analysisCanvas.width
          const scaleY = video.videoHeight / analysisCanvas.height
          const videoCoordinates: TrackedDetection[] = detections.map(
            (detection) => ({
              ...detection,
              bbox: [
                detection.bbox[0] * scaleX,
                detection.bbox[1] * scaleY,
                detection.bbox[2] * scaleX,
                detection.bbox[3] * scaleY,
              ],
            }),
          )

          const flowByTrack = new Map<number, {
            dx: number
            dy: number
            dt: number
            reliability: number
          }>()
          if (
            previousGrayFrame &&
            previousEntry &&
            previousFrameTime !== null
          ) {
            const flowDeltaTime = time - previousFrameTime
            const searchRadius =
              request.sampleRate >= 30
                ? 6
                : request.sampleRate >= 8
                  ? 8
                  : 12
            for (const previousDetection of previousEntry.detections) {
              if (
                previousDetection.trackId === undefined ||
                previousDetection.temporallyVisible === false
              ) {
                continue
              }
              const flow = estimateFlow(
                previousGrayFrame,
                currentGrayFrame,
                [
                  previousDetection.bbox[0] / scaleX,
                  previousDetection.bbox[1] / scaleY,
                  previousDetection.bbox[2] / scaleX,
                  previousDetection.bbox[3] / scaleY,
                ],
                { searchRadius },
              )
              if (!flow) continue
              const videoFlow = {
                dx: flow.dx * scaleX,
                dy: flow.dy * scaleY,
                dt: flowDeltaTime,
                reliability: flow.reliability,
              }
              previousDetection.flowToNext = videoFlow
              flowByTrack.set(previousDetection.trackId, videoFlow)
            }
          }

          updateTracks(
            tracks,
            videoCoordinates,
            time,
            index,
            maximumTrackGap,
            TRACK_IOU_THRESHOLD,
            trackingOptions,
          )
          for (const detection of videoCoordinates) {
            if (detection.trackId === undefined) continue
            const flow = flowByTrack.get(detection.trackId)
            if (flow) detection.flowFromPrevious = flow
          }
          const videoEntry = { time, detections: videoCoordinates }
          entries.push(videoEntry)
          previousGrayFrame = currentGrayFrame
          previousEntry = videoEntry
          previousFrameTime = time
        }

        const persistenceThreshold =
          sampleCount === 1
            ? 1
            : Math.max(2, Math.ceil(request.sampleRate * 0.5))
        const persistentTracks = tracks.filter(
          (track) =>
            track.everVisible &&
            track.visibleObservations >= persistenceThreshold,
        )
        entries = filterVideoEntries(entries, persistentTracks)
        playbackRef.current = createPlayback(entries, {
          smoothingTime: BOX_SMOOTHING_SECONDS,
          maximumGap: Math.max(
            0.2,
            maximumTrackGap * sampleInterval + 0.001,
          ),
          visibilityWindow: detectionWindow,
        })

        const displayedTracks = [...persistentTracks]
          .sort(
            (left, right) =>
              visibleObservationCount(right) -
                visibleObservationCount(left) ||
              right.maxConfidence - left.maxConfidence,
          )
          .slice(0, MAX_REPRESENTATIVE_TRACKS)
        const timelineItems: VideoTimelineItem[] = []
        for (const track of displayedTracks) {
          timelineItems.push({
            track,
            thumbnail: await captureTrackThumbnail(track),
          })
        }
        setTimeline(timelineItems)
        await seekVideo(video, 0)
        renderOverlay()
        setNote(
          `${sampleCount} frames analyzed; ${persistentTracks.length} regions survived final filtering. Play the video or select a timeline marker.`,
        )

        const summary =
          persistentTracks.length === 0
            ? ['No detections survived the final video filtering.']
            : [
                `${persistentTracks.length} persistent region${persistentTracks.length === 1 ? '' : 's'} survived the final video filtering.`,
                ...persistentTracks.map(
                  (track) =>
                    `${displayDetectionClass(track.className)}: ${formatVideoTime(track.startTime)}–${formatVideoTime(track.visibleEndTime)}, ${track.visibleObservations} samples, peak ${(track.maxConfidence * 100).toFixed(1)}%.`,
                ),
              ]
        return {
          summary,
          persistentTracks: persistentTracks.length,
          analyzedFrames: sampleCount,
        }
      },
    }),
  )

  const handleMetadata = () => {
    const video = videoRef.current
    const overlay = overlayRef.current
    if (!video || !overlay) return
    if (
      !Number.isFinite(video.duration) ||
      video.duration <= 0 ||
      video.videoWidth <= 0 ||
      video.videoHeight <= 0
    ) {
      onStatus('The selected video does not have valid metadata.', true)
      return
    }
    overlay.width = video.videoWidth
    overlay.height = video.videoHeight
    setDuration(video.duration)
    setNote(`${file.name} · ${video.duration.toFixed(1)} seconds`)
    const rates = videoSampleRates(video.duration)
    if (rates.length === 0) {
      onRatesChange([])
      onStatus('Video is too long to analyze at 1 FPS.', true)
      return
    }
    onRatesChange(rates)
    onStatus('Video ready to analyze.')
  }

  return (
    <div id="video-preview" className="video-preview">
      <div className="video-shell">
        <video
          id="video-player"
          ref={videoRef}
          src={url}
          controls
          playsInline
          onLoadedMetadata={handleMetadata}
          onPlay={startAnimation}
          onPause={() => {
            stopAnimation()
            renderOverlay()
          }}
          onEnded={stopAnimation}
          onTimeUpdate={() => {
            if (videoRef.current?.paused) renderOverlay()
          }}
          onSeeked={renderOverlay}
        />
        <canvas id="video-overlay" ref={overlayRef} />
      </div>
      <p id="video-note" className="video-note">
        {note}
      </p>
      <canvas id="analysis-canvas" ref={analysisRef} hidden />
      <VideoTimeline
        items={timeline}
        duration={duration}
        onSeek={(time) => {
          const video = videoRef.current
          if (!video) return
          video.currentTime = time
          video.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          })
        }}
      />
    </div>
  )
})
