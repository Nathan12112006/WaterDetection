import type {
  ButtonHTMLAttributes,
  ReactNode,
} from 'react'

export interface ActionButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  type?: 'button' | 'submit' | 'reset'
  disabledReason?: string
  busy?: boolean
  busyLabel?: ReactNode
}

export function ActionButton({
  type = 'button',
  disabled,
  disabledReason,
  busy = false,
  busyLabel,
  children,
  ...buttonProps
}: ActionButtonProps) {
  const unavailable = disabled === true || busy

  return (
    <button
      {...buttonProps}
      type={type}
      disabled={unavailable}
      data-disabled-reason={
        unavailable && !busy ? disabledReason : undefined
      }
      aria-busy={busy || undefined}
    >
      {busy && busyLabel !== undefined ? busyLabel : children}
    </button>
  )
}
