import type { VideoTrack } from '../lib/videoTracking'
import { displayDetectionClass } from '../lib/detections'
import { formatVideoTime } from '../lib/media'
import { ActionButton } from './ui/ActionButton'

export interface VideoTimelineItem {
  track: VideoTrack
  thumbnail: string
}

interface VideoTimelineProps {
  items: readonly VideoTimelineItem[]
  duration: number
  onSeek: (time: number) => void
}

function TimelineTrack({
  item: { track, thumbnail },
  duration,
  onSeek,
}: {
  item: VideoTimelineItem
  duration: number
  onSeek: (time: number) => void
}) {
  const startPercentage = (track.startTime / duration) * 100
  const widthPercentage = Math.max(
    0.8,
    ((track.visibleEndTime - track.startTime) / duration) * 100,
  )
  const className = displayDetectionClass(track.className)

  return (
    <article className="timeline-track">
      <img
        src={thumbnail}
        alt={`${className} near ${formatVideoTime(track.representativeTime)}`}
      />
      <div>
        <strong>
          {className} · {track.visibleObservations} samples
        </strong>
        <small>
          {formatVideoTime(track.startTime)}–
          {formatVideoTime(track.endTime)} · peak{' '}
          {(track.maxConfidence * 100).toFixed(1)}%
        </small>
        <div className="timeline-rail">
          <ActionButton
            className="timeline-range"
            title="Jump to representative detection"
            aria-label={`Jump to ${className} at ${formatVideoTime(track.representativeTime)}`}
            style={{
              left: `${startPercentage}%`,
              width: `${widthPercentage}%`,
            }}
            onClick={() => onSeek(track.representativeTime)}
          />
        </div>
      </div>
    </article>
  )
}

export function VideoTimeline({
  items,
  duration,
  onSeek,
}: VideoTimelineProps) {
  if (items.length === 0 || duration <= 0) return null

  return (
    <div id="video-timeline" className="video-timeline">
      {items.map((item) => (
        <TimelineTrack
          key={item.track.id}
          item={item}
          duration={duration}
          onSeek={onSeek}
        />
      ))}
    </div>
  )
}
