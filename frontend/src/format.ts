// Small formatters for sizes, speeds and times shown while models download.
export const formatBytes = (n: number): string => (n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : `${Math.round(n / 1e6)} MB`)

export const formatSpeed = (bytesPerSecond: number): string => `${(bytesPerSecond / 1e6).toFixed(bytesPerSecond >= 1e7 ? 0 : 1)} MB/s`

export function formatTimeLeft(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return ''
  if (seconds < 45) return 'less than a minute left'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `about ${minutes} ${minutes === 1 ? 'minute' : 'minutes'} left`
  return `about ${(seconds / 3600).toFixed(1)} hours left`
}

export const percent = (done: number, total: number): number => (total > 0 ? Math.min(100, Math.floor((done * 100) / total)) : 0)
