import { useOffline } from './offline'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelJob,
  chooseDictionaries,
  deleteDictionary,
  downloadDictionary,
  getDictionaries,
  getJob,
  importDictionary,
  isActive,
  type DictionaryList,
  type DictionaryPack,
  type Job,
} from './api'
import { formatBytes } from './format'
import { notify } from './notices'
import { TransferProgress } from './TransferProgress'

const BIN = (
  <path d="M3.5 4.5h9M6.5 4.5V3h3v1.5M5 4.5l.5 8h5l.5-8M7 7v3.5M9 7v3.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
)
const KIND: Record<string, string> = { builtin: 'Comes with Ocarina', wiktionary: 'Wiktionary', stardict: 'Added by you' }

// The dictionaries on this Mac: which are on and in what order they are asked, more to download, and your own to add.
export function Dictionaries() {
  const offline = useOffline()
  const [data, setData] = useState<DictionaryList | null>(null)
  const [error, setError] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [language, setLanguage] = useState('')
  const [name, setName] = useState('')
  const [sameLanguage, setSameLanguage] = useState(false) // the dictionary being added explains words in their own language
  const files = useRef<HTMLInputElement>(null)
  const [chosen, setChosen] = useState<File[]>([])

  const load = useCallback(() => getDictionaries().then(setData, (e) => setError(e.message)), [])
  useEffect(() => {
    load()
  }, [load])

  // A download or an import is followed until it ends.
  const jobId = isActive(job) ? job!.id : null
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      const j = await getJob(jobId).catch(() => null)
      if (!j) return
      setJob(j)
      if (!isActive(j)) {
        if (j.state === 'error') setError(j.error ?? 'It did not work.')
        if (j.state === 'done') notify(`${j.title ?? 'The dictionary'} is ready`)
        load()
      }
    }, 800)
    return () => clearInterval(timer)
  }, [jobId, load])

  async function act(work: Promise<unknown>) {
    setError('')
    try {
      await work
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // Moving a pack swaps it with the next pack of the same language (the order is asked per language).
  function move(pack: DictionaryPack, by: -1 | 1) {
    if (!data) return
    const ids = data.packs.map((p) => p.id)
    const same = data.packs.filter((p) => p.language === pack.language).map((p) => p.id)
    const at = same.indexOf(pack.id)
    const other = same[at + by]
    if (other === undefined) return
    const a = ids.indexOf(pack.id)
    const b = ids.indexOf(other)
    ;[ids[a], ids[b]] = [ids[b], ids[a]]
    act(chooseDictionaries({ order: ids }))
  }

  const toggle = (pack: DictionaryPack) => act(chooseDictionaries({ off: data!.packs.filter((p) => (p.id === pack.id ? pack.on : !p.on)).map((p) => p.id) }))

  async function remove(pack: DictionaryPack) {
    if (!window.confirm(`Delete ${pack.name} (${formatBytes(pack.bytes)})? You can add or download it again.`)) return
    act(deleteDictionary(pack.id))
  }

  async function add() {
    setError('')
    try {
      setJob(await importDictionary(chosen, chosenLanguage, name, sameLanguage ? chosenLanguage : 'en'))
      setChosen([])
      setName('')
      if (files.current) files.current.value = ''
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!data) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>
  const code = (c: string) => c.toUpperCase()
  const chosenLanguage = language || data.languages[0]?.code || ''
  const todo = data.available.filter((a) => !a.installed || job?.pack_id === a.id) // what is on this Mac is listed above
  const busy = isActive(job)
  return (
    <>
      <h1>Dictionaries</h1>
      <p className="muted">
        When you open a word, these dictionaries are asked in this order, and the first that knows it answers; the others that know it are listed under it. They work without
        internet. Wiktionary over the internet is only asked when none of them has the word.
      </p>
      {error && <p className="error">{error}</p>}

      <h2>On this Mac</h2>
      <div className="model-list dict-list">
        <ul>
          {data.packs.map((p) => {
            const same = data.packs.filter((x) => x.language === p.language)
            const at = same.findIndex((x) => x.id === p.id)
            return (
              <li key={p.id} className={`model-row dict-row${p.on ? '' : ' off'}`}>
                <div className="dict-main">
                  <span className="dict-order">
                    <button className="quiet small icon" aria-label={`Ask ${p.name} earlier`} title="Ask it earlier" disabled={at === 0 || busy} onClick={() => move(p, -1)}>
                      ▲
                    </button>
                    <button className="quiet small icon" aria-label={`Ask ${p.name} later`} title="Ask it later" disabled={at === same.length - 1 || busy} onClick={() => move(p, 1)}>
                      ▼
                    </button>
                  </span>
                  <div className="dict-text">
                    <div className="mr-name">
                      <span className="name">{p.name}</span>
                      <span className="lang-chip">{code(p.language)}</span>
                      <span className="muted mr-note">{p.meaning === p.language ? 'explained in the language itself' : `→ ${code(p.meaning)}`}</span>
                    </div>
                    <div className="muted mr-desc">
                      {KIND[p.kind] ?? p.kind} · {p.entries.toLocaleString()} entries · {formatBytes(p.bytes)} · {p.license}
                    </div>
                  </div>
                  <label className="dict-switch" title={p.on ? 'On: it is asked' : 'Off: it is not asked'}>
                    <input type="checkbox" checked={p.on} disabled={busy} onChange={() => toggle(p)} aria-label={`${p.name} is ${p.on ? 'on' : 'off'}`} />
                    <span>{p.on ? 'On' : 'Off'}</span>
                  </label>
                  {p.removable ? (
                    <button className="quiet small icon mr-bin" aria-label={`Delete ${p.name}`} title="Delete" disabled={busy} onClick={() => remove(p)}>
                      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                        {BIN}
                      </svg>
                    </button>
                  ) : (
                    <span />
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </div>

      <h2>More dictionaries</h2>
      <p className="muted">
        For each language of your library. The small WikDict ones are quick and have the English words for each meaning. The full Wiktionary has what they leave out: example sentences, and the
        inflected forms, so a form you meet in a text leads to its base word. The ones <em>in the language itself</em> (Dutch words explained in Dutch, and so on) are for when English meanings are not
        enough. A dictionary is downloaded compressed and made on this Mac as it arrives, which takes about a minute.
      </p>
      {todo.length === 0 && <p className="muted">Everything there is for your languages is on this Mac.</p>}
      {[...new Set(todo.map((a) => a.languageName))].map((lang) => (
        <div key={lang}>
          <h3 className="dict-language">{lang}</h3>
          <div className="model-list dict-list">
            <ul>
              {todo
                .filter((a) => a.languageName === lang)
                .map((a) => {
                  const mine = job?.pack_id === a.id ? job : null
                  const running = mine !== null && isActive(mine)
                  return (
                    <li key={a.id} className="model-row dict-row">
                      <div className="dict-main">
                        <span />
                        <div className="dict-text">
                          <div className="mr-name">
                            <span className="name">{a.name}</span>
                            <span className="lang-chip">{code(a.language)}</span>
                            <span className="muted mr-note">{a.meaning === a.language ? 'in the language itself' : '→ EN'}</span>
                          </div>
                          <div className="muted mr-desc">{a.description}</div>
                        </div>
                        <span className="muted dict-size">{a.installed ? '' : `${formatBytes(a.download)} to download`}</span>
                        {a.installed ? (
                          <span className="muted">Installed</span>
                        ) : (
                          <button disabled={busy || running || offline} title={offline ? 'Needs the internet (Work offline is on)' : undefined} onClick={() => act(downloadDictionary(a.id).then(setJob))}>
                            Download
                          </button>
                        )}
                      </div>
                      {running && mine && <TransferProgress job={mine} speed={0} onCancel={() => cancelJob(mine.id).then(setJob, () => undefined)} />}
                    </li>
                  )
                })}
            </ul>
          </div>
        </div>
      ))}

      <h2>Add your own</h2>
      <p className="muted">
        A StarDict dictionary: its three files (<code>.ifo</code>, <code>.idx</code> and <code>.dict</code> or <code>.dict.dz</code>), or one <code>.zip</code> or <code>.tar.gz</code> of them. Free ones
        are on the sites of <a href="https://www.wikdict.com/page/download" target="_blank" rel="noreferrer">WikDict</a> and <a href="https://freedict.org/downloads/" target="_blank" rel="noreferrer">FreeDict</a>.
      </p>
      <div className="form dict-add">
        <label>
          Language
          <select value={chosenLanguage} onChange={(e) => setLanguage(e.target.value)}>
            {data.languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Name (optional)
          <input value={name} placeholder="the dictionary's own name" onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="inline">
          <input type="checkbox" checked={sameLanguage} onChange={(e) => setSameLanguage(e.target.checked)} />
          The meanings are in the language itself (not English)
        </label>
        <label>
          Files
          <input ref={files} type="file" multiple disabled={busy} onChange={(e) => setChosen([...(e.target.files ?? [])])} />
        </label>
        <div>
          <button disabled={busy || chosen.length === 0 || !chosenLanguage} onClick={add}>
            Add dictionary
          </button>
        </div>
        {busy && job && !job.pack_id && <p className="muted">Reading the dictionary…</p>}
      </div>
    </>
  )
}
