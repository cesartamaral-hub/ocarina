import { useEffect } from 'react'

type Bridge = { set_title?: (title: string) => Promise<void> }
const bridge = (): Bridge | undefined => (window as { pywebview?: { api?: Bridge } }).pywebview?.api

// The window's title bar (in the desktop app) and the browser tab show this title.
export function setWindowTitle(title: string): void {
  document.title = title
  bridge()?.set_title?.(title)?.catch(() => undefined)
}

// While the page is open, the window carries this title (the book you are reading); the app's name comes back when it closes.
export function useWindowTitle(title: string): void {
  useEffect(() => {
    const show = () => setWindowTitle(title)
    show()
    window.addEventListener('pywebviewready', show) // the desktop bridge may arrive after the page
    return () => {
      window.removeEventListener('pywebviewready', show)
      setWindowTitle('Ocarina')
    }
  }, [title])
}
