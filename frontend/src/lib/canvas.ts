import type { Detection } from '../types'
import { displayDetectionClass } from './detections'

const CLASS_COLORS: Record<string, string> = {
  'pipe burst': '#fb7185',
  'water accumulation': '#facc15',
  'water drop': '#38bdf8',
}

function colorForClass(className: string): string {
  return CLASS_COLORS[displayDetectionClass(className)] ?? '#a78bfa'
}

export interface CanvasSize {
  width: number
  height: number
}

export interface ContentRect extends CanvasSize {
  left: number
  top: number
}

export function containedContentRect(
  container: CanvasSize,
  content: CanvasSize,
): ContentRect {
  const scale = Math.min(
    container.width / content.width,
    container.height / content.height,
  )
  const width = content.width * scale
  const height = content.height * scale
  return {
    left: (container.width - width) / 2,
    top: (container.height - height) / 2,
    width,
    height,
  }
}

export function canvasDimensions(
  width: number,
  height: number,
  maximumDimension = 1200,
): CanvasSize {
  const scale = Math.min(1, maximumDimension / Math.max(width, height))
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  }
}

export function drawDetections(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  sourceWidth: number,
  sourceHeight: number,
  detections: readonly Detection[],
): void {
  const scaleX = canvas.width / sourceWidth
  const scaleY = canvas.height / sourceHeight
  const lineWidth = Math.max(2, Math.round(canvas.width / 500))
  const fontSize = Math.max(14, Math.round(canvas.width / 45))
  context.lineWidth = lineWidth
  context.font = `700 ${fontSize}px system-ui`
  context.textBaseline = 'top'

  for (const detection of detections) {
    const [rawX1, rawY1, rawX2, rawY2] = detection.bbox
    const x1 = rawX1 * scaleX
    const y1 = rawY1 * scaleY
    const x2 = rawX2 * scaleX
    const y2 = rawY2 * scaleY
    const label = `${displayDetectionClass(detection.class)} ${Math.round(detection.confidence * 100)}%`
    const color = colorForClass(detection.class)

    context.strokeStyle = color
    context.strokeRect(x1, y1, x2 - x1, y2 - y1)

    const textWidth = context.measureText(label).width
    const labelHeight = fontSize + 10
    const labelY = y1 >= labelHeight ? y1 - labelHeight : y1
    context.fillStyle = color
    context.fillRect(x1, labelY, textWidth + 14, labelHeight)
    context.fillStyle = '#07111c'
    context.fillText(label, x1 + 7, labelY + 5)
  }
}

export function canvasBlob(
  canvas: HTMLCanvasElement,
  type = 'image/jpeg',
  quality = 0.9,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('The canvas could not be encoded.'))
      },
      type,
      quality,
    )
  })
}

export async function loadImage(url: string): Promise<HTMLImageElement> {
  const image = new Image()
  image.src = url
  await image.decode()
  return image
}
