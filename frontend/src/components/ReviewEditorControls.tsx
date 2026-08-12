import type { ReviewDetection } from '../types'
import { displayDetectionClass } from '../lib/detections'
import { MODEL_CLASSES, type ModelClass } from '../modelClasses'
import { ActionButton } from './ui/ActionButton'
import { FormField } from './ui/FormField'

export type ReviewToolbarAction =
  | 'undo'
  | 'redo'
  | 'zoom-out'
  | 'zoom-reset'
  | 'zoom-in'
  | 'toggle-drawing'
  | 'confirm'
  | 'remove'
  | 'restore'
  | 'toggle-approval'

interface ReviewPagerProps {
  currentIndex: number
  total: number
  label: string
  onPrevious: () => void
  onNext: () => void
}

export function ReviewPager({
  currentIndex,
  total,
  label,
  onPrevious,
  onNext,
}: ReviewPagerProps) {
  if (total <= 1) return null

  return (
    <nav
      id="image-pager"
      className="image-pager"
      aria-label="Ranked review queue"
    >
      <ActionButton
        id="previous-image"
        disabled={currentIndex <= 0}
        disabledReason="This is the first image."
        onClick={onPrevious}
      >
        Previous
      </ActionButton>
      <span
        id="image-page-status"
        className="image-page-status"
        title={label}
      >
        {label}
      </span>
      <ActionButton
        id="next-image"
        disabled={currentIndex < 0 || currentIndex >= total - 1}
        disabledReason="This is the last image."
        onClick={onNext}
      >
        Next
      </ActionButton>
    </nav>
  )
}

interface ReviewToolbarProps {
  canUndo: boolean
  canRedo: boolean
  zoom: number
  drawing: boolean
  selected: ReviewDetection | null
  imageApproved: boolean
  onAction: (action: ReviewToolbarAction) => void
}

export function ReviewToolbar({
  canUndo,
  canRedo,
  zoom,
  drawing,
  selected,
  imageApproved,
  onAction,
}: ReviewToolbarProps) {
  const confirmReason = !selected
    ? 'Select a box before confirming it.'
    : selected.removed
      ? 'Restore this box before confirming it.'
      : selected.confirmed
        ? 'This box is already confirmed.'
        : undefined
  const removeReason = !selected
    ? 'Select a box before removing it.'
    : 'This box has already been removed.'
  const restoreReason = !selected
    ? 'Select a removed box before restoring it.'
    : 'This box has not been removed.'

  return (
    <div className="review-toolbar">
      <div className="tool-group">
        <span className="toolbar-label">History</span>
        <div className="viewport-actions">
          <ActionButton
            id="undo-review"
            title="Undo (Ctrl+Z)"
            disabled={!canUndo}
            disabledReason="There are no annotation changes to undo."
            onClick={() => onAction('undo')}
          >
            ↶ <span>Undo</span>
          </ActionButton>
          <ActionButton
            id="redo-review"
            title="Redo (Ctrl+Y)"
            disabled={!canRedo}
            disabledReason="There are no annotation changes to redo."
            onClick={() => onAction('redo')}
          >
            ↷ <span>Redo</span>
          </ActionButton>
        </div>
      </div>
      <div className="tool-group">
        <span className="toolbar-label">View</span>
        <div className="viewport-actions zoom-actions">
          <ActionButton
            id="zoom-out-review"
            aria-label="Zoom out"
            onClick={() => onAction('zoom-out')}
          >
            −
          </ActionButton>
          <ActionButton
            id="reset-zoom-review"
            aria-label="Reset zoom"
            onClick={() => onAction('zoom-reset')}
          >
            {Math.round(zoom * 100)}%
          </ActionButton>
          <ActionButton
            id="zoom-in-review"
            aria-label="Zoom in"
            onClick={() => onAction('zoom-in')}
          >
            +
          </ActionButton>
        </div>
      </div>
      <div className="tool-group annotation-tool-group">
        <span className="toolbar-label">Annotation</span>
        <div className="review-actions">
          <ActionButton
            id="draw-annotation"
            className={drawing ? 'active-tool' : undefined}
            aria-pressed={drawing}
            onClick={() => onAction('toggle-drawing')}
          >
            {drawing ? '× Cancel drawing' : '+ Add box'}
          </ActionButton>
          <ActionButton
            id="confirm-annotation"
            className={selected?.confirmed ? 'confirmed' : undefined}
            disabled={!selected || selected.removed || selected.confirmed}
            disabledReason={confirmReason}
            onClick={() => onAction('confirm')}
          >
            {selected?.confirmed ? '✓ Confirmed' : '✓ Confirm'}
          </ActionButton>
          <ActionButton
            id="remove-annotation"
            className="danger"
            disabled={!selected || selected.removed}
            disabledReason={removeReason}
            onClick={() => onAction('remove')}
          >
            Remove
          </ActionButton>
          <ActionButton
            id="restore-annotation"
            disabled={!selected?.removed}
            disabledReason={restoreReason}
            onClick={() => onAction('restore')}
          >
            Restore
          </ActionButton>
        </div>
      </div>
      <div className="tool-group approval-tool-group">
        <span className="toolbar-label">Finish</span>
        <ActionButton
          id="approve-image"
          className={imageApproved ? 'confirmed' : 'approval-button'}
          aria-pressed={imageApproved}
          onClick={() => onAction('toggle-approval')}
        >
          {imageApproved ? '✓ Approved' : 'Approve image'}
        </ActionButton>
      </div>
    </div>
  )
}

export type CoordinateValues = [
  left: string,
  top: string,
  right: string,
  bottom: string,
]

const coordinateFields = [
  { id: 'x1', label: 'Left (x1)' },
  { id: 'y1', label: 'Top (y1)' },
  { id: 'x2', label: 'Right (x2)' },
  { id: 'y2', label: 'Bottom (y2)' },
] as const

interface AnnotationInspectorProps {
  detections: readonly ReviewDetection[]
  selected: ReviewDetection | null
  selectedId: number | null
  coordinates: CoordinateValues
  imageWidth: number
  imageHeight: number
  onCoordinateChange: (index: number, value: string) => void
  onCoordinateCommit: () => void
  onClassChange: (className: ModelClass) => void
  onSelect: (detection: ReviewDetection) => void
}

function annotationState(detection: ReviewDetection): string {
  if (detection.removed) return 'removed'
  if (detection.confirmed) return 'confirmed'
  if (detection.source === 'manual') return 'manual'
  return 'not reviewed'
}

export function AnnotationInspector({
  detections,
  selected,
  selectedId,
  coordinates,
  imageWidth,
  imageHeight,
  onCoordinateChange,
  onCoordinateCommit,
  onClassChange,
  onSelect,
}: AnnotationInspectorProps) {
  const selectedWidth = selected
    ? Math.round(selected.bbox[2] - selected.bbox[0])
    : 0
  const selectedHeight = selected
    ? Math.round(selected.bbox[3] - selected.bbox[1])
    : 0
  const selectedArea = selectedWidth * selectedHeight
  const imageArea = imageWidth * imageHeight

  return (
    <aside className="review-editor" aria-label="Annotation inspector">
      <div className="inspector-heading">
        <div>
          <p className="section-kicker">Inspector</p>
          <h3 id="review-selection-title">
            {selected
              ? displayDetectionClass(selected.class)
              : 'Select a box'}
          </h3>
        </div>
        <span className="box-count">{detections.length} boxes</span>
      </div>
      {selected ? (
        <>
          <div className="selection-summary">
            <span className={`selection-status ${annotationState(selected).replace(' ', '-')}`}>
              {annotationState(selected)}
            </span>
            <strong>
              {selectedWidth} × {selectedHeight} px
            </strong>
            <small>
              {(selected.confidence * 100).toFixed(1)}% confidence ·{' '}
              {imageArea > 0
                ? ((selectedArea / imageArea) * 100).toFixed(2)
                : '0.00'}
              % of image
            </small>
          </div>
          <FormField controlId="annotation-class" label="Class">
            <select
              id="annotation-class"
              value={selected.class}
              onChange={(event) =>
                onClassChange(event.currentTarget.value as ModelClass)
              }
            >
              {MODEL_CLASSES.map((className) => (
                <option key={className} value={className}>
                  {className}
                </option>
              ))}
            </select>
          </FormField>
          <div className="coordinate-grid">
            {coordinateFields.map(({ id, label }, index) => (
              <FormField
                key={id}
                controlId={`annotation-${id}`}
                label={label}
              >
                <input
                  id={`annotation-${id}`}
                  type="number"
                  min="0"
                  step="1"
                  value={coordinates[index]}
                  onChange={(event) =>
                    onCoordinateChange(index, event.currentTarget.value)
                  }
                  onBlur={onCoordinateCommit}
                />
              </FormField>
            ))}
          </div>
        </>
      ) : (
        <div className="inspector-empty">
          <span aria-hidden="true">↖</span>
          Click a box on the image or choose one below to edit its position,
          size, and review status.
        </div>
      )}
      <div className="annotation-list-heading">
        <strong>All annotations</strong>
        <span>Click to select</span>
      </div>
      <div id="annotation-list" className="annotation-list">
        {detections.map((detection, index) => (
          <ActionButton
            key={detection.id}
            className={`annotation-chip${detection.id === selectedId ? ' selected' : ''}${detection.removed ? ' removed' : ''}`}
            aria-pressed={detection.id === selectedId}
            onClick={() => onSelect(detection)}
          >
            <span
              className={`annotation-state-dot ${annotationState(detection).replace(' ', '-')}`}
              aria-hidden="true"
            />
            <span className="annotation-chip-label">
              <strong>
                {index + 1}. {displayDetectionClass(detection.class)}
              </strong>
              <small>
                {annotationState(detection)} ·{' '}
                {(detection.confidence * 100).toFixed(1)}%
              </small>
            </span>
          </ActionButton>
        ))}
      </div>
    </aside>
  )
}
