import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: ReactNode
  children: ReactNode
  icon?: ReactNode
  id?: string
  className?: string
}

export function EmptyState({
  title,
  children,
  icon,
  id,
  className,
}: EmptyStateProps) {
  return (
    <div
      id={id}
      className={`empty${className ? ` ${className}` : ''}`}
    >
      <div>
        {icon}
        <strong>{title}</strong>
        {children}
      </div>
    </div>
  )
}
