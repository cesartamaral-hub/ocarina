import { useEffect, useRef, useState } from 'react'
import type { AudioOptions } from './api'
import { useEscape } from './escape'

export type AudioChoice = { model: string; voice: string } // '' = what the language's settings say

type Item = { group: 'model' | 'voice'; id: string; label: string; note?: string; disabled?: boolean }

// "⋯" menu next to Generate audio: pick another model or voice for this one generation, without touching
// the language's settings. The choice is shown in plain text by the caller; the menu only changes it.
export function AudioOptionsMenu({
  options,
  choice,
  onChange,
  disabled,
}: {
  options: AudioOptions
  choice: AudioChoice
  onChange: (choice: AudioChoice) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)

  const modelId = choice.model || options.defaultModel
  const voiceId = choice.voice || options.defaultVoice
  const installed = options.models.filter((m) => m.installed && !m.problem)
  const missing = options.models.filter((m) => !m.installed || m.problem)
  const items: Item[] = [
    ...installed.map((m): Item => ({ group: 'model', id: m.id, label: m.name, note: m.id === options.defaultModel ? 'language default' : undefined })),
    ...options.voices.map((v): Item => ({ group: 'voice', id: v.id, label: v.name, note: v.id === options.defaultVoice ? 'language default' : undefined })),
  ]
  const checked = (it: Item) => (it.group === 'model' ? it.id === modelId : it.id === voiceId)

  const close = (returnFocus: boolean) => {
    setOpen(false)
    if (returnFocus) trigger.current?.focus()
  }

  useEscape(open, () => close(true))

  // Focus the chosen model when the menu opens, so the arrow keys start from something meaningful.
  useEffect(() => {
    if (!open) return
    const target = menu.current?.querySelector<HTMLElement>('[aria-checked="true"]') ?? menu.current?.querySelector<HTMLElement>('[role^="menuitem"]')
    target?.focus()
  }, [open])

  // A click outside closes the menu.
  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (!menu.current?.contains(e.target as Node) && !trigger.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  function onMenuKey(e: React.KeyboardEvent) {
    const els = [...(menu.current?.querySelectorAll<HTMLElement>('[role^="menuitem"]:not([aria-disabled="true"])') ?? [])]
    const at = els.indexOf(document.activeElement as HTMLElement)
    const go = (i: number) => {
      e.preventDefault()
      els[(i + els.length) % els.length]?.focus()
    }
    if (e.key === 'ArrowDown') go(at + 1)
    else if (e.key === 'ArrowUp') go(at - 1)
    else if (e.key === 'Home') go(0)
    else if (e.key === 'End') go(els.length - 1)
    else if (e.key === 'Tab') close(false)
  }

  function pick(it: Item) {
    const isDefault = it.id === (it.group === 'model' ? options.defaultModel : options.defaultVoice)
    onChange({ ...choice, [it.group]: isDefault ? '' : it.id })
    close(true)
  }

  const overridden = choice.model !== '' || choice.voice !== ''
  const row = (it: Item) => (
    <button
      key={`${it.group}:${it.id}`}
      role="menuitemradio"
      aria-checked={checked(it)}
      className="menu-item"
      tabIndex={-1}
      onClick={() => pick(it)}
    >
      <span className="menu-check" aria-hidden="true">
        {checked(it) ? '✓' : ''}
      </span>
      <span className="menu-label">
        {it.label}
        {it.note && <small className="muted">{it.note}</small>}
      </span>
    </button>
  )

  return (
    <div className="menu-wrap">
      <button
        ref={trigger}
        className={`secondary icon-button${overridden ? ' active' : ''}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Model and voice for this audio"
        title="Model and voice for this audio"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' && !open) {
            e.preventDefault()
            setOpen(true)
          }
        }}
      >
        ⋯
      </button>
      {open && (
        <div ref={menu} className="menu" role="menu" aria-label="Model and voice for this audio" onKeyDown={onMenuKey}>
          <div role="group" aria-labelledby="menu-model">
            <div id="menu-model" className="menu-heading">
              Model
            </div>
            {installed.length === 0 ? <p className="muted menu-empty">No model is downloaded yet.</p> : installed.map((m) => row(items.find((i) => i.group === 'model' && i.id === m.id)!))}
            {missing.map((m) => (
              <div key={m.id} role="menuitem" aria-disabled="true" className="menu-item disabled" tabIndex={-1}>
                <span className="menu-check" aria-hidden="true" />
                <span className="menu-label">
                  {m.name}
                  <small className="muted">{m.installed ? `doesn't work here: ${m.problem}` : 'not downloaded'}</small>
                </span>
              </div>
            ))}
          </div>
          <div role="group" aria-labelledby="menu-voice">
            <div id="menu-voice" className="menu-heading">
              Voice
            </div>
            {options.voices.map((v) => row(items.find((i) => i.group === 'voice' && i.id === v.id)!))}
          </div>
          <div className="menu-footer">
            <p className="muted">Applies to this audio only.</p>
            <a role="menuitem" tabIndex={-1} className="menu-item link" href="#/settings" onClick={() => setOpen(false)}>
              Change the defaults in Settings
            </a>
            {overridden && (
              <button role="menuitem" tabIndex={-1} className="menu-item link" onClick={() => {
                  onChange({ model: '', voice: '' })
                  close(true)
                }}>
                Back to the defaults
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
