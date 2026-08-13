import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import App from './App'

afterEach(cleanup)

describe('Water Detection Workspace', () => {
  it('renders upload controls and the two-stage review interface', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { name: 'Water Detection Workspace' }),
    ).toBeTruthy()
    expect(screen.getByLabelText('Upload image or video')).toBeTruthy()
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

  it('exposes the workspace title, persistent stages, and Help/About docs link', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { name: 'Water Detection Workspace' }),
    ).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Workspace workflow' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Help / About' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Help / About' }))
    expect(screen.getByRole('dialog', { name: 'Help and About' })).toBeTruthy()
    expect(
      screen.getByRole('link', { name: /API documentation/ }).getAttribute('href'),
    ).toBe('/docs')
  })

  it('does not mark Review active before image review is available', () => {
    render(<App />)

    const reviewStage = screen.getByRole('button', { name: /^Review$/ })
    fireEvent.click(reviewStage)

    expect(reviewStage.getAttribute('aria-current')).toBeNull()
    expect(
      screen
        .getByRole('button', { name: /^Upload$/ })
        .getAttribute('aria-current'),
    ).toBe('step')
    expect(
      screen
        .getByLabelText('Detection setup')
        .querySelector('.workspace-panel-content')
        ?.getAttribute('aria-hidden'),
    ).toBe('false')
    expect(
      screen
        .getByLabelText('Inspector')
        .querySelector('.workspace-panel-content')
        ?.getAttribute('aria-hidden'),
    ).toBe('true')
  })
})
