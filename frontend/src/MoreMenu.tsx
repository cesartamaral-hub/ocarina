import { Popover } from './Popover'
import { useAnchoredPopover } from './useAnchoredPopover'

export type MenuItem = { label: string; onChoose?: () => void; href?: string; danger?: boolean }

// A "⋯" button with a small menu (see Popover): closes after a choice. An item is an action or a link.
export function MoreMenu({ title, items }: { title: string; items: MenuItem[] }) {
  const { anchor, placement, toggle, close } = useAnchoredPopover(190, 'end')
  return (
    <>
      <button ref={anchor} className="secondary small icon" aria-label={title} title={title} aria-haspopup="menu" aria-expanded={placement !== null} onClick={() => toggle()}>
        ⋯
      </button>
      {placement && (
        <Popover anchor={anchor} placement={placement} onClose={close} label={title} role="menu" className="more-menu">
          <ul>
            {items.map((i) => (
              <li key={i.label} role="none">
                {i.href !== undefined ? (
                  <a role="menuitem" className={i.danger ? 'danger-text' : undefined} href={i.href} onClick={close}>
                    {i.label}
                  </a>
                ) : (
                  <button
                    role="menuitem"
                    className={i.danger ? 'link-button danger-text' : 'link-button'}
                    onClick={() => {
                      close()
                      i.onChoose?.()
                    }}
                  >
                    {i.label}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Popover>
      )}
    </>
  )
}
