import { describe, expect, it } from 'vitest'
import { questionBeforeLeaving } from './leaveGuard'

const ask = 'Discard your changes?'

describe('questionBeforeLeaving', () => {
  it('lets every link through when nothing is unsaved', () => {
    expect(questionBeforeLeaving('#/terms', '#/book/1/read/1', [])).toBeNull()
  })
  it('asks before leaving for another page', () => {
    expect(questionBeforeLeaving('#/terms', '#/book/1/read/1', [ask])).toBe(ask)
  })
  it('does not ask for the page you are on, or for things that are not pages', () => {
    expect(questionBeforeLeaving('#/book/1/read/1', '#/book/1/read/1', [ask])).toBeNull()
    expect(questionBeforeLeaving('#edit', '#/book/1/read/1', [ask])).toBeNull()
    expect(questionBeforeLeaving('https://example.com', '#/book/1/read/1', [ask])).toBeNull()
    expect(questionBeforeLeaving(null, '#/x', [ask])).toBeNull()
  })
  it('asks the most recent question', () => {
    expect(questionBeforeLeaving('#/terms', '#/', ['one', 'two'])).toBe('two')
  })
})
