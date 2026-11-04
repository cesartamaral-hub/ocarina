import { API, json, send } from './client'

export type StorageModel = { id: string; name: string; kind: 'speech' | 'text' | 'aligner' | 'transcriber'; installed: boolean; bytes: number; custom: boolean }
export type StorageGroup = { kind: StorageModel['kind']; label: string; bytes: number; count: number }
export type StorageData = { id: string; label: string; description: string; bytes: number; clearable: boolean }

export type Storage = {
  models: StorageModel[]
  groups: StorageGroup[]
  modelsBytes: number
  otherHubBytes: number // in the same Hugging Face folder, not Ocarina's
  leftoverBytes: number // left behind by models deleted by older versions
  hubPath: string
  data: StorageData[]
  dataBytes: number
  freeBytes: number | null
}

export const getStorage = () => fetch(`${API}/storage`).then((r) => json<Storage>(r))

export const clearStorage = (what: string) => send<Storage & { freed: number }>('POST', `${API}/storage/clear`, { what })
