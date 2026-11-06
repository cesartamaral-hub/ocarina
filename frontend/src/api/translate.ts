import { API, json, send } from './client'

export type LocalModel = { id: string; name: string; description: string; installed: boolean; sizeBytes: number }

export type TranslateSettings = {
  offline?: boolean // Work offline is on: only the models on this Mac are used
  provider: string
  target: string
  email: string
  hasDeeplKey: boolean
  deeplKeyHint: string | null
  providers: { id: string; name: string; needsKey: boolean; description: string }[]
  localAuto?: boolean // you never chose a model: each language uses the best of the ones you have
  localModel: LocalModel // the one in use
  localModels: LocalModel[] // every translation model that can run on this Mac
  localModelByLanguage: Record<string, string> // the model chosen for one source language (a language code), in place of the one above
  targets: { code: string; name: string }[]
  samples: { languageId: number; name: string; sample: string }[] // a short sentence in each language of the library, to try a translation with
}

export type Translation = { translation: string; provider: string; source: string; target: string; cached: boolean }

export const getTranslateSettings = () => fetch(`${API}/translate/settings`).then((r) => json<TranslateSettings>(r))

export const putTranslateSettings = (change: Partial<{ provider: string; target: string; email: string; deeplKey: string; localModel: string; allLanguages: boolean; localModelFor: { language: string; model: string } }>) =>
  send<TranslateSettings>('PUT', `${API}/translate/settings`, change)

export const translateSentence = (languageId: number, text: string) => send<Translation>('POST', `${API}/translate`, { languageId, text })

export type TestResult = Translation & { text: string; seconds: number; targetName: string }

export const testTranslation = (languageId?: number, text?: string) => send<TestResult>('POST', `${API}/translate/test`, { languageId, text })

export type Comparison = { id: string; name: string; translation?: string; error?: string; cached?: boolean; seconds: number }

export const compareModels = (languageId: number, text: string) =>
  send<{ results: Comparison[] }>('POST', `${API}/translate/compare`, { languageId, text })
