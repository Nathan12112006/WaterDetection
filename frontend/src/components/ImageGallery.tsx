import { useState } from 'react'
import type { ImageEntry } from '../types'
import { downloadAnnotatedImage } from '../lib/downloads'
import { errorText } from '../lib/media'
import { DetectionCanvas } from './DetectionCanvas'
import { ActionButton } from './ui/ActionButton'
import { EditedBadge, FileName } from './ui/MediaMetadata'

interface ImageGalleryProps {
  entries: readonly ImageEntry[]
  canExportDataset: boolean
  exporting: boolean
  onExportDataset: () => void
  onStatus: (message: string, error?: boolean) => void
}

function ImageCard({
  entry,
  onStatus,
}: {
  entry: ImageEntry
  onStatus: ImageGalleryProps['onStatus']
}) {
  const [downloading, setDownloading] = useState(false)
  const detections = entry.exportDetections ?? []

  const download = async () => {
    if (entry.exportDetections === null) return
    setDownloading(true)
    try {
      await downloadAnnotatedImage(entry, entry.exportDetections)
      onStatus(`${entry.file.name} downloaded.`)
    } catch (error) {
      onStatus(
        errorText(error, 'The annotated image could not be saved.'),
        true,
      )
    } finally {
      setDownloading(false)
    }
  }

  const count = entry.error
    ? 'Failed'
    : entry.exportDetections === null
      ? 'Not analyzed'
      : `${detections.length} detection${detections.length === 1 ? '' : 's'}`

  return (
    <article className={`image-card${entry.error ? ' error' : ''}`}>
      <DetectionCanvas
        imageUrl={entry.url}
        sourceWidth={entry.width}
        sourceHeight={entry.height}
        detections={detections}
      />
      <footer>
        <div className="image-card-meta">
          <div>
            <FileName name={entry.file.name} />
            <EditedBadge edited={entry.reviewEdited} />
          </div>
          <span>{count}</span>
        </div>
        <ActionButton
          className="download-annotated"
          hidden={entry.exportDetections === null}
          busy={downloading}
          busyLabel="Saving…"
          onClick={() => void download()}
        >
          Download
        </ActionButton>
      </footer>
    </article>
  )
}

export function ImageGallery({
  entries,
  canExportDataset,
  exporting,
  onExportDataset,
  onStatus,
}: ImageGalleryProps) {
  const sorted = [...entries].sort(
    (left, right) =>
      Number(left.reviewEdited) - Number(right.reviewEdited) ||
      left.originalIndex - right.originalIndex,
  )
  const completedCount = entries.filter(
    (entry) => entry.exportDetections !== null,
  ).length

  return (
    <>
      <div className="preview-heading">
        <div>
          <p className="section-kicker">Detection preview</p>
          <h2>Your images</h2>
        </div>
        <div className="preview-heading-actions">
          <span>
            {completedCount} of {entries.length} analyzed
          </span>
          {canExportDataset && (
            <ActionButton
              id="download-dataset"
              className="dataset-export"
              busy={exporting}
              busyLabel="Building dataset ZIP…"
              onClick={onExportDataset}
            >
              Download YOLO dataset ZIP
            </ActionButton>
          )}
        </div>
      </div>
      <div
        id="image-grid"
        className={`media-grid${entries.length === 1 ? ' single-image-mode' : ''}`}
      >
        {sorted.map((entry) => (
          <ImageCard
            key={entry.id}
            entry={entry}
            onStatus={onStatus}
          />
        ))}
      </div>
    </>
  )
}
