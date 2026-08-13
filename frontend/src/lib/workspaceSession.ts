import type {
  DestructiveConfirmationRequest,
  GridReturnPosition,
  MediaMode,
  WorkspaceNotification,
  WorkspacePanel,
  WorkspaceSessionAction,
  WorkspaceSessionState,
  WorkflowStage,
} from '../types'

/** Keep the inspector usable while preventing it from consuming the workspace. */
export const RIGHT_PANEL_MIN_WIDTH = 240
export const RIGHT_PANEL_MAX_WIDTH = 560
export const RIGHT_PANEL_DEFAULT_WIDTH = 320

export const DEFAULT_GRID_RETURN_POSITION: GridReturnPosition = {
  scrollTop: 0,
  focusedImageId: null,
}

export const BEFORE_UNLOAD_MESSAGE =
  'Your loaded media and workspace changes will be lost if you leave this page.'

function clampRightPanelWidth(width: number): number {
  if (!Number.isFinite(width)) return RIGHT_PANEL_DEFAULT_WIDTH
  return Math.min(
    RIGHT_PANEL_MAX_WIDTH,
    Math.max(RIGHT_PANEL_MIN_WIDTH, Math.round(width)),
  )
}

function normalizeGridReturnPosition(
  position: GridReturnPosition,
): GridReturnPosition {
  return {
    scrollTop: Number.isFinite(position.scrollTop)
      ? Math.max(0, Math.round(position.scrollTop))
      : 0,
    focusedImageId: position.focusedImageId ?? null,
  }
}

function cloneDefaultGridReturnPosition(): GridReturnPosition {
  return { ...DEFAULT_GRID_RETURN_POSITION }
}

export function createInitialWorkspaceSession(): WorkspaceSessionState {
  return {
    mediaMode: null,
    mediaCount: 0,
    hasMedia: false,
    workflowStage: 'upload',
    leftPanelOpen: true,
    rightPanelOpen: false,
    rightPanelWidth: RIGHT_PANEL_DEFAULT_WIDTH,
    exportSafety: 'safe',
    notifications: [],
    pendingConfirmation: null,
    gridReturnPosition: cloneDefaultGridReturnPosition(),
  }
}

export function workspaceSessionReducer(
  state: WorkspaceSessionState,
  action: WorkspaceSessionAction,
): WorkspaceSessionState {
  switch (action.type) {
    case 'media/loaded': {
      const mediaCount = Number.isFinite(action.count)
        ? Math.max(0, Math.floor(action.count))
        : 0
      const hasMedia = mediaCount > 0
      return {
        ...state,
        mediaMode: hasMedia ? action.mode : null,
        mediaCount,
        hasMedia,
        workflowStage: hasMedia ? 'configure' : 'upload',
        exportSafety: hasMedia ? 'unsafe' : 'safe',
      }
    }
    case 'media/cleared':
      return {
        ...state,
        mediaMode: null,
        mediaCount: 0,
        hasMedia: false,
        workflowStage: 'upload',
        leftPanelOpen: true,
        rightPanelOpen: false,
        exportSafety: 'safe',
        pendingConfirmation: null,
        gridReturnPosition: cloneDefaultGridReturnPosition(),
      }
    case 'workflow/set-stage':
      return { ...state, workflowStage: action.stage }
    case 'review/enter':
      return {
        ...state,
        workflowStage: 'review',
        leftPanelOpen: false,
        rightPanelOpen: true,
        gridReturnPosition: action.gridReturnPosition
          ? normalizeGridReturnPosition(action.gridReturnPosition)
          : state.gridReturnPosition,
      }
    case 'review/leave':
      return {
        ...state,
        workflowStage: 'run',
        leftPanelOpen: true,
        rightPanelOpen: false,
      }
    case 'panel/toggle':
      return action.panel === 'left'
        ? { ...state, leftPanelOpen: !state.leftPanelOpen }
        : { ...state, rightPanelOpen: !state.rightPanelOpen }
    case 'panel/set':
      return action.panel === 'left'
        ? { ...state, leftPanelOpen: action.open }
        : { ...state, rightPanelOpen: action.open }
    case 'panel/resize-right':
      return {
        ...state,
        rightPanelWidth: clampRightPanelWidth(action.width),
      }
    case 'export/mark-safe':
      return { ...state, exportSafety: 'safe' }
    case 'export/invalidate':
      return { ...state, exportSafety: 'unsafe' }
    case 'notification/add':
      return {
        ...state,
        notifications: [
          ...state.notifications.filter(
            (notification) => notification.id !== action.notification.id,
          ),
          action.notification,
        ],
      }
    case 'notification/dismiss':
      return {
        ...state,
        notifications: state.notifications.filter(
          (notification) => notification.id !== action.id,
        ),
      }
    case 'confirmation/request':
      return { ...state, pendingConfirmation: action.request }
    case 'confirmation/clear':
      return action.id === undefined ||
        state.pendingConfirmation?.id === action.id
        ? { ...state, pendingConfirmation: null }
        : state
    case 'grid/set-return-position':
      return {
        ...state,
        gridReturnPosition: normalizeGridReturnPosition(action.position),
      }
    default:
      return assertNever(action)
  }
}

function assertNever(value: never): never {
  throw new Error(`Unhandled workspace session action: ${String(value)}`)
}

export const workspaceSessionActions = {
  mediaLoaded: (mode: MediaMode, count: number): WorkspaceSessionAction => ({
    type: 'media/loaded',
    mode,
    count,
  }),
  mediaCleared: (): WorkspaceSessionAction => ({ type: 'media/cleared' }),
  setStage: (stage: WorkflowStage): WorkspaceSessionAction => ({
    type: 'workflow/set-stage',
    stage,
  }),
  enterReview: (
    gridReturnPosition?: GridReturnPosition,
  ): WorkspaceSessionAction => ({
    type: 'review/enter',
    ...(gridReturnPosition === undefined ? {} : { gridReturnPosition }),
  }),
  leaveReview: (): WorkspaceSessionAction => ({ type: 'review/leave' }),
  togglePanel: (panel: WorkspacePanel): WorkspaceSessionAction => ({
    type: 'panel/toggle',
    panel,
  }),
  setPanel: (panel: WorkspacePanel, open: boolean): WorkspaceSessionAction => ({
    type: 'panel/set',
    panel,
    open,
  }),
  resizeRightPanel: (width: number): WorkspaceSessionAction => ({
    type: 'panel/resize-right',
    width,
  }),
  markExportSafe: (): WorkspaceSessionAction => ({ type: 'export/mark-safe' }),
  invalidateExportSafety: (): WorkspaceSessionAction => ({
    type: 'export/invalidate',
  }),
  addNotification: (
    notification: WorkspaceNotification,
  ): WorkspaceSessionAction => ({ type: 'notification/add', notification }),
  dismissNotification: (id: string): WorkspaceSessionAction => ({
    type: 'notification/dismiss',
    id,
  }),
  requestConfirmation: (
    request: DestructiveConfirmationRequest,
  ): WorkspaceSessionAction => ({ type: 'confirmation/request', request }),
  clearConfirmation: (id?: string): WorkspaceSessionAction => ({
    type: 'confirmation/clear',
    ...(id === undefined ? {} : { id }),
  }),
  setGridReturnPosition: (
    position: GridReturnPosition,
  ): WorkspaceSessionAction => ({
    type: 'grid/set-return-position',
    position,
  }),
}

/** Media presence, rather than export safety, controls the unload warning. */
export function shouldWarnBeforeUnload(state: WorkspaceSessionState): boolean {
  return state.hasMedia || state.mediaCount > 0 || state.mediaMode !== null
}

export function handleBeforeUnload(
  state: WorkspaceSessionState,
  event: BeforeUnloadEvent,
): void {
  if (!shouldWarnBeforeUnload(state)) return
  event.preventDefault()
  event.returnValue = BEFORE_UNLOAD_MESSAGE
}

export function createBeforeUnloadHandler(
  getState: () => WorkspaceSessionState,
): (event: BeforeUnloadEvent) => void {
  return (event) => handleBeforeUnload(getState(), event)
}
