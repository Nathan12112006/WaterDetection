import {
  useEffect,
  useRef,
  type CSSProperties,
  type PointerEvent,
  type ReactNode,
} from 'react'
import {
  RIGHT_PANEL_MAX_WIDTH,
  RIGHT_PANEL_MIN_WIDTH,
} from '../lib/workspaceSession'

interface WorkspaceShellProps {
  leftOpen: boolean
  rightOpen: boolean
  rightWidth: number
  onToggleLeft: () => void
  onToggleRight: () => void
  onResizeRight: (width: number) => void
  left: ReactNode
  center: ReactNode
  right: ReactNode
}

function clampWidth(width: number): number {
  return Math.min(
    RIGHT_PANEL_MAX_WIDTH,
    Math.max(RIGHT_PANEL_MIN_WIDTH, Math.round(width)),
  )
}

export function WorkspaceShell({
  leftOpen,
  rightOpen,
  rightWidth,
  onToggleLeft,
  onToggleRight,
  onResizeRight,
  left,
  center,
  right,
}: WorkspaceShellProps) {
  const resizeRef = useRef<{
    startX: number
    startWidth: number
  } | null>(null)

  useEffect(() => {
    const handleMove = (event: globalThis.PointerEvent) => {
      const resize = resizeRef.current
      if (!resize) return
      onResizeRight(resize.startWidth + resize.startX - event.clientX)
    }
    const handleUp = () => {
      resizeRef.current = null
      document.body.classList.remove('workspace-resizing')
    }
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
    return () => {
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
      document.body.classList.remove('workspace-resizing')
    }
  }, [onResizeRight])

  const startResize = (event: PointerEvent<HTMLDivElement>) => {
    if (!rightOpen) return
    event.preventDefault()
    resizeRef.current = { startX: event.clientX, startWidth: rightWidth }
    document.body.classList.add('workspace-resizing')
  }

  const resizeByKeyboard = (delta: number) => {
    if (rightOpen) onResizeRight(clampWidth(rightWidth + delta))
  }

  return (
    <div
      className={`workspace-shell${leftOpen ? '' : ' left-collapsed'}${rightOpen ? '' : ' right-collapsed'}`}
      style={{ '--inspector-width': `${rightWidth}px` } as CSSProperties}
    >
      <aside
        className="workspace-panel workspace-left-panel"
        aria-label="Detection setup"
      >
        <div className="workspace-panel-content" aria-hidden={!leftOpen}>
          {left}
        </div>
        <button
          type="button"
          className="workspace-panel-toggle workspace-left-toggle"
          aria-label={leftOpen ? 'Collapse setup panel' : 'Expand setup panel'}
          aria-expanded={leftOpen}
          onClick={onToggleLeft}
        >
          <span aria-hidden="true">{leftOpen ? '‹' : '›'}</span>
        </button>
      </aside>

      <section className="workspace-center" aria-label="Main workspace">
        {center}
      </section>

      <aside
        className="workspace-panel workspace-right-panel"
        aria-label="Inspector"
      >
        {rightOpen && (
          <div
            className="workspace-resize-handle"
            role="separator"
            aria-label="Resize inspector"
            aria-orientation="vertical"
            aria-valuemin={RIGHT_PANEL_MIN_WIDTH}
            aria-valuemax={RIGHT_PANEL_MAX_WIDTH}
            aria-valuenow={rightWidth}
            tabIndex={0}
            onPointerDown={startResize}
            onKeyDown={(event) => {
              if (event.key === 'ArrowLeft') {
                event.preventDefault()
                resizeByKeyboard(16)
              } else if (event.key === 'ArrowRight') {
                event.preventDefault()
                resizeByKeyboard(-16)
              }
            }}
          />
        )}
        <div className="workspace-panel-content" aria-hidden={!rightOpen}>
          {rightOpen && right}
        </div>
        <button
          type="button"
          className="workspace-panel-toggle workspace-right-toggle"
          aria-label={rightOpen ? 'Collapse inspector' : 'Expand inspector'}
          aria-expanded={rightOpen}
          onClick={onToggleRight}
        >
          <span aria-hidden="true">{rightOpen ? '›' : '‹'}</span>
        </button>
      </aside>
    </div>
  )
}
