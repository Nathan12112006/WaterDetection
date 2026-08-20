export type BoundingBoxTuple = [
  x1: number,
  y1: number,
  x2: number,
  y2: number,
]

export type MediaMode = 'images' | 'video'
export type ModelSelection =
  | 'water_accumulation'
  | 'water_detection'
  | 'water_detection_last'
export interface ClassConfidences {
  'pipe burst': number
  'water accumulation': number
  'water drop': number
}
export type UploadSource = 'files' | 'folder'
export type WorkspaceTab = 'preview' | 'review'

export interface Detection {
  class: string
  confidence: number
  bbox: BoundingBoxTuple
}

export type DetectionSource = 'model' | 'manual'

export interface ReviewDetection extends Detection {
  id: number
  confirmed: boolean
  removed: boolean
  source: DetectionSource
}

export interface ReviewHistory {
  past: ReviewDetection[][]
  future: ReviewDetection[][]
}

export interface ReviewViewport {
  zoom: number
  panX: number
  panY: number
}

export interface ReviewSignals {
  confidence: number
  geometry: number
  empty: boolean
}

export interface ImageEntry {
  id: string
  file: File
  originalIndex: number
  url: string
  width: number
  height: number
  exportDetections: Detection[] | null
  reviewDetections: ReviewDetection[] | null
  reviewHistory: ReviewHistory
  reviewViewport: ReviewViewport
  reviewSelected: boolean
  reviewEdited: boolean
  imageApproved: boolean
  error: string | null
}

export interface StatusMessage {
  text: string
  error: boolean
}

export interface DetectionSettings {
  uploadSource: UploadSource
  model: ModelSelection
  confidence: number
  classConfidences: ClassConfidences
  videoSampleRate: number
}
