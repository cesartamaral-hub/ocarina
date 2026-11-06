import { HoverSettings } from './HoverSettings'
import { UpdateSettings } from './UpdateSettings'
import { OfflineSetting } from './OfflineSetting'

// The settings that are about the app as a whole: working without the internet, and how pointing at a word behaves.
export function General() {
  return (
    <>
      <h1>General</h1>
      <OfflineSetting />

      <HoverSettings />
      <UpdateSettings />
    </>
  )
}
