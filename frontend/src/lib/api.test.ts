import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestDetections } from './api'

describe('detection API', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends one server-owned ensemble request without runtime selectors', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            class: 'water accumulation',
            confidence: 0.8,
            bbox: [1, 2, 30, 40],
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    const image = new Blob(['image'], { type: 'image/jpeg' })

    await expect(
      requestDetections({
        media: image,
        filename: 'sample.jpg',
        model: 'water_detection',
        confidence: 0.25,
      }),
    ).resolves.toEqual([
      {
        class: 'water accumulation',
        confidence: 0.8,
        bbox: [1, 2, 30, 40],
      },
    ])

    const [, init] = fetchMock.mock.calls[0]
    expect(init?.method).toBe('POST')
    expect(init?.body).toBeInstanceOf(FormData)
    const body = init?.body as FormData
    expect([...body.keys()]).toEqual(['file', 'model', 'confidence'])
    expect(body.get('model')).toBe('water_detection')
    expect(body.get('confidence')).toBe('0.25')
    expect(body.get('file')).toBeInstanceOf(File)
  })
})
