import type { WorkflowStage } from '../types'

const WORKFLOW_STAGES: readonly WorkflowStage[] = [
  'upload',
  'configure',
  'run',
  'review',
  'export',
]

const STAGE_LABELS: Record<WorkflowStage, string> = {
  upload: 'Upload',
  configure: 'Configure',
  run: 'Run',
  review: 'Review',
  export: 'Export',
}

interface WorkflowStageBarProps {
  activeStage: WorkflowStage
  reviewAvailable?: boolean
  onStageSelect?: (stage: WorkflowStage) => void
}

export function WorkflowStageBar({
  activeStage,
  reviewAvailable = true,
  onStageSelect,
}: WorkflowStageBarProps) {
  const activeIndex = WORKFLOW_STAGES.indexOf(activeStage)

  return (
    <nav className="workflow-stage-bar" aria-label="Workspace workflow">
      {WORKFLOW_STAGES.map((stage, index) => {
        const isActive = stage === activeStage
        const isComplete = index < activeIndex
        const isUnavailable = stage === 'review' && !reviewAvailable
        return (
          <button
            key={stage}
            type="button"
            className={`workflow-stage${isActive ? ' active' : ''}${isComplete ? ' complete' : ''}`}
            aria-current={isActive ? 'step' : undefined}
            aria-disabled={isUnavailable || undefined}
            disabled={isUnavailable}
            onClick={() => onStageSelect?.(stage)}
          >
            <span className="workflow-stage-index" aria-hidden="true">
              {isComplete ? '✓' : index + 1}
            </span>
            <span>{STAGE_LABELS[stage]}</span>
          </button>
        )
      })}
    </nav>
  )
}
