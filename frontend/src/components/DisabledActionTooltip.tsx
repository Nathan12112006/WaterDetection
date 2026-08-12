import { useEffect, useState } from 'react'

interface TooltipState {
  text: string
  left: number
  top: number
}

export function DisabledActionTooltip() {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const directTarget =
        event.target instanceof Element
          ? event.target.closest<HTMLButtonElement>(
              'button:disabled[data-disabled-reason]',
            )
          : null
      const hovered =
        directTarget ??
        document
          .elementFromPoint(event.clientX, event.clientY)
          ?.closest<HTMLButtonElement>(
            'button:disabled[data-disabled-reason]',
          )
      const text = hovered?.dataset.disabledReason
      if (!text) {
        setTooltip(null)
        return
      }
      setTooltip({
        text,
        left: Math.min(event.clientX + 14, window.innerWidth - 280),
        top: Math.min(event.clientY + 14, window.innerHeight - 60),
      })
    }
    const hide = () => setTooltip(null)
    document.addEventListener('pointermove', handlePointerMove)
    document.documentElement.addEventListener('pointerleave', hide)
    return () => {
      document.removeEventListener('pointermove', handlePointerMove)
      document.documentElement.removeEventListener('pointerleave', hide)
    }
  }, [])

  return (
    <div
      id="disabled-action-tooltip"
      className="disabled-action-tooltip"
      role="tooltip"
      hidden={!tooltip}
      style={
        tooltip
          ? { left: tooltip.left, top: tooltip.top }
          : undefined
      }
    >
      {tooltip?.text}
    </div>
  )
}

