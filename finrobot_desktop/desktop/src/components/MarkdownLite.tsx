// Tiny no-dependency markdown renderer for chat bubbles.
// Covers the cases we actually see streaming from the agent: bold, italic,
// inline code, code blocks, ordered/unordered lists, headings up to ###, and
// [text](url) links. Anything we don't recognise renders as plain text so
// unknown markdown is never displayed as broken HTML.

import { type ReactNode } from 'react'

interface MarkdownLiteProps {
  text: string
  className?: string
  style?: React.CSSProperties
}

export function MarkdownLite({ text, className, style }: MarkdownLiteProps) {
  const blocks = parseBlocks(text)
  return (
    <div className={className} style={{ whiteSpace: 'pre-wrap', ...style }}>
      {blocks.map((block, i) => renderBlock(block, i))}
    </div>
  )
}

// ── Block parsing ────────────────────────────────────────────────────────────

type Block =
  | { kind: 'p'; text: string }
  | { kind: 'h'; level: number; text: string }
  | { kind: 'ul'; items: string[] }
  | { kind: 'ol'; items: string[] }
  | { kind: 'table'; header: string[]; rows: string[][] }
  | { kind: 'code'; text: string }
  | { kind: 'blank' }

// A GFM table's second line: `|---|:--:|` and friends, and NOTHING else. Requiring
// the separator row is what keeps a stray `|` (or a `|` inside prose) a paragraph.
const TABLE_SEPARATOR_RE = /^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$/

function isTableSeparator(line: string): boolean {
  return TABLE_SEPARATOR_RE.test(line)
}

// Table ink, in the component's own inline-style idiom (it carries no stylesheet,
// so `.md-content table.md-table` in App.css never applies to it).
const tableHeadStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '4px 8px',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  borderBottom: '1px solid var(--border)',
  whiteSpace: 'nowrap',
}

const tableCellStyle: React.CSSProperties = {
  padding: '4px 8px',
  borderBottom: '1px solid var(--border-faint)',
  color: 'var(--text-primary)',
  verticalAlign: 'top',
}


function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function parseBlocks(input: string): Block[] {
  const lines = input.split('\n')
  const blocks: Block[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    if (line.trim() === '') {
      blocks.push({ kind: 'blank' })
      i += 1
      continue
    }

    // Fenced code block
    if (line.startsWith('```')) {
      const buf: string[] = []
      i += 1
      while (i < lines.length && !lines[i].startsWith('```')) {
        buf.push(lines[i])
        i += 1
      }
      i += 1 // closing fence
      blocks.push({ kind: 'code', text: buf.join('\n') })
      continue
    }

    // Heading — `####`/`#####` are real headings in the report's Data Collection
    // section and used to fall through to a paragraph, printing "#### Foo" verbatim
    // (reviewer, 2026-10-15 TROW report).
    const heading = line.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      blocks.push({ kind: 'h', level: heading[1].length, text: heading[2] })
      i += 1
      continue
    }

    // GFM pipe table: header row, then a `|---|` separator row, then body rows.
    if (line.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const header = splitTableRow(line)
      i += 2
      const rows: string[][] = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        rows.push(splitTableRow(lines[i]))
        i += 1
      }
      blocks.push({ kind: 'table', header, rows })
      continue
    }

    // Unordered list (-, *, +)
    if (/^\s*[-*+]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*+]\s+/, ''))
        i += 1
      }
      blocks.push({ kind: 'ul', items })
      continue
    }

    // Ordered list (1. 2. 3.)
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''))
        i += 1
      }
      blocks.push({ kind: 'ol', items })
      continue
    }

    // Regular paragraph — collect contiguous non-empty lines
    const buf: string[] = [line]
    i += 1
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('```') &&
      !/^#{1,6}\s/.test(lines[i]) &&
      !/^\s*[-*+]\s/.test(lines[i]) &&
      !/^\s*\d+\.\s/.test(lines[i]) &&
      !(lines[i].includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      buf.push(lines[i])
      i += 1
    }
    blocks.push({ kind: 'p', text: buf.join('\n') })
  }
  return blocks
}

function renderBlock(block: Block, key: number): ReactNode {
  switch (block.kind) {
    case 'blank':
      return <div key={key} style={{ height: 4 }} />
    case 'p':
      return (
        <p key={key} style={{ margin: '0 0 6px', lineHeight: 1.55 }}>
          {renderInline(block.text)}
        </p>
      )
    case 'h':
      return (
        <strong
          key={key}
          style={{
            display: 'block',
            fontSize: block.level === 1 ? '0.95rem' : '0.88rem',
            margin: '6px 0 4px',
            color: 'var(--text-primary)',
          }}
        >
          {renderInline(block.text)}
        </strong>
      )
    case 'ul':
      return (
        <ul key={key} style={{ margin: '4px 0 6px', paddingLeft: 18, lineHeight: 1.5 }}>
          {block.items.map((it, idx) => (
            <li key={idx}>{renderInline(it)}</li>
          ))}
        </ul>
      )
    case 'ol':
      return (
        <ol key={key} style={{ margin: '4px 0 6px', paddingLeft: 20, lineHeight: 1.5 }}>
          {block.items.map((it, idx) => (
            <li key={idx}>{renderInline(it)}</li>
          ))}
        </ol>
      )
    case 'table': {
      // A short row is padded so the grid keeps its columns; a long one is kept
      // whole (the browser's own column sizing is the authority, not this parser).
      const width = Math.max(block.header.length, ...block.rows.map((r) => r.length), 0)
      return (
        <table
          key={key}
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            margin: '6px 0',
            fontSize: '0.78rem',
          }}
        >
          <thead>
            <tr>
              {Array.from({ length: width }, (_, c) => (
                <th key={c} style={tableHeadStyle}>
                  {renderInline(block.header[c] ?? '')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, r) => (
              <tr key={r}>
                {Array.from({ length: width }, (_, c) => (
                  <td key={c} style={tableCellStyle}>
                    {renderInline(row[c] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )
    }
    case 'code':
      return (
        <pre
          key={key}
          style={{
            margin: '6px 0',
            padding: '8px 10px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            overflowX: 'auto',
          }}
        >
          {block.text}
        </pre>
      )
  }
}

// ── Inline parsing — [text](url), **bold**, *italic*, `code` ────────────────

// Order matters: the link alternative ([text](url)) comes first so its brackets
// aren't half-eaten by the emphasis patterns; bold (** **) before italic (* *)
// so the italic regex doesn't swallow the bold markers.
const INLINE_TOKEN = /(\[[^\]\n]+\]\([^)\n]+\)|\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*|_[^_\n]+_)/g

const LINK_TOKEN = /^\[([^\]]+)\]\(([^)]+)\)$/

function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let lastIdx = 0
  let m: RegExpExecArray | null
  INLINE_TOKEN.lastIndex = 0
  while ((m = INLINE_TOKEN.exec(text))) {
    if (m.index > lastIdx) {
      out.push(text.slice(lastIdx, m.index))
    }
    const tok = m[0]
    const link = tok.match(LINK_TOKEN)
    if (link) {
      const [, label, url] = link
      if (/^https?:\/\//i.test(url)) {
        // Real external link — same target/rel pattern the report chapters use.
        out.push(
          <a
            key={out.length}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--info)' }}
          >
            {label}
          </a>,
        )
      } else {
        // Internal ref (sandbox://… artifact link, anchors) — not a navigable
        // URL. Show the label as styled text so the raw [text](url) syntax never
        // leaks, without emitting a dead anchor.
        out.push(
          <span key={out.length} style={{ color: 'var(--info)' }}>
            {label}
          </span>,
        )
      }
    } else if (tok.startsWith('**') && tok.endsWith('**')) {
      out.push(<strong key={out.length}>{tok.slice(2, -2)}</strong>)
    } else if (tok.startsWith('`') && tok.endsWith('`')) {
      out.push(
        <code
          key={out.length}
          style={{
            padding: '1px 4px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 3,
            fontSize: '0.85em',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {tok.slice(1, -1)}
        </code>,
      )
    } else if (
      (tok.startsWith('*') && tok.endsWith('*')) ||
      (tok.startsWith('_') && tok.endsWith('_'))
    ) {
      // Underscore emphasis is never intraword (CommonMark): `_` only opens
      // emphasis when it is NOT preceded by a word character and only closes it
      // when NOT followed by one. Without this guard a line carrying two
      // intraword fields (`fetched_at … from_cache`) matches `_…_` across them
      // and eats both underscores, rendering `fetchedat … fromcache` — the
      // engine-brief provenance defect. `*emphasis*` stays intraword-capable.
      const intraword =
        tok.startsWith('_') &&
        (/\w/.test(text[m.index - 1] ?? '') || /\w/.test(text[m.index + tok.length] ?? ''))
      out.push(intraword ? tok : <em key={out.length}>{tok.slice(1, -1)}</em>)
    } else {
      out.push(tok)
    }
    lastIdx = m.index + tok.length
  }
  if (lastIdx < text.length) out.push(text.slice(lastIdx))
  return out
}
