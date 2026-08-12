import type { ImageEntry } from '../types'
import {
  compareImageFilenames,
  rankReviewEntries,
} from '../lib/review'
import { ReviewOverviewCard } from './ReviewOverviewCard'
import { ActionButton } from './ui/ActionButton'
import { EmptyState } from './ui/EmptyState'

interface ReviewOverviewProps {
  entries: readonly ImageEntry[]
  onEntriesChange: (entries: ImageEntry[]) => void
  onOpen: (entryId: string) => void
  onStatus: (message: string) => void
}

export function ReviewOverview({
  entries,
  onEntriesChange,
  onOpen,
  onStatus,
}: ReviewOverviewProps) {
  const ranked = rankReviewEntries(entries).sort(
    (left, right) =>
      compareImageFilenames(left.entry, right.entry),
  )
  const selected = ranked.filter(({ entry }) => entry.reviewSelected)
  const reviewedCount = entries.filter((entry) => entry.reviewEdited).length
  const detectionCount = entries.reduce(
    (total, entry) => total + (entry.exportDetections?.length ?? 0),
    0,
  )

  const updateEntry = (
    id: string,
    update: (entry: ImageEntry) => ImageEntry,
  ) => {
    onEntriesChange(
      entries.map((entry) => (entry.id === id ? update(entry) : entry)),
    )
  }

  const approve = (id: string) => {
    const target = entries.find((entry) => entry.id === id)
    updateEntry(id, (entry) => ({
      ...entry,
      imageApproved: true,
      reviewEdited: true,
      reviewSelected: false,
    }))
    if (target) onStatus(`${target.file.name} approved.`)
  }

  const setAllSelected = (reviewSelected: boolean) => {
    const reviewableIds = new Set(ranked.map(({ entry }) => entry.id))
    onEntriesChange(
      entries.map((entry) =>
        reviewableIds.has(entry.id)
          ? { ...entry, reviewSelected }
          : reviewSelected
            ? entry
            : { ...entry, reviewSelected: false },
      ),
    )
  }

  const approveSelected = () => {
    const selectedIds = new Set(selected.map(({ entry }) => entry.id))
    if (selectedIds.size === 0) return
    onEntriesChange(
      entries.map((entry) =>
        selectedIds.has(entry.id)
          ? {
              ...entry,
              imageApproved: true,
              reviewEdited: true,
              reviewSelected: false,
            }
          : entry,
      ),
    )
    onStatus(
      `${selectedIds.size} image${selectedIds.size === 1 ? '' : 's'} approved.`,
    )
  }

  return (
    <div id="review-overview">
      <div className="review-overview-heading">
        <div>
          <p className="section-kicker">Review queue</p>
          <h2>Refine your detections</h2>
          <p>
            Images are ordered naturally by filename, with numbers first.
            Approve clean results or open an image for precise box editing.
          </p>
        </div>
        <div className="review-stats" aria-label="Review statistics">
          <span>
            <strong>{ranked.length}</strong>
            pending
          </span>
          <span>
            <strong>{reviewedCount}</strong>
            edited
          </span>
          <span>
            <strong>{detectionCount}</strong>
            boxes
          </span>
        </div>
      </div>
      <div className="bulk-review" aria-label="Bulk review actions">
        <div>
          <span className="bulk-label">Bulk actions</span>
          <span id="selected-image-count" className="bulk-image-selection">
            {selected.length} image{selected.length === 1 ? '' : 's'} selected
          </span>
        </div>
        <ActionButton
          id="select-all-review-images"
          onClick={() => setAllSelected(true)}
        >
          Select all
        </ActionButton>
        <ActionButton
          id="clear-review-selection"
          disabled={selected.length === 0}
          disabledReason="No overview images are selected."
          onClick={() => setAllSelected(false)}
        >
          Clear selection
        </ActionButton>
        <ActionButton
          id="bulk-approve"
          disabled={selected.length === 0}
          disabledReason="Select at least one image in the overview."
          onClick={approveSelected}
        >
          Approve
        </ActionButton>
      </div>
      <div id="review-overview-grid" className="review-overview-grid">
        {ranked.length === 0 ? (
          <EmptyState
            className="review-overview-empty"
            title="Review complete"
          >
            All detected images have been approved.
          </EmptyState>
        ) : (
          ranked.map(({ entry, signals }) => {
            return (
              <ReviewOverviewCard
                key={entry.id}
                entry={entry}
                signals={signals}
                onSelectionChange={(reviewSelected) =>
                  updateEntry(entry.id, (current) => ({
                    ...current,
                    reviewSelected,
                  }))
                }
                onApprove={() => approve(entry.id)}
                onOpen={() => onOpen(entry.id)}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
