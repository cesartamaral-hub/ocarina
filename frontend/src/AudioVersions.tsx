import { useEffect, useState } from 'react'
import { deleteAudioVersion, getAudioVersions, renameAudioVersion, selectAudioVersion, type AudioVersion } from './api'
import { notify } from './notices'

const kindLabel = (v: AudioVersion) => (v.kind === 'own' ? 'your recording' : 'generated')

// The audio versions of a book: pick which one plays. With compact = true only the picker is shown
// (the reader); otherwise the selected version can also be renamed or deleted.
export function AudioVersions({
  bookId,
  refreshKey,
  compact = false,
  disabled = false,
  onChanged,
}: {
  bookId: number
  refreshKey: number // changes when a version was added elsewhere (a finished generation)
  compact?: boolean
  disabled?: boolean
  onChanged: () => void
}) {
  const [versions, setVersions] = useState<AudioVersion[]>([])
  const [renaming, setRenaming] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getAudioVersions(bookId).then(setVersions, (e) => setError(e.message))
  }, [bookId, refreshKey])

  const current = versions.find((v) => v.selected)
  if (versions.length === 0) return null

  async function run(work: Promise<AudioVersion[]>, message?: string) {
    setError('')
    try {
      setVersions(await work)
      if (message) notify(message)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  async function remove(v: AudioVersion) {
    const what =
      v.kind === 'own'
        ? `Remove “${v.label}” from this book? The recording itself stays in your audio folder.`
        : `Delete “${v.label}”? The generated audio file is deleted; you can generate it again.`
    if (!window.confirm(what)) return
    setError('')
    try {
      const result = await deleteAudioVersion(bookId, v.id)
      setVersions(result.versions)
      notify(`“${v.label}” removed`)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="audio-versions">
      <label className="inline">
        <span className="muted">Audio</span>
        {versions.length > 1 ? (
          <select
            value={current?.id ?? ''}
            disabled={disabled}
            aria-label="Which audio to play"
            onChange={(e) => run(selectAudioVersion(bookId, Number(e.target.value)))}
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label} ({kindLabel(v)})
              </option>
            ))}
          </select>
        ) : (
          <strong>
            {current?.label} <span className="muted">({current ? kindLabel(current) : ''})</span>
          </strong>
        )}
      </label>
      {!compact && current && renaming === null && (
        <span className="row-actions">
          <button className="secondary" disabled={disabled} onClick={() => setRenaming(current.label)}>
            Rename
          </button>
          <button className="secondary" disabled={disabled} onClick={() => remove(current)}>
            Delete
          </button>
        </span>
      )}
      {!compact && current && renaming !== null && (
        <form
          className="row-actions"
          onSubmit={(e) => {
            e.preventDefault()
            if (renaming.trim()) run(renameAudioVersion(bookId, current.id, renaming.trim()))
            setRenaming(null)
          }}
        >
          <input value={renaming} maxLength={100} autoFocus aria-label="New name" onChange={(e) => setRenaming(e.target.value)} />
          <button disabled={!renaming.trim()}>Save</button>
          <button type="button" className="secondary" onClick={() => setRenaming(null)}>
            Cancel
          </button>
        </form>
      )}
      {current?.missing && <span className="error">The audio file is missing from your audio folder.</span>}
      {error && <span className="error">{error}</span>}
    </div>
  )
}
