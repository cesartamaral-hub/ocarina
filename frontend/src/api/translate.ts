import { API, json, send } from './client'

export type LocalModel = { id: string; name: string; description: string; installed: boolean; sizeBytes: number }

export type TranslateSettings = {
  provider: string
  target: string
  email: string
  hasDeeplKey: boolean
  deeplKeyHint: string | null
  providers: { id: string; name: string; needsKey: boolean; description: string }[]
  localModel: LocalModel // the one in use
  localModels: LocalModel[] // every translation model that can run on this Mac
  targets: { code: string; name: string }[]
}

export type Translation = { translation: string; provider: string; source: string; target: string; cached: boolean }

export const getTranslateSettings = () => fetch(`${API}/translate/settings`).then((r) => json<TranslateSettings>(r))

export const putTranslateSettings = (change: Partial<{ provider: string; target: string; email: string; deeplKey: string; localModel: string }>) =>
  send<TranslateSettings>('PUT', `${API}/translate/settings`, change)

export const translateSentence = (languageId: number, text: string) => send<Translation>('POST', `${API}/translate`, { languageId, text })

export const testTranslation = () => send<Translation>('POST', `${API}/translate/test`, {})

export type Comparison = { id: string; name: string; translation?: string; error?: string; cached?: boolean; seconds: number }

export const compareModels = (languageId: number, text: string) =>
  send<{ results: Comparison[] }>('POST', `${API}/translate/compare`, { languageId, text })
