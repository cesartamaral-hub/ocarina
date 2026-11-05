import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { currentNotices, notify } from './notices'

describe('notify', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    vi.runAllTimers()
    vi.useRealTimers()
  })

  it('shows a message once, however many times it is sent while it shows', () => {
    notify('Focus mode')
    notify('Focus mode')
    notify('Focus mode')
    expect(currentNotices().map((n) => n.text)).toEqual(['Focus mode'])
  })

  it('keeps other messages next to it', () => {
    notify('Saved')
    notify('Copied')
    notify('Saved')
    expect(currentNotices().map((n) => n.text)).toEqual(['Saved', 'Copied'])
  })

  it('stays for a full time after the last time it was sent', () => {
    notify('Saved', 3000)
    vi.advanceTimersByTime(2000)
    notify('Saved', 3000)
    vi.advanceTimersByTime(2000)
    expect(currentNotices()).toHaveLength(1)
    vi.advanceTimersByTime(1500)
    expect(currentNotices()).toHaveLength(0)
  })

  it('can be shown again once it has gone', () => {
    notify('Saved')
    vi.advanceTimersByTime(3500)
    expect(currentNotices()).toHaveLength(0)
    notify('Saved')
    expect(currentNotices()).toHaveLength(1)
  })
})
