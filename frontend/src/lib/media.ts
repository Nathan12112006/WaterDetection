import type { ImageEntry } from '../types'
import { emptyHistory } from './review'

export async function createImageEntry(
  file: File,
  originalIndex: number,
  id: string,
): Promise<ImageEntry> {
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    if (image.naturalWidth <= 0 || image.naturalHeight <= 0) {
      throw new Error('The selected image does not have valid dimensions.')
    }
    return {
      id,
      file,
      originalIndex,
      url,
      width: image.naturalWidth,
      height: image.naturalHeight,
      exportDetections: null,
      reviewDetections: null,
      reviewHistory: emptyHistory(),
      reviewViewport: { zoom: 1, panX: 0, panY: 0 },
      reviewSelected: false,
      reviewEdited: false,
      imageApproved: false,
      error: null,
    }
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
}

export function videoSampleRates(
  duration: number,
  maximumSamples = 2_000,
): number[] {
  return [1, 2, 4, 8, 15, 30, 60, 120].filter(
    (rate) => Math.ceil(duration * rate) <= maximumSamples,
  )
}

export function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

export function formatVideoTime(time: number): string {
  const minutes = Math.floor(time / 60)
  const seconds = Math.floor(time % 60)
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
