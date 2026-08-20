import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('Water Leaking Detector', () => {
  it('renders upload controls and the two-stage review interface', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { name: 'Water Leaking Detector' }),
    ).toBeTruthy()
    expect(screen.getByLabelText('Upload image or video')).toBeTruthy()
    expect(
      screen.getByRole('option', { name: 'WaterDetection (last.pt)' }),
    ).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Detection preview' })).toBeTruthy()
    const reviewTab = screen.getByRole('tab', {
      name: 'Review annotations',
    })
    expect(reviewTab).toBeInstanceOf(HTMLButtonElement)
    if (!(reviewTab instanceof HTMLButtonElement)) {
      throw new TypeError('Review tab must be a button.')
    }
    expect(reviewTab.disabled).toBe(true)
    expect(screen.queryByLabelText('Backend')).toBeNull()
    expect(screen.queryByLabelText('Checkpoint')).toBeNull()
    expect(screen.queryByText(/Best, Last/)).toBeNull()
    expect(document.querySelector('#review-overview-grid')).toBeTruthy()
    expect(document.querySelector('#review-editor-workspace')).toBeNull()
  })
})
