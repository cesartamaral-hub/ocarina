import { useEffect, useState } from 'react'
import { getUpdate, setUpdateCheck, unskipUpdate, type UpdateStatus } from './api'

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
    <section className="ap-card general-card">
      <h2>Updates</h2>
      <label className="ap-check">
        <input
          type="checkbox"
          checked={status.enabled}
          onChange={(e) => setUpdateCheck(e.target.checked).then(() => getUpdate().then(setStatus))}
        />
        <span>Look for a newer Ocarina when it starts</span>
      </label>
      <p className="muted">
        This is Ocarina {status.current}. Looking asks GitHub for the latest release and sends nothing about you. It is off while Work offline is on.
      </p>
      <p>
        <button className="secondary" disabled={status.offline} onClick={checkNow}>
          Check now
        </button>{' '}
        <span className="muted">{message}</span>
      </p>
      {status.skipped && (
        <p className="muted">
          You skipped {status.skipped}.{' '}
          <button className="link-button" onClick={() => unskipUpdate().then(() => getUpdate().then(setStatus))}>
            Tell me about it again
          </button>
        </p>
      )}
    </section>
  )
}
