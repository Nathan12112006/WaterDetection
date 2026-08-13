import { useState } from 'react'
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
  const [helpOpen, setHelpOpen] = useState(false)

  return (
    <header className="app-header" data-testid="workspace-header">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M12 2.8S5.8 9.3 5.8 14a6.2 6.2 0 0 0 12.4 0C18.2 9.3 12 2.8 12 2.8Z" />
            <path d="M9 15.1a3.3 3.3 0 0 0 2.8 1.8" />
          </svg>
        </div>
        <div>
          <p className="eyebrow">Local vision workspace</p>
          <h1>Water Detection Workspace</h1>
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
        <button
          type="button"
          className="help-button"
          aria-haspopup="dialog"
          aria-expanded={helpOpen}
          onClick={() => setHelpOpen((open) => !open)}
        >
          Help / About
        </button>
      </div>
      {helpOpen && (
        <div className="help-popover" role="dialog" aria-label="Help and About">
          <div className="help-popover-heading">
            <strong>Water Detection Workspace</strong>
            <button
              type="button"
              className="help-close"
              aria-label="Close Help / About"
              onClick={() => setHelpOpen(false)}
            >
              ×
            </button>
          </div>
          <p>
            Upload media, configure detection, review results, and export the
            current workspace without leaving this session.
          </p>
          <a className="docs-link" href="/docs">
            API documentation <span aria-hidden="true">→</span>
          </a>
        </div>
      )}
    </header>
  )
}
