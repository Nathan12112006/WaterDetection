import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { WorkspaceShell } from './WorkspaceShell'

afterEach(cleanup)

function renderShell(overrides: Partial<ComponentProps<typeof WorkspaceShell>> = {}) {
  return render(
    <WorkspaceShell
      leftOpen
      rightOpen={false}
      rightWidth={320}
      onToggleLeft={vi.fn()}
      onToggleRight={vi.fn()}
      onResizeRight={vi.fn()}
      left={<div>setup</div>}
      center={<div>center</div>}
      right={<div>inspector</div>}
      {...overrides}
    />,
  )
}

describe('WorkspaceShell', () => {
  it('renders the default left-open, right-closed composition', () => {
    renderShell()
    expect(
      screen.getByLabelText('Detection setup').querySelector('.workspace-panel-content')?.getAttribute('aria-hidden'),
    ).toBe('false')
    expect(
      screen.getByLabelText('Inspector').querySelector('.workspace-panel-content')?.getAttribute('aria-hidden'),
    ).toBe('true')
    expect(screen.getByRole('button', { name: 'Collapse setup panel' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Expand inspector' })).toBeTruthy()
  })

  it('exposes a keyboard-resizable inspector with the bounded width', () => {
    const onResize = vi.fn()
    renderShell({ rightOpen: true, onResizeRight: onResize })
    const handle = screen.getByRole('separator', { name: 'Resize inspector' })
    fireEvent.keyDown(handle, { key: 'ArrowLeft' })
    expect(onResize).toHaveBeenCalledWith(336)
    fireEvent.keyDown(handle, { key: 'ArrowRight' })
    expect(onResize).toHaveBeenCalledWith(304)
  })

})
