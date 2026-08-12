import type { Detection, ImageEntry } from '../types'
import { canvasBlob, drawDetections, loadImage } from './canvas'

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.hidden = true
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000)
}

export async function downloadAnnotatedImage(
  entry: ImageEntry,
  detections: readonly Detection[],
): Promise<void> {
  const image = await loadImage(entry.url)
  const canvas = document.createElement('canvas')
  canvas.width = entry.width
  canvas.height = entry.height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas rendering is unavailable.')
  context.drawImage(image, 0, 0)
  drawDetections(
    context,
    canvas,
    entry.width,
    entry.height,
    detections,
  )
  const blob = await canvasBlob(canvas, 'image/png')
  const basename = entry.file.name.replace(/\.[^.]+$/, '')
  downloadBlob(blob, `${basename}-annotated.png`)
}

