import type { ReactNode } from 'react'

export interface FormFieldProps {
  controlId: string
  id?: string
  label: ReactNode
  children: ReactNode
  hint?: ReactNode
  className?: string
  hidden?: boolean
}

export function FormField({
  controlId,
  id,
  label,
  children,
  hint,
  className,
  hidden,
}: FormFieldProps) {
  return (
    <div
      id={id}
      className={`field${className ? ` ${className}` : ''}`}
      hidden={hidden}
    >
      <label htmlFor={controlId}>{label}</label>
      {children}
      {hint !== undefined && <small className="hint">{hint}</small>}
    </div>
  )
}
