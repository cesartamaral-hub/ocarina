import { useEffect, useState } from 'react'
import { getUpdate, setUpdateCheck, unskipUpdate } from './api'
import { SettingRow, SettingsGroup, Toggle } from './SettingsKit'
import { loadUpdate, setUpdateStatus, showUpdate, useUpdate } from './updateStore'

// Settings → General: whether Ocarina looks for a newer version when it starts, and a button to look now.
export function UpdateSettings() {
  const { status, available } = useUpdate()
  const [message, setMessage] = useState('')
  useEffect(() => {
    loadUpdate()
  }, [])
  if (!status) return null

  async function checkNow() {
    setMessage('Looking…')
    try {
      const s = await getUpdate(true)
      setUpdateStatus(s)
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
        <Toggle label="Check for updates at start" checked={status.enabled} onChange={(on) => setUpdateCheck(on).then(() => getUpdate().then(setUpdateStatus))} />
      </SettingRow>
      <SettingRow label={`Ocarina ${status.current}`}>
        <span className="muted">{message}</span>
        {available && status.latest && (
          <button className="secondary" onClick={showUpdate}>
            Version {status.latest.version} is available
          </button>
        )}
        <button className="secondary" disabled={status.offline} onClick={checkNow}>
          Check now
        </button>
      </SettingRow>
      {status.skipped && (
        <SettingRow label={`You skipped ${status.skipped}`}>
          <button className="link-button" onClick={() => unskipUpdate().then(() => getUpdate().then(setUpdateStatus))}>
            Tell me about it again
          </button>
        </SettingRow>
      )}
    </SettingsGroup>
  )
}
