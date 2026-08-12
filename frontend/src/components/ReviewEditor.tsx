import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type {
  BoundingBoxTuple,
  ImageEntry,
  ReviewDetection,
  ReviewViewport,
} from '../types'
import {
  canvasDimensions,
  containedContentRect,
  loadImage,
} from '../lib/canvas'
import { displayDetectionClass } from '../lib/detections'
import { MODEL_CLASSES, type ModelClass } from '../modelClasses'
import {
  activeDetections,
  cloneReviewDetections,
  manualReviewDetection,
  rankReviewEntries,
  recordHistory,
  redoHistory,
  reviewReasons,
  undoHistory,
} from '../lib/review'
import {
  AnnotationInspector,
  type CoordinateValues,
  ReviewPager,
  ReviewToolbar,
  type ReviewToolbarAction,
} from './ReviewEditorControls'
import { ActionButton } from './ui/ActionButton'

type ResizeMode =
  | 'nw'
  | 'n'
  | 'ne'
  | 'e'
  | 'se'
  | 's'
  | 'sw'
  | 'w'
type BoxMode = ResizeMode | 'move'
type Point = [x: number, y: number]

interface BoxInteraction {
  detectionId: number
  mode: BoxMode
  start: Point
  originalBox: BoundingBoxTuple
  originalDetections: ReviewDetection[]
}

interface PanInteraction {
  startClientX: number
  startClientY: number
  startPanX: number
  startPanY: number
}

interface ReviewEditorProps {
  entry: ImageEntry
  entries: readonly ImageEntry[]
  onEntryChange: (entry: ImageEntry) => void
  onOpen: (entryId: string) => void
  onBack: () => void
  onStatus: (message: string, error?: boolean) => void
}

function clampViewport(
  viewport: ReviewViewport,
  width: number,
  height: number,
): ReviewViewport {
  return {
    ...viewport,
    panX: Math.max(
      width * (1 - viewport.zoom),
      Math.min(0, viewport.panX),
    ),
    panY: Math.max(
      height * (1 - viewport.zoom),
      Math.min(0, viewport.panY),
    ),
  }
}

function zoomedViewport(
  current: ReviewViewport,
  requestedZoom: number,
  anchorX: number,
  anchorY: number,
  canvasWidth: number,
  canvasHeight: number,
): ReviewViewport {
  const zoom = Math.max(1, Math.min(8, requestedZoom))
  return clampViewport(
    {
      zoom,
      panX:
        anchorX -
        ((anchorX - current.panX) / current.zoom) * zoom,
      panY:
        anchorY -
        ((anchorY - current.panY) / current.zoom) * zoom,
    },
    canvasWidth,
    canvasHeight,
  )
}

function drawReviewBox(
  context: CanvasRenderingContext2D,
  detection: ReviewDetection,
  selected: boolean,
  scaleX: number,
  scaleY: number,
  zoom: number,
  dimmed: boolean,
): void {
  const [x1, y1, x2, y2] = detection.bbox
  const canvasX = x1 * scaleX
  const canvasY = y1 * scaleY
  const canvasWidth = (x2 - x1) * scaleX
  const canvasHeight = (y2 - y1) * scaleY
  context.save()
  context.globalAlpha = dimmed ? 0.46 : 1
  context.lineWidth = (selected ? 3.5 : 2) / zoom
  context.strokeStyle = selected
    ? '#f472b6'
    : detection.confirmed
      ? '#4ade80'
      : '#22d3ee'
  if (selected) {
    context.fillStyle = 'rgb(244 114 182 / 12%)'
    context.fillRect(canvasX, canvasY, canvasWidth, canvasHeight)
    context.shadowColor = 'rgb(244 114 182 / 60%)'
    context.shadowBlur = 12 / zoom
  }
  context.strokeRect(canvasX, canvasY, canvasWidth, canvasHeight)
  context.shadowBlur = 0

  const state = detection.confirmed
    ? 'confirmed'
    : detection.source === 'manual'
      ? 'manual'
      : 'review'
  const label = `${displayDetectionClass(detection.class)} · ${state}`
  const fontSize = 13 / zoom
  const labelHeight = 23 / zoom
  const padding = 7 / zoom
  context.setLineDash([])
  context.font = `700 ${fontSize}px system-ui`
  context.textBaseline = 'middle'
  const textWidth = context.measureText(label).width
  const labelY = canvasY >= labelHeight
    ? canvasY - labelHeight
    : canvasY
  context.fillStyle = selected
    ? '#6b174f'
    : detection.confirmed
      ? '#14532d'
      : '#083344'
  context.fillRect(
    canvasX,
    labelY,
    textWidth + padding * 2,
    labelHeight,
  )
  context.fillStyle = '#f8fafc'
  context.fillText(
    label,
    canvasX + padding,
    labelY + labelHeight / 2,
  )

  if (selected && !detection.removed) {
    context.fillStyle = '#f472b6'
    for (const [handleX, handleY] of [
      [x1, y1],
      [(x1 + x2) / 2, y1],
      [x2, y1],
      [x2, (y1 + y2) / 2],
      [x2, y2],
      [(x1 + x2) / 2, y2],
      [x1, y2],
      [x1, (y1 + y2) / 2],
    ]) {
      context.beginPath()
      context.arc(
        handleX * scaleX,
        handleY * scaleY,
        6 / zoom,
        0,
        Math.PI * 2,
      )
      context.fill()
      context.lineWidth = 2 / zoom
      context.strokeStyle = '#fdf2f8'
      context.stroke()
    }
  }
  context.restore()
}

function drawDraft(
  context: CanvasRenderingContext2D,
  bbox: BoundingBoxTuple,
  scaleX: number,
  scaleY: number,
  zoom: number,
): void {
  const [x1, y1, x2, y2] = bbox
  const width = Math.max(0, Math.round(x2 - x1))
  const height = Math.max(0, Math.round(y2 - y1))
  const label = `${width} × ${height} px`
  context.save()
  context.setLineDash([8 / zoom, 5 / zoom])
  context.lineWidth = 3 / zoom
  context.strokeStyle = '#f472b6'
  context.fillStyle = 'rgb(244 114 182 / 12%)'
  context.fillRect(
    x1 * scaleX,
    y1 * scaleY,
    width * scaleX,
    height * scaleY,
  )
  context.strokeRect(
    x1 * scaleX,
    y1 * scaleY,
    width * scaleX,
    height * scaleY,
  )
  context.setLineDash([])
  context.font = `700 ${14 / zoom}px system-ui`
  const textWidth = context.measureText(label).width
  const labelX = Math.max(0, x1 * scaleX)
  const labelY = Math.max(0, y1 * scaleY - 27 / zoom)
  context.fillStyle = '#6b174f'
  context.fillRect(
    labelX,
    labelY,
    textWidth + 14 / zoom,
    24 / zoom,
  )
  context.fillStyle = '#fce7f3'
  context.fillText(label, labelX + 7 / zoom, labelY + 5 / zoom)
  context.restore()
}

function resizedBox(
  original: BoundingBoxTuple,
  mode: BoxMode,
  dx: number,
  dy: number,
  imageWidth: number,
  imageHeight: number,
): BoundingBoxTuple {
  let [x1, y1, x2, y2] = original
  if (mode === 'move') {
    const width = x2 - x1
    const height = y2 - y1
    x1 = Math.max(0, Math.min(imageWidth - width, x1 + dx))
    y1 = Math.max(0, Math.min(imageHeight - height, y1 + dy))
    return [x1, y1, x1 + width, y1 + height]
  }
  if (mode.includes('w')) x1 = Math.max(0, Math.min(x2 - 4, x1 + dx))
  if (mode.includes('e')) {
    x2 = Math.min(imageWidth, Math.max(x1 + 4, x2 + dx))
  }
  if (mode.includes('n')) y1 = Math.max(0, Math.min(y2 - 4, y1 + dy))
  if (mode.includes('s')) {
    y2 = Math.min(imageHeight, Math.max(y1 + 4, y2 + dy))
  }
  return [x1, y1, x2, y2]
}

export function ReviewEditor({
  entry,
  entries,
  onEntryChange,
  onOpen,
  onBack,
  onStatus,
}: ReviewEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imageRef = useRef<HTMLImageElement | null>(null)
  const boxInteraction = useRef<BoxInteraction | null>(null)
  const panInteraction = useRef<PanInteraction | null>(null)
  const drawingStart = useRef<Point | null>(null)
  const [detections, setDetections] = useState<ReviewDetection[]>(
    entry.reviewDetections ?? [],
  )
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [newBoxClass, setNewBoxClass] = useState<ModelClass>(
    MODEL_CLASSES[0],
  )
  const [draftBox, setDraftBox] = useState<BoundingBoxTuple | null>(null)
  const [viewport, setViewport] = useState(entry.reviewViewport)
  const [coordinates, setCoordinates] = useState<CoordinateValues>(
    ['', '', '', ''],
  )
  const liveDetections = useRef(detections)
  const liveDraftBox = useRef(draftBox)
  const liveViewport = useRef(viewport)
  const interactionFrame = useRef<number | null>(null)

  const renderInteractionFrame = () => {
    if (interactionFrame.current !== null) return
    interactionFrame.current = window.requestAnimationFrame(() => {
      interactionFrame.current = null
      setDetections(liveDetections.current)
      setDraftBox(liveDraftBox.current)
      setViewport(liveViewport.current)
    })
  }

  const flushInteractionFrame = () => {
    if (interactionFrame.current !== null) {
      window.cancelAnimationFrame(interactionFrame.current)
      interactionFrame.current = null
    }
    setDetections(liveDetections.current)
    setDraftBox(liveDraftBox.current)
    setViewport(liveViewport.current)
  }

  const ranked = useMemo(() => rankReviewEntries(entries), [entries])
  const queueIndex = ranked.findIndex(
    ({ entry: candidate }) => candidate.id === entry.id,
  )
  const queueItem = ranked[queueIndex]
  const selected = detections.find(
    (detection) => detection.id === selectedId,
  )

  useEffect(() => {
    let cancelled = false
    void loadImage(entry.url).then((image) => {
      if (!cancelled) {
        imageRef.current = image
        setDetections((current) => [...current])
      }
    })
    return () => {
      cancelled = true
      imageRef.current = null
    }
  }, [entry.url])

  useEffect(
    () => () => {
      if (interactionFrame.current !== null) {
        window.cancelAnimationFrame(interactionFrame.current)
      }
    },
    [],
  )

  useEffect(() => {
    const canvas = canvasRef.current
    const image = imageRef.current
    if (!canvas || !image) return
    const dimensions = canvasDimensions(entry.width, entry.height)
    canvas.width = dimensions.width
    canvas.height = dimensions.height
    const context = canvas.getContext('2d')
    if (!context) return
    const boundedViewport = clampViewport(
      viewport,
      canvas.width,
      canvas.height,
    )
    context.setTransform(1, 0, 0, 1, 0, 0)
    context.clearRect(0, 0, canvas.width, canvas.height)
    context.setTransform(
      boundedViewport.zoom,
      0,
      0,
      boundedViewport.zoom,
      boundedViewport.panX,
      boundedViewport.panY,
    )
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const scaleX = canvas.width / entry.width
    const scaleY = canvas.height / entry.height
    detections
      .filter((detection) => !detection.removed)
      .forEach((detection) =>
        drawReviewBox(
          context,
          detection,
          detection.id === selectedId,
          scaleX,
          scaleY,
          boundedViewport.zoom,
          selectedId !== null && detection.id !== selectedId,
        ),
      )
    if (draftBox) {
      drawDraft(
        context,
        draftBox,
        scaleX,
        scaleY,
        boundedViewport.zoom,
      )
    }
  }, [
    detections,
    draftBox,
    entry.height,
    entry.width,
    selectedId,
    viewport,
  ])

  const publish = (
    nextDetections: ReviewDetection[],
    message: string,
    historySnapshot: readonly ReviewDetection[] = entry.reviewDetections ?? [],
  ) => {
    liveDetections.current = nextDetections
    setDetections(nextDetections)
    onEntryChange({
      ...entry,
      reviewViewport: liveViewport.current,
      reviewDetections: cloneReviewDetections(nextDetections),
      exportDetections: activeDetections(nextDetections),
      reviewHistory: recordHistory(entry.reviewHistory, historySnapshot),
      reviewEdited: true,
      imageApproved: false,
    })
    onStatus(message)
  }

  const publishHistory = (
    result: ReturnType<typeof undoHistory>,
    message: string,
  ) => {
    if (!result) return false
    liveDetections.current = result.detections
    setDetections(result.detections)
    if (!result.detections.some((detection) => detection.id === selectedId)) {
      setSelectedId(null)
      setCoordinates(['', '', '', ''])
    } else {
      const restoredSelection = result.detections.find(
        (detection) => detection.id === selectedId,
      )
      if (restoredSelection) {
        setCoordinates(
          restoredSelection.bbox.map((value) =>
            String(Math.round(value)),
          ) as [string, string, string, string],
        )
      }
    }
    onEntryChange({
      ...entry,
      reviewDetections: result.detections,
      exportDetections: activeDetections(result.detections),
      reviewHistory: result.history,
      reviewEdited: true,
      imageApproved: false,
    })
    onStatus(message)
    return true
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      const editingText =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      if (editingText || !(event.ctrlKey || event.metaKey)) return

      const key = event.key.toLowerCase()
      const current = entry.reviewDetections ?? []
      if (key === 'z') {
        const result = event.shiftKey
          ? redoHistory(entry.reviewHistory, current)
          : undoHistory(entry.reviewHistory, current)
        if (
          publishHistory(
            result,
            event.shiftKey
              ? 'Annotation change redone.'
              : 'Last annotation change undone.',
          )
        ) {
          event.preventDefault()
        }
      } else if (
        key === 'y' &&
        publishHistory(
          redoHistory(entry.reviewHistory, current),
          'Annotation change redone.',
        )
      ) {
        event.preventDefault()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  })

  const canvasPoint = (event: React.PointerEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current
    if (!canvas) return [0, 0]
    const bounds = canvas.getBoundingClientRect()
    const content = containedContentRect(
      { width: bounds.width, height: bounds.height },
      { width: canvas.width, height: canvas.height },
    )
    const canvasX =
      ((event.clientX - bounds.left - content.left) / content.width) *
      canvas.width
    const canvasY =
      ((event.clientY - bounds.top - content.top) / content.height) *
      canvas.height
    const currentViewport = liveViewport.current
    return [
      Math.max(
        0,
        Math.min(
          entry.width,
          ((canvasX - currentViewport.panX) /
            currentViewport.zoom /
            canvas.width) *
            entry.width,
        ),
      ),
      Math.max(
        0,
        Math.min(
          entry.height,
          ((canvasY - currentViewport.panY) /
            currentViewport.zoom /
            canvas.height) *
            entry.height,
        ),
      ),
    ]
  }

  const pointerTolerance = (): Point => {
    const canvas = canvasRef.current
    if (!canvas) return [0, 0]
    const bounds = canvas.getBoundingClientRect()
    const content = containedContentRect(
      { width: bounds.width, height: bounds.height },
      { width: canvas.width, height: canvas.height },
    )
    return [
      (14 / Math.max(1, content.width)) *
        entry.width /
        liveViewport.current.zoom,
      (14 / Math.max(1, content.height)) *
        entry.height /
        liveViewport.current.zoom,
    ]
  }

  const detectionAt = (
    point: Point,
    tolerance: Point = [0, 0],
  ): ReviewDetection | undefined =>
    [...detections]
      .filter((detection) => !detection.removed)
      .reverse()
      .find(
        (detection) =>
          point[0] >= detection.bbox[0] - tolerance[0] &&
          point[0] <= detection.bbox[2] + tolerance[0] &&
          point[1] >= detection.bbox[1] - tolerance[1] &&
          point[1] <= detection.bbox[3] + tolerance[1],
      )

  const selectDetection = (detection: ReviewDetection | undefined) => {
    setSelectedId(detection?.id ?? null)
    setCoordinates(
      detection
        ? detection.bbox.map((value) => String(Math.round(value))) as [
            string,
            string,
            string,
            string,
          ]
        : ['', '', '', ''],
    )
  }

  const resizeHandle = (
    detection: ReviewDetection,
    point: Point,
  ): ResizeMode | null => {
    const [thresholdX, thresholdY] = pointerTolerance()
    const [x1, y1, x2, y2] = detection.bbox
    const nearLeft = Math.abs(point[0] - x1) <= thresholdX
    const nearRight = Math.abs(point[0] - x2) <= thresholdX
    const nearTop = Math.abs(point[1] - y1) <= thresholdY
    const nearBottom = Math.abs(point[1] - y2) <= thresholdY
    const withinHorizontal =
      point[0] >= x1 - thresholdX && point[0] <= x2 + thresholdX
    const withinVertical =
      point[1] >= y1 - thresholdY && point[1] <= y2 + thresholdY

    if (nearLeft && nearTop) return 'nw'
    if (nearRight && nearTop) return 'ne'
    if (nearRight && nearBottom) return 'se'
    if (nearLeft && nearBottom) return 'sw'
    if (nearTop && withinHorizontal) return 'n'
    if (nearRight && withinVertical) return 'e'
    if (nearBottom && withinHorizontal) return 's'
    if (nearLeft && withinVertical) return 'w'
    return null
  }

  const autoPanDrawingViewport = (
    event: React.PointerEvent<HTMLCanvasElement>,
  ): void => {
    const canvas = event.currentTarget
    const bounds = canvas.getBoundingClientRect()
    const content = containedContentRect(
      { width: bounds.width, height: bounds.height },
      { width: canvas.width, height: canvas.height },
    )
    const left = bounds.left + content.left
    const top = bounds.top + content.top
    const right = left + content.width
    const bottom = top + content.height
    const overflowX =
      event.clientX < left
        ? event.clientX - left
        : event.clientX > right
          ? event.clientX - right
          : 0
    const overflowY =
      event.clientY < top
        ? event.clientY - top
        : event.clientY > bottom
          ? event.clientY - bottom
          : 0
    if (overflowX === 0 && overflowY === 0) return

    const current = liveViewport.current
    liveViewport.current = clampViewport(
      {
        ...current,
        panX:
          current.panX -
          overflowX * (canvas.width / content.width),
        panY:
          current.panY -
          overflowY * (canvas.height / content.height),
      },
      canvas.width,
      canvas.height,
    )
  }

  const handlePointerDown = (
    event: React.PointerEvent<HTMLCanvasElement>,
  ) => {
    const canvas = event.currentTarget
    canvas.focus({ preventScroll: true })
    if (event.button !== 0) return
    const point = canvasPoint(event)
    if (drawing) {
      drawingStart.current = point
      liveDraftBox.current = [point[0], point[1], point[0], point[1]]
      setDraftBox(liveDraftBox.current)
      canvas.setPointerCapture(event.pointerId)
      return
    }
    const selectedHandle =
      selected && !selected.removed ? resizeHandle(selected, point) : null
    const detection = selectedHandle
      ? selected
      : detectionAt(point, pointerTolerance())
    selectDetection(detection)
    if (detection && !detection.removed) {
      boxInteraction.current = {
        detectionId: detection.id,
        mode:
          selectedHandle ??
          resizeHandle(detection, point) ??
          'move',
        start: point,
        originalBox: [...detection.bbox],
        originalDetections: cloneReviewDetections(detections),
      }
      canvas.setPointerCapture(event.pointerId)
      return
    }
    const currentViewport = liveViewport.current
    panInteraction.current = {
      startClientX: event.clientX,
      startClientY: event.clientY,
      startPanX: currentViewport.panX,
      startPanY: currentViewport.panY,
    }
    canvas.style.cursor = 'grabbing'
    canvas.setPointerCapture(event.pointerId)
    event.preventDefault()
  }

  const handlePointerMove = (
    event: React.PointerEvent<HTMLCanvasElement>,
  ) => {
    const canvas = event.currentTarget
    const pan = panInteraction.current
    if (pan) {
      const bounds = canvas.getBoundingClientRect()
      const content = containedContentRect(
        { width: bounds.width, height: bounds.height },
        { width: canvas.width, height: canvas.height },
      )
      liveViewport.current = clampViewport(
        {
          ...liveViewport.current,
          panX:
            pan.startPanX +
            (event.clientX - pan.startClientX) *
              (canvas.width / content.width),
          panY:
            pan.startPanY +
            (event.clientY - pan.startClientY) *
              (canvas.height / content.height),
        },
        canvas.width,
        canvas.height,
      )
      renderInteractionFrame()
      canvas.style.cursor = 'grabbing'
      return
    }

    const start = drawingStart.current
    if (drawing && start) {
      autoPanDrawingViewport(event)
      const point = canvasPoint(event)
      liveDraftBox.current = [
        Math.min(start[0], point[0]),
        Math.min(start[1], point[1]),
        Math.max(start[0], point[0]),
        Math.max(start[1], point[1]),
      ]
      renderInteractionFrame()
      return
    }
    const point = canvasPoint(event)
    const interaction = boxInteraction.current
    if (interaction) {
      const nextBox = resizedBox(
        interaction.originalBox,
        interaction.mode,
        point[0] - interaction.start[0],
        point[1] - interaction.start[1],
        entry.width,
        entry.height,
      )
      liveDetections.current = liveDetections.current.map((detection) =>
          detection.id === interaction.detectionId
            ? { ...detection, bbox: nextBox, confirmed: false }
            : detection,
        )
      liveDraftBox.current = nextBox
      renderInteractionFrame()
      return
    }

    const handle =
      selected && !selected.removed ? resizeHandle(selected, point) : null
    canvas.style.cursor = drawing
      ? 'crosshair'
      : handle === 'nw' || handle === 'se'
        ? 'nwse-resize'
        : handle === 'ne' || handle === 'sw'
          ? 'nesw-resize'
          : handle === 'n' || handle === 's'
            ? 'ns-resize'
            : handle === 'e' || handle === 'w'
              ? 'ew-resize'
              : detectionAt(point, pointerTolerance())
                ? 'move'
                : 'grab'
  }

  const handlePointerUp = (
    event: React.PointerEvent<HTMLCanvasElement>,
  ) => {
    if (panInteraction.current) {
      panInteraction.current = null
      flushInteractionFrame()
      event.currentTarget.style.cursor = 'grab'
      onEntryChange({
        ...entry,
        reviewViewport: liveViewport.current,
      })
      return
    }
    const interaction = boxInteraction.current
    if (interaction) {
      boxInteraction.current = null
      const finalDetections = liveDetections.current
      liveDraftBox.current = null
      flushInteractionFrame()
      const changed =
        JSON.stringify(finalDetections) !==
        JSON.stringify(interaction.originalDetections)
      if (changed) {
        const changedSelection = finalDetections.find(
          (detection) => detection.id === selectedId,
        )
        if (changedSelection) {
          setCoordinates(
            changedSelection.bbox.map((value) =>
              String(Math.round(value)),
            ) as [string, string, string, string],
          )
        }
        publish(
          finalDetections,
          'Box position or size updated. Confirm it when correct.',
          interaction.originalDetections,
        )
      } else {
        liveDetections.current = interaction.originalDetections
        setDetections(interaction.originalDetections)
      }
      return
    }
    const start = drawingStart.current
    const finalDraftBox = liveDraftBox.current
    if (!drawing || !start || !finalDraftBox) return
    drawingStart.current = null
    setDrawing(false)
    liveDraftBox.current = null
    setDraftBox(null)
    if (
      finalDraftBox[2] - finalDraftBox[0] < 4 ||
      finalDraftBox[3] - finalDraftBox[1] < 4
    ) {
      onStatus('Draw a larger area for the new box.', true)
      return
    }
    const nextId =
      Math.max(0, ...liveDetections.current.map((detection) => detection.id)) +
      1
    const detection = manualReviewDetection(
      finalDraftBox,
      nextId,
      newBoxClass,
    )
    setSelectedId(nextId)
    setCoordinates(
      detection.bbox.map((value) => String(Math.round(value))) as [
        string,
        string,
        string,
        string,
      ],
    )
    publish(
      [...liveDetections.current, detection],
      `Missed ${newBoxClass} area added to reviewed annotations.`,
    )
  }

  const handlePointerCancel = () => {
    panInteraction.current = null
    boxInteraction.current = null
    drawingStart.current = null
    liveDraftBox.current = null
    liveDetections.current = entry.reviewDetections ?? []
    setDraftBox(null)
    setDetections(entry.reviewDetections ?? [])
  }

  const setZoom = (
    requestedZoom: number,
    anchorX?: number,
    anchorY?: number,
  ) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const zoom = Math.max(1, Math.min(8, requestedZoom))
    const x = anchorX ?? canvas.width / 2
    const y = anchorY ?? canvas.height / 2
    const currentViewport = liveViewport.current
    const next = zoomedViewport(
      currentViewport,
      zoom,
      x,
      y,
      canvas.width,
      canvas.height,
    )
    liveViewport.current = next
    setViewport(next)
    onEntryChange({ ...entry, reviewViewport: next })
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      const bounds = canvas.getBoundingClientRect()
      const content = containedContentRect(
        { width: bounds.width, height: bounds.height },
        { width: canvas.width, height: canvas.height },
      )
      const anchorX =
        ((event.clientX - bounds.left - content.left) / content.width) *
        canvas.width
      const anchorY =
        ((event.clientY - bounds.top - content.top) / content.height) *
        canvas.height
      const current = liveViewport.current
      const next = zoomedViewport(
        current,
        current.zoom * (event.deltaY < 0 ? 1.2 : 1 / 1.2),
        anchorX,
        anchorY,
        canvas.width,
        canvas.height,
      )
      liveViewport.current = next
      setViewport(next)
      onEntryChange({ ...entry, reviewViewport: next })
    }
    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', handleWheel)
  }, [entry, onEntryChange])

  const applyCoordinates = () => {
    if (!selected) return
    const values = coordinates.map(Number)
    if (values.some((value) => !Number.isFinite(value))) return
    const bbox: BoundingBoxTuple = [
      Math.max(0, Math.min(entry.width, values[0])),
      Math.max(0, Math.min(entry.height, values[1])),
      Math.max(0, Math.min(entry.width, values[2])),
      Math.max(0, Math.min(entry.height, values[3])),
    ]
    if (bbox[2] <= bbox[0] || bbox[3] <= bbox[1]) {
      onStatus(
        'Box right/bottom coordinates must exceed left/top.',
        true,
      )
      return
    }
    publish(
      detections.map((detection) =>
        detection.id === selected.id
          ? { ...detection, bbox, confirmed: false }
          : detection,
      ),
      'Box coordinates updated. Confirm it when correct.',
    )
  }

  const changeSelected = (
    update: (detection: ReviewDetection) => ReviewDetection,
    message: string,
  ) => {
    if (!selected) return
    publish(
      detections.map((detection) =>
        detection.id === selected.id ? update(detection) : detection,
      ),
      message,
    )
  }

  const handleToolbarAction = (action: ReviewToolbarAction) => {
    switch (action) {
      case 'undo':
        publishHistory(
          undoHistory(entry.reviewHistory, entry.reviewDetections ?? []),
          'Last annotation change undone.',
        )
        break
      case 'redo':
        publishHistory(
          redoHistory(entry.reviewHistory, entry.reviewDetections ?? []),
          'Annotation change redone.',
        )
        break
      case 'zoom-out':
        setZoom(viewport.zoom / 1.25)
        break
      case 'zoom-reset':
        setZoom(1)
        break
      case 'zoom-in':
        setZoom(viewport.zoom * 1.25)
        break
      case 'toggle-drawing':
        setDrawing((current) => !current)
        liveDraftBox.current = null
        setDraftBox(null)
        drawingStart.current = null
        boxInteraction.current = null
        onStatus(
          drawing
            ? 'Manual drawing cancelled.'
            : 'Drag across the review image to mark the missed area.',
        )
        break
      case 'confirm':
        changeSelected(
          (detection) => ({ ...detection, confirmed: true }),
          'Detection confirmed as correct.',
        )
        break
      case 'remove':
        changeSelected(
          (detection) => ({
            ...detection,
            removed: true,
            confirmed: false,
          }),
          'False-positive box removed from reviewed exports.',
        )
        break
      case 'restore':
        changeSelected(
          (detection) => ({ ...detection, removed: false }),
          'Box restored. Confirm it if the detection is correct.',
        )
        break
      case 'toggle-approval':
        {
          const approving = !entry.imageApproved
          const remaining = ranked.filter(
            ({ entry: candidate }) => candidate.id !== entry.id,
          )
          const next =
            ranked
              .slice(Math.max(0, queueIndex + 1))
              .find(({ entry: candidate }) => candidate.id !== entry.id) ??
            remaining[0]
          onEntryChange({
            ...entry,
            imageApproved: approving,
            reviewSelected: false,
            reviewEdited: true,
          })
          onStatus(
            approving
              ? `${entry.file.name} approved.`
              : `Approval removed from ${entry.file.name}.`,
          )
          if (approving) {
            if (next) onOpen(next.entry.id)
            else onBack()
          }
        }
        break
    }
  }

  const movePage = (offset: number) => {
    const target = ranked[queueIndex + offset]
    if (target) onOpen(target.entry.id)
  }

  const pagerText = queueItem
    ? `Review ${queueIndex + 1} of ${ranked.length} · ${entry.file.name} · ${Math.round(queueItem.uncertainty * 100)}% uncertainty · ${reviewReasons(queueItem.signals).join(', ')}${entry.reviewEdited ? ' · reviewed' : ''}`
    : entry.file.name
  const activeBoxCount = detections.filter(
    (detection) => !detection.removed,
  ).length

  return (
    <div id="review-editor-workspace">
      <div className="review-editor-header">
        <div className="review-editor-heading-main">
          <ActionButton id="back-to-review-overview" onClick={onBack}>
            ← Queue
          </ActionButton>
          <div>
            <p className="section-kicker">Editing image</p>
            <h2 title={entry.file.name}>{entry.file.name}</h2>
            <span>
              {entry.width} × {entry.height} px · {activeBoxCount} active box
              {activeBoxCount === 1 ? '' : 'es'}
            </span>
          </div>
        </div>
        {queueItem && (
          <div className="editor-priority">
            <strong>{Math.round(queueItem.uncertainty * 100)}%</strong>
            uncertainty
          </div>
        )}
      </div>
      <ReviewPager
        currentIndex={queueIndex}
        total={ranked.length}
        label={pagerText}
        onPrevious={() => movePage(-1)}
        onNext={() => movePage(1)}
      />
      <ReviewToolbar
        canUndo={entry.reviewHistory.past.length > 0}
        canRedo={entry.reviewHistory.future.length > 0}
        zoom={viewport.zoom}
        drawing={drawing}
        selected={selected ?? null}
        imageApproved={entry.imageApproved}
        onAction={handleToolbarAction}
      />
      <label className="field" htmlFor="new-box-class">
        <span>Class for new boxes</span>
        <select
          id="new-box-class"
          value={newBoxClass}
          onChange={(event) =>
            setNewBoxClass(event.currentTarget.value as ModelClass)
          }
        >
          {MODEL_CLASSES.map((className) => (
            <option key={className} value={className}>
              {className}
            </option>
          ))}
        </select>
      </label>
      <div className="review-editing-layout">
        <section className="canvas-workbench" aria-label="Image editor">
          <div className="canvas-statusbar">
            <div>
              <span
                className={`editor-mode${drawing ? ' drawing' : ''}`}
              >
                {drawing
                  ? 'Drawing new box'
                  : selected
                    ? 'Box selected'
                    : 'Select mode'}
              </span>
              <span className="canvas-selection-label">
                {selected
                  ? `${displayDetectionClass(selected.class)} · ${(selected.confidence * 100).toFixed(1)}%`
                  : 'Click a box to begin editing'}
              </span>
            </div>
            <div className="canvas-shortcuts" aria-label="Editor shortcuts">
              <kbd>Wheel</kbd>
              <span>zoom</span>
              <kbd>Left drag empty space</kbd>
              <span>pan</span>
            </div>
          </div>
          <div
            className={`review-canvas-shell${drawing ? ' drawing' : ''}`}
          >
            {drawing && (
              <div className="canvas-mode-banner">
                Drag across the damaged area to create a box
              </div>
            )}
            <canvas
              id="review-canvas"
              ref={canvasRef}
              tabIndex={0}
              aria-label="Editable annotation canvas"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerCancel}
            />
          </div>
          <div className="interaction-guide">
            <span>
              <i className="guide-dot select" /> Click to select
            </span>
            <span>
              <i className="guide-dot move" /> Drag inside to move
            </span>
            <span>Drag empty space to pan</span>
            <span>
              <i className="guide-dot resize" /> Drag edge or corner to resize
            </span>
            <span>
              <kbd>Ctrl Z</kbd> Undo
            </span>
          </div>
        </section>
            <AnnotationInspector
          detections={detections}
          selected={selected ?? null}
          selectedId={selectedId}
          coordinates={coordinates}
          imageWidth={entry.width}
          imageHeight={entry.height}
          onCoordinateChange={(index, value) =>
            setCoordinates((current) => {
              const next: CoordinateValues = [...current]
              next[index] = value
              return next
            })
          }
          onCoordinateCommit={applyCoordinates}
          onClassChange={(className) =>
            changeSelected(
              (detection) => ({
                ...detection,
                class: className,
                confirmed: false,
              }),
              `Annotation class changed to ${className}. Confirm it when correct.`,
            )
          }
          onSelect={selectDetection}
        />
      </div>
    </div>
  )
}
