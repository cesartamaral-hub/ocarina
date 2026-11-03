// Short messages ("Saved", "Page finished") that fade by themselves. notify() can be called from anywhere;
// NoticeList shows them.
export type Notice = { id: number; text: string }

let notices: Notice[] = []
let nextId = 1
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())

export function notify(text: string, ms = 3000): void {
  const id = nextId++
  notices = [...notices, { id, text }]
  emit()
  setTimeout(() => {
    notices = notices.filter((n) => n.id !== id)
    emit()
  }, ms)
}

export const subscribeNotices = (l: () => void) => (listeners.add(l), () => void listeners.delete(l))
export const currentNotices = () => notices
