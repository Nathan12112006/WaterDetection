import { describe, expect, it } from 'vitest'
import {
  BEFORE_UNLOAD_MESSAGE,
  DEFAULT_GRID_RETURN_POSITION,
  RIGHT_PANEL_DEFAULT_WIDTH,
  RIGHT_PANEL_MAX_WIDTH,
  RIGHT_PANEL_MIN_WIDTH,
  createBeforeUnloadHandler,
  createInitialWorkspaceSession,
  shouldWarnBeforeUnload,
  workspaceSessionActions,
  workspaceSessionReducer,
} from './workspaceSession'

describe('workspace session defaults', () => {
  it('starts as an empty grid with the left setup panel open', () => {
    const state = createInitialWorkspaceSession()

    expect(state).toMatchObject({
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
      gridReturnPosition: DEFAULT_GRID_RETURN_POSITION,
    })
  })

  it('normalizes invalid media counts to an empty media state', () => {
    const initial = createInitialWorkspaceSession()
    const invalid = workspaceSessionReducer(
      initial,
      workspaceSessionActions.mediaLoaded('images', Number.NaN),
    )
    const negative = workspaceSessionReducer(
      initial,
      workspaceSessionActions.mediaLoaded('images', -3),
    )

    expect(invalid).toMatchObject({
      mediaMode: null,
      mediaCount: 0,
      hasMedia: false,
      workflowStage: 'upload',
      exportSafety: 'safe',
    })
    expect(negative.mediaCount).toBe(0)
  })
})

describe('review panel transitions', () => {
  it('collapses setup and opens the inspector on entry, then restores grid panels', () => {
    const initial = createInitialWorkspaceSession()
    const entered = workspaceSessionReducer(
      initial,
      workspaceSessionActions.enterReview({
        scrollTop: 180,
        focusedImageId: 'image-2',
      }),
    )

    expect(entered).toMatchObject({
      workflowStage: 'review',
      leftPanelOpen: false,
      rightPanelOpen: true,
      gridReturnPosition: {
        scrollTop: 180,
        focusedImageId: 'image-2',
      },
    })

    const left = workspaceSessionReducer(
      entered,
      workspaceSessionActions.leaveReview(),
    )
    expect(left).toMatchObject({
      workflowStage: 'run',
      leftPanelOpen: true,
      rightPanelOpen: false,
      gridReturnPosition: entered.gridReturnPosition,
    })
  })
})

describe('right inspector resizing', () => {
  it('clamps widths to the supported bounds', () => {
    const initial = createInitialWorkspaceSession()
    const tooSmall = workspaceSessionReducer(
      initial,
      workspaceSessionActions.resizeRightPanel(RIGHT_PANEL_MIN_WIDTH - 1),
    )
    const tooLarge = workspaceSessionReducer(
      initial,
      workspaceSessionActions.resizeRightPanel(RIGHT_PANEL_MAX_WIDTH + 1),
    )

    expect(tooSmall.rightPanelWidth).toBe(RIGHT_PANEL_MIN_WIDTH)
    expect(tooLarge.rightPanelWidth).toBe(RIGHT_PANEL_MAX_WIDTH)
  })
})

describe('media-loaded unload guard', () => {
  it('warns for loaded media even after export marks the state safe', () => {
    let state = createInitialWorkspaceSession()
    const handler = createBeforeUnloadHandler(() => state)
    const emptyEvent = new Event('beforeunload', { cancelable: true })
    handler(emptyEvent)
    expect(shouldWarnBeforeUnload(state)).toBe(false)
    expect(emptyEvent.defaultPrevented).toBe(false)

    state = workspaceSessionReducer(
      state,
      workspaceSessionActions.mediaLoaded('images', 2),
    )
    state = workspaceSessionReducer(
      state,
      workspaceSessionActions.markExportSafe(),
    )
    const loadedEvent = new Event('beforeunload', { cancelable: true })
    handler(loadedEvent)

    expect(state.exportSafety).toBe('safe')
    expect(shouldWarnBeforeUnload(state)).toBe(true)
    expect(loadedEvent.defaultPrevented).toBe(true)
    // jsdom normalizes returnValue to false after preventDefault; the browser
    // still uses the assigned message when presenting its native prompt.
    expect(BEFORE_UNLOAD_MESSAGE).toContain('loaded media')

    state = workspaceSessionReducer(
      state,
      workspaceSessionActions.mediaCleared(),
    )
    const clearedEvent = new Event('beforeunload', { cancelable: true })
    handler(clearedEvent)
    expect(shouldWarnBeforeUnload(state)).toBe(false)
    expect(clearedEvent.defaultPrevented).toBe(false)
  })
})
