import { useCallback, useEffect, useState } from 'react'
import { changeTag, deleteTag, getTagList, type TagKind, type TagRow } from './api'

function TagRowEditor({ kind, tag, onChanged }: { kind: TagKind; tag: TagRow; onChanged: () => void }) {
  const [text, setText] = useState(tag.text)
  const [comment, setComment] = useState(tag.comment)
  const [error, setError] = useState('')
  const dirty = text !== tag.text || comment !== tag.comment

  async function save() {
    setError('')
    try {
      await changeTag(kind, tag.id, { text, comment })
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function remove() {
    const used = tag.uses > 0 ? ` It is taken off the ${tag.uses} ${kind === 'term' ? 'terms' : 'books'} that use it.` : ''
    if (!window.confirm(`Delete the tag "${tag.text}"?${used}`)) return
    try {
      await deleteTag(kind, tag.id)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <tr>
      <td>
        <input value={text} maxLength={20} onChange={(e) => setText(e.target.value)} aria-label="Tag name" />
      </td>
      <td>
        <input className="wide" value={comment} maxLength={200} onChange={(e) => setComment(e.target.value)} aria-label="Comment" />
      </td>
      <td className="muted">{tag.uses}</td>
      <td className="row-inline">
        <button disabled={!dirty || !text.trim()} onClick={save}>
          Save
        </button>
        <button className="danger" onClick={remove}>
          Delete
        </button>
        {error && <span className="error">{error}</span>}
      </td>
    </tr>
  )
}

function TagTable({ kind, title }: { kind: TagKind; title: string }) {
  const [tags, setTags] = useState<TagRow[] | null>(null)
  const [error, setError] = useState('')
  const load = useCallback(() => getTagList(kind).then(setTags, (e) => setError(e.message)), [kind])
  useEffect(() => {
    load()
  }, [load])
  return (
    <>
      <h2>{title}</h2>
      {error && <p className="error">{error}</p>}
      {!tags ? null : tags.length === 0 ? (
        <p className="muted">No tags yet. Add one when you edit a {kind}.</p>
      ) : (
        <table className="dicts tags">
          <thead>
            <tr>
              <th>Tag</th>
              <th>Comment</th>
              <th>Used</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {tags.map((t) => (
              <TagRowEditor key={`${t.id}:${t.text}:${t.comment}`} kind={kind} tag={t} onChanged={load} />
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

export function Tags() {
  return (
    <>
      <p>
        <a href="#/settings">← Settings</a>
      </p>
      <h1>Tags</h1>
      <TagTable kind="term" title="Term tags" />
      <TagTable kind="book" title="Book tags" />
    </>
  )
}
