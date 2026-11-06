import { useSyncExternalStore, type RefObject } from 'react'
import { getPref, pronounce, type PronounceSource } from './api'
import type { Playable } from './media'
import { notify } from './notices'

// Says a word or some words aloud. One thing is said at a time: pressing again, or asking for something else, stops what is playing.
// The book's audio or video is paused while a word is said, and carries on afterwards if it was playing.

export type Speaking = { text: string; state: 'loading' | 'playing' } | null

let speaking: Speaking = null
let audio: HTMLAudioElement | null = null
let token = 0 // the latest request: an answer that arrives after another request began is dropped
let media: RefObject<Playable | null> | null = null
let resume = false
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())
const set = (s: Speaking) => {
  speaking = s
  emit()
}

// The reader says which player to pause.
export const pauseThisWhileSaying = (ref: RefObject<Playable | null> | null) => {
  media = ref
}

export const defaultSource = (): PronounceSource => getPref<PronounceSource>('pronounce.source', 'auto')

function finish() {
  audio = null
  set(null)
  if (resume) media?.current?.play().catch(() => undefined)
  resume = false
}

export function stopSaying() {
  token++
  audio?.pause()
  if (audio || speaking) finish()
}

export async function say(text: string, languageId: number, source?: PronounceSource) {
  const clean = text.replace(/\s+/g, ' ').trim()
  if (!clean) return
  if (speaking?.text === clean && !source) return stopSaying() // the same button again
  const mine = ++token
  audio?.pause()
  audio = null
  const player = media?.current
  if (player && !player.paused) {
    resume = true
    player.pause()
  }
  set({ text: clean, state: 'loading' })
  try {
    const got = await pronounce(clean, languageId, source ?? defaultSource())
    if (mine !== token) return
    if (got.note) notify(got.note, 6000)
    const el = new Audio(got.url)
    audio = el
    el.onended = () => mine === token && finish()
    el.onerror = () => {
      if (mine !== token) return
      notify('The sound could not be played.')
      finish()
    }
    await el.play()
    if (mine === token) set({ text: clean, state: 'playing' })
  } catch (e) {
    if (mine !== token) return
    notify((e as Error).message, 5000)
    finish()
  }
}

export const useSaying = () =>
  useSyncExternalStore(
    (l) => (listeners.add(l), () => void listeners.delete(l)),
    () => speaking,
  )
