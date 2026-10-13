// Single source of truth for chapter labels (number + title + sub).
// Both ReportLeftRail (left rail) and each Chapter component read from here so
// the chapter index never drifts between sidebar and headers.
//
// Chapter ids match the <section id="..."> on each chapter and the URL hash
// (e.g. /stocks/AAPL/runs/abc#thesis).

import type { Locale } from '../../../i18n'

export interface ChapterLabel {
  /** Two-digit display number, e.g. "01". User-visible — must read 1-15, not 0-14. */
  num: string
  title: string
  sub: string
}

// Reading order is importance- and dependency-driven (2026-06): the thesis leads
// (conclusion-first), then the company (overview) and WHERE it competes
// (competitive) frame how to read the numbers — so the valuation case is built up
// (financial → valuation) and stress-tested immediately (sensitivity), then the
// recent event record (news — itemized, sourced) and its aggregate signal read
// (catalysts — net direction + category mix, no re-listing), the quant deep-dive
// (technical), and finally the appendix (data → filings → ownership → disclaimer).
//
// ⚠ This array drives ONLY the numbering (chapterNum) + the chapter part of the
// section manifest. The VISUAL render order is the JSX sequence in
// ReportChapters.tsx, which reportSections.ts mirrors (chapters + the interleaved
// auxiliary/non-chapter sections). Reorder in lockstep — the
// ReportChapters.sections test asserts the rendered DOM order against that
// manifest, so a silent mismatch now fails the suite instead of shipping.
export const CHAPTER_ORDER = [
  'cover',
  'thesis',
  'overview',
  'competitive',
  'financial',
  'valuation',
  'sensitivity',
  'news',
  'catalysts',
  'technical',
  // Structural credit risk (Merton/KMV). Placed at the END of the analytical
  // spine — after the quant deep-dive, before the appendix. It is a risk lens on
  // the SAME balance sheet the financial chapter reads; inserting it between
  // `financial` and `valuation` would break the documented financial → valuation
  // build-up, so it reads as the closing risk chapter of the argument.
  'credit',
  'data',
  // Primary-source appendix (2026-10-11): the SEC 10-K/10-Q history + 8-K events
  // and the XBRL concept snapshot the numbers were read from. Persisted since the
  // SEC wiring landed but never rendered — the report cited "10-K" without ever
  // showing the filing. Sits with the other appendix material (data → filings).
  'filings',
  'ownership',
  'disclaimer',
] as const

export type ChapterId = (typeof CHAPTER_ORDER)[number]

// ── Fund research (fund_research) ────────────────────────────────────────────
//
// A fund files no income statement: no thesis, no DCF, no peer comps, no SEC
// filings, no ownership. Forcing it through the equity spine would render fifteen
// empty shells, so `fund_research` carries its own five-section report. Same
// label contract as CHAPTER_ORDER (the rail, the chapter headers and the section
// manifest all read from here), separate array — the equity numbering 01–15 and
// its tests must not shift when the fund report is added.
export const FUND_CHAPTER_ORDER = [
  'fund-profile',
  'fund-cost',
  'fund-holdings',
  'fund-risk',
  'fund-narrative',
] as const

export type FundChapterId = (typeof FUND_CHAPTER_ORDER)[number]

const FUND_ZH: Record<FundChapterId, Omit<ChapterLabel, 'num'>> = {
  'fund-profile': { title: '基金概况', sub: '名称 · 家族 · 类别 · 净资产与净值' },
  'fund-cost': { title: '费用成本', sub: '费率 · 成本拖累 · 与同类平均对比' },
  'fund-holdings': { title: '持仓与配置', sub: '资产配置 · 行业 · 信用质量 · 重仓' },
  'fund-risk': { title: '风险与收益', sub: '区间收益 · 波动率 · 最大回撤 · 夏普' },
  'fund-narrative': { title: '分析叙述', sub: '引擎记录' },
}

const FUND_EN: Record<FundChapterId, Omit<ChapterLabel, 'num'>> = {
  'fund-profile': { title: 'Fund Profile', sub: 'Name · Family · Category · NAV' },
  'fund-cost': { title: 'Cost', sub: 'Expense Ratio · Cost Drag · Category Average' },
  'fund-holdings': {
    title: 'Holdings & Allocation',
    sub: 'Allocation · Sectors · Credit · Top Holdings',
  },
  'fund-risk': { title: 'Risk & Return', sub: 'Trailing Returns · Volatility · Drawdown · Sharpe' },
  'fund-narrative': { title: 'Narrative', sub: 'Engine record' },
}

export function fundChapterNum(id: FundChapterId): string {
  const idx = FUND_CHAPTER_ORDER.indexOf(id)
  return String(idx + 1).padStart(2, '0')
}

export function fundChapterLabel(id: FundChapterId, locale: Locale): ChapterLabel {
  const table = locale === 'en' ? FUND_EN : FUND_ZH
  return { num: fundChapterNum(id), ...table[id] }
}

/** Is this section id one of the fund report's chapters? The discriminator the
 *  Chapter primitive uses to pick the right label table (the two id sets are
 *  disjoint, so a plain membership test is exact). */
export function isFundChapterId(id: string): id is FundChapterId {
  return (FUND_CHAPTER_ORDER as readonly string[]).includes(id)
}

const ZH: Record<ChapterId, Omit<ChapterLabel, 'num'>> = {
  cover: { title: '封面', sub: '研报基本信息' },
  thesis: { title: '投资论点', sub: '多空论证 · 估值依据 · 市场隐含' },
  overview: { title: '公司概览', sub: '板块 · 行业 · 规模 · 盈利质量' },
  financial: { title: '财务分析', sub: '历史回顾与三年预测' },
  // 不在副标列举方法名——实际渲染的方法行按票动态取舍(KO 无 DDM/LBO 行,
  // 静态列举必然漂移,外审当成"标题承诺正文没有"挑掉,2026-07-07)。
  valuation: { title: '估值分析', sub: 'Football Field · 多方法三角互证' },
  news: { title: '近期新闻与事件', sub: '事件 · 情绪' },
  sensitivity: { title: '敏感性分析', sub: '关键假设变动' },
  catalysts: { title: '催化剂信号', sub: '方向判读 · 类别构成' },
  technical: { title: '技术分析', sub: '蒙特卡洛 · 交易点位 · 价格走势' },
  credit: { title: '信用与违约风险', sub: 'Merton/KMV 结构模型 · 违约距离 · 隐含利差' },
  competitive: { title: '竞争格局', sub: '同业三视图' },
  data: { title: '财务数据', sub: '原始数据 · 来源 · 审计轨迹' },
  filings: { title: '申报文件与 XBRL', sub: '10-K / 10-Q · 8-K 事件 · XBRL 科目快照' },
  ownership: { title: '股权与治理', sub: '内部人交易 · 机构持仓 · 高管薪酬' },
  disclaimer: { title: '免责声明', sub: '投资建议提示' },
}

const EN: Record<ChapterId, Omit<ChapterLabel, 'num'>> = {
  cover: { title: 'Cover', sub: 'Report meta' },
  thesis: { title: 'Investment Thesis', sub: 'Bull / Bear · Valuation Bridge · Market-Implied' },
  overview: { title: 'Company Overview', sub: 'Sector · Industry · Scale · Profitability' },
  financial: { title: 'Financial Analysis', sub: 'Historical · 3-Year Forecast' },
  valuation: { title: 'Valuation Analysis', sub: 'Football Field · Method Triangulation' },
  news: { title: 'Recent News & Events', sub: 'Events · Sentiment' },
  sensitivity: { title: 'Sensitivity Analysis', sub: 'Key Assumption Shifts' },
  catalysts: { title: 'Catalyst Signal', sub: 'Directional Read · Category Mix' },
  technical: { title: 'Technical Analysis', sub: 'Monte Carlo · Trade Levels · Price' },
  credit: { title: 'Credit & Default Risk', sub: 'Structural model · Distance to Default' },
  competitive: { title: 'Competitive Landscape', sub: 'Peers — 3 views' },
  data: { title: 'Financial Data', sub: 'Raw · Source · Audit Trail' },
  filings: { title: 'Filings & XBRL', sub: '10-K / 10-Q · 8-K Events · XBRL Facts' },
  ownership: { title: 'Ownership & Governance', sub: 'Insiders · Institutions · Compensation' },
  disclaimer: { title: 'Disclaimer', sub: 'Investment Advice Notice' },
}

export function chapterNum(id: ChapterId): string {
  const idx = CHAPTER_ORDER.indexOf(id)
  // Display 01-15 (1-indexed); 0-based is a developer convention not appropriate for users.
  return String(idx + 1).padStart(2, '0')
}

export function chapterLabel(id: ChapterId, locale: Locale): ChapterLabel {
  const table = locale === 'en' ? EN : ZH
  return { num: chapterNum(id), ...table[id] }
}

/** All chapter labels for a given locale, in reading order. The rail consumes
 *  reportSections() (which wraps these and interleaves the auxiliary sections);
 *  this stays the chapter-only view. */
export function allChapterLabels(locale: Locale): (ChapterLabel & { id: ChapterId })[] {
  return CHAPTER_ORDER.map((id) => ({ id, ...chapterLabel(id, locale) }))
}
