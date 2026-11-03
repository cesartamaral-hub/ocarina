import { API, json, send } from './client'

export type BackupFile = { name: string; manual: boolean; size: string; sizeBytes: number; modified: number }

export type BackupSettings = { enabled: boolean; auto: boolean; warn: boolean; dir: string; count: number; lastBackup: number | null }

export type BackupState = { settings: BackupSettings; warning: string; dueNow: boolean; backups: BackupFile[] }

export const getBackups = () => fetch(`${API}/backups`).then((r) => json<BackupState>(r))

export const saveBackupSettings = (s: Omit<BackupSettings, 'lastBackup'>) => send<BackupState>('PUT', `${API}/backups/settings`, s)

export const makeBackup = (manual: boolean) => send<{ name: string }>('POST', `${API}/backups`, { manual })

export const skipBackup = () => send<{ lastBackup: number }>('POST', `${API}/backups/skip`, {})

export const backupDownloadUrl = (name: string) => `${API}/backups/${encodeURIComponent(name)}/download`

let startupBackup: Promise<void> = Promise.resolve()

// Once a day (when the app opens and the last backup is old) a backup is made without asking.
export function runDueBackup(): void {
  startupBackup = (async () => {
    try {
      const state = await getBackups()
      if (state.dueNow) await makeBackup(false)
    } catch {
      // The Backups page shows problems; failing quietly here must not stop the app from opening.
    }
  })()
}

// Screens that show backup state wait for the startup backup, so they don't show it out of date.
export const getBackupsAfterStartup = () => startupBackup.then(getBackups)
