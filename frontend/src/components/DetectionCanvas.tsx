import { useEffect, useRef } from 'react'
import type { Detection } from '../types'
import {
  canvasDimensions,
  drawDetections,
  loadImage,
} from '../lib/canvas'

interface DetectionCanvasProps {
  imageUrl: string
  sourceWidth: number
  sourceHeight: number
  detections: readonly Detection[]
  maximumDimension?: number
  className?: string
}

export function DetectionCanvas({
  imageUrl,
  sourceWidth,
  sourceHeight,
  detections,
  maximumDimension,
  className,
}: DetectionCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let cancelled = false
    const draw = async () => {
      const canvas = canvasRef.current
      if (!canvas) return
      const dimensions = canvasDimensions(
        sourceWidth,
        sourceHeight,
        maximumDimension,
      )
      canvas.width = dimensions.width
      canvas.height = dimensions.height
      const image = await loadImage(imageUrl)
      if (cancelled) return
      const context = canvas.getContext('2d')
      if (!context) return
      context.clearRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      drawDetections(
        context,
        canvas,
        sourceWidth,
        sourceHeight,
        detections,
      )
    }
    void draw()
    return () => {
      cancelled = true
    }
  }, [
    detections,
    imageUrl,
    maximumDimension,
    sourceHeight,
    sourceWidth,
  ])

  return <canvas ref={canvasRef} className={className} />
}

