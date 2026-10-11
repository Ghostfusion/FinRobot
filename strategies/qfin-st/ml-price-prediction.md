# ML Price Prediction — learnings from the q-fin.ST corpus

`736` of 4372 corpus papers matched this category (731 with PDFs); this doc is based on a close reading of `6`.

Two of the six (the THieF hierarchy paper and the probabilistic-EPF review) are **electricity-price papers whose domain does not transfer to equities**; their *methodological layers* (forecast reconciliation, conformal calibration) do, and they are used that way in §2.5–2.6, but their feature sets, error scales and reported gains do not. This is flagged inline.

## 1. What the corpus actually offers

- **Inter-stock attention is near-uniform but the deviation is low-rank, and Nyström attention matches full attention.** MASTER's Step ➂ (inter-stock multi-head attention) holds 42.5% of parameters (329,216) and contributes the largest single ablation drop, ΔIC = −25.3% (full 0.0646 → no-Step➂ 0.0482 IC); mean per-row attention entropy is 5.63 nats vs ln(300)=5.70 (a 1.2% gap, perplexity 278/300), yet forcing exact uniformity destroys all cross-sectional discrimination because the deviation `D = A − (1/N)11ᵀ` carries 1.3% of output energy but 100% of cross-sectional variance. The deviation is low-rank: effective rank ≈ 65 of 300, top-10 singular values = 96.5% of $\lVert D\rVert_F^2$; median over 208 day×head matrices is rank 65 [IQR 45–81] (arXiv:2609.08106).
- **Sparsification fails, low-rank approximation succeeds.** GraphMask + correlation neighbours (IC 0.045±0.004) is *worse than deleting the module* (0.050±0.001); Top-K K=16 keeps ≤50% of either metric; Performer (random features) trails Nyström at the same m. Nyström m=32 (10.7% of N) matches full $O(N^2)$ attention: TOST equivalence at N=300 (5 seeds) with Rank IC within ±0.005 (p=0.003) and IC within ±0.008 (p=0.028), and at N=800 (10 seeds) both p=0.038/0.034 (arXiv:2609.08106).
- **Dynamic recomputation, not a stable backbone, carries the value.** Winter-freezing attention to the test-set time-average oracle recovers ~47% of Rank IC value but only ~9% of IC; a learned static rank-32 attention (LearnedLowRank) collapses to the no-attention floor. Attention decorrelates fully in ~20 trading days (cosine similarity lag-1 0.967, lag-5 0.665, lag-20 0.048) (arXiv:2609.08106).
- **Attention anti-correlates with return correlation** — it seeks *complementarity*, not co-movement: pooled Spearman ρ = −0.614 (n=73,910 pairs), −0.645 on the industry-labelled subset, partial −0.627 after controlling for industry, beta and volatility; negative on all 619 test days (per-day mean −0.215, sd 0.071). This explains why correlation-graph masking damps performance (arXiv:2609.08106).
- **Shifted Data Augmentation (SDA) plus cosine-with-warmup dominates architecture scaling for one-step index forecasting.** Best-in-study MAE fell from 42.24 (baseline) → 22.13 (generalized inverse-power + GeLU) → 17.45 (cosine annealing) → 11.26 (cosine + SDA) on VN30, and 422.5 → 214.4 → 122.2 → 35.21 on S&P 500; run-to-run MAE std fell from 3.74 → 0.03 (VN30) and 41.1 → 0.04 (S&P 500). With SDA, a 31K-parameter model matched multi-million-parameter models (arXiv:2606.15701).
- **Length = 5, shallow depth, moderate width.** Shortest input window (L=5) won on both indices; VN30 preferred 1 encoder–decoder layer, S&P 500 4–6; d_model 128–256 (S&P 500 64–128); scaling d_model 512→1024 raised params 7.6M→30M and *degraded* accuracy (arXiv:2606.15701).
- **Chaotic nonlinearities + volatility gating improve interval calibration.** BCF-GCN (correlation-graph GCN → logistic/tent chaotic fusion → LSTM → interval head) achieves the best Winkler score 0.0778 and PIAW 0.1407 at PICP 0.9660 vs LSTM 0.0827/0.1536/0.9710, GRU, GCN (0.0794/0.1422) and HGNN (0.0894/0.1574); Diebold–Mariano statistics −8.46 (vs GCN) to −30.54 (vs LSTM), all p<0.001. Ablation: removing the tent-chaos branch is the single most damaging (PIAW 0.1338 → 0.1432) (arXiv:2605.16324).
- **A 3-D PCA path carries persistent, interpretable latent curvature.** Expanding-window PCA of standardized log-returns (lagged loadings) captures 67.5% of variance in 3 components; local Gaussian curvature on the embedded path has mean K=−0.0207, sd 0.0186, ACF(1)=0.997 and regime shares P(K≤−0.01)=73.9%, P(|K|≤0.01)=24.4%, P(K≥0.01)=1.7%; a persistent-homology torus test fires on 88.4% of 4,251 windows. The full geometry-informed model (eigenvalue-weighted sleeves + curvature gating) reaches annualized Sharpe ≈0.64 vs risk-parity 0.439 and long-only 0.390, while the *native-space* baselines are negative (−0.386/−0.289) (arXiv:2511.05030).
- **[Electricity, non-transferable]** Temporal hierarchy reconciliation of hourly and 2–24h block forecasts improves accuracy at *every* level, up to 5.5% (hourly) and 13.4% (baseload) MAE, consistently across ARX, NARX, XGBoost and a 72M-parameter pretrained transformer, significant at 1% by a multivariate Diebold–Mariano test (arXiv:2508.11372).
- **[Electricity, non-transferable specifics]** Probabilistic EPF has shifted from Bayesian/Monte-Carlo/Distribution-based methods toward quantile regression (QR, QRA) and, since ~2020, conformal prediction (SCP/EnbPI/SPCI); CP gives distribution-free coverage guarantees but wider intervals, while QRA is sharper yet under-covers in volatile regimes (arXiv:2511.05523).

## 2. Implementable formulas & algorithms

### 2.1 Nyström low-rank inter-stock attention (arXiv:2609.08106)

**Purpose.** Scale cross-sectional (stock-vs-stock) attention to large universes at $O(mN)$ instead of $O(N^2)$ without losing ranking power.

**Formula (Nyströmformer form).** With queries/keys/values $Q,K,V\in\mathbb{R}^{N\times d}$ and $m\ll N$ random landmarks $\tilde Q,\tilde K$:
$$\text{Attn}(Q,K,V)\;\approx\;\text{softmax}\!\Big(\frac{Q\tilde K^\top}{\sqrt d}\Big)\,\Big(\text{softmax}\!\Big(\frac{\tilde Q\tilde K^\top}{\sqrt d}\Big)\Big)^{+}\,\text{softmax}\!\Big(\frac{\tilde Q K^\top}{\sqrt d}\Big)V,$$
where $(\cdot)^{+}$ is a Moore–Penrose pseudo-inverse computed with **6 Newton–Schulz iterations** so no $N\times N$ matrix is materialised. The full-attention baseline is $z_{u,t}=\sum_v \alpha_{uv}^{(t)}V_v^{(t)}$, $\alpha^{(t)}=\text{softmax}(Q^{(t)}K^{(t)\top}/\sqrt d)$.

**Inputs.** Per-stock feature vectors from temporal attention: Alpha158-style technical factors, market-index features, and lagged returns, all aligned to a daily cross-section.

**Parameters / defaults reported.** $m=32$ landmarks (10.7% of N=300, 4% of N=800), sampled uniformly at random *each forward pass*; 6 Newton–Schulz iterations; Adam; stop when train loss ≤ 0.95. Performance is **non-monotonic** in $m$: peak at $m=32$, dip at $m=48$ (1.2σ below), below peak at 64–128 — because Nyström landmarks do not map 1:1 to SVD components and over-sizing worsens pseudo-inverse conditioning. Optimal $m\approx32$ was stable from N=300 to N=800.

**Observed effect sizes.** Equivalence to full attention certified by TOST; latency crossover at $N^\*\approx1{,}300$ (at N=300 Nyström is *slower*, 5.90 vs 1.65 ms, due to the ~4 ms fixed pseudo-inverse overhead); at N=3500 5.5× faster / 4.5× less memory, at N=9000 14.7×/11.2×; full attention OOMs at N=12,000 where Nyström needs 974 MB. Lower seed-to-seed IC variance than full attention (0.002 vs 0.007).

**Failure modes.** (i) Benefits do **not** transfer to $N\approx3{,}500$ with adapted architectures: no cross-stock module beats a per-stock LSTM (MASTER+Nyst32 vs PureLSTM IC p=0.27, Rank IC p=0.53; n=4). (ii) Equivalence weakens under per-day cross-sectional z-scoring: full-attention IC improves +0.005 and the Rank IC TOST p degrades 0.003 → 0.120, i.e. the margin is partly an artefact of default Qlib global robust z-scoring. (iii) Sparse/graph attention must not be substituted — it destroys the near-global support the mechanism depends on.

### 2.2 Shifted Data Augmentation + LR schedules + GeLU/dropout (arXiv:2606.15701)

**Purpose.** Stabilise noisy, non-stationary one-step index/price-level forecasting and remove hyperparameter sensitivity.

**SDA formula.** Replicate the training series with constant additive offsets:
$$X^{(c)}=\{x_t+c\mid t=0,\dots,T\},\qquad X_{\text{aug}}=X\cup\bigcup_{c\in C}X^{(c)}.$$
Reported offsets: $C=\{750\}$ for VN30, $C=\{4000\}$ for S&P 500 — chosen to extend the training value range toward plausible unseen levels. Temporal structure is preserved exactly (unlike noise injection / warping / permutation).

**Learning-rate schedules.**
- Generalized inverse-power: $lr = d_{\text{model}}^{-k}\cdot\min\!\big(step^{-k},\; step\cdot warmup\_steps^{-(1+k)}\big)$; $k=0.5$ recovers the original Transformer schedule. Best $k=0.8$–$0.9$ (datasets sensitive: MAE fell monotonically as $k$ went 0.5→0.9).
- Cosine with warmup: warmup $lr = lr_{\text{base}}\cdot step/warmup\_steps$; then $lr = lr_{\min} + \tfrac{lr_{\text{base}}-lr_{\min}}{2}\big(1+\cos(\pi\frac{step-warmup}{total-warmup})\big)$. Defaults $lr_{\text{base}}=10^{-4}$, $lr_{\min}=10^{-6}$, warmup 3000, total 15000.

**Architecture recipe.** Encoder–decoder Transformer; scalar input projected to $d_{\text{model}}$, sinusoidal PE, scaled by $\sqrt{d_{\text{model}}}$; **GeLU** ($\text{GeLU}(x)=x\Phi(x)$) instead of ReLU in the FFN; dropout on sublayer outputs **before** residual+LayerNorm but **not** at the embedding stage; MSE loss; Adam $\beta_1=0.9,\beta_2=0.999,\epsilon=10^{-8}$.

**Parameters / defaults.** With cosine annealing, best dropout was extreme ($p_{\text{drop}}=0.9$); with the inverse-power schedule, best dropout was 0 ($p_{\text{drop}}>0$ degraded it). Best $h$: 16 (inverse-power) / up to 16 (cosine), but insensitive once SDA is on. Best $L=5$. Best depth 1 (VN30) / 4–6 (S&P 500). Best $d_{\text{model}}$ 128–256.

**Observed effect sizes.** GeLU vs ReLU at $k=0.8$: VN30 MAE 37.76→27.60 (RMSE 75.25→51.71); S&P 500 MAE 439.9→233.2. Cosine vs inverse-power: −30% (VN30) / −50% (S&P 500) MAE; +SDA: −35% / −71% MAE over cosine-only. SDA collapsed run-to-run std by 2–3 orders of magnitude and made dropout/activation/head-count choices nearly irrelevant.

**Failure modes / caveats.** (i) The offset constants are hand-picked per dataset from knowledge of the test value range — a form of analyst look-ahead; a production version must choose $c$ only from training-range information. (ii) The near-zero SDA variance (MAE sd 0.03) and MAPE 0.64–0.80% are strikingly low for a *price-level* (not return) target; treat the reported magnitude as an upper bound and validate on a held-out regime where the index leaves the training range. (iii) Augmenting raw price levels with constant offsets is not equivalent to augmenting returns; apply SDA to the level series only if the model is trained on levels, and prefer return-space augmentation otherwise.

### 2.3 Bi-level chaotic fusion + LUBE prediction intervals (arXiv:2605.16324)

**Purpose.** Produce calibrated, sharp prediction intervals (not point forecasts) from a spatio-temporal stock graph.

**Graph.** Edge iff $|{\rm Corr}(r_i,r_j)|\ge 0.30$ (Pearson on daily returns, built on the **training window only**); 2-layer GCN with renormalised adjacency $H^{(l+1)}=\sigma(\tilde D^{-1/2}\tilde A\tilde D^{-1/2}H^{(l)}W^{(l)})$, batch-norm per layer, then $\tanh$ clipping $z_{\text{raw}}=\tanh(3H^{(2)})$ to $[-1,1]$.

**Chaotic fusion (BL-CFT).** Logistic branch for the interval centre and tent branch for the width:
$$C_l(x)=r\,x\,(1-x),\quad r\in[3.57,4.0]\ \text{(learnable)},$$
$$C_t(x)=\begin{cases}2x,&x<0.5\\ 2(1-x),&x\ge0.5\end{cases}$$
each applied after normalise→sigmoid→map→rescale with a residual skip and a stock-wise learned perturbation strength $\alpha$:
$$z_{\text{center}}=z_{\text{raw}}+\alpha_{\log}(z_{\text{raw}})\cdot\text{Rescale}\big(C_l(\text{Sigmoid}(\text{Norm}(z_{\text{raw}})))\big),$$
$$z_{\text{width}}=z_{\text{raw}}+\alpha_{\text{tent}}(z_{\text{raw}})\cdot\text{Rescale}\big(C_t(\text{Sigmoid}(\text{Norm}(z_{\text{raw}})))\big).$$
Volatility-aware gate (no regime label needed): $g=\sigma(FC_2(\text{ReLU}(FC_1(z_{\text{raw}}))))$, then $z_{\text{center}}^g=g\,z_{\text{center}}$, $z_{\text{width}}^g=(1-g)\,z_{\text{width}}$.

**Interval head + LUBE loss.** With $T=40$ lookback fed to a 2×128 LSTM:
$$\text{center}=\tanh(FC_c(h^\*))\times0.5,\qquad \text{width}=\text{softplus}(FC_w(h^\*))+0.002,\qquad [L,U]=[\text{center}\mp\text{width}],$$
$$\mathcal L_{\text{LUBE}}=\lambda_w\,\text{PIAW}+\lambda_u\,\text{ReLU}(\alpha-\text{PICP})+\lambda_o\,\text{ReLU}(\text{PICP}-\alpha),\quad(\lambda_w,\lambda_u,\lambda_o)=(30,10,15).$$

**Parameters / defaults.** lookback 40 days; GCN hidden 64; LSTM 2 layers × 128; dropout 0.15; Adam lr 1e-3, weight-decay 1e-4; ReduceLROnPlateau; grad-norm clip 3.0; early-stop patience 40; 200 max epochs; chronological 70/15/15 split; stochastic snapshot sampling of 40 train + 20 val windows per epoch; ADF test on returns before training.

**Observed effect sizes.** Winkler 0.0778 / PIAW 0.1407 / PICP 0.9660 vs HGNN 0.0894/0.1574/0.9470; ablation (tent chaos removed) PIAW 0.1338→0.1432 and Winkler 0.0763→0.0792; adaptive-$\alpha$ → static-$\alpha$ marginally worse; DM tests all p<0.001. Multi-seed (42/123/456) PICP/PIAW stable to 4 dp.

**Failure modes.** (i) 43 stocks, 8 NSE sectors, 2016–2026 — small cross-section and single market; graph edges are a *static* training-window correlation graph, so sector-correlation breaks (earnings, shocks) are unmodelled (the authors list dynamic graphs as future work). (ii) The coverage target is stated inconsistently (α=0.90 "desired", text also writes PICP ≈ 1−α and mentions α=0.05); pin α explicitly in any reimplementation. (iii) The main table (PIAW 0.1407) and the ablation table (PIAW 0.1338) use different reference values for the same "full" model — reconcile before reusing numbers. (iv) PICP > nominal (0.966 vs 0.90) means intervals are wider than needed; DStat=1.000 for *every* model shows the directional metric has no discriminating power here, so use DM on interval-score losses, not DStat.

### 2.4 Manifold-geometry features + tangent-space forecasting (arXiv:2511.05030)

**Purpose.** Exploit persistent latent *curvature* of a low-dimensional market embedding as both a regime signal and a feature.

**Embedding.** Standardised log-returns $R_t\in\mathbb R^N$; expanding-window PCA; **lagged** loadings to avoid look-ahead: $p_{i,t}=u_{i,t-1}^\top R_t$, $i=1,2,3$; $X_t=(\sum_{s\le t}p_{1,s},\sum p_{2,s},\sum p_{3,s})\in\mathbb R^3$.

**Curvature feature.** Local weighted quadratic Monge patch by least squares,
$$z=ax^2+bxy+cy^2+dx+ey+f,\qquad \hat\beta=(A^\top W_t^2 A)^{-1}A^\top W_t^2 z,$$
$$K_t\approx\frac{4\hat a_t\hat c_t-\hat b_t^2}{1+4\hat a_t^2+\hat b_t^2+4\hat c_t^2}.$$
Geometry decision: **torus** if a Takens delay embedding $T_t=(X_s,X_{s-\tau},\dots,X_{s-(m-1)\tau})$ over the window has ≥2 long-lived $H_1$ bars (Vietoris–Rips persistent homology, $\beta_1=2$); else sphere if $K_t\ge\kappa_+$, hyperbolic if $K_t\le-\kappa_-$, else Euclidean. Reported thresholds $(\kappa_+,\kappa_-)=(+0.01,-0.01)$; torus flag additionally needs $\#\{\text{long }H_1\}\ge2$, a concentration ratio in [0.4,0.7], and the second lifetime above a phase-randomised-surrogate 95th percentile.

**Forecasting.** (1) infer geometry; (2) tangent velocity $v_t=P(X_{t-1})(X_t-X_{t-1})$ with $P=I-nn^\top$; (3) tangent-space PCA → coefficients $c_t\in\mathbb R^d$; (4) fit **VAR(p=25)** to $\{c_t\}$ and forecast; (5) lift back with the exponential map. Native-space (plain VAR on $X_t$) is the explicit comparator.

**Trading translation.** $s_{k,t+1}=\text{sign}(\Delta\hat X_{k,t+1})/\hat\sigma_{k,t}$ with $\hat\sigma_{k,t}$ the 500-day rolling std of increments; eigenvalue-weighted sleeves $C_{i,t}=\lambda_i(t)/\sum_j\lambda_j(t)$; Sharpe annualised by $\sqrt{252}$.

**Observed effect sizes.** Full GIM Sharpe ≈0.64 vs RP 0.439 (+0.199) and LO 0.390 (+0.248); native-space baselines −0.386/−0.289. Curvature regimes are persistent (ACF(1)=0.997) and coherent with macro history (2007–2010 flat, 2011–2020 hyperbolic, 2021 torus-like, 2022–2025 hyperbolic).

**Failure modes.** (i) Curvature thresholds are arbitrary in magnitude and the estimator is a Monge patch — pre-smoothing and a minimum window size $m_0$ are required or $K_t$ is noise. (ii) The torus test is "heuristic but informative": $H_1$ bars are stable but $H_2$ is not, and persistence thresholds need surrogate calibration. (iii) In a genuinely flat (Euclidean) data-generating process the pipeline correctly collapses to inverse-vol + linear forecasts — so gains must be shown against a *matched* native-space baseline, as the paper does, or they are illusory. (iv) The paper is a single multi-asset universe (equities, sectors, rates, credit, commodities, vol) with a single reported Sharpe, no multi-seed confidence interval — treat 0.64 as a point estimate.

### 2.5 Temporal hierarchy forecast reconciliation — THieF (arXiv:2508.11372, **electricity; methodology transfers**)

**Purpose.** Make forecasts of a series at several non-overlapping temporal aggregation levels coherent, and gain accuracy by combining levels.

**Formula.** For frequency $m$ (24 for hourly→daily), divisors $k_i$ give the summing matrix $S= [S_{k_p}^\top \dots S_{k_1}^\top]^\top$ with $S_k=s_k I_{m/k}\otimes J_{1,k}$, $s_k=1/k$. With base forecasts $\hat P_d$ and error covariance $W$:
$$\tilde P_d = S(S^\top W^{-1}S)^{-1}S^\top W^{-1}\hat P_d.$$
**Use mean-aggregation weights** ($s_k=1/k$), not sum weights, which normalises $W$. Estimate $W$ with **constant-correlation shrinkage (Ledoit–Wolf)** or diagonal-target shrinkage (Schäfer–Strimmer); plain variance-scaling (WLS, off-diagonals zero) removes most of the gain — error correlation is necessary.

**Inputs (electricity-specific).** Day-ahead load and wind forecasts, lagged same-block prices, previous-day min/max price, coal (API2) and gas (TTF) futures, weekday dummies; variance-stabilise with $\operatorname{asinh}((y-\hat\mu_y)/\hat\sigma_y)$ estimated on the training window only.

**Parameters / defaults.** 7 yearly lags; 3-year rolling window rolled daily; 60 blocks total; per-block models (ARX/OLS, NARX 5-tanh-hidden committee of 10, XGBoost with Bayesian HPO, or a pretrained transformer).

**Observed effect sizes.** Up to 5.5% hourly and 13.4% baseload MAE reduction (XGB, Germany 24H: 29.50 → 25.54); mean XGB gain 6.7% (Germany) / 4.8% (Spain); significant at 1% via multivariate DM on the L2 norm; reconciliation cost ≈2.5× the single-level baseline (sub-second per model per day).

**Transfer to equities.** The reconciliation *layer* applies directly to any multi-horizon or multi-aggregation target (e.g. coherency between daily-return forecasts and weekly/monthly sleeve forecasts, or between per-stock forecasts and an index/sector aggregate). The electricity feature set, the 13.4% number and the block-trading rationale **do not transfer**.

### 2.6 Conformal / quantile interval layer (arXiv:2511.05523, review, **electricity-focused**)

**Purpose.** Wrap any point model with a distribution-free interval that has a coverage guarantee, and/or combine several point forecasts into quantiles.

**Formulas.**
- Quantile regression check loss: $\hat\beta_\alpha=\arg\min_\beta\sum_t\rho_\alpha(y_t-x_t^\top\beta)$ with $\rho_\alpha(u)=\alpha u$ for $u\ge0$, $(\alpha-1)u$ otherwise; $\Sigma_\alpha=\alpha(1-\alpha)\,f_{y|x}(\hat q_\alpha)^{-2}(X'X)^{-1}$.
- QRA: apply QR to the vector of $M$ point forecasts as regressors.
- Split CP: nonconformity $A=|y-f(x)|$, threshold $\lambda$ = the $\lceil(1-\alpha)(N+1)\rceil$-th smallest calibration score, interval $[f(x)-\lambda,f(x)+\lambda]$.
- EnbPI: $B$ bootstrap ensembles, average prediction ± quantile-$\alpha$ of leave-one-out residuals.
- SPCI: sequentially update the residual quantile; asymptotic conditional coverage $\lim_{t\to\infty}P(y_{t+1}\in\Gamma\mid X_t)\ge1-2\alpha$.
- Coverage/sharpness: PICP (target nominal), PIAW, Winkler score, CWC.

**Observed.** QRA sharp but under-covers in volatile regimes; CP valid but wider; **SPCI and EnbPI** give the best validity/economic balance in the most volatile market studied (balancing), where CP hybrids beat QR/QRA on both coverage and trading P&L. SCP is valid but over-conservative; exchangeability fails on time series so standard SCP needs the EnbPI/SPCI variants.

**Transfer.** Interval construction is model-agnostic and applies to equity return/log-price forecasts unchanged; the specific studies, markets and gains are electricity. Note the review's own headline gap — no standardised benchmarks — so a FinRobot implementation must define its own coverage test.

## 3. Data requirements → available endpoints

Endpoint rows are from `strategies/endpoints.json` (54 live-probed rows, 17 providers). Note that `yfinance` leads several `PRIORITY` groups in `finrobot/engine/data/categories.py` but declares no endpoint catalog and is therefore not cited below. Probe status is the recorded `ok`/`code` (`ok`, `gateway`, `auth`, `rate_limited`, `connect`, `http`).

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily adjusted OHLCV (universe panel) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily prices (alt source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily prices (alt source) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Daily prices / realtime | `https://api.stockdata.org/v1/data/eod` | core_stock_apis | stockdata | ok |
| Daily aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Quote / snapshot (incl. index proxies) | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway (SDK, local OpenD) |
| K-line / intraday bars | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway |
| Technical indicators (RSI/MACD/…) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Alpha158-style factor set (Source-1: all features) | **gap** — must be computed locally from OHLCV; no provider returns Alpha158 | technical_indicators | — | gap |
| Market-index features for MASTER-style gating | `https://eodhd.com/api/eod/AAPL` (index ticker, e.g. `GSPC.INDX`) | core_stock_apis | eodhd | ok |
| Universe / listing metadata | `https://eodhd.com/api/exchange-symbol-list/US` | exchange_symbols | eodhd | ok |
| Sector / industry membership (for graph edges or GCN) | **gap** — no probed row returns industry labels | — | — | gap |
| Cross-sectional volatility / beta / turnover (SVD-factor labels) | Derived from OHLCV (above) | core_stock_apis | eodhd | ok (derived) |
| Macro state triad: output gap, inflation, policy rate | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Risk-free rate (Sharpe / discounting) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Earnings dates (event dummies / ex-earnings splits) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | earnings_calendar | benzinga | ok |
| Earnings price-move history | `moomoo://get_financials_earnings_price_move` | earnings_surprise | moomoo | gateway |
| Analyst ratings / revisions (sentiment feature) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| News sentiment score (feature) | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| News sentiment (alt) | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| Macro news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate_limited (HTTP 429) |
| Options implied vol / surface (interval benchmarks, vol features) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Expected move (forward vol proxy) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Short interest (feature) | `moomoo://get_short_interest` | short_interest | moomoo | gateway |
| Institutional holdings (feature) | `moomoo://get_shareholders_institutional` | institution_data | moomoo | gateway |
| Capital flow (feature) | `moomoo://get_capital_flow` | capital_flow | moomoo | gateway |
| Market breadth (regime feature) | `moomoo://get_rise_fall_distribution` | market_breadth | moomoo | gateway |
| Insider trades (feature) | `moomoo://get_insider_trade_list` | smart_money | moomoo | gateway |
| Event / election probabilities (exogenous feature) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| **Electricity-only inputs** (load forecast, wind forecast, coal API2, gas TTF, block products) | **gap** — no provider in the data layer supplies power-market fundamentals | — | — | gap |
| Reported fundamental statement data (feature) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | fundamental_data | tiingo | ok |

## 4. Pitfalls, validation and measurement

- **Single-seed results in financial ML are not evidence.** arXiv:2609.08106 documents a case where a single-seed (seed 42) result suggested a consistent IC↑/Rank IC↓ trade-off across all cross-stock module types, and a 5-seed analysis suggested a Nyström gap at N=800 — both vanished with more seeds (10 seeds → IC p=0.038, RankIC p=0.034 equivalent). At N≈3,500 seed-to-seed IC std was 4× that at N=300 (0.008 vs 0.002). **Rule: every claimed improvement needs ≥5, preferably 10, seeds and a paired test; report seed variance.**
- **Use equivalence testing, not just difference testing, for "as good as" claims.** The Nyström result is certified with TOST at a pre-registered margin (±0.005 Rank IC, ±0.008 IC), which is far more informative than a non-significant t-test.
- **Significance of forecast improvements must be a Diebold–Mariano (or multivariate DM) test on the loss series**, as in arXiv:2605.16324 (interval-score losses, all p<0.001) and arXiv:2508.11372 (multivariate DM on the L2 norm). Raw mean-metric comparisons are not enough.
- **Leakage controls that actually appear in the corpus** (adopt all of them):
  1. Build correlation graphs only from training-window returns (arXiv:2605.16324); never from the full sample.
  2. Use lagged PCA loadings for eigenportfolios — composition known at the close of $t-1$ (arXiv:2511.05030: $p_{i,t}=u_{i,t-1}^\top R_t$).
  3. Chronological 70/15/15 splits and rolling one-step-ahead evaluation with **no re-training during the test period**, all preprocessing (scaling, graph construction) fit on train only (arXiv:2605.16324).
  4. Fit normalisation statistics ($\hat\mu_y,\hat\sigma_y$, z-score $\bar x,s$) on the training window only and freeze them for test (arXiv:2606.15701, arXiv:2508.11372).
  5. Use a label with a gap: MASTER's label is $\text{close}(t+5)/\text{close}(t+1)-1$ — a 4-day forward return with a one-day gap, so the feature window cannot touch the target window (arXiv:2609.08106).
- **Do not mix up IC and Rank IC.** In arXiv:2609.08106 IC scales with aggregation *breadth* while Rank IC scales with weight *sharpness*, and removing the temporal-aggregation step *raises* Rank IC by 5.4% while lowering IC by 6.3%. Pick the metric that matches the downstream use (continuous position sizing → IC; top-K selection → Rank IC) before tuning.
- **Cross-sectional vs per-stock modelling is scale-dependent.** Evidence of a large benefit from cross-stock attention at N≈300–800 did not survive at N≈3,500 (no module beat a per-stock LSTM, n=4). Validate the cross-sectional machinery at the universe size FinRobot will actually trade.
- **Domain transfer of "power price" papers.** arXiv:2508.11372 (THieF) and arXiv:2511.05523 (probabilistic EPF review) are trained and evaluated on day-ahead/intraday/balancing *electricity* markets: features are load/wind/coal/gas, prices go negative and spike to ±500 EUR/MWh, and the traded objects are hourly and block products. Their *decoupling* structure (temporal reconciliation, conformal recalibration) transfers; their features, error magnitudes and reported percentage gains do not. Cite them only for the method layer.
- **Interval calibration must be checked, not assumed.** Require PICP close to (not far above) nominal — BCF-GCN over-covers (0.966 at a 0.90 target), which means the intervals are needlessly wide; the review (arXiv:2511.05523) shows QR/QRA under-cover in volatile regimes while CP over-widens, so test conditional coverage (Christoffersen), not just marginal coverage.
- **Over-smoothing and static graphs are the failure mode of graph models** (arXiv:2605.16324): repeated GCN aggregation makes node embeddings similar, degrading interval sharpness, and static correlation clusters break on shocks. Chaotic nonlinearities mitigate the former; a dynamic graph is needed for the latter.
- **Beware spurious geometry.** Any curvature/topology pipeline must pass the Euclidean null control of arXiv:2511.05030 (equicorrelated Brownian motion, $\Sigma_\rho=\rho\mathbf{11}^\top+(1-\rho)I$, eigenvalues $\lambda_1=1+(n-1)\rho$, $\lambda_{2..n}=1-\rho$) and correctly report *flat*. If your estimator finds curvature in a flat null, it is detecting the PCA embedding, not the market.
- **How to test an implementation is sound.** (1) Reproduce the null/floor baselines first (no-module, uniform-attention, per-stock LSTM, native-space VAR, random-walk/naive for Theil's U). (2) Run ≥5 seeds, report mean±sd. (3) Report paired DM/TOST. (4) Evaluate only on out-of-range regimes (test values outside the training range) for level-target models. (5) Include friction: the Nyström paper's Sharpes (5.6) are explicitly frictionless and in a short-restricted market, so they are not achievable as-is.

## 5. Recommended first implementation in FinRobot

1. **Cross-sectional ranking model with Nyström inter-stock attention.** Build a per-day cross-section from `core_stock_apis` (eodhd `…/eod`), compute Alpha158/technical factors locally, feed intra-stock temporal attention then Nyström inter-stock attention with $m=32$ landmarks, and predict a 4-day forward return with a 1-day gap. Evaluate with IC/Rank IC/ICIR over ≥10 seeds and TOST against full attention. *Data:* OHLCV panel (eodhd ok) + index proxy for gating. *Value:* high (the single largest ablated component, −25.3% IC). *Risk:* benefits may not transfer at FinRobot's universe size — validate at the target N before committing. *Effort:* L.
2. **Interval/conformal layer as a wrapper on any point model.** Implement split CP first (cheap, valid), then EnbPI and SPCI, using interval-score losses and PICP/PIAW/Winkler/CWC plus conditional-coverage tests; never tune α post hoc. *Data:* residuals of an existing point model; requires only a return series. *Value:* high — turns point forecasts into risk-aware outputs and is model-agnostic. *Risk:* over-wide intervals if exchangeability is naively assumed; must use the time-series variants. *Effort:* S.
3. **Shifted Data Augmentation + cosine-warmup scheduler for the one-step regression head.** Apply SDA to the training series (choose offsets from training range only), GeLU, dropout-before-residual (not at embedding), L=5 window, Adam. *Data:* daily close panel (eodhd/tiingo ok). *Value:* medium–high — the largest reported single accuracy gain and it removes hyperparameter sensitivity. *Risk:* the reported near-zero variance is suspicious for a level target; validate on out-of-range test data. *Effort:* S.
4. **Prediction-interval module with graph + LUBE (BCF-GCN pattern).** Correlation-graph GCN (|ρ|≥0.30, train-only edges) → LSTM → dual centre/width heads trained on the LUBE loss with $\lambda=(30,10,15)$, top-40-day lookback, 70/15/15 chronological split. *Data:* OHLCV panel + sector labels (**gap** — must be sourced; eodhd symbol list has no industry field, so either obtain a GICS/Shenwan mapping or fall back to a returns-correlation graph). *Value:* medium–high — calibrated intervals directly usable for position sizing. *Risk:* static graph and the small reported cross-section. *Effort:* M–L.
5. **Manifold-curvature regime feature.** Compute the 3-D lagged-PCA embedding, the rolling Monge-patch Gaussian curvature $K_t$, and the threshold-based geometry label; expose $K_t$ as (a) a feature and (b) a risk-budget gate (expand risk when $K_t<0$, contract when $K_t>0$). Ship it **with** the Euclidean null control and a native-space comparator. *Data:* a multi-asset return panel (eodhd ok) + macro triad from fred (ok) for interpretation. *Value:* medium — a persistent, low-cost regime signal (ACF(1)=0.997). *Risk:* arbitrary thresholds; must pre-smooth and validate against the flat null. *Effort:* M.
6. **Temporal-hierarchy reconciliation for multi-horizon FinRobot forecasts.** Enforce coherency between per-stock forecasts and index/sector aggregates (or between daily and weekly sleeve forecasts) via $S(S^\top W^{-1}S)^{-1}S^\top W^{-1}$ with constant-correlation shrinkage on the error covariance. *Data:* only FinRobot's own forecast errors; no external feed. *Value:* medium — near-free accuracy at aggregation levels. *Risk:* electricity-only evidence; verify on equity data that error correlation is material (variance-scaling alone showed it is not optional). *Effort:* S–M.
7. **Feature-enrichment recipes from the corpus, wired to real endpoints.** Add (i) news sentiment from eodhd `/api/sentiments` and alpha_vantage (both ok); (ii) macro state from fred (ok); (iii) event dummies from benzinga earnings calendar (ok); (iv) prediction-market probabilities from polymarket (ok); treat moomoo-gateway categories (short interest, capital flow, breadth, insider/expected-move) as **conditionally available** only when the local OpenD gateway is up (`ok:false`, code `gateway`). Do **not** design a strategy that hard-depends on a gateway-only row or on a single provider: moomoo rows need the local OpenD gateway, and gdelt is rate-limited (429) — while cboe and federal_reserve both probe `ok`, their earlier `HTTP 307`/`ReadTimeout` results were probe bugs (a non-followed redirect; a 15 s timeout against a ~17 s CSV), fixed and re-probed 2026-10-10. *Value:* medium — orthogonal signal, honest availability. *Risk:* sentiment/event leakage (must be timestamped before the prediction cut-off). *Effort:* M.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2609.08106 | Nyström Attention Matches Full Attention for Cross-Sectional Stock Prediction | 2026 |
| 2606.15701 | Robust Transformer-Based One-Step Stock Index Forecasting via Shifted Data Augmentation | 2026 |
| 2605.16324 | Bi-Level Chaotic Fusion Based Graph Convolutional Network for Stock Market Prediction Interval | 2026 |
| 2511.05030 | The Shape of Markets: Machine learning Modeling and Prediction Using 2-Manifold Geometries | 2025 |
| 2508.11372 | Stealing Accuracy: Predicting Day-ahead Electricity Prices with Temporal Hierarchy Forecasting (THieF) | 2025 |
| 2511.05523 | The Evolution of Probabilistic Price Forecasting Techniques: A Review of the Day-Ahead, Intra-Day, and Balancing Markets | 2025 |
