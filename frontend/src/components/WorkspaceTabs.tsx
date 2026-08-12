import type { MediaMode, WorkspaceTab } from '../types'
import { ActionButton } from './ui/ActionButton'

interface WorkspaceTabsProps {
  activeTab: WorkspaceTab
  mediaMode: MediaMode | null
  reviewEnabled: boolean
  onTabChange: (tab: WorkspaceTab) => void
}

export function WorkspaceTabs({
  activeTab,
  mediaMode,
  reviewEnabled,
  onTabChange,
}: WorkspaceTabsProps) {
  const reviewDisabledReason = 'Run image detection before reviewing annotations.'

  return (
    <div className="stage-heading">
      <div
        className="stage-tabs"
        role="tablist"
        aria-label="Image workspace"
      >
        <ActionButton
          id="preview-tab"
          className={`stage-tab${activeTab === 'preview' ? ' active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'preview'}
          onClick={() => onTabChange('preview')}
        >
          Detection preview
        </ActionButton>
        <ActionButton
          id="review-tab"
          className={`stage-tab${activeTab === 'review' ? ' active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'review'}
          disabled={!reviewEnabled}
          disabledReason={reviewDisabledReason}
          onClick={() => onTabChange('review')}
        >
          Review annotations
        </ActionButton>
      </div>
      <span className="stage-badge">
        {mediaMode === 'images'
          ? 'Images'
          : mediaMode === 'video'
            ? 'Video'
            : 'Ready'}
      </span>
    </div>
  )
}
