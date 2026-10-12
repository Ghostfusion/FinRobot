// Chapter 12 — Credit & Default Risk. The DEBT leg of the capital structure,
// priced off the equity view: the pipeline solves the Merton identity
// (equity as a call on the firm's assets) for the latent asset value and asset
// volatility, then reports how many standard deviations of asset value sit
// between the firm and its default barrier (DD) and the model-implied one-year
// default probability that follows (Φ(−DD)).
//
// Why it exists: the report valued the EQUITY from cash flows and said nothing
// about whether the DEBT is serviced — the one risk a shareholder cannot see in
// a DCF. `structured.credit_risk` is produced by the deterministic credit_risk
// pipeline step (no LLM) and until now reached no reading surface at all.
//
// The four states render as four deliberately different things, because they mean
// four different things:
//   computed       the model ran — numbers, with the barrier basis disclosed.
//   no_debt        a genuinely debt-free balance sheet: no barrier to breach, so
//                  DD/PD are undefined BY CONSTRUCTION — not missing data.
//   not_applicable a balance-sheet financial (bank / insurer), where deposits and
//                  float are operating raw material: the same category error that
//                  withholds the FCFF-DCF and the EV/EBITDA band for those names.
//   not_computable an input is genuinely absent, stated with its reason.
// A zero is NEVER rendered in place of an absent number, and the reading is never
// presented as a rating — it is a structural, equity-implied measure whose
// assumptions are on the page.

import { Link } from 'react-router-dom'
import type { CSSProperties } from 'react'
import { useI18n, type Locale } from '../../../i18n'
import { formatCurrencyCompact, formatPercent } from '../../../utils/format'
import { Chapter, SubChapter } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import type { CreditRiskShape } from './types'

interface Props {
  /** structured.credit_risk — null on artifacts written before the step existed. */
  credit: CreditRiskShape | null
}

export function ChapterCreditRisk({ credit }: Props): React.ReactElement {
  const { locale } = useI18n()
  const state = credit?.state ?? null
  const warnings = (credit?.warnings ?? []).filter(
    (w): w is string => typeof w === 'string' && w.trim() !== '',
  )

  if (!credit || state === null) {
    return (
      <Chapter id="credit">
        <GapCallout
          title={tr('本次运行未生成信用风险数据', 'No credit-risk reading in this run', locale)}
          body={tr(
            '该报告生成于信用风险步骤上线之前。重新运行以获得 Merton/KMV 结构性违约距离与隐含违约概率。',
            'This artifact predates the credit-risk step. Re-run the report to get the structural (Merton/KMV) distance to default and implied default probability.',
            locale,
          )}
        />
      </Chapter>
    )
  }

  if (state !== 'computed') {
    return (
      <Chapter id="credit">
        <StateCallout state={state} credit={credit} warnings={warnings} locale={locale} />
      </Chapter>
    )
  }

  return (
    <Chapter id="credit">
      <SubChapter heading={tr('结构性违约距离', 'Structural Distance to Default', locale)}>
        <MetricModule
          title={tr('信用读数', 'Credit Readout', locale)}
          accent="cyan"
          columns={2}
          meta={tr('Merton/KMV · 1 年 · USD', 'Merton/KMV · 1Y · USD', locale)}
          cells={headlineCells(credit, locale)}
        />
        <p style={readingNote}>
          {tr(
            '违约距离 = 资产价值与违约屏障之间相隔的标准差数,是连续读数,不是评级。违约概率是模型自身的 Φ(−DD),由股权价格反推,不构成评级机构估计,也不宜跨行业、跨资本结构直接比较。',
            'Distance to default is how many standard deviations of asset value sit between the firm and its default barrier — a continuous score, not a rating. The default probability is the model’s own Φ(−DD), backed out of the equity price: not a rating-agency estimate, and not comparable across sectors or capital structures.',
            locale,
          )}
        </p>
      </SubChapter>

      <SubChapter heading={tr('模型求解', 'The Solve', locale)}>
        <MetricModule
          title={tr('求解输入与拟合结果', 'Solve Inputs & Fitted Outputs', locale)}
          accent="cyan"
          columns={3}
          cells={solveCells(credit, locale)}
        />
      </SubChapter>

      <SubChapter heading={tr('假设与限制', 'Assumptions & Limits', locale)}>
        <ul style={assumptionList}>
          {assumptionLines(credit, locale).map((line) => (
            <li key={line} style={assumptionItem}>
              {line}
            </li>
          ))}
        </ul>
        {warnings.length > 0 && (
          <div data-testid="credit-warnings" style={warningBox}>
            {warnings.map((w) => (
              <div key={w} style={warningLine}>
                ⚠ {w}
              </div>
            ))}
          </div>
        )}
      </SubChapter>
    </Chapter>
  )
}

// ── computed state ───────────────────────────────────────────────────────────

function headlineCells(credit: CreditRiskShape, locale: Locale): MetricCell[] {
  const cells: MetricCell[] = []
  const dd = num(credit.distance_to_default)
  const pd = num(credit.default_probability)
  const spread = num(credit.implied_credit_spread)
  const leverage = num(credit.debt_to_value)

  if (dd !== null) {
    cells.push({
      label: tr('违约距离 DD', 'Distance to Default', locale),
      value: dd.toFixed(2),
      sub: tr('标准差 · 越高越安全', 'STANDARD DEVIATIONS · HIGHER IS SAFER', locale),
    })
  }
  if (pd !== null) {
    cells.push({
      label: tr('1 年违约概率', '1Y Default Probability', locale),
      value: probabilityLabel(pd, locale),
      sub: tr('模型隐含 Φ(−DD)', 'MODEL-IMPLIED Φ(−DD)', locale),
    })
  }
  if (spread !== null) {
    cells.push({
      label: tr('隐含信用利差', 'Implied Credit Spread', locale),
      value: spreadLabel(spread, locale),
      sub: tr('模型自身债务收益率 − 无风险利率', 'MODEL DEBT YIELD − RISK-FREE', locale),
    })
  }
  if (leverage !== null) {
    cells.push({
      label: tr('市场杠杆', 'Market Leverage', locale),
      value: formatPercent(leverage, locale, 1),
      sub: tr('屏障 /（屏障 + 市值）', 'BARRIER / (BARRIER + EQUITY)', locale),
      // A barrier-to-value ratio IS a natural 0–100% scale, so the module's inline
      // proportion bar is honest here (no bar is forced on the other cells).
      ratio: Math.max(0, Math.min(1, leverage)),
    })
  }
  return cells
}

function solveCells(credit: CreditRiskShape, locale: Locale): MetricCell[] {
  const cells: MetricCell[] = []
  const equity = num(credit.equity_value)
  const barrier = num(credit.debt_barrier)
  const assetValue = num(credit.asset_value)
  const assetVol = num(credit.asset_volatility)
  const equityVol = num(credit.equity_volatility)
  const bars = num(credit.volatility_bars)
  const rate = num(credit.risk_free_rate)
  const horizon = num(credit.horizon_years)
  const iterations = num(credit.iterations)

  if (equity !== null) {
    cells.push({
      label: tr('股权市值', 'Market Value of Equity', locale),
      value: formatCurrencyCompact(equity, 'USD', locale),
      sub: tr('股权端 E', 'EQUITY LEG E', locale),
    })
  }
  if (barrier !== null) {
    cells.push({
      label: tr('违约屏障', 'Default Barrier', locale),
      value: formatCurrencyCompact(barrier, 'USD', locale),
      sub: barrierBasisLabel(credit.barrier_basis, locale),
    })
  }
  if (assetValue !== null) {
    cells.push({
      label: tr('资产价值 V', 'Asset Value V', locale),
      value: formatCurrencyCompact(assetValue, 'USD', locale),
      sub: tr('由等式反解', 'SOLVED FROM THE IDENTITY', locale),
    })
  }
  if (assetVol !== null) {
    cells.push({
      label: tr('资产波动率 σ_V', 'Asset Volatility σ_V', locale),
      value: formatPercent(assetVol, locale, 1),
      sub: tr('年度化 · 拟合', 'ANNUALIZED · FITTED', locale),
    })
  }
  if (equityVol !== null) {
    cells.push({
      label: tr('股权波动率 σ_E', 'Equity Volatility σ_E', locale),
      value: formatPercent(equityVol, locale, 1),
      sub:
        bars === null
          ? tr('年度化 · 历史实现', 'ANNUALIZED · REALIZED', locale)
          : tr(`近 ${bars} 个交易日`, `TRAILING ${bars} BARS`, locale),
    })
  }
  if (rate !== null) {
    cells.push({
      label: tr('无风险利率', 'Risk-Free Rate', locale),
      value: formatPercent(rate, locale, 2),
      sub: tr('年度化 · 连续复利', 'ANNUAL · CONTINUOUS', locale),
    })
  }
  if (horizon !== null) {
    cells.push({
      label: tr('期限', 'Horizon', locale),
      value: `${horizon.toFixed(1)}Y`,
      sub: tr('屏障定义的期限', 'BARRIER HORIZON', locale),
    })
  }
  if (iterations !== null) {
    cells.push({
      label: tr('不动点迭代', 'Fixed-Point Iterations', locale),
      value: String(iterations),
      sub:
        credit.converged === false
          ? tr('未收敛 — 见下方限制', 'NOT CONVERGED — SEE LIMITS', locale)
          : tr('KMV 迭代已收敛', 'KMV ITERATION CONVERGED', locale),
    })
  }
  return cells
}

/** The standing limitations, stated once and in full — the numbers above are only
 *  readable next to them. */
function assumptionLines(credit: CreditRiskShape, locale: Locale): string[] {
  const lines = [
    tr(
      '屏障取报告的总债务。KMV 惯例为「短期债务 + ½ 长期债务」,需要供应商拆分资产负债表;因此本报告的违约距离偏保守 —— 屏障不低于 KMV 口径。',
      'The barrier is reported TOTAL debt. KMV’s convention is short-term debt + ½·long-term debt, which needs a provider that splits the balance sheet — so this distance to default is conservative: the barrier sits at least as high as KMV’s.',
      locale,
    ),
    tr(
      '股权波动率是近一年日收益的历史实现波动(与「技术分析」章节同一序列),不是期权隐含波动率。',
      'The equity volatility is a trailing one-year realized estimate over daily returns — the same series the Technical Analysis chapter builds on — not an option-implied volatility.',
      locale,
    ),
    tr(
      '模型假设资产价值服从对数正态、波动率恒定,且只可能在期限末违约(股权对资产的看涨期权为欧式)。违约事件之外的契约违约、流动性事件不在模型内。',
      'The model assumes a lognormal asset value with constant volatility, and that default can only occur at the horizon (the equity’s call on the assets is European). Covenant breaches and liquidity events outside that structure are invisible to it.',
      locale,
    ),
    tr(
      '隐含利差是模型自身的债务收益率减无风险利率。在一年期、低杠杆下它会趋近于零 —— 这是结构模型已知的短期限局限,不等于市场认为没有信用风险。',
      'The implied spread is the model’s own risky-debt yield minus the risk-free rate. At a one-year horizon it floors near zero for low leverage — a known short-horizon limitation of the structural model, not a claim that the market prices no credit risk.',
      locale,
    ),
  ]
  if (credit.converged === false) {
    lines.push(
      tr(
        'KMV 不动点未收敛:上面的数字是最后一次迭代值,不是不动点。',
        'The KMV fixed point did not converge: the figures above are the last iterate, not a fixed point.',
        locale,
      ),
    )
  }
  return lines
}

// ── non-computed states ──────────────────────────────────────────────────────

function StateCallout({
  state,
  credit,
  warnings,
  locale,
}: {
  state: NonNullable<CreditRiskShape['state']>
  credit: CreditRiskShape
  warnings: string[]
  locale: Locale
}): React.ReactElement {
  const equity = num(credit.equity_value)

  if (state === 'no_debt') {
    return (
      <div data-testid="credit-no-debt" style={gapCallout}>
        <div style={gapCalloutTitle}>
          {tr('资产负债表上没有债务', 'No debt on the balance sheet', locale)}
        </div>
        <p style={gapCalloutBody}>
          {tr(
            '没有需要跨越的违约屏障,因此结构模型的违约距离与违约概率对该发行人无定义 —— 这不是数据缺失。',
            'There is no default barrier to breach, so the structural model’s distance to default and default probability are undefined for this issuer by construction — this is not missing data.',
            locale,
          )}
        </p>
        {equity !== null && (
          <p style={gapCalloutMeta}>
            {tr('股权市值', 'Market value of equity', locale)}:{' '}
            {formatCurrencyCompact(equity, 'USD', locale)}
          </p>
        )}
        {warnings.map((w) => (
          <p key={w} style={gapCalloutMeta}>
            {w}
          </p>
        ))}
      </div>
    )
  }

  const title =
    state === 'not_applicable'
      ? tr('该发行人适用性不足', 'Not applicable to this issuer', locale)
      : tr('本次运行未计算信用风险', 'Credit risk was not computed for this run', locale)
  const body =
    state === 'not_applicable'
      ? tr(
          '银行/保险等资产负债表驱动的金融机构:存款与浮存金是经营原料,不是资本结构,违约屏障在经济学上不成立 —— 与这些发行人被隐去 FCFF-DCF 和 EV/EBITDA 区间是同一类错误。',
          'A balance-sheet financial (bank / insurer): deposits and float are operating raw material, not capital structure, so the default barrier has no economic meaning here — the same category error that withholds the FCFF-DCF and the EV/EBITDA band for these issuers.',
          locale,
        )
      : (warnings[0] ??
        tr('输入不足,未生成读数。', 'Insufficient input; no reading was produced.', locale))

  return (
    <div data-testid={`credit-${state}`} style={gapCallout}>
      <div style={gapCalloutTitle}>{title}</div>
      <p style={gapCalloutBody}>{body}</p>
      {state === 'not_computable' && <ReRunCta locale={locale} />}
      {warnings.length > 1 &&
        warnings.slice(1).map((w) => (
          <p key={w} style={gapCalloutMeta}>
            {w}
          </p>
        ))}
    </div>
  )
}

/** A missing input is fixable by a re-run with the provider reachable; the
 *  category error above is not, which is why only this branch offers the CTA. */
function ReRunCta({ locale }: { locale: Locale }): React.ReactElement {
  return (
    <p style={gapCalloutMeta}>
      <Link to="/settings" style={gapCalloutCta}>
        {tr('检查数据源配置', 'Check data-source settings', locale)}
      </Link>
    </p>
  )
}

function GapCallout({ title, body }: { title: string; body: string }): React.ReactElement {
  return (
    <div data-testid="credit-absent" style={gapCallout}>
      <div style={gapCalloutTitle}>{title}</div>
      <p style={gapCalloutBody}>{body}</p>
    </div>
  )
}

// ── formatting ───────────────────────────────────────────────────────────────

function num(v: number | null | undefined): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** A model probability this small is numerically zero: `<0.01%` says that, while
 *  `8e-28` would read as precision the model does not have. */
function probabilityLabel(pd: number, locale: Locale): string {
  if (pd <= 0) return '0.00%'
  if (pd < 0.0001) return tr('<0.01%', '<0.01%', locale)
  return formatPercent(pd, locale, 2)
}

/** Same flooring logic for the spread, in basis points — `4e-17` is not a spread. */
function spreadLabel(spread: number, locale: Locale): string {
  const bps = spread * 10_000
  if (Math.abs(bps) < 0.5) {
    return tr('≈0 bp', '≈0 bp', locale)
  }
  return `${bps.toFixed(0)} bp`
}

function barrierBasisLabel(basis: string | null | undefined, locale: Locale): string {
  if (basis === 'short_term_plus_half_long_term') {
    return tr('短期债务 + ½ 长期债务', 'SHORT-TERM + ½ LONG-TERM', locale)
  }
  return tr('总债务', 'TOTAL DEBT', locale)
}

function tr(zh: string, en: string, locale: Locale): string {
  return locale === 'en' ? en : zh
}

// ── styles ───────────────────────────────────────────────────────────────────

const readingNote: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: '4px 0 0',
  maxWidth: 780,
}

const assumptionList: CSSProperties = {
  margin: '10px 0 0',
  padding: '0 0 0 18px',
  maxWidth: 820,
}

const assumptionItem: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  marginBottom: 6,
}

const warningBox: CSSProperties = {
  marginTop: 10,
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid var(--border-soft)',
  background: 'var(--surface-2)',
}

const warningLine: CSSProperties = {
  fontSize: 12,
  lineHeight: 1.55,
  color: 'var(--text-muted)',
  fontFamily: 'var(--font-mono)',
}

const gapCallout: CSSProperties = {
  padding: '16px 18px',
  borderRadius: 10,
  border: '1px solid var(--border-soft)',
  background: 'var(--surface-2)',
  maxWidth: 820,
}

const gapCalloutTitle: CSSProperties = {
  fontFamily: 'var(--font-display)',
  fontSize: 14.5,
  fontWeight: 600,
  color: 'var(--text-primary)',
  marginBottom: 8,
}

const gapCalloutBody: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: 0,
}

const gapCalloutMeta: CSSProperties = {
  fontSize: 11.5,
  lineHeight: 1.6,
  color: 'var(--text-muted)',
  margin: '8px 0 0',
}

const gapCalloutCta: CSSProperties = {
  color: 'var(--primary)',
  textDecoration: 'none',
  fontWeight: 500,
}
