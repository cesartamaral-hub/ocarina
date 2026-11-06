import { API, json, send } from './client'

export type LogInfo = { path: string; folder: string; bytes: number }

export const getLogInfo = () => fetch(`${API}/log`).then((r) => json<LogInfo>(r))
export const openLogFolder = () => send<{ opened: boolean; folder: string }>('POST', `${API}/log/open`, {})
