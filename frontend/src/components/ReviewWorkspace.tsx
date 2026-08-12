import { useState } from 'react'
import type { ImageEntry } from '../types'
import { ReviewEditor } from './ReviewEditor'
import { ReviewOverview } from './ReviewOverview'

interface ReviewWorkspaceProps {
  entries: readonly ImageEntry[]
  onEntriesChange: (entries: ImageEntry[]) => void
  onStatus: (message: string, error?: boolean) => void
}

export function ReviewWorkspace({
  entries,
  onEntriesChange,
  onStatus,
}: ReviewWorkspaceProps) {
  const [editorEntryId, setEditorEntryId] = useState<string | null>(null)
  const editorEntry = entries.find((entry) => entry.id === editorEntryId)

  const replaceEntry = (updated: ImageEntry) => {
    onEntriesChange(
      entries.map((entry) =>
        entry.id === updated.id ? updated : entry,
      ),
    )
  }

  return (
    <>
      <div hidden={Boolean(editorEntry)}>
        <ReviewOverview
          entries={entries}
          onEntriesChange={onEntriesChange}
          onOpen={setEditorEntryId}
          onStatus={(message) => onStatus(message)}
        />
      </div>
      {editorEntry && (
        <ReviewEditor
          key={editorEntry.id}
          entry={editorEntry}
          entries={entries}
          onEntryChange={replaceEntry}
          onOpen={setEditorEntryId}
          onBack={() => setEditorEntryId(null)}
          onStatus={onStatus}
        />
      )}
    </>
  )
}
