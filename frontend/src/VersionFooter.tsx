import { useEffect } from 'react'
import { loadUpdate, showUpdate, useUpdate } from './updateStore'

// The foot of the Books page: which Ocarina this is, and, when a newer one has been released (even if its window was closed), a way back to it.
export function VersionFooter() {
  const { status, available } = useUpdate()
  useEffect(() => {
    loadUpdate()
  }, [])
  if (!status?.current) return null
  return (
    <footer className="version-footer">
      <span>Ocarina {status.current}</span>
      {available && status.latest && (
        <>
          <span aria-hidden="true">·</span>
          <button className="link-button" onClick={showUpdate}>
            Update available ({status.latest.version})
          </button>
        </>
      )}
    </footer>
  )
}
