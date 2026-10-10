import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { api } from '../../api/client'
import { AiModelPanel, type DraftProvider, type LlmTestState } from './AiModelPanel'

// Data Layer v3: provider API keys are read-only (they live in the repo-root
// .env), so these cover the two things still editable — provider/model
// selection and custom-provider add — plus the live "Test connection" probe,
// which must flush any pending edit before firing. scheduleStandardSave is
// stubbed to invoke its onSaved synchronously, so the assertions stay free of
// the real debounce/react-query timing (non-flaky).

vi.mock('../../api/client', () => ({
  api: { POST: vi.fn(), PUT: vi.fn() },
  BASE_URL: 'http://127.0.0.1:8321',
}))
vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (k: string) => k, locale: 'en' }) }))
vi.mock('../../stores/toastStore', () => ({ useToastStore: () => vi.fn() }))

const ANTHROPIC = {
  id: 'anthropic',
  label: 'Anthropic',
  kind: 'anthropic',
  base_url: null,
  models: ['claude-sonnet-4-6'],
  key_set: false,
  is_builtin: true,
}

// scheduleStandardSave stub that runs onSaved immediately (stands in for "the
// debounced PUT landed"). Exposed so tests can assert the saved payload too.
const saveSpy = vi.fn((_payload: Record<string, unknown>, onSaved?: () => void) => onSaved?.())

function renderPanel(over: Partial<React.ComponentProps<typeof AiModelPanel>> = {}) {
  const props: React.ComponentProps<typeof AiModelPanel> = {
    providers: [ANTHROPIC],
    customProviders: [],
    serverModelName: 'anthropic:claude-sonnet-4-6',
    modelName: 'anthropic:claude-sonnet-4-6',
    setModelName: vi.fn(),
    addingCustom: false,
    setAddingCustom: vi.fn(),
    draftProvider: { name: '', baseUrl: '', modelId: '' } as DraftProvider,
    setDraftProvider: vi.fn(),
    testState: { status: 'idle' } as LlmTestState,
    setTestState: vi.fn(),
    scheduleStandardSave: saveSpy,
    flushPending: vi.fn().mockResolvedValue(undefined),
    ...over,
  }
  return render(<AiModelPanel {...props} />)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.POST).mockResolvedValue({
    data: { ok: false, code: 'auth', detail: 'invalid key' },
    error: undefined,
  } as never)
})

describe('AiModelPanel read-only credentials', () => {
  it('renders the provider key as a disabled read-only field with the .env hint', () => {
    renderPanel()

    // The label is aria-linked to the field; mocked t() returns the raw key.
    const keyField = screen.getByLabelText('settings.llm.apiKeyLabelFor')
    expect(keyField).toBeDisabled()
    expect(keyField).toHaveAttribute('readonly')
    // No way to edit or clear the key from here any more.
    expect(
      screen.queryByRole('button', { name: 'settings.clearKey.button' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText('settings.keysManagedInEnv')).toBeInTheDocument()
  })

  it('keeps the model id editable and saves model_name on change', () => {
    renderPanel({
      providers: [{ ...ANTHROPIC, key_set: true }],
      modelName: 'anthropic:',
      serverModelName: 'anthropic:',
    })

    const modelInput = screen.getByPlaceholderText('settings.model.idPlaceholder')
    expect(modelInput).toBeEnabled()
    fireEvent.change(modelInput, { target: { value: 'claude-sonnet-4-6' } })

    expect(saveSpy).toHaveBeenCalledWith(
      { model_name: 'anthropic:claude-sonnet-4-6' },
      expect.any(Function),
    )
  })

  it('does not show the provider first suggestion as a fake model default', () => {
    renderPanel({ modelName: 'anthropic:', serverModelName: 'anthropic:' })

    expect(screen.getByPlaceholderText('settings.model.idPlaceholder')).toBeEnabled()
    expect(screen.queryByPlaceholderText('claude-sonnet-4-6')).not.toBeInTheDocument()
  })

  it('disables model/test controls until a provider is selected', () => {
    renderPanel({ modelName: '', serverModelName: '' })

    expect(screen.getByPlaceholderText('settings.model.idPlaceholder')).toBeDisabled()
    expect(screen.getByLabelText('settings.llm.apiKeyLabelFor')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'settings.test.button' })).toBeDisabled()
  })

  it('normalizes a custom provider id and saves it without any provider_keys payload', () => {
    renderPanel({
      addingCustom: true,
      draftProvider: {
        name: 'OpenRouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        modelId: 'openai/gpt-4o-mini',
      },
    })

    fireEvent.click(screen.getByRole('button', { name: 'settings.customProvider.add' }))

    // Credentials are never part of the PUT payload — only the provider config.
    expect(saveSpy).toHaveBeenCalledWith({
      custom_providers: [
        {
          id: 'openrouter',
          label: 'OpenRouter',
          kind: 'openai-compatible',
          base_url: 'https://openrouter.ai/api/v1',
          models: ['openai/gpt-4o-mini'],
        },
      ],
      model_name: 'openrouter:openai/gpt-4o-mini',
    })
  })

  it('flushes the pending save BEFORE the manual Test probe (no test-before-save race)', async () => {
    const flushPending = vi.fn().mockResolvedValue(undefined)
    renderPanel({ flushPending })
    fireEvent.click(screen.getByRole('button', { name: 'settings.test.button' }))

    await vi.waitFor(() =>
      expect(api.POST).toHaveBeenCalledWith('/api/settings/test-provider', {
        body: { provider_id: 'anthropic', model_id: 'claude-sonnet-4-6' },
      }),
    )
    expect(flushPending).toHaveBeenCalled()
    // Ordering is the whole point: flush must complete before the probe fires.
    expect(flushPending.mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(api.POST).mock.invocationCallOrder[0],
    )
  })

  it('surfaces the failure verdict (✗ auth) without touching the read-only key', async () => {
    const setTestState = vi.fn()
    renderPanel({ setTestState })
    fireEvent.click(screen.getByRole('button', { name: 'settings.test.button' }))

    // testConnection flips to "testing" then resolves to the failed verdict.
    await vi.waitFor(() => expect(setTestState).toHaveBeenCalledWith({ status: 'testing' }))
    await vi.waitFor(() =>
      expect(setTestState).toHaveBeenCalledWith({
        status: 'done',
        ok: false,
        code: 'auth',
        detail: 'invalid key',
      }),
    )
  })
})
