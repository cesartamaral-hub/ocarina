import { useSyncExternalStore } from 'react'
import { getPref, setPref } from './api'

// Work offline (Settings → General): the app uses only what is on this Mac. The switch is the preference `offline.only`, which the server reads
// too (it refuses anything that would use the internet); this keeps the pages in step with it.
const PREF = 'offline.only'
const listeners = new Set<() => void>()

export const isOffline = (): boolean => getPref<boolean>(PREF, false)

export function setOffline(on: boolean): void {
  setPref(PREF, on)
  listeners.forEach((l) => l())
}

export const useOffline = (): boolean =>
  useSyncExternalStore(
    (l) => (listeners.add(l), () => void listeners.delete(l)),
    isOffline,
  )

export const OFFLINE_REASON = 'Work offline is on (Settings → General)'
