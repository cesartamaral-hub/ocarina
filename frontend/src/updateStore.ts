import { useSyncExternalStore } from 'react'
import { getUpdate, type UpdateStatus } from './api'

// What the app knows about updates, shared by the update window, the footer of the Books page and the Settings list: the status from the
// server (asked once when the app starts), and whether the window was closed for now. "Update available" stays true after the window was
// dismissed, so the footer and Settings can still point to it, and a click on the footer opens the window again.
type State = { status: UpdateStatus | null; dismissed: boolean; forced: boolean }

let state: State = { status: null, dismissed: false, forced: false }
let loading: Promise<void> | null = null
const listeners = new Set<() => void>()
const set = (patch: Partial<State>) => {
  state = { ...state, ...patch }
  listeners.forEach((l) => l())
}

export function loadUpdate(): Promise<void> {
  loading ??= getUpdate().then(
    (status) => set({ status }),
    () => undefined,
  )
  return loading
}

export const setUpdateStatus = (status: UpdateStatus) => set({ status })
export const dismissUpdate = () => set({ dismissed: true, forced: false })
export const showUpdate = () => set({ dismissed: false, forced: true })
export const updateAvailable = (status: UpdateStatus | null): boolean => Boolean(status?.latest?.newer)

export function useUpdate(): State & { available: boolean } {
  const snapshot = useSyncExternalStore(
    (l) => (listeners.add(l), () => void listeners.delete(l)),
    () => state,
  )
  return { ...snapshot, available: updateAvailable(snapshot.status) }
}
