import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EvidenceList } from '../EvidenceList'

describe('EvidenceList', () => {
  it('renders nothing when items is empty', () => {
    const { container } = render(<EvidenceList items={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders top N items by default (max=3)', () => {
    render(<EvidenceList items={['a', 'b', 'c', 'd', 'e']} />)
    const list = screen.getByTestId('evidence-list')
    expect(list.querySelectorAll('li.flex').length).toBe(3)
  })

  it('renders +N more disclosure when items.length > max', () => {
    render(<EvidenceList items={['a', 'b', 'c', 'd', 'e']} max={3} />)
    const button = screen.getByTestId('evidence-show-more')
    expect(button.textContent).toBe('+2 more')
  })

  it('expands to show all items when disclosure clicked', () => {
    render(<EvidenceList items={['a', 'b', 'c', 'd', 'e']} max={3} />)
    fireEvent.click(screen.getByTestId('evidence-show-more'))
    const list = screen.getByTestId('evidence-list')
    expect(list.querySelectorAll('li.flex').length).toBe(5)
  })

  it('does NOT show disclosure when items.length <= max', () => {
    render(<EvidenceList items={['a', 'b']} max={3} />)
    expect(screen.queryByTestId('evidence-show-more')).toBeNull()
  })
})
