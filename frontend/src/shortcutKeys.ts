import { getPref, setPref } from './api'

// Every keyboard shortcut in the reader. The user can change a key; it is saved as the preference key.<id>.
export type Action = { id: string; label: string; key: string; status?: number }

export const ACTIONS: Action[] = [
  { id: 'status1', label: 'Status 1 (new)', key: '1', status: 1 },
  { id: 'status2', label: 'Status 2 (recognised)', key: '2', status: 2 },
  { id: 'status3', label: 'Status 3 (familiar)', key: '3', status: 3 },
  { id: 'status4', label: 'Status 4 (learned)', key: '4', status: 4 },
  { id: 'status5', label: 'Status 5 (known)', key: '5', status: 5 },
  { id: 'status99', label: 'Well known', key: 'w', status: 99 },
  { id: 'status98', label: 'Ignore', key: 'i', status: 98 },
  { id: 'playPause', label: 'Play or pause the audio', key: 'k' },
  { id: 'skipBack', label: 'Audio back: this sentence again, or 10 seconds', key: 'j' },
  { id: 'skipForward', label: 'Audio forward: next sentence, or 10 seconds', key: 'l' },
  { id: 'prevPage', label: 'Previous page', key: 'ArrowLeft' },
  { id: 'nextPage', label: 'Next page', key: 'ArrowRight' },
  { id: 'highlights', label: 'Hide or show the word colours', key: 'h' },
  { id: 'speak', label: 'Hear the selected word or text', key: 's' },
  { id: 'togglePanel', label: 'Show or hide the word panel', key: 'p' },
  { id: 'cycleTranslation', label: 'Show the translation: original, side by side, translation only', key: 't' },
  { id: 'focus', label: 'Focus mode: only the text and the player', key: 'f' },
  { id: 'toggleVocab', label: 'Show or hide the vocabulary panel', key: 'v' },
  { id: 'help', label: 'Show or hide the key list', key: '?' },
  { id: 'clear', label: 'Clear the selection', key: 'Escape' },
]

export const keyOf = (id: string): string => getPref(`key.${id}`, ACTIONS.find((a) => a.id === id)!.key)

// Letters match whatever the case, so caps lock or shift don't break a shortcut.
export const normalise = (key: string) => (key.length === 1 ? key.toLowerCase() : key)

export const actionFor = (e: KeyboardEvent): Action | undefined => ACTIONS.find((a) => keyOf(a.id) === normalise(e.key))

export const statusForKey = (e: KeyboardEvent): number | undefined => {
  const action = actionFor(e)
  return action?.status
}

export function keyLabel(key: string): string {
  const names: Record<string, string> = { ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓', Escape: 'Esc', ' ': 'Space', Enter: 'Return' }
  return names[key] ?? (key.length === 1 ? key.toUpperCase() : key)
}

export const statusKeyLabel = (status: number): string => {
  const action = ACTIONS.find((a) => a.status === status)
  return action ? keyLabel(keyOf(action.id)) : ''
}

const MODIFIERS = ['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Tab', 'Dead']

// Gives an action a new key. Returns what is wrong (a key already used, or not usable), or null when it worked.
export function assignKey(id: string, key: string): string | null {
  if (MODIFIERS.includes(key)) return 'Press a single key, without Shift, Ctrl, Alt or ⌘.'
  const k = normalise(key)
  const taken = ACTIONS.find((a) => a.id !== id && keyOf(a.id) === k)
  if (taken) return `${keyLabel(k)} is already used for "${taken.label}".`
  setPref(`key.${id}`, k)
  return null
}

export const resetKeys = () => ACTIONS.forEach((a) => setPref(`key.${a.id}`, a.key))
