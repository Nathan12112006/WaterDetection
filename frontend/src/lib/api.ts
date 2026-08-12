import type {
  Detection,
  ModelSelection,
  ClassConfidences,
} from '../types'
import { normalizeDetections } from './detections'

export interface DetectionRequest {
  media: Blob
  filename: string
  model: ModelSelection
  confidence: number
  classConfidences?: ClassConfidences
  signal?: AbortSignal
}

export class DetectionRequestError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'DetectionRequestError'
    this.status = status
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof body.detail === 'string'
    ) {
      return body.detail
    }
  } catch {
    // The HTTP status still gives the caller a useful failure.
  }
  return `Detection failed with HTTP ${response.status}.`
}

export async function requestDetections({
  media,
  filename,
  model,
  confidence,
  classConfidences,
  signal,
}: DetectionRequest): Promise<Detection[]> {
  const data = new FormData()
  data.append('file', media, filename)
  data.append('model', model)
  data.append('confidence', String(confidence))
  if (classConfidences) {
    data.append('confidence_pipe_burst', String(classConfidences['pipe burst']))
    data.append('confidence_water_accumulation', String(classConfidences['water accumulation']))
    data.append('confidence_water_drop', String(classConfidences['water drop']))
  }

  const response = await fetch('/detect', {
    method: 'POST',
    body: data,
    signal,
  })
  if (!response.ok) {
    throw new DetectionRequestError(
      await errorMessage(response),
      response.status,
    )
  }
  return normalizeDetections(await response.json())
}
