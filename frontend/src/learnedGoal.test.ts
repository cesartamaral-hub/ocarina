import { describe, expect, it } from 'vitest'
import { nextGoal, progress } from './learnedGoal'

describe('learnedGoal', () => {
  it('starts at 50 and climbs the steps', () => {
    expect(nextGoal(0)).toBe(50)
    expect(nextGoal(49)).toBe(50)
    expect(nextGoal(50)).toBe(100)
    expect(nextGoal(132)).toBe(250)
    expect(nextGoal(9999)).toBe(10000)
  })
  it('goes on every 5,000 after the table', () => {
    expect(nextGoal(10000)).toBe(15000)
    expect(nextGoal(17000)).toBe(20000)
  })
  it('uses your own goal while it is ahead, and the steps once it is reached', () => {
    expect(nextGoal(132, 400)).toBe(400)
    expect(nextGoal(400, 400)).toBe(500)
    expect(nextGoal(10, null)).toBe(50)
  })
  it('says how far along it is', () => {
    expect(progress(132)).toEqual({ goal: 250, toGo: 118, fraction: 132 / 250 })
    expect(progress(0).fraction).toBe(0)
  })
})
