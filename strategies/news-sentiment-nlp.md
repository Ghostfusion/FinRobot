# News sentiment & NLP — learnings from the q-fin.ST corpus

`373` of 4372 corpus papers matched this category; this doc is based on a close reading of `6`.

Emphasis of the reading: text→signal pipelines, market-aligned calibration of sentiment, aggregation
choices on long documents, zero-shot LLM agent aggregation, causal/event designs for news effects
(including "buy the rumor, sell the news" timing), and the measured decay horizons of every signal.

## 1. What the corpus actually offers

**Where the news move sits in event time (arXiv:2608.14014v1).** On 1.68M (stock, day, tag) events from
4.57M tagged articles over ~3,000 US stocks (2023–2026), the news-aligned move concentrates before and
at publication: the pooled cumulative beta-adjusted abnormal return in the news direction reaches
$+0.58\%$ by the close of publication day (day 0) but ends day $+20$ at $+0.20\%$ — a ratio of $2.8$.
Rumor-flagged events show the saying literally: rumor day $+0.36\%$ (n=18,618; 94% confirmed by a
same-tag non-rumor event within 60 trading days, median gap 6 days), rumor→confirmation $-0.09\%$,
confirmation day $+0.01\%$, and days $+6..+20$ give back $-0.06\%$.

**Underreaction to numbers, overreaction to stories (arXiv:2608.14014v1).** Net of a size-matched
placebo, adjusted drift over days $+6..+20$ is positive for quantified fundamental tags — capital
returns $+0.35\%$, earnings $+0.22\%$, guidance $+0.13\%$, analyst actions $+0.10\%$ — and negative for
soft story tags — macro read-throughs $-0.34\%$, product launch $-0.18\%$, leadership $-0.18\%$,
competition $-0.17\%$ (all in the direction of the news). The measured drift table is offered as a
per-tag/per-attribute/per-size ranking prior for news-conditioned forecasting.

**A background drift masquerades as reversal (arXiv:2608.14014v1).** Neutral-sentiment events (n=364,405)
trail a single-beta benchmark by $-0.92\%$ (small caps), $-0.58\%$ (mid), $-0.34\%$ (large) over the
following month; news-free "quiet days" drift similarly ($-0.74\%$, $-0.88\%$, $-0.59\%$). Raw days
$+6..+20$ drift is $-0.62\%$ after positive news and $+0.63\%$ after negative news; after subtracting
the placebo both collapse to $0.00\%$ ($p\approx0.9$). With 73% of signed events positive, the pooled
average reads as "widespread reversal of good news" when it is really benchmark residual.

**News carries width, and publication resolves it (arXiv:2608.14014v1).** Day-0 absolute abnormal move
is $1.29\times$ the stock's normal day for neutral guidance (1.23× over the following week) and
$1.11\times$ for neutral earnings; $\ge10$ articles on a day gives $1.36\times$ versus $1.05\times$ for
single-article days. Post-event realized volatility runs at $0.86$ of the EWMA forecast. In-hours
publication moves $1.18\times$ the normal day vs $1.05\times$ for overnight items.

**Turning articles into events (arXiv:2608.14014v1).** A frozen LLM teacher (gpt-5-mini, Azure) labels
29,472 articles into 17 event tags + 5 binary attributes (scheduled, forward-looking, primary source,
quantified, rumor) at ~$0.0002/article; a `distilroberta-base` student (82M params, 7 heads) trained on
600k fresh articles is refined with active learning (100k lowest-confidence back to the teacher; 129,463
final labels). Student agreement with the teacher: 87.5% on primary tag overall, 94.0% at confidence
$\ge0.8$ (85% of articles), 92–99% on attributes; ~95% corpus-wide teacher fidelity for ~$29; 125–160
articles/second on an M4 Pro. Story clustering uses cosine similarity on title+summary embeddings
(threshold 0.80, same tag), with per-tag story lifetimes (M&A/legal up to 90 days, commentary 2 days);
55% of all articles are follow-up coverage of a running story.

**Market-aligned sentiment calibration beats static labels (arXiv:2607.28127v1).** FinSMART trains the
sentiment policy with GRPO directly on realized market outcomes. A daily 35%/35% equal-weighted
long–short portfolio (next-day open-to-open) built from its continuous scores returns 264.9% cumulative
/ 91.5% annualized, Sharpe 1.97, Sortino 2.40, Calmar 4.23, RankIC 0.061 — versus FinDPO 109.8% /
45.0%, Sharpe 1.12, RankIC 0.053; FinBERT RankIC 0.043, FinLlama 0.048, LMD 0.029, VADER 0.011.
Six-monthly market-aligned retraining lifts it to 406.2% / Sharpe 2.41 / RankIC 0.065, and the gain
correlates with the number of newly observed articles ($r=0.72$).

**How much of a 10-K matters depends on aggregation level (arXiv:2607.14174v1).** Extending supervised
lexicon learning (Ke et al. 2020) to 1,383 filings from 94 Nasdaq-100 firms (2006–2023), **full-filing**
text wins at sector and portfolio level for both return and volatility targets (sector 78%/92% vs
Item 1A 73%/90%; portfolio 76%/78% vs 71%/74%), but the ordering **reverses at the single-firm level**
(Nvidia: Item 1A 76%/75% vs full 75%/69%). Item 1A is only 10–15% of filing length yet retains ~57% of
the post-preprocessing word count. A Loughran–McDonald dictionary baseline is strongly *negatively*
correlated with price at every level (sector $r=-0.91$; portfolio $-0.84$ to $-0.94$).

**News sentiment is a persistent state, not daily noise (arXiv:2607.06220v1).** On a daily US economic
news sentiment index (24 newspapers, 1980–2025, $N=16{,}737$ days), DFA shows a crossover near 81 days:
short scale (7–81 d) $H\approx0.67$ (weak persistence), long scale (81–1095 d) $H\approx0.94$ (near
$1/f$); first differences are mildly anti-persistent at 2–8 days ($H\approx0.43$) and near-memoryless
beyond ($H\approx0.03$). Rolling 1,095-day windows: short-scale persistence trends $-0.0046$/yr pre-web,
$-0.0004$ in the web era, $+0.0062$ after 2009 (start-to-end changes $-0.067$, $-0.005$, $+0.090$ Hurst
units). Volatility falls 0.020→0.014, zero-crossings 0.47→0.35, bimodality $(ν²+1)/κ$ rises 0.24→0.35.
Mean tone is stable; the *response time* changed.

**Trained aggregation of zero-shot agents beats every single agent (arXiv:2603.20965v2).** Three fixed
zero-shot prompts (performance / guidance / risk) each return a label, a confidence and a rationale; a
logistic meta-classifier over labels, confidences and disagreement structure predicts next-day return
direction. Balanced accuracy rises 0.561 (best single agent, guidance) → 0.573 (majority) → 0.584
(confidence-weighted) → 0.612 (trained aggregator); FinBERT 0.544. Gains concentrate where the text
disagrees: 3-agent agreement 0.642→0.651, 2–1 split 0.558→0.603, high conflict 0.517→0.581.

**Sentiment's causal effect on profitability is conditional, and often indistinguishable from zero
(arXiv:2602.17851v1).** With FinancialBERT sentiment from quarterly reports as a binary treatment in a
causal forest (AIPW, honest splitting) on 10 NEPSE banks (2013–2024), net-profit ATEs are significant
for Interest Expense (negative) and Interest Coverage Ratio (positive) but **not** for the sentiment
label itself ($p=0.75$ in the asset-composition framework, $p=0.07$–$0.13$ in the leverage framework).
Sentiment's influence is heterogeneous in leverage and loan-portfolio composition.

## 2. Implementable formulas & algorithms

### 2.1 Beta-adjusted event study with a matched placebo baseline
*Purpose:* measure where in event time a news-aligned move sits, and strip benchmark residual that
would otherwise read as news reversal. (arXiv:2608.14014v1)

$$AR_t = r_t - \beta_t\, r_{m,t}, \qquad \beta_t = \text{OLS slope of } r \text{ on } r_m \text{ over trailing 252 days (min 126; missing}\to1)$$

Cumulate $AR$ over four windows: $[-5,0]$, $\{0\}$, $[+1,+5]$, $[+6,+20]$. Stack signed events by the
sentiment sign $s\in\{-1,+1\}$. The placebo-corrected estimator is
$$s\big(AR_w - b_{k,w}\big),$$
where $b_{k,w}$ is the mean $AR$ of **neutral** events in the same size bucket $k$ (dollar-volume
terciles, re-formed yearly) over window $w$. "Adjusted" always means this subtraction.

*Inputs:* daily adjusted closes for the stock and an index proxy (SPY), a per-event sentiment sign, a
neutral-sentiment control set.
*Parameters/defaults:* beta window 252 d / min 126 obs; windows above; 5,000 cluster-bootstrap draws
**resampling trading dates** (events on the same day are cross-sectionally correlated).
*Observed effects:* pooled completion ratio 2.8; per-tag drift as in §1.
*Failure modes:* a tag-matched baseline (each tag's own neutral drift) is required for capital-returns
and launch tags whose neutral coverage selects unusual stocks; richer factor models shrink the baseline
but leave adjusted estimates essentially unchanged; daily closes cannot separate the trading-hours
reaction from the overnight gap.

### 2.2 Distilled LLM tagging + story clustering (text → structured events)
*Purpose:* turn millions of articles into tagged, deduplicated events. (arXiv:2608.14014v1)

1. *Tagging.* Frozen prompt over 17 tag definitions, 5 binary attributes and 4 few-shot examples →
   strict JSON; teacher = small GPT. Distil a 7-head student on teacher labels, then
   uncertainty-sample the lowest-confidence ~15% back to the teacher and retrain. Route only the
   low-confidence tail to the teacher at inference; keep teacher labels where they exist.
2. *Events.* Within each stock-day, cluster articles by cosine similarity of title+summary embeddings
   (threshold 0.80, same primary tag); match each day-cluster to the stock's running stories against a
   frozen centroid. Flag each article NEW (first report) or follow-up; set per-tag story lifetimes
   (commentary 2 d, weeks for operations/leadership, up to 90 d for M&A/legal).
3. *Aggregation.* An event is a (stock, trading day, tag) aggregate; articles published after 16:00 NY
   roll to the next trading day; simplify to the sign of the event-level (mean) sentiment.

*Inputs:* article title + summary + publication timestamp + ticker link.
*Parameters:* similarity 0.80; confidence cut ~0.8; ~$0.0002/article teacher cost.
*Observed effects:* 55% of articles are follow-ups; restricting to NEW shrinks the earnings pre-window
from $+1.41\%$ to $+1.02\%$.
*Failure modes:* student–teacher disagreements (12.5%) concentrate in the two junk tags (price
commentary, promotional) where a wrong label matters least; a mislabeled article can join the wrong
story and degrade clustering.

### 2.3 Represent news as tagged event lines, not sentiment scalars
*Purpose:* encode what survives. (arXiv:2608.14014v1)
Because direction is ~spent by the closing bell while width persists, the durable encoding is
`(tag, scheduled, rumor, primary_source, NEW/follow-up age, article count)` per event, ordered by the
measured per-tag drift prior, rather than one polarity number. Use event tags as **width** signals
(widening into scheduled disclosure, narrowing after).

### 2.4 Market-aligned RL calibration of a sentiment model (FinSMART)
*Purpose:* learn sentiment from realized outcomes instead of static labels. (arXiv:2607.28127v1)
Define idiosyncratic alpha $\alpha = r_{stock} - r_{SPY}$ and the directional ground truth
$$y=\begin{cases}+1 & \alpha>\tau \ \wedge\ r>0\\ -1 & \alpha<-\tau \ \wedge\ r<0\\ 0 & \text{otherwise}\end{cases},\qquad \tau = 0.5\%,$$
and the asymmetric discrete reward
$$R_{trade}(d,y)=\begin{cases}+2.0 & d=y\neq0\\ +0.1 & d=y=0\\ -1.5 & d=-y\neq0\\ -1.0 & \text{otherwise}\end{cases}.$$
Optimize with GRPO: $G=8$ sampled completions per article,
$A_i=(r_i-\mu(r))/(\sigma(r)+\delta)$, clipped surrogate objective with $\beta=0.1$ KL to the frozen
reference. Practical setup: LoRA $r=16,\alpha=32$, dropout 0.05 (13.6M trainable, 0.17%), single 48 GB
GPU, ~8 h. Filter first with NER (BERT-base-NER confidence >98% for the target company else discard) and
a **sentiment gate** (keep only articles where the reference model's top token is Positive/Negative/
Neutral). Convert the causal LLM's discrete label to a continuous score with a logit-to-score converter;
aggregate multiple same-day articles as the daily mean $S_t=\tfrac1{N_t}\sum_i S_{it}$.

*Observed effects:* see §1 (264.9% vs 109.8%; RankIC 0.061 vs 0.053; 6-month retraining → 406.2%).
*Failure modes (critical):* publication-day returns align far more with article sentiment than
next-day — TMF positive-minus-negative alpha spread ≈5.0% same-day vs 0.3% next-day; Pearson corr
0.41→0.03 (MarketWatch 2.3%→0.3%, 0.37→0.03). Same-day returns may be used **only** to shape training
supervision; all trading evaluation must use next-day returns. A too-low $\tau$ admits market noise; a
symmetric reward collapses the policy to "neutral".

### 2.5 Prompt-diverse zero-shot agent aggregation for disclosure classification
*Purpose:* convert cross-agent disagreement into a signal. (arXiv:2603.20965v2)
Three fixed prompts read the same disclosure through performance, guidance and risk lenses; each emits
`{label ∈ {-1,0,+1}, confidence ∈ [0,1], rationale}` in JSON (deterministic decoding, $T=0$, top-$p=1$,
fixed seed). Confidence is the geometric-mean token probability of the label string
$$c_k=\exp\!\Big(\tfrac1m\sum_{j=1}^m \log p(t_j\mid t_{<j},x)\Big),$$
clipped to $[0,1]$ when a model only self-reports. Build the feature vector $z(x)$ = 3 labels + 3
confidences + majority label + counts of positive/neutral/negative + number of agreeing agents +
confidence gap between the two most confident agents + 3 "which agent was most confident" interaction
features. Fit an L2 logistic meta-classifier (liblinear) on a chronological split.

*Observed effects:* balanced accuracy 0.612 vs 0.561 best single agent; gains are largest where agents
disagree (§1).
*Failure modes:* the prompt partition is researcher-designed, so part of the gain may be the partition
rather than "agent diversity"; self-reported confidence is only an approximation; pretrained-model
contamination — the paper's abstract restricts evaluation to a post-release sample (9,860 disclosures,
Jan–Mar 2025) to mitigate memorization.

### 2.6 Supervised lexicon-learning sentiment (full document vs targeted section)
*Purpose:* an interpretable, target-adaptable filing/news sentiment score. (arXiv:2607.14174v1)
Word $w$ is scored by the share of its occurrences that fall in positively-labeled documents,
$$f_w=\frac{\sum_{i=1}^n \mathbb{1}\{d_{w,i}>0\}\mathbb{1}\{y_i>0\}}{\sum_{i=1}^n \mathbb{1}\{d_{w,i}>0\}},$$
retained if $f_w>0.5+\alpha$ or $f_w<0.5-\alpha$ and it occurs $>k$ times. Topic vectors are estimated
by regression on the label proxy, $\hat O = \hat H\,\check W^\top(\check W\check W^\top)^{-1}$ (negative
entries clipped, columns renormalized). A new document's score maximizes a penalized mixture
log-likelihood,
$$\hat p = \arg\max_{p\in[0,1]}\ \sum_{w\in\hat S} \hat s^{-1} d_{i,w}\log\!\big(p\hat O^+_w+(1-p)\hat O^-_w\big) + \lambda\log p(1-p),$$
with $\lambda=0.1$ shrinking sparse documents toward 0.5. Labels: return via percentile rank of
open-to-close log returns taken only up to the publication date; volatility via a min–max normalized
proxy with a (65th-percentile, $q=0.65$) split, computed from the intraday log range (Corsi 2009)
averaged over 3 days. Smooth irregular daily aggregates with a local-level Kalman filter
($\mu_{i+1}=\mu_i+\eta_i$, $\bar p_i=\mu_i+\varepsilon_i$) at sector/portfolio level; keep firm-level
scores unfiltered.

*Aggregation rule (the paper's headline result):* use **full text** when many firms' documents share the
training signal (sector/portfolio; +2–5 pp accuracy), and the **narrow section** (Item 1A) for a single
firm (+1 pp return, +6 pp volatility). Item 1A additionally surfaces supply-chain/covid narratives that
full text dilutes.
*Failure modes:* bag-of-words cannot see multi-word phrases; equally-weighted aggregates ignore index
weights; a finance dictionary baseline is strongly negatively correlated with price on filings and must
not be trusted directionally.

### 2.7 Persistence-aware sentiment features (memory, not daily reset)
*Purpose:* model news sentiment as an accumulating state. (arXiv:2607.06220v1)
Estimate the Hurst exponent by DFA: profile $Y(k)=\sum_{t\le k}(x_t-\bar x)$, detrend windows with a
polynomial of order $m$, fit $\log F(s)=\alpha\log s+c$ (use $m=2$ for the level, $m=1$ for first
differences). The paper's mechanic model is
$$x_t = x^L_t + y_t,$$
where the slow component $x^L$ is fractional Gaussian noise with memory $d_k$ ($H_k=0.5+d_k$) and the
fast component is a heteroskedastic AR(1), $y_t=\phi_k y_{t-1}+\sqrt{1+\omega y_{t-1}^2}\,\varepsilon_t$.
Calibrated memory rises across eras ($d_k\approx0.28,0.36,0.45$) while corrective feedback weakens
($\phi_k\approx-0.03,0.04,0.26$).
*Use in FinRobot:* derive a "sentiment state age" / distance-from-crossover feature rather than feeding
the current level as an instantaneous shock; expect a shock's trace to persist at weekly-to-quarterly
scales, longer for negative bursts (power-law burst-magnitude exponents $\gamma\approx2.5$–$4.0$,
steeper for positive; negative bursts last longer).
*Failure modes:* lexicon scores enable long-horizon comparability but admit semantic drift; the index
excludes broadcast and social sources; the periodization is descriptive, not causal.

### 2.8 Causal forest check: is the sentiment signal causal or confounded?
*Purpose:* test whether a sentiment signal has a causal channel to fundamentals (or is confounded by
expenses/leverage). (arXiv:2602.17851v1)
Treat binarized sentiment as treatment $S=\{p,n\}$ with potential outcomes $Y_i(p),Y_i(n)$; estimate
$$\text{ATE}=\mathbb{E}[Y\mid W=p]-\mathbb{E}[Y\mid W=n],\qquad
\tau(x)=\mathbb{E}[Y_i(p)-Y_i(n)\mid X_i=x],$$
with a causal forest (bootstrap + subsample, honest splitting, split criterion
$\Delta\tau^2=(\tau_{left}-\tau_{right})^2$, AIPW doubly-robust estimation) and use SHAP to pick
covariates and characterize heterogeneity (here: leverage ratios and loan-portfolio/asset mix).
*Observed effect:* sentiment's ATE is not significant; interest expense and interest coverage are.
*Failure modes:* the fundamental problem of causal inference (only one potential outcome observed);
controlling for many collinear financials can itself introduce bias; SHAP importance is not causation.

## 3. Data requirements → available endpoints

Every row cites a probed row of `strategies/endpoints.json` unless marked **gap**. Provider ids match
`finrobot_desktop/finrobot/engine/data/categories.py` `PRIORITY`. Credentials are referenced by env-var
name only.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| News headline/URL/publish time per ticker | `https://eodhd.com/api/news` (`api_token=$EODHD_API_KEY`) | news_data | eodhd | ok |
| Per-article polarity (EODHD `sentiment.polarity`) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Aggregated daily sentiment series (`normalized` ∈ [-1,1]) | `https://eodhd.com/api/sentiments` (`s={ticker}`) | news_sentiment | eodhd | ok |
| News + per-ticker sentiment score (AV feed) | `https://www.alphavantage.co/query?function=NEWS_SENTIMENT` | news_sentiment | alpha_vantage | ok |
| Global news tone timeline (per-article tone) | `https://api.gdeltproject.org/api/v2/doc/doc` (`mode=timelinetone`) | news_sentiment | gdelt | rate_limited |
| Wire/company news feed, Benzinga | `https://api.benzinga.com/api/v2/news` (`token=$BENZINGA_API_KEY`) | news_data | benzinga | ok |
| News retractions/corrections | `https://api.benzinga.com/api/v2/news-removed` | news_retractions | benzinga | ok |
| General news search | `https://newsapi.org/v2/everything` (`X-Api-Key:$NEWSAPI_API_KEY`) | news_data | newsapi | ok |
| News (alt aggregate) | `https://api.stockdata.org/v1/news/all` | news_data | stockdata | ok |
| Daily OHLC for returns & the 252-day beta | `https://eodhd.com/api/eod/AAPL` (any ticker; also `api.tiingo.com/tiingo/daily/{t}/prices`, `api.twelvedata.com/time_series`, `api.massive.com/v2/aggs/ticker/{t}/prev`) | core_stock_apis | eodhd / tiingo / twelvedata / massive | ok |
| Analyst actions / ratings | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| Guidance revisions (quantified-news tag) | `https://api.benzinga.com/api/v2.1/calendar/guidance` | guidance_revisions | benzinga | ok |
| Earnings calendar / timing | `https://api.benzinga.com/api/v2.1/calendar/earnings` | earnings_calendar | benzinga | ok |
| Event-implied probabilities (rumor/event priors) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Macro consumer-sentiment survey proxy (UMCSENT; corr 0.59 with news sentiment) | `https://api.stlouisfed.org/fred/series/observations` (`$FRED_API_KEY`) | macro_data | fred | ok |
| Insider/ownership, short interest, capital flow (conditioning) | `moomoo://get_insider_trade_list`, `moomoo://get_short_interest`, `moomoo://get_capital_flow` | smart_money / short_interest / capital_flow | moomoo | gateway (endpoint reachable only via local OpenD SDK; `ok=false`) |
| Intraday bars for Corsi range vol / day-0 abs-move ratios | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (no keyless intraday alternative; daily EOD rows are insufficient) |
| **Full article body text** for LLM tagging / NER / story clustering | — | — | — | **gap** — no probed endpoint returns article body; EODHD/NewsAPI/StockData carry title+URL only, Alpha Vantage adds a short summary |
| **10-K full text + Item 1A section**, quarterly-report narrative | — | sec_filings (routes to `sec_edgar` → runtime `edgar_tools`, identity `SEC_USER_AGENT`) | — | **gap** — `sec_filings` exists in `PRIORITY` but has **no row in `endpoints.json`**; needs a dedicated probe |
| **Rumor flag, first-report (NEW) flag, event tags, source-quality score** | — | — | — | **gap** — must be derived from text (§2.2), not fetched |
| **45-year newspaper news-sentiment index** (Shapiro et al.) | — | — | — | **gap** — no provider; GDELT tone covers only a ~3-month rolling window; use FRED UMCSENT as a coarse survey proxy |
| Off-exchange long/short book, borrow fees (execution realism) | — | — | — | **gap** — not in the inventory |

## 4. Pitfalls, validation and measurement

**The background-drift trap (arXiv:2608.14014v1).** A single-beta benchmark leaves $-0.3\%$ to $-0.9\%$
per month of residual drift on covered *and* uncovered stocks. Scored without a placebo, this drift
manufactures (i) apparent reversal of good news, (ii) apparent continuation of bad news, (iii) an
apparent small-vs-large size gradient, and (iv) an apparently profitable "fade news" strategy. The
paper's fade-small-cap-launch/partnership portfolio earns 15.8% annualized / Sharpe 1.35 — statistically
identical to blindly shorting *every* covered small cap (15.9% / 1.35). **Always report a
coverage-presence baseline**; if your alpha equals "short stock that appeared in the news", you have no
news alpha.

**Direction is largely spent; treat the move as priced in.** Pooled completion ratio 2.8; rumor captures
everything before confirmation (M&A: +0.24% rumor day, then -0.32% into confirmation, -0.10% on the
news, -0.37% after — "whoever bought the confirmation bought the top"). Any news-conditioned model must
clear costs net of this: residual tag alphas are thin (earnings +0.22% per event over 15 days) and die
at 10–20 bps/side.

**Multiple testing and cross-sectional dependence.** Seventeen tags are tested at once; only macro
reversal, capital-returns and earnings continuation survive Benjamini–Hochberg FDR at $q=0.05$ (analyst,
leadership, launch sit at the boundary $q\in[0.05,0.07]$). Events on the same day are correlated —
bootstrap by resampling *trading dates* (5,000 draws), never assume i.i.d. events.

**Base-rate imbalance.** 73% of signed events are positive, so any pooled signed average is a positive-news
average; per-sign and per-tag breakdowns are mandatory.

**Look-ahead and contamination.**
- *Same-day returns* (arXiv:2607.28127v1): publication-day alignment is 5.0% alpha spread / 0.41 corr on
  TMF but 0.3% / 0.03 next-day. Use same-day only to shape training supervision, **never** for returns
  you report.
- *LLM pretraining* (arXiv:2603.20965v2): zero-shot judges may have memorized historical disclosures;
  restrict evaluation to a post-release window (the paper's 9,860-filing Jan–Mar 2025 sample).
- *Label vintage* (arXiv:2608.14014v1): tagging a corpus retrospectively with a later-trained classifier
  can leak; re-run conclusions on teacher-only labels (the paper's Table 4) as a check.

**Aggregation-level choice is not neutral (arXiv:2607.14174v1).** Full-filing text wins at sector/portfolio,
Item 1A wins at single-firm level — an effect of document volume interacting with available independent
training signal, not of text "quality". Validate the full-text/section choice at the exact level you
deploy.

**Dictionary scores are biased on filings.** Loughran–McDonald is *negatively* correlated with price at
every level tested ($-0.91$ sector; $-0.84$ to $-0.94$ portfolio); 3/4 of Harvard-IV-4 "negative" words
in 10-Ks are not negative in a financial context. Do not use a raw dictionary tone as a price signal.

**Non-stationarity and regime caveats.** Sentiment persistence itself drifts (arXiv:2607.06220v1):
short-scale Hurst trends $-0.0046$/yr pre-web vs $+0.0062$/yr after 2009; the paper's raw reversal halves
from 2024 to 2026 and adjusted drift is zero from 2025 (arXiv:2608.14014v1) — "a market that learns". Any
calibration of a sentiment→return mapping needs periodic re-estimation (FinSMART retrains every 6 months
and beats static: 406.2% vs 264.9%).

**Causal over-claiming (arXiv:2602.17851v1).** SHAP importance is not causation; sentiment's causal ATE
on profitability is insignificant here, while leverage/expense covariates are significant. Before
attributing P&L to "sentiment", test with a causal forest and report heterogeneity in the covariates that
matter (leverage, asset mix).

**Validation checklist for a sound implementation.**
1. Chronological train/dev/test split; no future text in training.
2. Java-free placebo: neutral-sentiment events **and** news-free "quiet days", in matched size buckets.
3. NEW-report-only rerun (removes follow-up inflation of anticipation).
4. Teacher-only label rerun (removes distilled-classifier error).
5. Single-event-tag days (removes co-occurring-story contamination; analyst events are <7% single-tag).
6. Per-source grouping (aggregators/portals/retail show +0.6–1.5% pre-drift; press wires show none,
   $-0.06\%$) — anticipation is not information.
7. BH-FDR across the tag grid; cluster bootstrap by date.
8. Traded P&L reported at 5/10/20 bps per side, beta-hedged, with borrow/locate caveats for small caps.

## 5. Recommended first implementation in FinRobot

1. **News event-tag + attribute extractor with distilled tagging.** Build §2.2 over the news the data
   layer already fetches (EODHD `news_data`, Benzinga `/v2/news`, Alpha Vantage `NEWS_SENTIMENT`). *Data:*
   title + summary + timestamp + ticker (bodies are a **gap** — see §3); add a dedicated full-text fetch
   later. Emit `(tag, scheduled, rumor, primary_source, NEW/age, count)` per event. *Value:* high — it is
   the ranking/importance-sampling prior for every other news model. *Risk:* title-only tagging loses body
   context; teacher disagreements concentrate in junk tags. *Effort:* L.
2. **Beta-adjusted event study + placebo harness.** §2.1 over `core_stock_apis` daily bars + news sentiment
   signs. Produce a per-tag drift table for FinRobot's covered universe, and make it the mandatory gate
   for any news-alpha claim. *Value:* high (the paper's central lesson). *Risk:* thin residual alphas;
   daily-close timing limitations. *Effort:* M.
3. **Aggregated sentiment series + persistence features.** Wire EODHD `/sentiments` (`normalized`) and the
   GDELT tone timeline into a daily series per ticker; add the DFA/Hurst state-age feature of §2.7 so the
   model does not reset after each event. *Value:* medium — supplies a state variable that a
   level-only feature misses. *Risk:* GDELT's ~3-month window and rate limiting; no long history. *Effort:* S–M.
4. **Market-aligned calibration as an evaluation metric (and optionally as training).** §2.4: at minimum
   compute RankIC of FinRobot's sentiment output against next-day alpha with the same-day/next-day
   distinction enforced; if FinRobot trains its own sentiment model, use the asymmetric dual-filter reward
   and 6-month retraining cadence. *Value:* medium–high (an economically meaningful, self-supervised
   objective). *Risk:* reward hacking / τ sensitivity; needs same-day alpha alignment which must never
   leak into reported returns. *Effort:* L.
5. **Zero-shot multi-agent aggregator for disclosure/news classification.** §2.5: three fixed
   perspective prompts + a learned logistic aggregator over the disagreement vector, using whatever text
   the layer can retrieve (SEC filings via `sec_filings`/`edgar_tools` for the disclosure variant).
   *Value:* medium — +0.044 balanced accuracy over the best single agent, concentrated in conflict cases.
   *Risk:* LLM contamination (restrict to post-release windows); prompt-partition dependence. *Effort:* M.
6. **Supervised lexicon-learning sentiment for filings at the correct aggregation level.** §2.6 on
   10-K/Item 1A (and quarterly report narratives where available): full text at sector/portfolio, the
   targeted section at single-firm; add the volatility target alongside the return target. *Value:*
   medium — an interpretable, cheap, target-adaptable score that beats dictionary tone. *Risk:* bag-of-words
   phrase blindness; SEC text retrieval needs its own probe (currently a **gap**). *Effort:* M.
7. **"Buy the rumor, sell the news" timing module.** Use the rumor attribute, the NEW/first-report flag,
   the scheduled flag and the day-0/intraday-vs-overnight split to place entry *before* publication day's
   close for rumor-flagged, scheduled events, and to *avoid* the $+6..+20$ window for soft tags (launch,
   leadership, macro, competition) while allowing it only for quantified fundamental tags. *Value:*
   medium — encodes the measured decay horizons directly. *Risk:* rumor detection is a text-derivation
   **gap**; small-cap borrow costs. *Effort:* M.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2608.14014v1 | Buy the Rumor, Sell the News: When Is News Priced In? | 2026 |
| 2607.28127v1 | FinSMART: Financial Sentiment Analysis for Algorithmic Trading through Market-Aligned Reinforcement Learning | 2026 |
| 2607.14174v1 | How Much of a 10-K Matters? Aggregation-Dependent Value of Full-Text versus Risk-Factor Sentiment | 2026 |
| 2607.06220v1 | Stable Sentiment and Persistent Dynamics in U.S. Economic News over 45 Years | 2026 |
| 2603.20965v2 | Learning to Aggregate Zero-Shot LLM Agents for Corporate Disclosure Classification | 2026 |
| 2602.17851v1 | Beyond the Numbers: Causal Effects of Financial Report Sentiment on Bank Profitability | 2026 |