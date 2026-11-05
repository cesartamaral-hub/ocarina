import { getPref } from '../api'

// Which word a status key or the speak key acts on: the one under the pointer, the selected one, or both in some order.
export type KeyTarget = 'pointer' | 'selection' | 'selected-only'
export const KEY_TARGET_PREF = 'keys.target'
export const KEY_TARGETS: { id: KeyTarget; label: string }[] = [
  { id: 'pointer', label: 'The word under the pointer first, else the selected word' },
  { id: 'selection', label: 'The selected word first, else the word under the pointer' },
  { id: 'selected-only', label: 'Only the selected word' },
]

export const keyTarget = (): KeyTarget => {
  const saved = getPref<string>(KEY_TARGET_PREF, 'pointer')
  return KEY_TARGETS.some((t) => t.id === saved) ? (saved as KeyTarget) : 'pointer'
}

// 'pointer' when the key goes to the hovered word, 'selected' when it goes to the selected one, null when there is nobody to act on.
export function whoGetsTheKey(mode: KeyTarget, hovered: boolean, selected: boolean): 'pointer' | 'selected' | null {
  if (mode === 'selected-only') return selected ? 'selected' : null
  if (mode === 'pointer') return hovered ? 'pointer' : selected ? 'selected' : null
  return selected ? 'selected' : hovered ? 'pointer' : null
}
