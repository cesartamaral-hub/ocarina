import { useEffect, useState } from 'react'
import { getUpdate, setUpdateCheck, unskipUpdate, type UpdateStatus } from './api'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'

// Settings → General: whether Ocarina looks for a newer version when it starts, and a button to look now.
export function UpdateSettings() {
  const [status, setStatus] = useState<UpdateStatus | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => {
    getUpdate().then(setStatus, () => undefined)
  }, [])
  if (!status) return null

  async function checkNow() {
    setMessage('Looking…')
    try {
      const s = await getUpdate(true)
      setStatus(s)
      setMessage(s.error ?? (s.latest?.newer ? `Ocarina ${s.latest.version} is available.` : 'You have the latest version.'))
    } catch (e) {
      setMessage((e as Error).message)
    }
  }

  return (
    <SettingsGroup title="Updates">
      <SettingRow
        label="Check for updates at start"
        info="Asks GitHub for the latest release when Ocarina starts, and sends nothing about you. It is off while Work offline is on."
      >
        <Toggle label="Check for updates at start" checked={status.enabled} onChange={(on) => setUpdateCheck(on).then(() => getUpdate().then(setStatus))} />
      </SettingRow>
      <SettingRow label={`Ocarina ${status.current}`}>
        <span className="muted">{message}</span>
        <button className="secondary" disabled={status.offline} onClick={checkNow}>
          Check now
        </button>
      </SettingRow>
      {status.skipped && (
        <SettingRow label={`You skipped ${status.skipped}`}>
          <button className="link-button" onClick={() => unskipUpdate().then(() => getUpdate().then(setStatus))}>
            Tell me about it again
          </button>
        </SettingRow>
      )}
    </SettingsGroup>
  )
}
