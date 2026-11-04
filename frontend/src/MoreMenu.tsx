import { useEffect, useRef, useState } from 'react'
import { useEscape } from './escape'

export type MenuItem = { label: string; onChoose?: () => void; href?: string; danger?: boolean }

// A "⋯" button with a small menu: closes on Esc, on a click outside and after a choice. An item is an action or a link.
export function MoreMenu({ title, items }: { title: string; items: MenuItem[] }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLSpanElement>(null)
  useEscape(open, () => setOpen(false))
  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [open])
  return (
    <span className="more" ref={box}>
      <button className="secondary small icon" aria-label={title} title={title} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        ⋯
      </button>
      {open && (
        <ul className="more-menu" role="menu">
          {items.map((i) => (
            <li key={i.label} role="none">
              {i.href !== undefined ? (
                <a role="menuitem" className={i.danger ? 'danger-text' : undefined} href={i.href} onClick={() => setOpen(false)}>
                  {i.label}
                </a>
              ) : (
                <button
                  role="menuitem"
                  className={i.danger ? 'link-button danger-text' : 'link-button'}
                  onClick={() => {
                    setOpen(false)
                    i.onChoose?.()
                  }}
                >
                  {i.label}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </span>
  )
}
