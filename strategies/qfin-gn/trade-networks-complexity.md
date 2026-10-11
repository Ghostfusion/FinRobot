# Trade Networks & Economic Complexity — learnings from the q-fin.GN corpus

`495` of 3095 corpus papers matched this category (493 with PDFs); this doc is based on a close reading of `6`.

Headline: **the category's central object — the bilateral country-by-country (or country-by-industry) trade
value matrix — is not served by any endpoint in `strategies/endpoints.json`.** Five of the six papers below
estimate something structural from that matrix (backbones, spanning trees, entropy, complexity indices,
efficiency under node removal); none of it can be computed from FinRobot's live data layer today. The sixth
is a sectoral bilateral-trade econometric study that is off the network core and is flagged as such. The
doc therefore separates (a) estimators that are *fully specified* and can run the moment a static trade
matrix is shipped as data, and (b) the two constructions that can be approximated today from country GDP
and firm fundamentals.

## 1. What the corpus actually offers

- **The World Trade Web is better described as hyperbolic than flat, and the departure grows.** A gravity
  model for the *existence* of a trade channel, $p_{ij}=1/(1+\chi_{ij})$ with
  $\chi_{ij}=(d_{a,ij}/\mu\kappa_i\kappa_j)^{\beta}$, is isomorphic to a purely geometric model in the
  hyperbolic plane; embeddings of 129 annual backbones (1870–2013, WWI 1914–1919 and WWII 1939–1947
  excluded, weights in current US$ millions) predict real trade channels with **AUC in $[0.95,1.00]$** every
  year, and the global hierarchy level rises from **$H<0.7$ (19th century) to $\approx0.9$ (2013)**
  (arXiv:1512.02233).
- **Filtering is decisive for the distance result.** In the unfiltered network the connection probability is
  almost independent of geographic distance; in the statistically significant backbone it decays as a power
  law $p(d_g)\propto d_g^{-\nu}$ with a stable **$\nu\approx0.7$** across the whole period — i.e. the
  *significant* channels are the geographically close ones, even as the aggregate network globalises
  (arXiv:1512.02233).
- **A maximum-weight spanning tree is a genuine backbone.** On Gleditsch bilateral trade 1950–2000
  (symmetric $w_{ij}=\tfrac14(w^e_{ij}+w^i_{ij}+w^e_{ji}+w^i_{ji})$, current US$ millions), the tree carries
  **$T^*/T\approx55\%$ (early 1950s) falling to $\approx40\%$ (late 1990s)** and **$E^*/E\approx5\%$ falling
  to $\approx2\%$**, yet the ratio of average edge weights $\langle w^*\rangle/\langle w\rangle$ *grows
  linearly* over the same 50 years — the tree becomes a larger fraction of the *value* even as it becomes a
  smaller fraction of the *links* (arXiv:1412.1618).
- **The tree's strength tail is Pareto with a time-stable exponent.** $P(s^*)\sim(s^*)^{-\gamma}$ with
  **$\gamma\simeq2$** in every year 1950–2000, matching the Pareto tail of national GDP values
  (arXiv:1412.1618).
- **The volume gravity model reproduces the tree only with distance switched on.** With distance coefficient
  **$\alpha=0$** the synthetic tree is a pure star around the USA; with **$\alpha=1.35$** (the 1950–2000
  average) it reproduces the real tree — except that the synthetic tree *overstates* China's importance,
  which the authors read as trade lagging GDP (a hysteresis/memory effect) (arXiv:1412.1618).
- **Aggregation level changes the measured heterogeneity, not the economy.** On the World Input-Output
  Database (43 countries, 56 industries, 2000–2014, current US$ millions; $\approx0.03\%$ of observations per
  year dropped for negative final-demand entries), normalised strength entropy falls monotonically from the
  single-layer (43 strengths) to the multiplex ($43\times57$) to the multi-layer ($43\times57\times57$)
  representation; the single-layer strength distribution shows *no clear heavy tail* while the multi-layer
  one does (arXiv:1809.07407).
- **Entropy is a structural crisis signal, in sample.** Normalised entropy rises from 2001, peaks in 2008 —
  the year the global downturn peaked — and declines afterwards; the *cross-layer* (inter-industry) component
  drives the rise to 2008 while the *intra-layer* component drives the subsequent fall
  (arXiv:1809.07407).
- **Economic complexity transfers cleanly from exports to venture capital.** Applying the Hidalgo–Hausmann
  eigenvector machinery to a Revealed Venture Advantage matrix (Crunchbase, 17 countries, 2014–2024,
  $\le$3,000 firms/country at $\ge$\$1M raised, 18 emerging-technology domains assigned by an LLM multi-label
  classifier at **90.9% mean precision / 78.8% mean recall** against 200 hand-labelled startups), the 2024
  country ranking is **US 0.685, Israel 0.680, China 0.539, France 0.505, Japan 0.495, Germany 0.433**, down
  to **Sweden 0.149**; the domain ranking is **Cloud Computing 1.000 (ubiquity 2), Cybersecurity Tools 0.895
  (3), Medtech 0.870 (3), Defense 0.818 (3)**, with **Raw Materials & Recycling 0.000 (ubiquity 7)**
  (arXiv:2604.09187).
- **Complexity rankings are persistent, and the highest-ranked countries cannot improve by a single move.**
  Both rankings are stable 2021–2024; simulated single-specialisation additions give **no rank gain for the
  US, Israel, China or Germany**, but **Canada +6 (Cybersecurity Tools, relatedness 13)** and **Sweden +7
  (Cybersecurity Tools or Medtech, relatedness 13)** (arXiv:2604.09187).
- **Trade-network efficiency is fragile to import-side shocks, robust to export-side ones.** On directed
  UN Comtrade pesticide networks (2007–2018, five HS categories 380891–380899), removing the top-$p$ nodes by
  **authority, in-closeness or in-degree** destroys efficiency far faster than removing by hub, out-closeness
  or out-degree; across 8 of 9 metrics the robustness ordering is
  $R^{\rm ascend}>R^{\rm random}>R^{\rm descend}$ (clustering is the lone exception). Efficiency rose
  2007–2010, was flat 2010–2015, and fell after 2015 — a year in which pesticide market sales dropped
  **8.5% y/y** (arXiv:2302.13695).
- **Off-topic note.** arXiv:1206.3387v1 (Portuguese horticultural imports/exports) is *not* a
  network/complexity paper: it has no network object, and its own volatility tests (inverse chi-squared,
  inverse normal, inverse logit $t$) reject stationarity for every series, so its convergence coefficients
  ($-0.943$ import, $-1.077$ export, $|t|>18$, $R^2\approx0.51$–$0.54$) are, as the author concedes, of
  "weak regularity". It is retained only because it is the sole assigned paper whose primary category is
  q-fin.GN itself and it supplies the one concrete bilateral-trade econometric specification in the set; it
  should not drive any implementation.

## 2. Implementable formulas & algorithms

### 2.1 Hyperbolic embedding of the trade backbone (World Trade Map)
**Purpose.** Turn a binary/weighted trade backbone into coordinates such that two countries are close iff
they are likely to trade, and read off the hierarchy of the system.

**Formula.** Angular distance $d_{a,ij}=\min(|\theta_i-\theta_j|,\,2\pi-|\theta_i-\theta_j|)$; connectivity
gravity law and its hyperbolic form
$$p_{ij}=\frac{1}{1+\chi_{ij}},\qquad \chi_{ij}=\left(\frac{d_{a,ij}}{\mu\,\kappa_i\kappa_j}\right)^{\beta},
\qquad p_{ij}=\frac{1}{1+e^{\beta(x_{ij}-R)}}$$
with radial map and hyperbolic distance
$$r_i=R-\frac{2}{\beta}\ln\frac{\kappa_i}{\kappa_0},\qquad R=2\ln\!\left(\frac{N}{\beta^2\mu\kappa_0^2}\right),
\qquad d_{h,ij}\approx x_{ij}=r_i+r_j+2\ln\frac{d_{a,ij}}{2}.$$
Coordinates are the maximum-likelihood embedding of the backbone,
$$\mathcal L=\sum_{i<j}\big[a_{ij}\ln p_{ij}+(1-a_{ij})\ln(1-p_{ij})\big],$$
and the backbone itself comes from the disparity filter
$$\alpha_{ij}=1-(k_i-1)\int_0^{w_{ij}/s_i}(1-x)^{k_i-2}\,dx,\qquad \text{keep }(i,j)\iff \alpha_{ij}<\alpha .$$

**Required inputs.** An annual symmetric bilateral-trade matrix $W(t)$ (or its binary support) with country
identifiers; per-country economic size $\kappa_i$ (GDP or degree in the backbone).

**Parameters & defaults.** Disparity threshold $\alpha=0.05$; $\kappa_0=\min_i\kappa_i$; $\beta$ and $\mu$
estimated by the embedding (average over **100 realizations** for the distance matrices, a single realization
for visualisation). 129 annual maps 1870–2013.

**Observed effect sizes.** Link-prediction AUC $[0.95,1.00]$ per year; backbone $p(d_g)\propto d_g^{-0.7}$;
global hierarchy $H$: $<0.7\to\approx0.9$; the GDP–degree correlation inside the backbone is "extremely high"
while the unfiltered network gives only $r\approx0.3$–$0.4$ after WWII.

**Failure modes.** The embedding is estimated on a *filtered* graph — the distance result is not stable to
the filter choice, so the unfiltered (distance-independent) answer must be reported alongside. Trade
distance is a scalarised proxy for culture, borders and policy; do not interpret $d_h$ as kilometres.
Embedding coordinates are only comparable *within* a year (distances are normalised by $2R$ and $2\pi$).

### 2.2 Maximum-weight spanning tree backbone and strength tail
**Purpose.** Reduce a dense trade network to its $N-1$ dominant channels, and quantify how much value and how
much heterogeneity they retain.

**Formula.** Symmetrise the directed flows first,
$$w_{ij}(t)=\tfrac14\big(w^e_{ij}+w^i_{ij}+w^e_{ji}+w^i_{ji}\big),$$
then take the maximum-weight spanning tree $W^*(t)$ by running **Prim's algorithm on weights $-w_{ij}$**.
Strength, total weight, edge count and their tree counterparts:
$$s_i=\sum_j w_{ij},\qquad T=\sum_{i<j}w_{ij}=\tfrac12\sum_i s_i,\qquad E=\sum_{i<j}\mathbf 1(w_{ij}>0);$$
$$s_i^*,\;T^*,\;E^* \text{ from } W^*;\qquad \frac{T^*}{T},\quad \frac{E^*}{E},\quad
\frac{\langle w^*\rangle}{\langle w\rangle}=\frac{T^*/E^*}{T/E}.$$
Tail exponent of the tree strength distribution by Hill with a KS-optimal cutoff:
$$\hat\gamma = \frac{1}{k}\sum_{i=1}^{k}\ln\frac{s^*_{(i)}}{s^*_{(k+1)}}.$$

**Required inputs.** Annual bilateral trade values by direction (exports and imports) plus a GDP panel.

**Parameters & defaults.** No free parameters in the tree itself; $\alpha$ enters only the gravity comparison
(§2.3). Hill cutoff chosen by minimising the KS distance of the fitted tail.

**Observed effect sizes.** $T^*/T:0.55\to0.40$; $E^*/E:0.05\to0.02$; $\langle w^*\rangle/\langle w\rangle$
linear in $t$ over 1950–2000; $\hat\gamma\simeq2$ (time-independent).

**Failure modes.** The tree is *not* a clustering — it is a star-of-stars around the USA and Germany, so do
not read community structure from it. Reporting $T^*/T$ alone suggests the tree is losing importance; the
$\langle w^*\rangle/\langle w\rangle$ ratio reverses that conclusion, so report all three ratios. The
symmetric averaging $\tfrac14(\cdot)$ hides reporting asymmetries between partners that are themselves
informative.

### 2.3 Gravity model of trade *volumes* (distance-coefficient fit)
**Purpose.** Separate the size effect from the geography effect and produce a synthetic network for null
tests of any backbone method.

**Formula.**
$$\langle w_{ij}(t)\rangle=G\,\frac{x_i(t)\,x_j(t)}{r_{ij}^{\alpha(t)}},\qquad
\ln w_{ij}=\ln G+\ln x_i+\ln x_j-\alpha\ln r_{ij},$$
where $x_i$ is GDP and $r_{ij}$ the distance between capitals (km). Synthetic weights
$v_{ij}(t)=G\,x_i(t)x_j(t)\,r_{ij}^{-\alpha}\,\mathbf 1(w_{ij}(t)>0)$ keep the real binary support, and the
tree is recomputed on $-v_{ij}$.

**Required inputs.** GDP panel $\{x_i(t)\}$, capital-to-capital distances $r_{ij}$, and the real binary
support $\mathbf 1(w_{ij}>0)$.

**Parameters & defaults.** $G=1$ (irrelevant to tree structure and to all three ratios); **$\alpha=1.35$** is
the 1950–2000 average; **$\alpha=0$** is the no-geography null.

**Observed effect sizes.** $\alpha=0$ yields a US-centred star; $\alpha=1.35$ reproduces the real 2000 tree;
the real $T^*/T$ is closer to the $\alpha=0$ synthetic curve, yet $\langle v^*\rangle/\langle v\rangle$ matches
for both $\alpha$ values.

**Failure modes.** $\ln w_{ij}$ is undefined on the zero-trade pairs that dominate the full matrix — the paper
sidesteps this by fitting only on realised links; if the model is ever fitted on all pairs, use Poisson
pseudo-maximum-likelihood rather than log-OLS, otherwise the elasticity $\alpha$ is biased. $G$ and $\alpha$
do **not** affect the spanning tree, only the weights — so do not tune them to "improve" the tree.

### 2.4 Strength and entropy across single-layer / multiplex / multi-layer trade networks
**Purpose.** Measure how concentrated traded value is, and at which aggregation level, and track its drift
through the value chain.

**Formula.** For a directed representation with weights $w_{ij}$,
$$s_i^{\rm in}=\sum_j w_{ji},\qquad s_i^{\rm out}=\sum_j w_{ij};$$
normalised Shannon entropy of the strength sequence of length $L$:
$$H=-\sum_{l=1}^{L}p_l\ln p_l,\qquad p_l=\frac{s_l}{\sum_{h=1}^{L}s_h},\qquad \tilde H=\frac{H}{\ln L}.$$
The three representations give $L=43$ (single-layer, aggregated by country), $L=43\times57$ (multiplex, split
by industry of origin), and $L=43\times57\times57$ (multi-layer, split by industry pair, separating intra-
from cross-layer transactions).

**Required inputs.** A country$\times$industry$\times$industry input–output table (WIOD-style), with the
final-demand components; or, at minimum, a country$\times$industry export matrix for the multiplex case.

**Parameters & defaults.** Annual frequency 2000–2014; drop individual final-demand transactions with
negative totals ($\approx0.03\%$ of observations per year). Always normalise by $\ln L$ before comparing
across representations.

**Observed effect sizes.** $\tilde H$ strictly decreases single-layer $\to$ multiplex $\to$ multi-layer in
every year; the cross-layer entropy is always the lowest; the aggregate $\tilde H$ peaks in 2008.

**Failure modes.** The strength *distribution shape* is a function of the aggregation, not of the economy —
single-layer strengths show no heavy tail while multi-layer ones do, from identical data. Raw $H$ is not
comparable across representations because $L$ differs by up to $57^2$; only $\tilde H$ is. The 2008 peak is
an in-sample structural marker, not a forecasting rule.

### 2.5 Economic-complexity indices on a bipartite specialisation matrix (RVA / GCI / ETGCI)
**Purpose.** Rank countries by how *rare and sophisticated* their portfolio is, and domains by how
concentrated among sophisticated countries they are — the export-complexity machinery applied to any
country$\times$activity flow matrix (here, VC investment).

**Formula.** Revealed specialisation (RCA/RVA analogue)
$$M_{ij}=1\iff
\frac{S_{ij}\big/\sum_{j}S_{ij}}{\sum_{i}S_{ij}\big/\sum_{i,j}S_{ij}}\ge 1,\qquad M_{ij}=0\text{ otherwise},$$
with diversity $k_{c,i}=\sum_j M_{ij}$ and ubiquity $k_{t,j}=\sum_i M_{ij}$. The mutual definitions
$$x=\alpha\,M\,y,\qquad y=\beta\,M^{\!\top}x
\quad\Longrightarrow\quad MM^{\!\top}x=(\alpha\beta)^{-1}x,\qquad M^{\!\top}M\,y=(\alpha\beta)^{-1}y$$
give complexity as the **second** eigenvector of $MM^\top$ (countries) and $M^\top M$ (domains) — the leading
Perron–Frobenius component is removed because it only encodes diversification/ubiquity. Standardise each
eigenvector to zero mean, unit variance: the country vector is the **GCI**, the domain vector the **ETGCI**
(normalised to $[0,1]$ in the paper).

**Required inputs.** A country$\times$domain investment (or export, or patent) value matrix $S$; country
identifiers; a domain taxonomy.

**Parameters & defaults.** Binarisation robustness: (i) round each $S_{ij}$ up to the next \$100 M before
applying the threshold; (ii) use a two-year window $(t,t-1)$. Continuous alternatives (ECI+, GENEPY) are
reported to give consistent results. Domains/LLM-classifier: assign at most two domains per startup with a
probability threshold calibrated on $\ge$10 hand-labelled examples per domain.

**Observed effect sizes.** 2024 GCI: US 0.685 / Israel 0.680 / China 0.539 / France 0.505 / Japan 0.495 /
Germany 0.433 / Korea 0.381 / Singapore 0.331 / Switzerland 0.284 / India 0.280 / Netherlands 0.270 /
UK 0.233 / Brazil 0.220 / Canada 0.214 / Australia 0.203 / Sweden 0.149. ETGCI: Cloud 1.000,
Cybersecurity 0.895, Medtech 0.870, Defense 0.818, Autonomous Systems 0.723, AI 0.668, Raw Materials 0.000.
SSSET rank gains: Canada +6, Sweden +7, Netherlands +4, UK +4, Brazil +4.

**Failure modes.** Binarisation is threshold-sensitive — always run both robustness variants and the
continuous variant. Country attribution by *startup headquarters* abstracts from investor nationality, so
domestic sovereignty is overstated where foreign-controlled capital dominates. Crunchbase undercoverage
makes all totals lower bounds. Aggregating to a bloc (e.g. EU27) mechanically dilutes specialisation and can
erase a member's signal — do not pool flows before thresholding.

### 2.6 Network efficiency and efficiency-based robustness under node removal
**Purpose.** Quantify how much trade-flow efficiency survives when economies are removed (i.e. hit by
shocks), and *which* economies matter.

**Formula.** Directed, unweighted efficiency and its normalised loss
$$E=\frac{1}{N(N-1)}\sum_{i\ne j}\frac{1}{d_{ij}},\qquad
I(p)=\frac{E_p}{E},\qquad
R=\int_0^1 I(p)\,dp\approx\frac{1}{n}\sum_{k=1}^{n}I\!\left(p_k\right),\quad p_k=\frac{k}{n},$$
where $d_{ij}$ is the directed shortest path and $E_p$ the efficiency after removing fraction $p$ of nodes.
Removal is ordered by each of nine metrics — clustering coefficient, betweenness, PageRank, in-degree,
out-degree, in-closeness, out-closeness, authority, hub — under three strategies: **descend** (largest $I$
first), **ascend** (smallest first), **random**.

**Required inputs.** A directed weighted trade network (nodes = economies, directed edges = trade
relationships) at annual frequency; the nine node metrics computed on it.

**Parameters & defaults.** $p\in[0,1]$ in steps of $1/n$; **random removal repeated 20 times and averaged**;
recompute efficiency on the residual network each step.

**Observed effect sizes.** For 8 of 9 metrics $R^{\rm ascend}>R^{\rm random}>R^{\rm descend}$; clustering
inverts this ($R^{\rm random}$ largest impact). Import-side metrics (authority, in-closeness, in-degree) do
more damage than export-side (hub, out-closeness, out-degree). Efficiency: rise 2007–2010, flat 2010–2015,
fall after 2015 (2015 sales $-8.5\%$ y/y); robustness rises over the sample for all metrics except
clustering; the aggregated network is most robust, insecticides second.

**Failure modes.** Directed trade graphs contain many pairs with *no* directed path (share of $d>5$ was
$\approx0.5$ in 2007) — define efficiency on the largest connected component and state it. A single random
removal draw is not a benchmark; average 20. Ascending removal is not a curiosity — it exposes weak ties
whose loss breaks connectivity, and omitting it misses metrics for which "more" is not "worse".

### 2.7 Panel convergence regression on bilateral trade shares
**Purpose.** Test whether a country's trade share with its partners converges toward a common level over
time — a crude but concrete estimator for sectoral bilateral trade.

**Formula.** Neoclassical (Solow / Islam) absolute-convergence panel
$$\ln y_{i,t}-\ln y_{i,t-1}=c+\big(e^{-bT}-1\big)\ln y_{i,t-1}+u_{i,t},$$
estimated with fixed effects, random effects, and dynamic panel (Arellano–Bond DPD) estimators; convergence
requires the coefficient on $\ln y_{i,t-1}$ to be negative.

**Required inputs.** An annual panel of bilateral trade shares (import and export separately, absolute values
and as shares of each country's and each year's total) by product and partner.

**Parameters & defaults.** Five-year window 2006–2010; fixed vs random chosen by the Hausman test; DPD with
lagged levels as instruments.

**Observed effect sizes.** FE import coefficient $-0.943$ ($t=-18.24$, $R^2=0.512$, $N=449$); FE export
$-1.077$ ($t=-23.10$, $R^2=0.544$, $N=641$); DPD $[-1.51,-1.79]$ on 200–277 observations with 5 instruments.

**Failure modes.** Coefficients of magnitude $>1$ and a strongly significant constant signal a misspecified
model (omitted variables, as the paper admits); every series fails stationarity tests, so treat the result as
descriptive. Do not apply this to a network object — it is a panel econometric, not a structural estimator.

## 3. Data requirements → available endpoints

Rows below are real entries in `strategies/endpoints.json`; **gap** means no current provider can supply it.
The corpus's central input — the bilateral country-pair trade matrix — is absent, so almost every technique
above is *specified but not runnable* on live data.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Country GDP (gravity size term $x_i$) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicators via local gateway | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Equity daily prices (aligning shocks to listed firms) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Firm fundamentals (sector/R&D proxy for complexity) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Firm fundamentals (secondary) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| News stream (shock timing / event stamps) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Global news sentiment (shock detection) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited (HTTP 429) |
| Tradable symbol universe (mapping firms to countries) | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **Bilateral country×country trade values (annual matrix)** | — | — | — | **gap** |
| **Country×industry input–output table (WIOD/EXIOBASE)** | — | — | — | **gap** |
| **Geographic distance between capitals ($r_{ij}$)** | — | — | — | **gap** |
| **Firm/deal-level venture-capital data (Crunchbase-class)** | — | — | — | **gap** |
| **HS-6 commodity-level trade flows (UN Comtrade)** | — | — | — | **gap** |
| **Investor nationality / ultimate ownership of firms** | — | — | — | **gap** |

**What the gap costs, quantified.** The hyperbolic-atlas work needed 129 annual matrices spanning 1870–2013
from two merged historical sources (Correlates of War 1870–1996 plus a bespoke 1997–2013 database); the
spanning-tree study needed the Gleditsch bilateral panel for 1950–2000 (51 annual symmetric matrices, tens of
thousands of directed flows per year); the entropy study needed the WIOD, i.e. a $43\times57\times57$
country–industry–industry table per year for 2000–2014; the robustness study needed UN Comtrade flows for
five HS categories at annual frequency 2007–2018; the complexity study needed ~**32,654 startups / 115,991
rounds / \$4.3 T** of VC deals across 17 countries and 11 years. None of these is a per-symbol time series —
they are *relational* datasets keyed on country (and industry or firm) pairs, which is precisely the shape the
current catalog does not carry. Geographic distance and investor ownership are small static tables, not APIs.
The practical consequence: with today's endpoints one can build the *size* terms (GDP) and the *shock timing*
(news) but not the matrix that every estimator in §2 consumes.

## 4. Pitfalls, validation and measurement

- **The filter decides the answer.** The unfiltered trade network is almost distance-independent; the
  statistically significant backbone is a $d^{-0.7}$ power law (arXiv:1512.02233). Any distance or backbone
  claim must be reported for both the filtered and unfiltered graph, or it is an artefact of the threshold.
- **Report all three backbone ratios.** $T^*/T$ and $E^*/E$ both fall over time while
  $\langle w^*\rangle/\langle w\rangle$ rises; quoting only the first two reverses the conclusion
  (arXiv:1412.1618).
- **Aggregation level is a measurement choice, not a nuisance.** The same WIOD data yields a non-heavy-tailed
  strength distribution in the single-layer network and a heavy-tailed one in the multi-layer network, and
  three different entropy levels (arXiv:1809.07407). Fix and state the representation; normalise entropy by
  $\ln L$.
- **Binarisation/threshold sensitivity in complexity.** RCA/RVA thresholding is sensitive; the paper runs
  \$100 M rounding and a two-year window as robustness and reports consistent GENEPY/ECI+ results
  (arXiv:2604.09187). Never present one threshold's ranking as *the* ranking.
- **Look-ahead in the specialisation window.** The two-year window $(t,t-1)$ is the only temporal smoothing
  allowed; extending it forward leaks. Complexity rankings are persistent (2021–2024), so a single-year
  fluctuation is not news (arXiv:2604.09187).
- **Coverage and attribution bias.** Crunchbase undercoverage makes investment totals lower bounds, and
  headquarters-based nationality abstracts from investor control — both understate foreign dependence
  (arXiv:2604.09187).
- **Directedness and infinite paths.** In directed trade networks a large fraction of country pairs have no
  directed path at all (share of $d>5$ was $\approx0.5$ in 2007); efficiency is only defined on a stated
  connected component (arXiv:2302.13695).
- **Import-side vs export-side asymmetry.** Shocks to import-oriented economies (authority, in-closeness,
  in-degree) hurt efficiency far more than export-oriented ones (arXiv:2302.13695). Do not average the two
  sides into a single "centrality" shock.
- **Benchmark randomness.** Random node removal must be repeated (20 runs, averaged) before any
  descend/ascend ordering is claimed (arXiv:2302.13695).
- **Gravity predicts links, not volumes.** The connectivity gravity law reaches AUC $\approx0.95$+ for link
  *existence* (arXiv:1512.02233) while the volume gravity law fits *weights* with $\alpha\approx1.35$
  (arXiv:1412.1618); the two are different models and must not be cross-validated against each other's targets.
- **Memory / hysteresis.** The synthetic gravity tree overstates China's role relative to the real tree —
  trade adjusts to GDP with a lag, so a contemporaneous gravity fit is not a causal forecast
  (arXiv:1412.1618).
- **Non-stationarity invalidates naive convergence claims.** All Portuguese trade series fail stationarity
  tests and the convergence coefficients have $|\beta|>1$ with a large significant constant — a specification
  warning, not a finding (arXiv:1206.3387).
- **Negative weights before entropy.** WIOD final-demand entries can be negative; filter them
  ($\approx0.03\%$/year) before computing strengths or Shannon entropy, which requires non-negative weights
  (arXiv:1809.07407).
- **Null tests.** The correct null for a backbone/tree method is the gravity-synthetic network at $\alpha=0$
  (star) and $\alpha=1.35$ (real-like); a backbone that "works" without beating the $\alpha=1.35$ null is not
  evidence (arXiv:1412.1618).

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the layer can fetch today. Items 1–2 are runnable now; items 3–8 are
blocked on a static trade-matrix ingestion step.

1. **`GravitySizeTable` — country GDP panel.** *What:* pull GDP series from FRED `macro_data` and expose a
   `country -> x_i(t)` table with ISO keys. *Data:* `fred` `series/observations` (primary), moomoo
   `get_macro_indicator_list` (gateway fallback). *Value:* the size term for §2.1/§2.3 and the join key for
   every trade technique. *Pass:* reproduces the top-10 GDP ordering; joins cleanly to any incoming trade
   matrix by ISO code. *Effort:* S.
2. **`EconComplexityIndex` on a firm-fundamentals proxy.** *What:* implement §2.5 (RVA threshold, $MM^\top$
   eigenvector, standardisation) on a country$\times$sector matrix assembled from listed-firm fundamentals
   and revenue breakdowns. *Data:* `tiingo`/`alpha_vantage` `fundamental_data`, eodhd `exchange-symbol-list`
   for country mapping, moomoo `get_financials_revenue_breakdown` (gateway). *Value:* a working complexity
   pipeline that needs no relational trade data; directly reusable when a VC or trade matrix arrives. *Pass:*
   the same code recovers the published US/Israel top-2 and Cloud/Cybersecurity top-ETGCI on a
   Crunchbase-format sample, and is stable to the \$100 M-rounding and two-year-window variants. *Effort:* M.
3. **`BilateralTradeMatrix` ingestion (gap-filler).** *What:* register a static relational dataset
   (UN Comtrade bulk / Gleditsch / WIOD extract) as a new data category, loaded from disk, keyed
   `(reporter, partner, year, product)`. *Data:* the archive itself — **no endpoint serves it**. *Value:*
   unblocks items 4–7 entirely; without it the whole category is offline research. *Pass:* a documented
   loader that materialises an annual symmetric matrix and a directed graph. *Effort:* L.
4. **`TradeBackbone` — disparity filter + max-weight spanning tree.** *What:* §2.1 filter and §2.2 tree,
   emitting $T^*/T$, $E^*/E$, $\langle w^*\rangle/\langle w\rangle$, and the Hill strength-tail exponent.
   *Data:* item 3. *Value:* the canonical summary of trade structure and the cheapest structural monitor.
   *Pass:* $\hat\gamma\approx2\pm0.3$ and $T^*/T\in[0.4,0.55]$ on the historical panel; the tree beats the
   $\alpha=1.35$ gravity-synthetic null on $\langle w^*\rangle/\langle w\rangle$. *Effort:* M.
5. **`TradeEntropyMonitor`.** *What:* §2.4 normalised strength entropy, computed at whichever aggregations the
   ingested matrix supports (single-layer always; multiplex/multi-layer only with an input–output table).
   *Data:* item 3. *Value:* a slow-moving structural early-warning series. *Pass:* the single-layer $\tilde H$
   exceeds the multiplex exceeds the multi-layer value in every year, and the historical peak lands in 2008.
   *Effort:* M.
6. **`NetworkEfficiencyRobustness`.** *What:* §2.6 — directed efficiency $E$, the loss curve $I(p)$, and the
   area $R$ under the three removal strategies for the nine node metrics. *Data:* item 3. *Value:* stress-tests
   any trade network for import-side fragility. *Pass:* $R^{\rm ascend}>R^{\rm random}>R^{\rm descend}$ for
   8 of 9 metrics (clustering the exception), and import-side metrics dominate export-side. *Effort:* M.
7. **`ShockTiming` — news-driven economy-shock stamps.** *What:* convert the news streams into dated
   country-level shock events to drive the removal experiment (the paper's "shocks to economies" are
   simulated; real events are the natural replacement). *Data:* eodhd `news_data`, gdelt `news_sentiment`
   (rate-limited — cache and back off). *Value:* turns §2.6 from a synthetic experiment into an event study.
   *Pass:* the 2015 pesticide-market collapse is flagged in the news stream within the correct quarter.
   *Effort:* M.
8. **`BilateralConvergencePanel`.** *What:* §2.7 panel FE/RE/DPD on trade shares, with the Hausman test and
   stationarity diagnostics wired in. *Data:* item 3 (partner-level panel). *Value:* a defensible (if weak)
   econometric layer; low priority because the source paper is itself non-stationary. *Pass:* negative,
   significant convergence coefficient with stationarity diagnostics reported *before* the estimate.
   *Effort:* M.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 1512.02233v2 | The hidden hyperbolic geometry of international trade: World Trade Atlas 1870-2013 | 2015 |
| 1412.1618v1 | Spanning trees of the World Trade Web: real-world data and the gravity model of trade | 2014 |
| 1809.07407v2 | Unfolding the complexity of the global value chain: Strengths and entropy in the single-layer, multiplex, and multi-layer international trade networks | 2018 |
| 1206.3387v1 | Import and export of horticultural products in Portugal | 2012 |
| 2604.09187v1 | The Geoeconomics of Venture Capital: An Economic Complexity Approach to Emerging Technological Sovereignty | 2026 |
| 2302.13695v1 | Impact of shocks to economies on the efficiency and robustness of the international pesticide trade networks | 2023 |
