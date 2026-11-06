import { useEffect, useState } from 'react'
import { getLogInfo, getModels, getUpdate, openLogFolder, type LogInfo, type Model } from './api'
import { formatBytes } from './format'

const LINKS: [string, string, string][] = [
  ['Lute v3', 'https://github.com/LuteOrg/lute-v3', 'MIT, Copyright (c) 2023 Jeff Zohrab: the reader, parser, terms and database this app is forked from.'],
  ['Wiktionary', 'https://en.wiktionary.org', 'CC BY-SA 4.0, by the Wiktionary contributors: the entries of every dictionary pack.'],
  ['Wiktextract and kaikki.org', 'https://kaikki.org', 'Tatu Ylonen: the extracted data behind the full Wiktionary packs.'],
  ['WikDict', 'https://www.wikdict.com', 'Karl Bartel: the small packs that come with the app (CC BY-SA 4.0).'],
  ['MLX, mlx-lm, mlx-audio', 'https://github.com/ml-explore/mlx', 'Apple and contributors (MIT): run the models locally.'],
  ['Hugging Face', 'https://huggingface.co', 'Apache 2.0: download and loading of the models.'],
  ['React, Flask, SQLAlchemy and others', 'https://github.com', 'MIT, BSD and Apache 2.0: the full list is in NOTICE.md.'],
]

// Credits and licences: what Ocarina is made from, where its dictionaries come from, and the licence of each model.
export function About() {
  const [models, setModels] = useState<Model[]>([])
  const [version, setVersion] = useState('')
  const [log, setLog] = useState<LogInfo | null>(null)
  useEffect(() => {
    getModels().then(setModels, () => undefined)
    getUpdate().then((s) => setVersion(s.current), () => undefined)
    getLogInfo().then(setLog, () => undefined)
  }, [])
  return (
    <>
      <h1>About Ocarina</h1>
      <p className="muted">{version && `Version ${version}`}</p>
      <section className="ap-card general-card">
        <h2>Made from</h2>
        <p className="muted">
          Ocarina is a personal language-study app, a fork of Lute v3. It is made with the work below; thank you to everyone behind it.
        </p>
        <ul className="about-list">
          {LINKS.map(([name, url, text]) => (
            <li key={name}>
              <a href={url} target="_blank" rel="noreferrer">
                {name}
              </a>{' '}
              <span className="muted">{text}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="ap-card general-card">
        <h2>Dictionaries</h2>
        <p className="muted">
          The dictionary packs are made from Wiktionary and are shared under CC BY-SA 4.0 (
          <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">
            licence
          </a>
          ). Ocarina converted them into its own file format and changed nothing else of their meaning; the converted packs stay under the same licence. Each pack
          lists its source and licence under Settings → Dictionaries.
        </p>
      </section>
      <section className="ap-card general-card">
        <h2>Models</h2>
        <p className="muted">Models are downloaded by you from Hugging Face and keep the licence of their authors.</p>
        <ul className="about-list">
          {models.map((m) => (
            <li key={m.id}>
              {m.name} <span className="muted">· {m.license}</span>
            </li>
          ))}
        </ul>
        <p className="muted">Gemma is provided under and subject to the Gemma Terms of Use, ai.google.dev/gemma/terms.</p>
      </section>
      <section className="ap-card general-card">
        <h2>If something goes wrong</h2>
        <p className="muted">
          Ocarina keeps a log of what it does and of its errors{log ? ` (${formatBytes(log.bytes)})` : ''}. Send it with a description of what happened. It holds file locations, versions and error messages,
          not the texts you read; look it over first.
        </p>
        <p>
          <button className="secondary" onClick={() => openLogFolder().catch(() => undefined)}>
            Open the log folder
          </button>
        </p>
      </section>
      <p className="muted">The full text of these credits is in NOTICE.md, next to LICENSE.txt, inside the app and in the project.</p>
    </>
  )
}
