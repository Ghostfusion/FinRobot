import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownLite } from './MarkdownLite'

describe('MarkdownLite', () => {
  it('still renders ### headings and **bold** (regression guard)', () => {
    render(<MarkdownLite text={'### Title\n\nsome **bold** text'} />)
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('bold').tagName).toBe('STRONG')
  })

  it('keeps intraword underscores verbatim (engine-brief fields) while still rendering _emphasis_', () => {
    // The brief line carries two intraword fields on one line. The old regex
    // matched `_…_` across them and ate both underscores (fetched_at →
    // `fetchedat`, from_cache → `fromcache`). They must survive byte-for-byte.
    const line = 'provenance: fetched_at=2026-10-13T20:00:00Z, from_cache=false'
    const { container } = render(<MarkdownLite text={line} />)
    expect(container.textContent).toBe(line)
    expect(container.textContent).toContain('fetched_at')
    expect(container.textContent).toContain('from_cache')
    expect(container.querySelector('em')).toBeNull()
  })

  it('still renders a genuine _emphasis_ pair as <em>', () => {
    const { container } = render(
      <MarkdownLite text={'fetched_at 20:00 UTC, from_cache=false, _emphasis_ kept'} />,
    )
    // Intraword underscores survive verbatim…
    expect(container.textContent).toBe('fetched_at 20:00 UTC, from_cache=false, emphasis kept')
    // …while the genuinely-delimited pair still becomes emphasis.
    const em = container.querySelectorAll('em')
    expect(em).toHaveLength(1)
    expect(em[0].textContent).toBe('emphasis')
  })

  it('renders a markdown link to an http(s) url as a real external anchor', () => {
    render(<MarkdownLite text={'see [the report](https://example.com/r)'} />)
    const link = screen.getByText('the report')
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', 'https://example.com/r')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('renders an internal sandbox:// ref as styled text, never raw [text](url) syntax', () => {
    // sandbox://… is an internal artifact reference, not a navigable URL — it must
    // never render as a dead anchor, and the raw markdown/url must never leak.
    render(<MarkdownLite text={'open the [Equity Research Report](sandbox://art_123) now'} />)
    const label = screen.getByText('Equity Research Report')
    expect(label.tagName).not.toBe('A')
    expect(screen.queryByText(/sandbox:\/\//)).not.toBeInTheDocument()
    expect(screen.queryByText(/\]\(/)).not.toBeInTheDocument()
  })
})
