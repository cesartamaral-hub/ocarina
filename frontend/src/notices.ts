// Short messages ("Saved", "Page finished") that fade by themselves. notify() can be called from anywhere;
// NoticeList shows them. A message that is already showing is not added again (pressing a key twice would stack it): it
// stays for another full time instead.
export type Notice = { id: number; text: string }

let notices: Notice[] = []
let nextId = 1
const timers = new Map<number, ReturnType<typeof setTimeout>>()
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())

export function notify(text: string, ms = 3000): void {
  const showing = notices.find((n) => n.text === text)
  const id = showing?.id ?? nextId++
  if (!showing) {
    notices = [...notices, { id, text }]
    emit()
  }
  clearTimeout(timers.get(id))
  timers.set(
    id,
    setTimeout(() => {
      timers.delete(id)
      notices = notices.filter((n) => n.id !== id)
      emit()
    }, ms),
  )
}

export const subscribeNotices = (l: () => void) => (listeners.add(l), () => void listeners.delete(l))
export const currentNotices = () => notices
