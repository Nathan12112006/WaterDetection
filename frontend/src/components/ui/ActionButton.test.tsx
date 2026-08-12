import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ActionButton } from './ActionButton'

describe('ActionButton', () => {
  it('uses a safe button type and exposes disabled reasons', () => {
    render(
      <ActionButton
        disabled
        disabledReason="Select a detection first."
      >
        Confirm
      </ActionButton>,
    )

    const button = screen.getByRole('button', { name: 'Confirm' })
    expect(button).toHaveProperty('type', 'button')
    expect(button).toHaveProperty('disabled', true)
    expect(button.getAttribute('data-disabled-reason')).toBe(
      'Select a detection first.',
    )
  })

  it('shows its busy label without treating it as an invalid action', () => {
    render(
      <ActionButton busy busyLabel="Saving…">
        Save
      </ActionButton>,
    )

    const button = screen.getByRole('button', { name: 'Saving…' })
    expect(button).toHaveProperty('disabled', true)
    expect(button.getAttribute('aria-busy')).toBe('true')
    expect(button.hasAttribute('data-disabled-reason')).toBe(false)
  })
})
