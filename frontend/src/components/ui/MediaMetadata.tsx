interface FileNameProps {
  name: string
}

export function FileName({ name }: FileNameProps) {
  return (
    <span className="filename" title={name}>
      {name}
    </span>
  )
}

interface EditedBadgeProps {
  edited: boolean
}

export function EditedBadge({ edited }: EditedBadgeProps) {
  if (!edited) return null

  return (
    <span
      className="edited-badge"
      title="Annotations changed during review"
    >
      ✓ Edited
    </span>
  )
}
