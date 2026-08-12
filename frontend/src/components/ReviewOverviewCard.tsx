import type { MouseEvent } from 'react'
import type { ImageEntry, ReviewSignals } from '../types'
import {
  reviewReasons,
  reviewStatus,
  statusLabel,
} from '../lib/review'
import { DetectionCanvas } from './DetectionCanvas'
import { ActionButton } from './ui/ActionButton'
import { EditedBadge, FileName } from './ui/MediaMetadata'

interface ReviewOverviewCardProps {
  entry: ImageEntry
  signals: ReviewSignals
  onSelectionChange: (selected: boolean) => void
  onApprove: () => void
  onOpen: () => void
}

export function ReviewOverviewCard({
  entry,
  signals,
  onSelectionChange,
  onApprove,
  onOpen,
}: ReviewOverviewCardProps) {
  const detections = entry.reviewDetections ?? []
  const status = reviewStatus(detections, entry.imageApproved)
  const statusTone = status.imageApproved
    ? 'approved'
    : status.allBoxesConfirmed
      ? 'confirmed'
      : 'pending'
  const stopCardClick = (event: MouseEvent) => event.stopPropagation()

  return (
    <article
      className={`review-overview-card${entry.reviewSelected ? ' selected' : ''}`}
      onClick={onOpen}
    >
      <label
        className="review-card-selection"
        title={`Select ${entry.file.name} for bulk actions`}
        onClick={stopCardClick}
      >
        <input
          type="checkbox"
          checked={entry.reviewSelected}
          aria-label={`Select ${entry.file.name} for bulk actions`}
          onChange={(event) =>
            onSelectionChange(event.currentTarget.checked)
          }
        />
      </label>
      <DetectionCanvas
        imageUrl={entry.url}
        sourceWidth={entry.width}
        sourceHeight={entry.height}
        detections={entry.exportDetections ?? []}
        maximumDimension={420}
      />
      <footer>
        <div className="review-card-title">
          <FileName name={entry.file.name} />
          <EditedBadge edited={entry.reviewEdited} />
        </div>
        <span className={`review-card-status ${statusTone}`}>
          <span className="status-dot" aria-hidden="true" />
          {statusLabel(status)}
        </span>
        <span className="review-card-priority">
          {reviewReasons(signals).join(', ')}
        </span>
        <div className="review-card-actions">
          <ActionButton
            className="review-card-approve"
            onClick={(event) => {
              stopCardClick(event)
              onApprove()
            }}
          >
            Approve
          </ActionButton>
          <ActionButton
            className="review-card-open"
            onClick={(event) => {
              stopCardClick(event)
              onOpen()
            }}
          >
            Edit boxes
          </ActionButton>
        </div>
      </footer>
    </article>
  )
}
