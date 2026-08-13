export type BoundingBoxTuple = [
  x1: number,
  y1: number,
  x2: number,
  y2: number,
]

export type MediaMode = 'images' | 'video'
export type ModelSelection = 'water_accumulation' | 'water_detection'
export interface ClassConfidences {
  'pipe burst': number
  'water accumulation': number
  'water drop': number
}
export type UploadSource = 'files' | 'folder'
export type WorkspaceTab = 'preview' | 'review'

/** The durable-in-memory stages of the workspace workflow. */
export type WorkflowStage = 'upload' | 'configure' | 'run' | 'review' | 'export'

export type WorkspacePanel = 'left' | 'right'
export type ExportSafety = 'safe' | 'unsafe'
export type NotificationTone = 'info' | 'success' | 'warning' | 'error'

export interface WorkspaceNotification {
  id: string
  message: string
  tone: NotificationTone
  /** Optional action (for example, Undo) shown by the notification host. */
  action?: {
    label: string
    action: string
  }
}

export type ConfirmationKind =
  | 'replace-media'
  | 'remove-selected'
  | 'rerun'
  | 'refresh'
  | 'export'
  | 'custom'

export interface DestructiveConfirmationRequest {
  id: string
  kind: ConfirmationKind
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
}

/** The grid location to restore when leaving the review workspace. */
export interface GridReturnPosition {
  scrollTop: number
  focusedImageId: string | null
}

export interface WorkspaceSessionState {
  mediaMode: MediaMode | null
  mediaCount: number
  hasMedia: boolean
  workflowStage: WorkflowStage
  leftPanelOpen: boolean
  rightPanelOpen: boolean
  rightPanelWidth: number
  exportSafety: ExportSafety
  notifications: WorkspaceNotification[]
  pendingConfirmation: DestructiveConfirmationRequest | null
  gridReturnPosition: GridReturnPosition
}

export type WorkspaceSessionAction =
  | { type: 'media/loaded'; mode: MediaMode; count: number }
  | { type: 'media/cleared' }
  | { type: 'workflow/set-stage'; stage: WorkflowStage }
  | { type: 'review/enter'; gridReturnPosition?: GridReturnPosition }
  | { type: 'review/leave' }
  | { type: 'panel/toggle'; panel: WorkspacePanel }
  | { type: 'panel/set'; panel: WorkspacePanel; open: boolean }
  | { type: 'panel/resize-right'; width: number }
  | { type: 'export/mark-safe' }
  | { type: 'export/invalidate' }
  | { type: 'notification/add'; notification: WorkspaceNotification }
  | { type: 'notification/dismiss'; id: string }
  | { type: 'confirmation/request'; request: DestructiveConfirmationRequest }
  | { type: 'confirmation/clear'; id?: string }
  | { type: 'grid/set-return-position'; position: GridReturnPosition }

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
