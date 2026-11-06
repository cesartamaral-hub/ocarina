import { useEffect } from 'react'
import { setPref } from './api'
import { AddLanguagesPage } from './AddLanguagesPage'
import { Appearance } from './Appearance'
import { About } from './About'
import { Backups } from './Backups'
import { LanguageEditor, LanguageList } from './Languages'
import { Settings } from './Settings'
import { GROUPS, SECTIONS, sectionHash, type SectionId } from './settingsRoutes'
import { Shortcuts } from './Shortcuts'
import { Storage } from './Storage'
import { Tags } from './Tags'
import { Dictionaries } from './Dictionaries'
import { General } from './General'
import { Translation } from './Translation'
import { loadUpdate, useUpdate } from './updateStore'

function Content({ section, rest }: { section: SectionId; rest: string }) {
  switch (section) {
    case 'appearance':
      return <Appearance />
    case 'shortcuts':
      return <Shortcuts />
    case 'general':
      return <General />
    case 'languages':
      if (rest === 'add') return <AddLanguagesPage />
      return rest === '' ? <LanguageList /> : <LanguageEditor key={rest} languageId={rest === 'new' ? null : Number(rest)} />
    case 'tags':
      return <Tags />
    case 'dictionaries':
      return <Dictionaries />
    case 'models':
      return <Settings part="models" />
    case 'voices':
      return <Settings part="voices" />
    case 'translation':
      return <Translation />
    case 'backups':
      return <Backups />
    case 'storage':
      return <Storage />
    case 'about':
      return <About />
  }
}

// Settings: a list of sections on the left, the chosen one on the right. Settings alone opens the section you were last in.
export function SettingsShell({ section, rest }: { section: SectionId; rest: string }) {
  const { available } = useUpdate()
  useEffect(() => {
    setPref('settings.section', section)
  }, [section])
  useEffect(() => {
    loadUpdate()
  }, [])
  return (
    <div className="settings-shell">
      <nav className="settings-nav" aria-label="Settings sections">
        {GROUPS.map((group) => (
          <div key={group} className="settings-group">
            {group && <h2>{group}</h2>}
            <ul>
              {SECTIONS.filter((s) => s.group === group).map((s) => (
                <li key={s.id}>
                  <a href={sectionHash(s.id)} aria-current={s.id === section ? 'page' : undefined}>
                    {s.label}
                    {s.id === 'general' && available && (
                      <span className="nav-alert" role="img" aria-label="An update is available" title="An update is available">
                        !
                      </span>
                    )}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="settings-content">
        <Content section={section} rest={rest} />
      </div>
    </div>
  )
}
