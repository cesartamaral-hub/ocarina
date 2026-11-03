import { API, json, send } from './client'

export type TranslateSettings = {
  provider: string
  target: string
  email: string
  hasDeeplKey: boolean
  deeplKeyHint: string | null
  providers: { id: string; name: string; needsKey: boolean; description: string }[]
  localModel: { id: string; name: string; installed: boolean; sizeBytes: number }
  targets: { code: string; name: string }[]
}

export type Translation = { translation: string; provider: string; source: string; target: string; cached: boolean }

export const getTranslateSettings = () => fetch(`${API}/translate/settings`).then((r) => json<TranslateSettings>(r))

export const putTranslateSettings = (change: Partial<{ provider: string; target: string; email: string; deeplKey: string }>) =>
  send<TranslateSettings>('PUT', `${API}/translate/settings`, change)

export const translateSentence = (languageId: number, text: string) => send<Translation>('POST', `${API}/translate`, { languageId, text })

export const testTranslation = () => send<Translation>('POST', `${API}/translate/test`, {})
