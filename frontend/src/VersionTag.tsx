import { useEffect } from 'react'
import { loadUpdate, useUpdate } from './updateStore'

// Under the name in the header: which Ocarina this is, and whether it is a dev build rather than a release.
export function VersionTag() {
  const { status } = useUpdate()
  useEffect(() => {
    loadUpdate()
  }, [])
  if (!status?.current) return null
  return (
    <span className="version-tag" title={status.dev ? `Built from the latest code (${status.dev}), not a release` : undefined}>
      v{status.current}
      {status.dev && ' · dev build'}
    </span>
  )
}
