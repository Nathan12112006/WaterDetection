import type { MediaMode } from '../types'

interface AppHeaderProps {
  mediaMode: MediaMode | null
  imageCount: number
  processing: boolean
}

function workspaceLabel(
  mediaMode: MediaMode | null,
  imageCount: number,
): string {
  if (mediaMode === 'video') return '1 video loaded'
  if (mediaMode === 'images') {
    return `${imageCount} image${imageCount === 1 ? '' : 's'} loaded`
  }
  return 'Ready for media'
}

export function AppHeader({
  mediaMode,
  imageCount,
  processing,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M12 2.8S5.8 9.3 5.8 14a6.2 6.2 0 0 0 12.4 0C18.2 9.3 12 2.8 12 2.8Z" />
            <path d="M9 15.1a3.3 3.3 0 0 0 2.8 1.8" />
          </svg>
        </div>
        <div>
          <p className="eyebrow">Local vision workspace</p>
          <h1>Water Leaking Detector</h1>
          <p className="header-description">
            Detect, compare, and refine water-leak annotations without
            sending media outside this service.
          </p>
        </div>
      </div>
      <div className="header-actions">
        <div className="workspace-state" aria-live="polite">
          <span className={`state-dot${processing ? ' processing' : ''}`} />
          {processing ? 'Analyzing media' : workspaceLabel(mediaMode, imageCount)}
        </div>
        <a className="docs-link" href="/docs">
          API docs <span aria-hidden="true">↗</span>
        </a>
      </div>
    </header>
  )
}
