export const API = '/ocarina/api'

export async function json<T>(res: Response): Promise<T> {
  const body = await res.json()
  if (!res.ok) throw Object.assign(new Error(body.error ?? res.statusText), body)
  return body as T
}

export const send = <T,>(method: string, url: string, body: unknown) =>
  fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => json<T>(r))
