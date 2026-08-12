import { describe, expect, it } from 'vitest'
import { containedContentRect } from './canvas'

describe('containedContentRect', () => {
  it('accounts for horizontal letterboxing around portrait content', () => {
    expect(
      containedContentRect(
        { width: 1000, height: 720 },
        { width: 600, height: 1200 },
      ),
    ).toEqual({
      left: 320,
      top: 0,
      width: 360,
      height: 720,
    })
  })

  it('accounts for vertical letterboxing around landscape content', () => {
    expect(
      containedContentRect(
        { width: 600, height: 600 },
        { width: 1200, height: 600 },
      ),
    ).toEqual({
      left: 0,
      top: 150,
      width: 600,
      height: 300,
    })
  })
})
