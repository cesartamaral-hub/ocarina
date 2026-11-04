// Small formatters for sizes, speeds and times shown while models download.
// 2.3 GB, 15 MB, 3.4 MB, 380 KB: enough digits to tell sizes apart, never more.
export function formatBytes(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`
  if (n >= 1e7) return `${Math.round(n / 1e6)} MB`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} MB`
  if (n >= 1e3) return `${Math.round(n / 1e3)} KB`
  return n > 0 ? '1 KB' : '0 KB'
}

export const formatSpeed = (bytesPerSecond: number): string => `${(bytesPerSecond / 1e6).toFixed(bytesPerSecond >= 1e7 ? 0 : 1)} MB/s`

export function formatTimeLeft(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return ''
  if (seconds < 45) return 'less than a minute left'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `about ${minutes} ${minutes === 1 ? 'minute' : 'minutes'} left`
  return `about ${(seconds / 3600).toFixed(1)} hours left`
}

export const percent = (done: number, total: number): number => (total > 0 ? Math.min(100, Math.floor((done * 100) / total)) : 0)
