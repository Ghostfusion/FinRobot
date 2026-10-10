# Regime Switching — learnings from the q-fin.ST corpus

135 of 4372 corpus papers matched this category; this doc is based on a close reading of 6.

Scope note: the six assigned papers are all on-topic for *state inference you can run* (continuous HMM with heavy-tailed emissions, multi-scale Markov-switching GARCH, Bayesian multi-change-point on a correlation metric, graph-similarity network change-point detection, copula–Markov change-point on a heavy-tailed positive series). One — the Dirichlet-ARMA structural-break paper (arXiv:2601.16821) — is only partly on-topic: its data are hospitality compositions, not returns, and it contributes the *smooth-transition break timing* mechanism (logistic gate + direction/amplitude decomposition), which is relevant to regime-transition timing and calibration rather than to return-regime state inference. It is flagged where used.

---

## 1. What the corpus actually offers

- **A low-state continuous HMM with a heavy-tailed emission reproduces the three symmetric Cont stylized facts** (heavy tails, negligible linear ACF of raw returns, slow decay of |return| ACF) that Rydén et al.'s K=2–3 Gaussian HMM could not. On SPY 2014-01-03…2024-01-03 (T_IS=2516) observed excess kurtosis is 7.68 in-sample / 5.29 out-of-sample; CHMM-N reaches 91.5% IS / 78.0% OoS KS pass rate at K⋆=3, and the shared-ν Student-t variant reaches 91.9% IS / 82.1% OoS with simulated kurtosis 4.68 / 4.46, the cleanest tail match without a tuning penalty (arXiv:2606.23492).
- **The ACF of |growth rate| is a finite sum of geometric modes governed by the spectrum of the transition matrix**: with T = **1**π̄ᵀ + Σ_{k=2}^K λ_k v_k w_kᵀ, ρ_{|G|}(τ) = Σ_{k=2}^K a_k λ_k^τ. At K=2 this collapses to the single mode ρ_{|G|}(τ)=a₂λ₂^τ with λ₂ = T₁₁+T₂₂−1, which is exactly why K=2–3 Gaussian fits fail to bend the ACF shape; the *number* of decay modes is bounded by rank(T − **1**π̄ᵀ) = K−1 (arXiv:2606.23492).
- **The rank bound is not empirically binding on equities at small K**: at K=18 on SPY a single non-unit eigenvalue carries 93.6% of the lag-1 |growth| ACF, and across a 30-ticker panel the cross-ticker median dominant-mode share is 0.76 (min 0.326 on NEM). Marginal flexibility (emission family) explained more of the residual fit gap than adding decay modes (arXiv:2606.23492).
- **Regime-conditional VaR built from the CHMM one-step-ahead (filtered) state forecast passes the Christoffersen joint conditional-coverage test** on the main window and most walk-forward folds; the model's value over an i.i.d. bootstrap is *not* per-day distributional fidelity (the bootstrap wins OoS KS) but the regime-conditional risk forecast and multi-asset copula composition (arXiv:2606.23492).
- **A triple-timescale AR(1)-MS-GARCH with Filardo time-varying transition probabilities beats single-regime GARCH(1,1) on EUR/USD volatility forecasting**: Diebold–Mariano DM = +4.7040 (p = 1.28×10⁻⁶); smoothed RMSE 0.037411→0.036711 (−1.87%), Spearman IC 0.5264→0.5371; TVTP is strongly justified at 4H and 1H (ΔAIC = +690.7 and +499.9) but rejected at 1D (ΔAIC = −2170.24, static retained). The three states Calm/Turbulent/Crisis are distributionally distinct (KS Calm-vs-Turbulent p = 1.35×10⁻¹⁵³) (arXiv:2606.06190).
- **Single-regime GARCH absorbs regime-switching into its shock-response parameter**: on EUR/USD 2021–2025 it estimates α̂ = 0.3038 (3–6× the typical FX range 0.05–0.10) with β̂ = 0.6076, persistence 0.9114 — a diagnostic signature of misspecification against a multi-regime sample (arXiv:2606.06190).
- **A fully Bayesian multi-trend change-point analysis over *all* CP configurations decodes crisis timing from a single correlation metric**: applied to the S&P500 *mean market correlation* C̄ = (1/N)Σ_{i,j}C_{i,j} computed on rolling 42-day windows and stamped at the 21st window timestamp, the posterior CP densities peak at the dot-com, global-financial-crisis and Euro-crisis dates. On-line (successively updated) analysis has a sensitivity horizon of roughly 80–100 trading days after a crisis onset and cannot act as a precursor (arXiv:2308.00087).
- **A data-driven graph similarity function localises network change-points online with no delay and a shorter history than classical graph distances**: the s-GNN statistic Z_t(s,L) = (1/L)Σ_{i=1}^L s(G_t,G_{t−i}) with detection rule (Z_t ≤ 0.5 after a prior Z_{t′} > 0.5) outperforms Frobenius, Procrustes-Laplacian, DeltaCon, WL-kernel, spectral-clustering and CUSUM baselines on synthetic SBMs and on a financial correlation network, with the CUSUM baselines needing larger windows (arXiv:2203.15470).
- **Offline change-point estimation on a non-negative, non-linearly-dependent series (VIX) is accurate for τ but fragile for the dependence parameter**: a copula-Markov chain with Weibull marginals and Clayton/Joe dependence recovers τ̂ with RMSE 1.5588 (Clayton, T=250, RE 0.0125) and 1.1958 (Joe, RE 0.0096); the change point stays accurate under copula misspecification (RMSE(τ̂) 1.93 when Joe data are fit by Clayton) while the tail-dependence parameters blow up (RE 0.77–1.20) (arXiv:2605.29541).
- **A smooth-transition break parameterised by (direction, amplitude, logistic gate) is well-calibrated for interval coverage but the transition *speed* is weakly identified**: 77.5% direction recovery, amplitude bias −0.003, timing bias −0.23 months (RMSE ≈ 2.2 months), 80% CI coverage 79.6%; at near-instantaneous breaks κ is underestimated by ≈1.86 while the product Δ·w_t stays identified; under an 80% partial reversion coverage degrades gracefully to 72.9% (arXiv:2601.16821).

---

## 2. Implementable formulas & algorithms

### 2.1 Continuous HMM (CHMM) with heavy-tailed emissions — EM/ECM estimation

**Purpose.** Infer K latent volatility/return regimes from a single return series and produce filtered regime probabilities usable for regime-conditional risk.

**Model.** {G_t} is the output of a K-state Markov chain with transition matrix T (T_ij = P(s_{t+1}=j | s_t=i)), initial π, and per-state emission f_k(·;θ_k). The pooled marginal is a mixture at the stationary distribution:

$$f(x)=\sum_{k=1}^{K}\bar\pi_k\, f_k(x;\theta_k),\qquad \bar\pi=\bar\pi T .$$

Emission families and their updates (all under one shared log-space forward-backward):
- Gaussian: f_k = N(μ_k, σ_k²), closed-form weighted mean/variance (classical Baum-Welch).
- Student-t: f_k = t_{ν_k}(μ_k, σ_k); ECM/ECME with the latent scale variable

$$u_{t,k}=\frac{\nu_k+1}{\nu_k+\big((O_t-\mu_k)/\sigma_k\big)^2},\qquad
\mu_k\!\leftarrow\!\frac{\sum_t \gamma_t(k)u_{t,k}O_t}{\sum_t\gamma_t(k)u_{t,k}},\quad
\sigma_k^2\!\leftarrow\!\frac{\sum_t\gamma_t(k)u_{t,k}(O_t-\mu_k)^2}{\sum_t\gamma_t(k)},$$

then ν_k by a 1-D golden-section search on the state-weighted observed-data t log-likelihood.
- Laplace: f_k = Laplace(μ_k, b_k); μ_k = weighted median, b_k = Σ_t γ_t(k)|O_t−μ_k| / Σ_t γ_t(k).
- GED: f_k = GED(μ_k, α_k, p_k) with p=2 ⇒ Gaussian and p=1 ⇒ Laplace; three-stage block-coordinate update (bracketed μ_k, closed-form α_k, bracketed p_k).

**Required inputs.** One return/growth-rate series (daily is what the paper fits); optionally the |return| series for the ACF diagnostic.

**Parameters / defaults reported.** Convergence |ΔL| < ε = 10⁻⁴ on the observed-data log-likelihood; max_iter = 60; golden-section sub-step 40 iterations; Student-t bracket (ν_min,ν_max) = (2.1, 50) with ν⁽⁰⁾=6; GED bracket (0.5, 3.0) with p⁽⁰⁾=1.5; transition and initial distribution initialised uniform T_ij⁽⁰⁾ = π_k⁽⁰⁾ = 1/K. Initialisation is **quantile-based**: sort observations, split into K equal chunks, seed state k's location/scale from chunk k — this keeps starting regimes from overlapping and helps K≥3 converge non-degenerately. Reported T and π should be read at the stationary distribution π̄ for simulation (avoids transient dependence on day 1).

**How K is picked.** Sweep K ∈ {3,6,9,12,15,18,21}; choose by rolling-origin held-out log-likelihood and BIC. In the paper K=3 vs K=6 sat inside sampling noise (|z| ≤ 0.07, sign flipping across folds) and BIC also picked 3, so the smaller model was taken; K=18 had substantially lower mean held-out likelihood. A **spectral diagnostic** decides whether extra states can help: compute the dominant non-unit eigenvalue's share of the lag-1 |return| ACF from Eq. (6) — if one mode already carries ~90%+, adding states buys little.

**Observed effect sizes.** CHMM-N: KS 91.5% IS / 78.0% OoS, kurtosis 3.83/3.62, |G| ACF-MAE 0.0462. CHMM-t shared-ν: KS 91.9/82.1, kurtosis 4.68/4.46. CHMM-GED: 90.3/78.4, 5.45/5.09. CHMM-L: 80.5/63.6, 5.24/5.20 (≈15pp OoS KS below GED). GARCH(1,1) 27.4/59.6; MS-GARCH K=3 36.1/33.1; ML HSMM-N 98.4/91.0. The four CHMM variants were indistinguishable on OoS sample-CRPS (1.0393–1.0432), so pick the family by the kurtosis match.

**Failure modes.** (i) A new regime appearing out-of-sample is the dominant failure: 11/30 tickers below 60% OoS KS, driven by regime-introducing names; a *quarterly* refit lifts the OoS KS median 69.1%→84.7% and cuts failures to 8/30 (monthly refit at K=18 closes slightly more at ~3× compute). (ii) The penalised-t variant's aggregate kurtosis is 1/ν_k-shrinkage sensitive and near-undefined in the fourth moment when a state pins the lower ν bracket — do not tune the penalty at one K and reuse at another. (iii) Two stress folds (COVID, 2022 rate-hike onset) reject *every* generator in the panel; report the walk-forward median, not a single window.

**Evaluation formula.** |G| ACF-MAE over L = 252 lags:

$$\mathrm{ACF\text{-}MAE}=\frac{1}{L}\sum_{\tau=1}^{L}\big|\hat\rho^{obs}_{|G|}(\tau)-\bar{\hat\rho}^{sim}_{|G|}(\tau)\big| .$$

### 2.2 Regime-conditional Value-at-Risk from a fitted CHMM

**Purpose.** One-step-ahead tail risk that conditions on the *running* (filtered) regime estimate.

**Method.** From the fitted per-state CDFs F_k and the filtered state probabilities at t−1 (the causal, one-step-ahead forecast, not the smoothed γ), the conditional predictive CDF is the mixture F_t(x) = Σ_k ξ_{t|t−1}(k) F_k(x;θ_k); the α-VaR solves F_t(VaR_α) = α. Back-test with the unconditional Kupiec coverage test plus the **Christoffersen joint conditional-coverage** test (the paper's primary backtest); report an ES envelope as the [5%,95%] band of simulated ES across paths.

**Observed effect.** Passed joint conditional coverage on the main SPY window and most walk-forward folds (arXiv:2606.23492).

### 2.3 Multi-scale AR(1)-MS-GARCH with Filardo TVTP

**Purpose.** Volatility-regime detection and forecasting at several timescales, with exogenous leading drivers.

**Model.** K=3 states (Calm, Turbulent, Crisis). Return: r_t = μ_{S_t} + φ_{S_t} r_{t−1} + ε_t. Haas-style parallel regime variances (exactly tractable, avoids Gray's path dependence):

$$\sigma^2_{t,k}=\omega_k+\alpha_k\varepsilon_{t−1}^2+\beta_k\sigma^2_{t−1,k},\qquad
\sigma^2_{k,\infty}=\frac{\omega_k}{1-\alpha_k-\beta_k},\quad \alpha_k+\beta_k<1\ \forall k .$$

Emissions are standardised skewed Student-t with state-specific ν_k. Transition probabilities follow Filardo's multinomial logit in a standardised stress driver z_t:

$$p_{ij,t}=\frac{\exp(a_{ij}+\gamma_{ij}z_t)}{\sum_{k=0}^{K-1}\exp(a_{ik}+\gamma_{ik}z_t)} .$$

The Hamilton filter is causal: predict ξ_{t|t−1}(j)=Σ_k p_{kj}ξ_{t−1|t−1}(k), then update ξ_{t|t}(k) ∝ f(r_t|S_t=k,θ_k)ξ_{t|t−1}(k), with log-sum-exp throughout; O(TK). Expected dwell time E[T_k]=1/(1−p_{kk}).

**Parameters / defaults.** 27 static optimisation parameters per timeframe (18 emission + 9 unconstrained transition logits mapped through softmax); TVTP adds K²=9 sensitivity coefficients γ_ij (36 total). Estimation is **penalised MLE** with L-BFGS-B on the penalised negative log-likelihood

$$\mathcal{L}_{pen}(\theta)=-\log L(\theta)+\sum_k \lambda_k(-\log p_{kk})
+\lambda_{ord}\sum_k \max(0,p_{k+1,k+1}-p_{k,k})^2
+\lambda_{stat}\sum_k \max(0,\alpha_k+\beta_k-0.999)^2 ,$$

i.e. a log-Dirichlet stickiness prior on the diagonal, an ordering penalty enforcing p₀₀ ≥ p₁₁ ≥ p₂₂, and a stationarity penalty. **Staggered box constraints** on ω_k and ν_k force Calm<Turbulent<Crisis in variance and tail weight. Label switching is resolved by **variance-based state sorting** (state 0 = lowest within-state variance); warm-starting each walk-forward quarter at the previous quarter's estimates further stabilises labels. Hamilton filter compiled with Numba-JIT.

**Composite stress driver (concrete).** Vol_Spike = σ_15min/σ_24h, Jump_Ratio = RV_24h/BV (realised variance / bipower variation), composite_meta = Vol_Spike × log(1+Jump_Ratio), then rolling 30-day z-score clipped to ±3σ. The 4H driver mixes it with day-of-week and a macro index; the macro index is Macro_Stress_Index = VIX_Z + Yield_Z with both components 1-period lagged.

**Observed effect sizes.** DM = +4.7040 (p = 1.28×10⁻⁶) vs GARCH(1,1); smoothed Spearman IC 0.5264→0.5371; error mean −46%; ΔAIC(TVTP) +690.7 (4H) / +499.9 (1H) / −2170.24 (1D). Dwell times: 1D 45.1/13.9/7.6 days, 4H 10.8/1.9/0.6 days, 1H 10.7/5.1/3.9 hours. OoS allocations 1D 82.3/10.1/7.7%, 4H 8.4/71.6/20.0%, 1H 65.6/32.5/2.0%. RCM clarity 27.6/52.4/54.0%; Brier Skill Score +0.2132/+0.0874/+0.1185; KS purity p=1.35×10⁻¹⁵³ (Calm vs Turbulent) and 1.03×10⁻³⁸ (Turbulent vs Crisis); ACF of squared returns 0.2579→0.1889 (26.8% absorbed); 99% VaR breach 0.54% vs 1.00% target; OoS directional IC +0.0252 (p = 6.75×10⁻⁵).

**Validation formulas.**
Regime Classification Measure (100% = perfect, 0% = uniform uncertainty):

$$\mathrm{RCM}=100\Big[1-\frac{K}{K-1}\cdot\frac{1}{T}\sum_{t=1}^{T}\sum_{k=0}^{K-1}\pi_t(k)\big(1-\pi_t(k)\big)\Big].$$

Brier Skill Score vs climatology:

$$\mathrm{BSS}=1-\frac{\frac{1}{T}\sum_t (p_t-y_t)^2}{\bar p(1-\bar p)},\qquad p_t=\pi_t(\text{Crisis}),\ y_t=\mathbf{1}[|r_t|>\text{85th pct}].$$

Shannon entropy filter: H_t = −Σ_k π_t(k)log π_t(k), normalised by log K; block trading when H̃_t > 0.85 (high regime uncertainty).

**Cross-scale tensor.** With three independent per-scale filtered probability vectors, form the outer product P_t(i,j,k)=π_t^{(1D)}(i)π_t^{(4H)}(j)π_t^{(1H)}(k) (27 entries) as soft routing weights, plus a Disagreement_t = std over scales of π_t^{(·)}(k) as an explicit transition-risk feature. Macro-level state probabilities are forward-filled onto the faster index (strictly causal) — never back-filled.

**Failure modes.** (i) Residual ARCH remains in all three timeframes (ARCH-LM 12.19 / 16.75 / 38.49; p=0.032/0.005/0.000) because Haas' path-independence ignores volatility inherited across a Crisis→Calm transition; the Gray collapsing formulation fixes continuity at 3–5× cost. (ii) RCM of only 27.6–54.0% means regime assignments are moderate-confidence in FX (emission overlap); NIG/VG emissions are suggested to sharpen separation. (iii) Batch MLE does not adapt in real time — particle-filter / SMC would be needed for continuous updating.

### 2.4 Bayesian multi-change-point on a 1-D correlation metric (offline + online)

**Purpose.** Locate regime/trend changes in an aggregate market-correlation series and date crisis onsets.

**Model.** Mean market correlation C̄(t) = (1/N)Σ_{i,j}C_{i,j} from locally normalised returns over rolling windows (τ = 42 days, stamped at the 21st timestamp), then modelled by m piecewise-linear segments

$$\phi_K(t\mid E,C_{ord},I)=\bar C_K\frac{t_{K+1}-t}{t_{K+1}-t_K}+\bar C_{K+1}\frac{t-t_K}{t_{K+1}-t_K},\quad t_K\le t\le t_{K+1}.$$

The full posterior over CP configurations E is p(E | C̄(t),t,I) ∝ p(E|t,I)·p(C̄(t)|t,E,I), evaluated over Z_m = C(N−2, m) configurations (thinning: keep every 40th point, 132 points total). The **marginal CP PDFs** are obtained by averaging the joint probability at each timestamp over its ordinal position in each configuration; the MAP configurations and a PDF-weighted segment fit with 3σ credibility bands are read off directly.

**Parameters / defaults.** m ∈ {1,…,5} (results robust; at least 3 CPs for a period with 3 major events). On-line: re-run on successively extended segments; sensitivity horizon ≈ 80–100 trading days. Implementation reference: the open-source `antiCPy` package (parallel, on-the-fly configuration generation — the naive serial/memory approach is infeasible: a 5-CP thinned problem needs a (286,243,776 × 7) double matrix).

**Observed effect.** CP-density peaks coincide with the dot-com onset/decline, the U.S. housing-bubble burst (Oct 2006–Jan 2007), the Lehman bankruptcy (Sep 2008) and the Greece downgrade (Apr 2010). Configuration rank of the first dot-com-containing configuration: 264/8385 (m=2), 26/357760 (m=3), 354/11358880 (m=4).

**Failure modes.** Ex-post only — it cannot be a precursor; overlapping events make causal attribution impossible (the method narrows *which* periods to research, it does not identify the cause). The correlation metric responds to price bubbles almost immediately but to real-world events (inter-bank rate spikes) with delay.

### 2.5 Graph-similarity network change-point detection (online, delay-free)

**Purpose.** Detect structural breaks in a correlation network (or any snapshot graph) without specifying the generative model or the change type.

**Statistic.** With a learned similarity s(G_a,G_b) ∈ [0,1] (s > 0.5 ⇔ same generative distribution), monitor the short-history average

$$Z_t(s,L)=\frac{1}{L}\sum_{i=1}^{L}s(G_t,G_{t-i}),\qquad t>L,\quad L<L_0,$$

and declare a change-point at t when Z_t ≤ 0.5 given some t′ ∈ [t−L, t) with Z_{t′} > 0.5. Offline localisation: τ̂ = argmin_{t∈[L,T]} Z_t or argmax_t |Z_t − Z_{t−1}|. A small tolerance (order L) allows a forward-window / MMD variant.

**Similarity model.** Siamese GNN: shared GCN encoder

$$H^{(j)}=\sigma\big(\tilde A H^{(j-1)}W^{(j)}+B^{(j)}\big),\qquad \tilde A=\tilde D^{-1/2}(A+I_n)\tilde D^{-1/2},$$

then a node-wise Euclidean distance vector, **Sort-k pooling** of its k largest entries (picks up *localised* changes on few nodes and cuts parameters), two FC layers, sum-pool, sigmoid. Trained as a binary pair classifier with cross-entropy; for the unattributed case, positional encodings are required (Degree / Random-Walk / Laplacian / Identity — Degree and Random-Walk generally best; Laplacian suffers eigenvector sign ambiguity; Identity helps only when node symmetry is broken). Sampling: a **Random scheme** for training pairs (far-apart snapshots, balanced) and a **Windowed scheme** for validation (pairs within L, mimicking the test setting). With no ground-truth labels, a **self-supervised** loop pre-estimates change-points by spectral clustering, then samples pairs from those pseudo-labels.

**Parameters / defaults.** Synthetic SBM: T=100, n=400, L=6; window/tolerance ±5 timestamps for the adjusted-F1 localisation metric. Baselines used k=6 clusters/singular values and L⁰=L/2 windows.

**Observed effect.** Beats Frobenius, Procrustes-Laplacian, DeltaCon, WL-kernel, SC-NCPD, LAD and CUSUM on Merge/Birth/Swap SBM scenarios and needs a shorter history; CUSUM needs larger windows.

### 2.6 Copula–Markov change-point on a non-negative heavy-tailed series

**Purpose.** Offline estimation of one structural break in a non-negative, non-linearly dependent series (e.g. VIX), separating a shift in the *marginal* from a shift in *serial dependence*.

**Model.** X₁…X_τ ~ Weibull(λ₀,k₀) with copula parameter α₀; X_{τ+1}…X_T ~ Weibull(λ₁,k₁) with α₁; the single crossing pair uses a fixed α₀₁ (set α₀₁ = 2). Weibull CDF F(x)=1−exp(−(x/λ)^k); Clayton C_α(u,v)=(u^{−α}+v^{−α}−1)^{−1/α} for lower-tail dependence, Joe for upper-tail. Conditional density f(x_t|x_{t−1})=c_{α}(F_γ(x_{t−1}),F_γ(x_t))·f_γ(x_t); the log-likelihood sums the marginal logs plus the copula-density logs over pre-break, crossing and post-break pairs.

**Estimation.** The likelihood is not differentiable in τ, so use a **two-stage profile MLE**: fix τ, maximise over (k₀,k₁,λ₀,λ₁,α₀,α₁) by Newton–Raphson, then τ̂ = argmax_τ ℓ(τ | ·) over τ ∈ {3,…,T−3}. Re-parameterise to unconstrained space for stability: K=log k, Λ=log λ, A=log(α+1). Confidence intervals via **parametric bootstrap Monte Carlo**.

**Parameters / defaults.** α bounds (−1, 1000); sample sizes 100–250 in the study.

**Observed effect sizes.** RMSE(τ̂)=1.5588 (Clayton, RE 0.0125), 1.1958 (Joe, RE 0.0096) at T=250; RMSE falls from 1.69→1.56 (Clayton) and 1.41→1.20 (Joe) going 100→250. Under copula misspecification τ̂ stays accurate (RMSE 1.93 Joe-data-as-Clayton; 3.58 Clayton-data-as-Joe) while α estimates are badly biased (RE 0.77–1.20). VIX COVID application: Clayton wins on AIC (stronger downside dependence in stress).

**Failure modes.** Marginal parameter estimates (k, λ) are noisier than τ̂; τ̂ is the robust output, tail-dependence parameters are not. Estimating α requires ≥3 points, hence α₀₁ must be fixed.

### 2.7 Directional-shift smooth-transition break (logistic gate) — optional

**Purpose.** Model a *gradual*, approximately monotone structural break with interpretable direction, magnitude and timing; useful for regime-transition timing rather than state inference. (arXiv:2601.16821; data are compositional, so treat the mechanism, not the emission.)

**Model.** In ILR space, drift d_t = b + B X_t + Δ·w_t·v with unit direction v (‖v‖=1), amplitude Δ, and a normalised piecewise logistic gate

$$w_t(\tau,\kappa)=\frac{\sigma(\kappa(t-\tau))-\sigma(\kappa(\ell-\tau))}{1-\sigma(\kappa(\ell-\tau))},\quad t>\ell;\qquad w_t=0,\ t\le\ell,$$

where ℓ is the last pre-break index, σ the logistic, κ the transition speed (κ=0.3 slow, κ=3.0 near-step). The mean recursion is η_t = d_t + Σ_p A_p(Z_{t−p}−d_{t−p}) + Σ_q Θ_q e_{t−q}; the concentration can shift too: log λ_t = X_{φ,t}ᵀγ + δ_φ w_t. The trajectory is a geodesic on the simplex and is invariant to the ILR basis choice (the *mechanism* is; the full diagonal-AR model is not).

**Estimation.** Bayesian, Stan/NUTS, 4 chains, 500 warmup + 800 sampling, R̂ < 1.01, no divergences. Sign identification by a hemisphere constraint (first raw direction component > 0). Priors: Δ~N(0,1.5), τ~N(ℓ+2, 4²), κ~LogNormal(−0.5, 1²), DARMA coefficients Uniform(−0.99,0.99).

**Observed effect sizes.** Direction recovery 77.5% (cos > 0.5); conditional amplitude bias −0.003 (SD 0.130); timing bias −0.23 months (RMSE ≈2.2); 80% CI coverage 79.6%. At κ=3, κ bias −1.86 but amplitude bias modest and coverage nominal (the product Δ·w_t is identified, not κ). Under 80% partial reversion coverage 72.9%. Fixed-effect alternative under-covers badly (66.1% vs intervention 79.6%).

---

## 3. Data requirements → available endpoints

Probe status is the live-probe field from `strategies/endpoints.json`. `gateway` = local OpenD/SDK bridge required (not a plain HTTP endpoint); the probe row itself is `ok=false`.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV per ticker (regime fit, return series) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt failover) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily OHLCV (alt failover) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Daily OHLCV (alt failover) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Intraday 1H/4H bars (multi-scale MS-GARCH) | `https://api.twelvedata.com/time_series` (interval param) | core_stock_apis | twelvedata | ok |
| Intraday bars (alt, local gateway) | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (needs local OpenD) |
| Cross-sectional return panel (mean correlation C̄, correlation networks) | `https://eodhd.com/api/eod/AAPL` (bulk) + `https://eodhd.com/api/exchange-symbol-list/US` | core_stock_apis / exchange_symbols | eodhd | ok / ok |
| VIX level (Macro_Stress_Index VIX_Z term) | `https://api.stlouisfed.org/fred/series/observations` (series VIXCLS) | macro_data | fred | ok |
| US 10Y yield (Macro_Stress_Index Yield_Z term) | `https://api.stlouisfed.org/fred/series/observations` (series DGS10) | macro_data | fred | ok |
| Risk-free rate (excess growth rate G) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | **failed** (connect/ReadTimeout) — substitute `macro_data`/fred (DGS3MO) |
| Realised variance / bipower variation (Vol_Spike, Jump_Ratio) | derived from intraday bars via `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok (derived); needs intraday granularity |
| News sentiment as TVTP exogenous driver | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| News sentiment (alt driver) | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| GDELT tone (alt driver) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate_limited (HTTP 429) |
| Event probabilities (forward-looking regime triggers) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Economic calendar (dates to validate detected change-points) | `moomoo://get_economic_calendar` | economic_calendar | moomoo | gateway |
| Options-implied vol / surface (stress driver) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | **failed** (HTTP 307) |
| Options chain IV (alt stress driver) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move (alt stress driver) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Short interest (smart-money stress driver) | `moomoo://get_short_interest` | short_interest | moomoo | gateway |
| Institutional holdings (stress driver) | `moomoo://get_shareholders_institutional` | institution_data | moomoo | gateway |
| Capital flow (stress driver) | `moomoo://get_capital_flow` | capital_flow | moomoo | gateway |
| Insider trades (stress driver) | `moomoo://get_insider_trade_list` | smart_money | moomoo | gateway |
| Fed target rate (rate-cycle regime driver) | `moomoo://get_fed_watch_target_rate` | fed_watch | moomoo | gateway |
| **Intraday FX (EUR/USD 1-min, the MS-GARCH paper's exact setting)** | — | — | — | **gap** — no FX provider in the inventory (twelvedata *may* serve FX intraday but is not probed for it) |
| **Ground-truth regime / change-point labels** | — | — | — | **gap** — none available; must be inferred or hand-dated from the economic calendar |

Notes: the moomoo rows are all `gateway` (local OpenD SDK), so they are only usable when the desktop gateway is running; treat them as degraded/conditional. The single-vendor `risk_free_curve` (federal_reserve) and `options_surface` (cboe) endpoints failed the live probe, so any design that depends on them must fall back to FRED (`macro_data`) or a provider in `core_stock_apis`. Required env-var names (do not hard-code values): `EODHD_API_KEY`, `TIINGO_API_KEY`, `TWELVEDATA_API_KEY`, `MASSIVE_API_KEY`, `FRED_API_KEY`, `ALPHAVANTAGE_API_KEY`.

---

## 4. Pitfalls, validation and measurement

**Look-ahead / leakage — the central hazard in regime labelling.**
- Distinguish **smoothed** posteriors γ_t(k)=P(s_t=k | O_{1:T}) from **filtered** ξ_{t|t}(k)=P(s_t=k | O_{1:t}). The CHMM fits with smoothed γ (fine for historical fitting/labelling) but the regime-conditional VaR uses the *one-step-ahead filtered* state forecast (arXiv:2606.23492). Labelling a historical bar with γ_t and then claiming it as a tradeable signal is look-ahead: γ_t has seen the future.
- The MS-GARCH framework documents three explicit causal-isolation devices that any implementation should copy: (i) every TVTP driver enters with a one-period lag; (ii) the train/test split uses strict boundary slicing; (iii) the last 24 training observations are trimmed to prevent multi-step target overlap; and (iv) daily/4H state probabilities are **forward-filled** onto the hourly index (never back-filled) (arXiv:2606.06190).
- The graph NCPD statistic Z_t uses only the *past* window (G_t vs G_{t−i}); do not build the test-time similarity from a forward window unless you accept detection delay ≈ L (arXiv:2203.15470).
- The Bayesian CP method's on-line variant *cannot* be a precursor: it needs 80–100 trading days of data beyond a trend change before the CP density peaks; the retrospective fit uses the whole series and is therefore not an ex-ante signal (arXiv:2308.00087). The copula-Weibull method is offline by construction (arXiv:2605.29541).

**Overfitting and model selection.**
- K selection: sweep, then use held-out rolling-origin log-likelihood *and* BIC; prefer the smaller K when the criteria cannot separate them (K=3 vs 6 within noise), and use the spectral mode-share diagnostic to check that extra states could plausibly add decay modes (arXiv:2606.23492). For the MS-GARCH, K is fixed at 3 with staggered bounds and an ordering penalty rather than selected (arXiv:2606.06190).
- CV must be **rolling-origin / walk-forward**, not a single split: the SPY single-window OoS pair was misleadingly good while the walk-forward median (62.1% OoS KS) and two stress folds (COVID, 2022 rate hike) exposed the real behaviour (arXiv:2606.23492).

**Label switching.** Mixture/HMM optimisers permute state labels across runs. Fix by variance-based sorting (state 0 = lowest within-state variance) and by warm-starting each refit at the previous fit's parameters; verify by checking that the OoS volatility ordering Calm<Turbulent<Crisis is monotonic (arXiv:2606.06190). Staggered box constraints on ω_k, ν_k also help.

**Regime drift / periodic refit.** Static fits decay out-of-sample; a quarterly refit lifted the 30-ticker OoS KS median 69.1%→84.7% and cut failures 11/30→8/30; a non-equity stress test (GLD) broke down under static fitting — refit periodically and scope the model to its asset class (arXiv:2606.23492).

**Distributional assumptions.** The Clayton/Joe copula choice matters for tail dependence but the change-point estimate is robust to moderate copula misspecification; do not trust the dependence parameter if you are unsure of the family (arXiv:2605.29541). The Dirichlet-ARMA diagonal AR/MA restriction leaves non-trivial residual cross-dependence (mean |r| 0.165–0.186, max 0.52) — check residual cross-correlation before trusting a diagonal specification (arXiv:2601.16821).

**Measurement / back-tests to run.**
- Marginal fidelity: two-sample KS pass rate, but recalibrate with a **stationary block bootstrap** because KS assumes i.i.d. and returns are dependent (block length L=20 gave overlapping IS/OoS kurtosis CIs of [2.17,12.40] and [0.90,8.26], so read kurtosis against the envelope, not the point) (arXiv:2606.23492).
- Temporal fidelity: |return| ACF-MAE over 252 lags (Eq. 5).
- Forecast comparison: Diebold–Mariano test on the loss differential d_t = L(e_{1t})−L(e_{2t}); report DM and its p-value, not just RMSE deltas (arXiv:2606.06190).
- Regime sharpness: RCM; regime purity: two-sample KS between states; transition quality: Brier Skill Score vs climatology.
- Risk: Kupiec unconditional coverage + Christoffersen joint conditional coverage for VaR; report realised breach rate against target.
- Change-point localisation: localisation error |τ̂−τ| for a single break, adjusted F1 with a ±5-timestamp tolerance for multiple breaks (arXiv:2203.15470); for the correlation-CP method, compare CP-density peaks against a dated event timeline (arXiv:2308.00087).

**Churn / implementability.** Regime signals flip; the MS-GARCH reports 4,365 flips / 24,955 hours (5.72h average dwell) and gates trading on the normalised Shannon entropy (>0.85 ⇒ stand down). Any strategy built on regime labels must budget for turnover and entropy-based de-risking (arXiv:2606.06190).

---

## 5. Recommended first implementation in FinRobot

1. **Build a `regime_inference` module wrapping a 3-state continuous HMM with Student-t emissions** over `CORE_STOCK_APIS` daily returns (eodhd primary, tiingo/massive failover). Quantile initialisation, log-space forward-backward, ECM/ECME for the t parameters (brackets ν∈(2.1,50), init 6), convergence 1e-4 / max 60 iters. Expose both smoothed γ and filtered ξ_{t|t}; only ξ may feed signals. **Data:** daily OHLCV. **Expected value:** high — reproduces the Cont stylized facts and gives a regime label the rest of the engine can condition on. **Risk:** medium (label switching, drift → needs refit cadence). **Effort: M.**
2. **Add K selection as a first-class step**: sweep K∈{3,6,9,12}, score by rolling-origin held-out log-likelihood + BIC, and compute the dominant-eigenvalue mode share from Eq. (6) as a "would more states help?" diagnostic; default to K=3. **Data:** same. **Expected value:** medium (prevents over-parameterised, unstable regimes). **Risk:** low. **Effort: S.**
3. **Regime-conditional VaR** from the filtered mixture F_t(x)=Σ_k ξ_{t|t−1}(k)F_k(x) and back-test with Kupiec + Christoffersen joint conditional coverage. **Data:** daily returns (already fetched). **Expected value:** high for the risk surface; the paper's VaR passed joint conditional coverage where the i.i.d. bootstrap could not serve the use case. **Risk:** medium (needs enough tail events to test). **Effort: M.**
4. **Causal TVTP stress driver** built from FRED VIX (VIXCLS) and 10Y yield (DGS10) — z-scores, 1-period lag, clipped ±3σ — feeding a multinomial-logit transition matrix on a 3-state model, with a stickiness/ordering/stationarity penalty. **Data:** `MACRO_DATA`/fred (works); optionally news_sentiment (eodhd/alpha_vantage) as an extra driver. **Expected value:** medium-high (TVTP gave ΔAIC +690.7 at 4H). **Risk:** medium (driver over-fitting; constrain γ). **Effort: M.**
5. **Mean-market-correlation change-point monitor** (offline + rolling on-line) over the `CORE_STOCK_APIS` cross-section: rolling 42-day correlation matrix, C̄ stamped at the 21st window date, thinned, Bayesian piecewise-linear CP over m∈{1..4}. Use it as a market-stress dashboard, not a signal. **Data:** cross-sectional daily returns (eodhd bulk). **Expected value:** medium (crisis dating / situational awareness). **Risk:** low-medium (ex-post by nature). **Effort: M.**
6. **Regime-aware risk gate**: normalised Shannon entropy of filtered state probabilities; suppress new exposure when H̃_t > 0.85, and expose a cross-scale/cross-asset Disagreement feature. **Data:** outputs of items 1/4. **Expected value:** medium (cheap de-risking overlay). **Risk:** low. **Effort: S.**
7. **(Optional, only if intraday is added)** multi-scale MS-GARCH with three timescales via twelvedata intraday bars + FRED macro index; treat as a research spike because the paper's exact 1-min FX setting has no provider here. **Data:** twelvedata intraday (ok) + fred macro (ok); FX 1-min is a **gap**. **Expected value:** medium. **Risk:** high (residual ARCH, cost). **Effort: L.**
8. **Do not build** on the failed/degraded rows without a fallback: `risk_free_curve`/federal_reserve (ReadTimeout) and `options_surface`/cboe (HTTP 307) failed the probe — use FRED for rates and defer options-implied stress drivers until a working options source exists (moomoo options rows need the local gateway). **Effort: S.**

---

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2606.23492 | Continuous Hidden Markov Models for Equity Returns: Heavy-Tail Emission Families and Regime-Conditional Value-at-Risk | 2026 |
| 2606.06190 | Multi-Scale Markov Switching GARCH: Volatility Regime Detection in EUR/USD | 2026 |
| 2308.00087 | Efficient Multi-Change Point Analysis to decode Economic Crisis Information from the S&P500 Mean Market Correlation | 2023 |
| 2203.15470 | Graph similarity learning for change-point detection in dynamic networks | 2022 |
| 2605.29541 | Change-point estimation for Weibull time series with copula-based Markov models | 2026 |
| 2601.16821 | Directional-Shift Dirichlet ARMA Models for Compositional Time Series with Structural Break Intervention | 2026 |
