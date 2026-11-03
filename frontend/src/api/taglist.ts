import { API, json, send } from './client'

export type TagKind = 'term' | 'book'
export type TagRow = { id: number; text: string; comment: string; uses: number }

export const getTagList = (kind: TagKind) => fetch(`${API}/tag-list/${kind}`).then((r) => json<TagRow[]>(r))

export const changeTag = (kind: TagKind, id: number, change: Partial<Pick<TagRow, 'text' | 'comment'>>) =>
  send<TagRow>('PATCH', `${API}/tag-list/${kind}/${id}`, change)

export const deleteTag = (kind: TagKind, id: number) =>
  fetch(`${API}/tag-list/${kind}/${id}`, { method: 'DELETE' }).then((r) => json<{ deleted: number; uses: number }>(r))
