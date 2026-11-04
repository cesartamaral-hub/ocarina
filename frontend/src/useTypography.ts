import { useState } from 'react'
import { saveTypography, typography } from './appearanceSettings'
import type { Typography } from './typography'

// The reader's text settings and a function that changes them (applied and saved at once); shared by the Aa popover and the Appearance page.
export function useTypography(): [Typography, (patch: Partial<Typography> | 'reset') => void] {
  const [t, setT] = useState<Typography>(typography)
  return [t, (patch) => setT(saveTypography(patch))]
}
