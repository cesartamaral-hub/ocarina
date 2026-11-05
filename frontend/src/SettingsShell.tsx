import { useEffect } from 'react'
import { setPref } from './api'
import { Appearance } from './Appearance'
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

function Content({ section, rest }: { section: SectionId; rest: string }) {
  switch (section) {
    case 'appearance':
      return <Appearance />
    case 'shortcuts':
      return <Shortcuts />
    case 'general':
      return <General />
    case 'languages':
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
  }
}

// Settings: a list of sections on the left, the chosen one on the right. Settings alone opens the section you were last in.
export function SettingsShell({ section, rest }: { section: SectionId; rest: string }) {
  useEffect(() => {
    setPref('settings.section', section)
  }, [section])
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
