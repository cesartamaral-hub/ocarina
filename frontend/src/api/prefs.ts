import { API, json, send } from './client'

// Preferences live on the server (a file in the data folder): the packaged app uses a new port
// on every launch, and the web view's own storage is tied to the port.
let cache: Record<string, unknown> = {}

export async function loadPrefs(): Promise<void> {
  try {
    cache = await fetch(`${API}/prefs`).then((r) => json<Record<string, unknown>>(r))
  } catch {
    cache = {} // the app still works, it just won't remember
  }
}

export function getPref<T>(key: string, fallback: T): T {
  return key in cache ? (cache[key] as T) : fallback
}

export function setPref(key: string, value: unknown): void {
  cache = { ...cache, [key]: value }
  send('PUT', `${API}/prefs`, { [key]: value }).catch(() => undefined)
}
