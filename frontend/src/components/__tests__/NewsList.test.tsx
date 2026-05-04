import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NewsList } from '../NewsList'
import type { Headline } from '@/schemas'

function h(
  source: string,
  publishedAt: string,
  title: string,
  url: string,
): Headline {
  return { source, published_at: publishedAt, title, url }
}

describe('NewsList', () => {
  it('renders empty state when headlines is empty', () => {
    render(<NewsList headlines={[]} snapshotComputedAt="2026-05-04T12:00:00Z" />)
    expect(screen.getByTestId('news-list-empty')).toBeInTheDocument()
  })

  it('groups headlines by source', () => {
    const headlines = [
      h('Yahoo Finance', '2026-05-03T12:00:00Z', 'Y1', 'https://y.com/1'),
      h('Reuters', '2026-05-03T11:00:00Z', 'R1', 'https://r.com/1'),
      h('Yahoo Finance', '2026-05-03T10:00:00Z', 'Y2', 'https://y.com/2'),
      h('Reuters', '2026-05-03T09:00:00Z', 'R2', 'https://r.com/2'),
    ]
    render(
      <NewsList
        headlines={headlines}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const groups = screen.getAllByTestId('news-source-group')
    expect(groups).toHaveLength(2)
    const sources = groups.map((g) => g.getAttribute('data-source'))
    expect(sources).toContain('Yahoo Finance')
    expect(sources).toContain('Reuters')
  })

  it('sorts within each group by published_at DESC (most recent first)', () => {
    const headlines = [
      h('Yahoo Finance', '2026-05-01T12:00:00Z', 'Y_old', 'https://y.com/old'),
      h('Yahoo Finance', '2026-05-03T12:00:00Z', 'Y_new', 'https://y.com/new'),
      h('Yahoo Finance', '2026-05-02T12:00:00Z', 'Y_mid', 'https://y.com/mid'),
    ]
    render(
      <NewsList
        headlines={headlines}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const titles = screen
      .getAllByTestId('news-title-link')
      .map((a) => a.textContent)
    expect(titles).toEqual(['Y_new', 'Y_mid', 'Y_old'])
  })

  it('tags headlines newer than snapshotComputedAt with NEW', () => {
    // snapshot at 12:00 — first headline at 13:00 (NEW), second at 11:00 (not NEW)
    const headlines = [
      h(
        'Yahoo Finance',
        '2026-05-04T13:00:00Z',
        'post-snapshot',
        'https://y.com/p',
      ),
      h(
        'Yahoo Finance',
        '2026-05-04T11:00:00Z',
        'pre-snapshot',
        'https://y.com/q',
      ),
    ]
    render(
      <NewsList
        headlines={headlines}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const items = screen.getAllByTestId('news-item')
    expect(items[0].getAttribute('data-is-new')).toBe('true')
    expect(items[1].getAttribute('data-is-new')).toBe('false')
    const newTags = screen.getAllByTestId('news-new-tag')
    expect(newTags).toHaveLength(1)
  })

  it('renders headline as a clickable link with target=_blank rel=noopener', () => {
    const headlines = [
      h('Reuters', '2026-05-03T12:00:00Z', 'Title', 'https://reuters.com/x'),
    ]
    render(
      <NewsList
        headlines={headlines}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const link = screen.getByTestId('news-title-link')
    expect(link.getAttribute('href')).toBe('https://reuters.com/x')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
  })

  it('renders source heading uppercase via class', () => {
    const headlines = [h('Yahoo Finance', '2026-05-03T12:00:00Z', 'X', 'https://y.com/1')]
    render(
      <NewsList
        headlines={headlines}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const heading = screen.getByTestId('news-source-heading')
    expect(heading.textContent).toBe('Yahoo Finance')
    expect(heading.className).toContain('uppercase')
  })
})
