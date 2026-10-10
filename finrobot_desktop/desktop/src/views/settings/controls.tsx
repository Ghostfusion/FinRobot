// Shared primitive controls for the Settings panels: inline icon glyphs, the
// read-only credential display, and the toggle-switch row.

import { useI18n } from '../../i18n'

// ─── Small inline icons (cosmic spec: simple glyphs as inline SVG) ────────────

export function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
export const ICON_MODEL = 'M8 1.5 14 5v6l-6 3.5L2 11V5l6-3.5ZM8 8 14 5M8 8v6.5M8 8 2 5'
export const ICON_DATA =
  'M2.5 4c0-1.1 2.5-2 5.5-2s5.5.9 5.5 2-2.5 2-5.5 2-5.5-.9-5.5-2Zm0 0v8c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2V4'
export const ICON_UPDATE = 'M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5V5H11'

// ─── Read-only credential display ────────────────────────────────────────────
// Data Layer v3 sources every credential from the repository-root .env, so the
// UI only reports whether a key is present — it never accepts, edits, or clears
// one. Masked when configured; empty otherwise.

export function ReadOnlyCredential({
  configured,
  ariaLabel,
  placeholder,
  value,
}: {
  configured: boolean
  ariaLabel?: string
  /** Overrides the default "keys are managed in .env" copy for non-key
   * credentials (the SEC identity shows its expected format instead). */
  placeholder?: string
  /** The credential's live value, read from the repo-root .env by the caller.
   * Omitted (e.g. the credentials fetch failed) degrades to masked dots, so the
   * field still distinguishes configured from unconfigured. */
  value?: string
}): React.ReactElement {
  const { t } = useI18n()
  return (
    <input
      className="settings-input"
      type="text"
      value={value ?? (configured ? '••••••••' : '')}
      placeholder={placeholder ?? t('settings.keysManagedInEnv')}
      readOnly
      disabled
      aria-label={ariaLabel}
      autoComplete="off"
      spellCheck={false}
    />
  )
}

// ─── Toggle-switch row ────────────────────────────────────────────────────────

export function ToggleRow({
  label,
  desc,
  enabled,
  onToggle,
}: {
  label: string
  desc: string
  enabled: boolean
  onToggle: () => void
}): React.ReactElement {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 0',
        borderTop: '1px solid var(--border-soft)',
      }}
    >
      <div style={{ paddingRight: 24 }}>
        <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
          {desc}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label={label}
        onClick={onToggle}
        style={{
          position: 'relative',
          width: 44,
          height: 24,
          flexShrink: 0,
          borderRadius: 12,
          border: '1px solid var(--border-soft)',
          background: enabled ? 'var(--primary-soft)' : 'var(--bg-card)',
          cursor: 'pointer',
          transition: 'all 0.2s',
          padding: 0,
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 2,
            left: enabled ? 22 : 2,
            width: 18,
            height: 18,
            borderRadius: '50%',
            background: enabled ? 'var(--primary)' : 'var(--text-muted)',
            boxShadow: enabled ? 'var(--glow-blue)' : 'none',
            transition: 'all 0.2s',
          }}
        />
      </button>
    </div>
  )
}
