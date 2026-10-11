# Insurance & Mortality-Linked — learnings from the q-fin.PR corpus
`133` of 2274 corpus papers matched this category (`132` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Mortality is a stochastic force of mortality driving a doubly stochastic lifetime.** $\tau$ is the first jump of a Cox process with intensity $\lambda(t)$, so $P(\tau>t\mid\mathcal{K}_t)=\exp(-\int_0^t\lambda\,du)$, and $\lambda$ is an $\mathcal{F}$-adapted diffusion, not a table (arXiv:2410.11849v1, arXiv:1011.0248v1). The hedging paper requires $\lambda$ to have a **positive lower bound** and vanishing volatility at the bound, otherwise the pricing PDE loses its comparison principle (arXiv:1011.0248v1).
- **Coupled lives need a bereavement ("broken-heart") mechanism.** Each spouse's pre-death intensity is an OU diffusion, the first death is the first jump of a Cox process with intensity $\lambda_{x_1}+\lambda_{x_2}$, and the survivor's intensity jumps by $r_q(\tau_p)=\delta_q+\epsilon_q\lambda_q(\tau_p^-)+\zeta_q\lambda_p(\tau_p^-)$ then decays at $\kappa_q$; the joint density of $(\tau_{x_1},\tau_{x_2})$ is closed-form (arXiv:2410.11849v1). Raising the jump $\epsilon_x$ raises the policy value monotonically — it forces two claims in quick succession (arXiv:2410.11849v1, Fig. 6.5).
- **Ignoring dependence between intensities is a 40% error.** In the linear-rational Wishart model the instantaneous intensity correlation is $v_{12}(\sigma^2)_{12}/\sqrt{v_{11}v_{22}(\sigma^2)_{11}(\sigma^2)_{22}}$ — **0.40 at inception, 0.65 asymptotically** with the authors' parameters, against the $[0.41,0.56]$ band Frees et al. report for last-survivor annuities. Forcing $v_{12}=0$ **lowers the guaranteed joint-survival annuity option by up to 40%** at low guarantee rates (arXiv:2602.06415v1).
- **In that model one parameter dominates.** The option price rises nearly linearly in $\beta,\rho_\sigma,m_{11},\sigma_{11}$ and falls mildly in $T$, but a **10% fall in $\alpha$ (0.04→0.036) multiplies the price almost fivefold** (arXiv:2602.06415v1). Plausible scale: intensities 0.0199/0.0198 at $s=2$, versus a US excess-mortality estimate of 0.0132 (2017–2022) and a one-year conditional rate of 0.0107 (Human Mortality Database) cited in the same paper.
- **Unobservable mortality/health shifts are filterable with a jump-diffusion.** With a hidden change-point $\xi$ moving the hazard from $\mu_\ell$ to $\mu_h$, the filter $\Pi_t=P_\pi(\xi\le t\mid\mathcal{G}_t^Y)$ is the unique strong solution of a Kushner–Stratonovich SDE with a discontinuous term; it jumps at death and the closed-form conditional survival probability uses $\kappa=\Delta\mu/(\Delta\mu-\lambda)$ (arXiv:2505.13185v3). Calibration uses served-style inputs — $r=0.0263$ (3-month T-bills, 1990–2020), $\mu_\ell=0.0366$ (ICE BofA BB US High Yield OAS), $\mu_h=0.1148$ (ICE BofA CCC & Lower OAS), $\lambda=0.25$, $\beta=0.15$ — and partial information **under**-prices the defaultable bond before the shock (hazard over-estimated) and over-prices it afterwards.
- **Hedging with a mortality derivative may raise *or* lower the price; the sign is a condition, not a theorem.** For $n$ pure endowments hedged by a $q$-forward, $\frac1nP^{(n)}$ decreases in $n$ and converges to a value solving a *linear* PDE; with $\rho=1$ hedging reduces the limiting per-contract price iff $q^I<\eta$ (the insurer's Sharpe ratio), but with $\rho<1$ — population basis risk — it can raise the price even then; a **negative** $q^I$ (a "natural hedge", e.g. life insurance) always lowers it (arXiv:1011.0248v1). Anchors: unhedged single-life price ≈0.435, unhedged limiting price ≈0.343, with the $q^I=0.09$/$0.15$ curves lying *above* them.
- **Mortality-linked securities are thin.** Only a $q$-forward on an *indexed* population exists, leaving population basis risk; the paper's prescription is transparent index design and a lower $q^I$ (arXiv:1011.0248v1).
- **CAT bond pricing is dominated by expected loss, but the trigger design controls basis risk.** Across 734 primary tranches (Jun 1997–Dec 2020): mean spread **7.7%** (0.65%–49%), mean expected loss **2.5%** (0–15%), mean attachment probability **3.9%** (0.02%–23%), mean attachment point \$2,505mn, mean limit \$3,267mn, mean term 36.4 months; 43.1% indemnity triggers, 62.5% US wind, 18.8% Europe wind (arXiv:2512.22660v1).
- **A transparent cost-field trigger roughly doubles the explained variance of losses.** With $C_i(x)=D(Z_i(x))E(x)$ and a power damage function $D(z)=(z/c_1)^\beta$ over a max-stable wind field, regressing log industry loss on log trigger gives $R^2=0.9307$ at $\beta=7.8$, versus $0.6923$ (max-wind benchmark), $0.7293$ and $0.7390$ (arXiv:2609.22052v1). The trigger uses only public hazard and exposure data, so it avoids indemnity moral hazard and vendor-model opacity.
- **Cat-bond prices are model-sensitive.** Pricing a 100y/200y tranche to par needs a Wang skew $\lambda=0.737$; substituting Brown–Resnick gives 100.11 and a 150y par spread of 6.28%, and a univariate wind model 101.26 — **model choice moves the price by more than a point of spread**. Literature $\lambda$ spans 0.7 (Galeotti et al.) to 1.23 (Tang–Yuan) (arXiv:2609.22052v1).
- **ML adds little in absolute terms, but climate indices carry signal.** Adding ONI/AO/NAO/OLR/PNA/PDO/SOI and regional SST cuts test RMSE from 0.01774 to 0.01682 (OLS) and, for the best learner (extremely randomized trees), from 0.0142 to 0.0123 (**−13.2%**); OLR, SOI and PNA correlate most with coupons at 10–16 month lags (up to ≈0.2), PDO and ONI negatively (arXiv:2512.22660v1). Against a mean spread of 0.077 the absolute gain is ~0.2 points.
- **The corpus disagrees on paradigm.** Exponential-affine survival models give affine survival bonds but neither an exact option price nor a general correlation structure; the linear-rational Wishart construction buys a one-dimensional-integration option price instead (arXiv:2602.06415v1). Hedging is a price reducer under some $(\rho,q^I,\eta)$ and a price increaser under others (arXiv:1011.0248v1); CAT-bond risk premia are treated as exogenous inputs (arXiv:2609.22052v1) rather than derived.

## 2. Implementable formulas & algorithms

### 2.1 Doubly stochastic lifetimes with OU hazard rates
**Purpose.** The baseline engine: survival probabilities, joint/last-survivor annuity factors, and the hazard process every other model here consumes.

$$P(\tau>t\mid\mathcal{K}_t)=\exp\!\Big(-\int_0^t\!\lambda(u)du\Big),\quad d\lambda_i=\mu_i\lambda_i\,dt+\sigma_i\,dW^i_t,$$
$$m(t)=\sum_i\frac{\lambda_i(0)}{\mu_i}\big(e^{\mu_i t}-1\big),\quad \sigma^2(t)=\sum_i\frac{\sigma_i^2}{\mu_i^2}\Big[t+\frac{e^{2\mu_i t}-1}{2\mu_i}-\frac{2(e^{\mu_i t}-1)}{\mu_i}\Big],$$
$$P\big(\{\tau_{x_1}>t\}\cap\{\tau_{x_2}>t\}\big)=\exp\!\big(\tfrac{\sigma^2(t)}{2}-m(t)\big),\quad P(\text{union})=P(\tau_{x_1}>t)+P(\tau_{x_2}>t)-P(\text{both}).$$

- **Inputs:** initial intensities $\lambda_{x_i}(0)$ by age, $\mu_i$, $\sigma_i$; the joint density $\rho(t_1,t_2)$ from the paper's Theorem 1 for full couple models.
- **Parameters:** $\lambda_i(0),\mu_i,\sigma_i>0$; the OU may go negative, dismissed as ≤0.01% probability over 100 years (arXiv:2410.11849v1 footnote 1).
- **Observed effects:** the closed-form union probability makes "at least one survivor" coupons an integral over $\rho$ (arXiv:2410.11849v1, Eq. (4.5)).
- **Failure modes:** negative intensities never empirically rejected; assuming independent lives removes the entire bereavement effect.

### 2.2 Bereavement (broken-heart) mortality jump
**Purpose.** Add the short-term partner dependence that makes joint-life products non-separable.

$$r_q(\tau_p)=\delta_q+\epsilon_q\lambda_q(\tau_p^-)+\zeta_q\lambda_p(\tau_p^-),\quad r_q(t)=\epsilon_q\lambda_q(\tau_p^-)e^{-\kappa_q(t-\tau_p)},\quad \tilde\lambda_q(t)=\lambda_q(t)+r_q(t),$$
$$\tau_q=\inf\Big\{t>\tau_p:\textstyle\int_{\tau_p}^{t}\tilde\lambda_q(u)du\ge E_2\Big\},\quad P\big((x_1)=p\big)=\frac{\lambda_{x_1}(\tau_p)}{\lambda_{x_1}(\tau_p)+\lambda_{x_2}(\tau_p)}.$$

- **Inputs:** both spouses' pre-death intensity paths; uniform $U$ selects the first decedent (arXiv:2410.11849v1, Sec. 3.1).
- **Parameters:** $\delta_q,\epsilon_q,\zeta_q\ge0$ (jump size), $\kappa_q>0$ (decay); the paper sets $\delta_q=\zeta_q=0$, leaving one amplitude $\epsilon_q$ per spouse.
- **Observed effects:** the value of GMAB+SB+DB rises monotonically in $\epsilon_x$ (arXiv:2410.11849v1, Fig. 6.5); $\rho$ inherits the factor $e^{-\kappa_q(\cdot)}$ (Eq. (3.8)).
- **Failure modes:** shared frailty is captured only via $\lambda_p(\tau_p^-)$ once $\delta_q=\zeta_q=0$; $\epsilon_q,\kappa_q$ are identified from very few couple deaths.

### 2.3 The $Q\odot P$ rule for hybrid (equity-linked) insurance
**Purpose.** Price a contract mixing market risk (equity, rates, surrender) with mortality risk without forcing both into one measure.

$$E_{Q\odot P}[X\mid\mathcal{G}]=E_Q\big[E_P[X\mid\mathcal{F}]\mid\mathcal{G}\big]\ (\mathcal{G}\subset\mathcal{F}),\quad E_{Q\odot P}[X\mid\mathcal{G}]=E_P[X\mid\mathcal{G}]\ (\mathcal{F}\subset\mathcal{G}\subset\mathcal{H}),$$
$$P=P_{\mathrm{GMAB}}+P_{\mathrm{SB}}+P_{\mathrm{DB}},\qquad P_{\mathrm{GMAB}}=P_T\,B(0,T)\,Ie^{\delta T}(A_1+A_2),$$
$$\lambda^s_t=\beta\,|D(t_i)|+C\ \text{ on }[t_i,t_{i+1}),\qquad D(t)=Y_t-p(t)+\int_t^T\!f(t,s)ds-\delta T,\quad Y_t=\log S_t.$$

- **Inputs:** equity index $S_t$ (hybrid Lévy forward-rate model), forward curve $f(t,T)$, notional $I$, surrender schedule $\underline{t}$, mortality schedule $\bar{t}$.
- **Parameters:** guaranteed rate $\delta$, death-benefit loading $1<\alpha<2$, baseline surrender $C$, sensitivity $\beta\in[0,1]$, penalty $\bar P\in[0,1)$.
- **Observed effects:** $\beta\uparrow$ raises SB but lowers GMAB and DB and lowers total value; $C\uparrow$ raises total value; $\delta\uparrow$ raises all components; $T=3$ gives 100.61, $T=10$ gives 109.63 per notional (arXiv:2410.11849v1, Table 4, Figs. 6.3–6.4).
- **Failure modes:** multidimensional integrands peak sharply near the origin, so plain Monte Carlo is high-variance; the paper uses importance sampling and validates against SciPy quadrature (bias and standard error <0.5%), while quadrature is impractical beyond ~4 dimensions (Sec. 6.1–6.2).

### 2.4 Linear-rational Wishart joint survival annuity and guaranteed annuity option
**Purpose.** Price a joint-survival annuity and an option on it under general dependence, with an exact one-integration option price.

$$dv_t=(\omega+mv_t+v_tm^\top)dt+\sqrt{v_t}\,dw_t\sigma+\sigma\,dw_t^\top\!\sqrt{v_t},\qquad \omega=\beta\sigma^2,\ \beta\ge n+1,$$
$$\mathrm{SB}(t,T)=P(t,T)e^{-\alpha(T-t)}\frac{1+b_0(T-t)+\operatorname{tr}[a_0(T-t)v_t]}{1+\operatorname{tr}[u_0v_t]},\quad \mu_x(s)=\frac{\alpha/2+\alpha\operatorname{tr}[u_1v_s]-\operatorname{tr}[u_1\omega]-2\operatorname{tr}[u_1mv_s]}{1+\operatorname{tr}[u_0v_s]},$$
$$\bar C(t,T,T_N)=P(t,T)e^{-\alpha(T-t)}\frac{E_t[(b_4+\operatorname{tr}[a_4v_T])_+]}{1+\operatorname{tr}[u_0v_t]},\qquad E_t[(Y_T)_+]=\frac1\pi\int_0^\infty\!\Re\frac{\Phi_Y(z+iz_i)}{(i(z+iz_i))^2}dz.$$

- **Inputs:** the Wishart state $v_0$ (or its moments), matrices $m,\sigma$, $\omega=\beta\sigma^2$, deterministic $P(t,T)$.
- **Parameters:** $\alpha,\beta,\rho_\sigma,m,\sigma,u_0=u_1+u_2\in\mathbb{S}^+_n$; both intensities are positive when $\alpha/2>\max(\omega_{11},\omega_{22})$ in the diagonal $n=2$ case; a $k$-joint annuity needs $n\ge k$.
- **Observed effects:** $\rho_\sigma$ (hence $(\sigma^2)_{12}$) drives the price; $\alpha$ is near-critical; the annuity density is known to one integration, giving VaR/ES; the **gamma approximation** beats the Gaussian and spectral ones (Gaussian over-estimates, spectral under-estimates) (Props. 5.2–5.7, Sec. 6).
- **Failure modes:** matrix parameters need constrained optimisation; the Bru case $\omega=\beta\sigma^2$ is restrictive (outside it the MGF is unknown and the option needs a second integration); illustration: 5-year joint annuity 4.467, at-the-money guarantee $g\approx0.225$.

### 2.5 Change-point hazard filter and partial-information pricing
**Purpose.** Estimate an unobserved mortality/default regime shift from noisy observations plus death data, and price under that information.

$$d\Pi_t=\lambda(1-\Pi_t)dt+\Pi_t(1-\Pi_t)\frac{\Delta\mu}{\beta}d\hat B_t+\frac{\Delta\mu(1-\Pi^-_t)\Pi^-_t}{\mu_\ell+\Delta\mu\Pi^-_t}d\hat m_t,\ \ \Pi_0=\pi;\ \ \Pi_\tau=\frac{\mu_h\Pi^-_\tau}{\mu_\ell+\Delta\mu\Pi^-_\tau};\ \ \kappa=\frac{\Delta\mu}{\Delta\mu-\lambda};$$
$$P_\pi(\tau>T\mid\mathcal{G}_t^Y)=\mathbf{1}_{\{\tau>t\}}\big[\kappa(1-\Pi_t)e^{-(\mu_\ell+\lambda)(T-t)}+\big(1-\kappa(1-\Pi_t)\big)e^{-\mu_h(T-t)}\big],$$
$$P(t,T)=e^{-\int_t^Tr}L\,P_\pi(\tau>T\mid\mathcal{G}_t^Y)+\int_t^TP_\pi(\tau>s\mid\mathcal{G}_t^Y)e^{-\int_t^sr}p(s)ds+\int_t^Te^{-\int_t^sr}W(s)f_{\tau|\mathcal{G}_t^Y}(s)ds.$$

- **Inputs:** noisy observation $d\hat Y_t=\mu_t\,dt+\beta\,dB_t$; death indicator $H_t$; priors $\pi,\lambda$ and levels $\mu_\ell,\mu_h$.
- **Parameters:** $\beta>0$, $\lambda$ (mean time to jump $1/\lambda$), $\pi=P_\pi(\xi=0)$. $L=1$ gives a defaultable coupon bond, $L=0$ a CDS; the same formulae price a death benefit (arXiv:2505.13185v3, Sec. 4.2).
- **Observed effects:** larger $\beta$ damps Brownian noise but worsens accuracy (at $t=\xi/2$, 45.4% of paths have $\Pi_t<0.3$ for $\beta=1$ vs 35.2% for $\beta=2$); larger $\mu_h$ accelerates the jump and sharpens accuracy (98.8% below 0.3); the $\mathcal{G}^Y$ estimate beats the $\mathcal{F}^Y$ estimate in mean-square error by construction (Sec. 3.1).
- **Failure modes:** before the shock the filter over-estimates the hazard, so partial-information prices sit below full-information prices pre-$\xi$ and above post-$\xi$; nothing identifies $\xi$ before death.

### 2.6 Hedging a pure endowment with a mortality $q$-forward
**Purpose.** Decide whether and how much a mortality derivative reduces the price of a pure endowment.

$$d{}^P\lambda_t=a^P{}^P\lambda_t\,dt+b^P(t)\,{}^P\lambda_t\,dW^P_t,\quad d{}^I\lambda_t=a^I{}^I\lambda_t\,dt+b^I(t)\,{}^I\lambda_t\,dW^I_t,\quad dW^IdW^P=\rho\,dt;$$
$$\theta^q_t=\frac{{}^P\lambda_t}{b^I(t)\,{}^I\lambda_t}\Big[\frac{{}^P\lambda_t}{{}^P\lambda_t+{}^I\lambda_t}\rho+\frac{{}^I\lambda_t}{{}^P\lambda_t+{}^I\lambda_t}\Big],\quad \lim_{h\to0}\tfrac1h\mathrm{Var}=(1-\rho^2)(b^P)^2({}^P\lambda)^2+{}^P\lambda\,({}^P P)^2;$$
$$\lim_{n\to\infty}\tfrac1nP^{(n)}=F(r;t)\,\psi({}^I\lambda,{}^P\lambda;t),\qquad \psi \text{ solves a \emph{linear} PDE}.$$

- **Inputs:** two correlated hazard rates (insured and reference populations), a $T$-bond, a $q$-forward with delivery price $K=E^Q[e^{\int_0^T{}^I\lambda}]$.
- **Parameters:** $\rho\in[-1,1]$, $q^I$ (market price of reference-mortality risk), $\eta\in(0,{}^P\lambda)$ (Sharpe ratio), $T$.
- **Observed effects:** with $\rho=1$ the risk is fully hedgeable as $n\to\infty$ and hedging lowers the limiting price iff $q^I<\eta$; with $\rho<1$ basis risk can reverse this; $q^I<0$ always lowers it; for a *single* life hedging is not guaranteed to reduce the price even when $q^I<\eta$ (Remark 4.1, Corollaries 4.1–4.3). Benchmark: $r=0.04$, $a^P=0.04$, $b^P=0.1$, ${}^P\lambda_{\min}=0.02$, $\eta=0.1$, $T=10$.
- **Failure modes:** the benefit's sign is a joint condition on $(\rho,q^I,\eta)$, so no rule is uniformly optimal; small $n$ keeps the mortality-timing variance that vanishes only asymptotically.

### 2.7 CAT bond pricing with a Wang distortion and Vasicek discounting
**Purpose.** Price a tranche from a loss sample and recover the par spread (or the risk-premium parameter).

$$V_0=\sum_{n=1}^{T}E_Q\big[B_n^{-1}(r_n+s)\mathbf{1}_{\{\tau^*>n\}}+B_n^{-1}(1-p_n)\mathbf{1}_{\{\tau^*=n\}}FV\big]+E_Q[B_T^{-1}\mathbf{1}_{\{\tau^*>T\}}FV],$$
$$p_n=\Big(\frac{(S_n-u_a)\vee0}{u_e-u_a}\Big)\wedge1,\quad \tau^*=\inf\{n:S_n\ge u_a\},\quad Q[\tau^*>n]=\prod_{u=1}^{n}Q[S_u<u_a],$$
$$g(q)=\Phi\big(\Phi^{-1}(q)-\lambda\big),\quad F_S^{Q}=g\circ F_S,\quad E_QB_n^{-1}=e^{A_1(0,n)-A_2(0,n)r_0},\quad \text{multiple}=\frac{s}{\text{expected loss}}.$$

- **Inputs:** a sample $\{S_j\}$ of annual losses from a frequency–severity or cat model, its empirical CDF $\hat F_S$; a Vasicek short rate.
- **Parameters:** $(u_a,u_e)$, spread $s$, skew $\lambda$ (catastrophe risk premium), $(\alpha,\mu,\sigma,r_0)$; the Q-expectation is $E_Q[(1-p_1)\mathbf{1}_{\{S\ge u_a\}}]=\sum_j[g\hat F_S(S_{(j)})-g\hat F_S(S_{(j-1)})](1-\frac{S_{(j)}-u_a}{u_e-u_a}\mathbf{1}_{\{u_a\le S_{(j)}<u_e\}})$.
- **Observed effects:** with $s=7\%$, $\alpha=20\%$, $\mu=2\%$, $\sigma=10\%$, $r_0=1\%$, $u_e=11.008$bn (200y), $u_a=7.861$bn (100y), the par skew is $\lambda=0.737$ and the AAL $0.891$bn; the 150y tranche prices to 100.69 at a 6.28% par spread; Brown–Resnick gives 100.11/100.79 and a univariate model 101.26/101.87 (Sec. 4.6).
- **Failure modes:** the spread is exogenous, so the model cannot say whether 7% is fair; expected loss rests on ~20 historical events, leaving the tail (Pareto index ≈2.55) poorly pinned down.

### 2.8 Transparent parametric-modeled-loss trigger from a max-stable hazard field
**Purpose.** Build a cat-bond trigger computable from public hazard data plus industry exposure, and measure its basis risk.

$$C_i(x)=D(Z_i(x))E(x),\quad D(z)=(z/c_1)^\beta,\quad S=\sum_i\sum_kC_i(x_k),\quad L_i=\sum_kC_i(x_k);$$
$$Z\overset{d}{=}\bigvee_{i\ge1}U_iY_i\ \text{(spectral repr.)},\quad \gamma_W(x)=\big(\|x\|/\kappa\big)^{\psi},\quad \rho(h)=\big(1+(h/\kappa)^2\big)^{-\psi}\ \text{(Cauchy)};$$
$$\text{basis risk: }\log\ell_i^{\mathrm{ins}}=\log\beta_1+\beta\sum_k\big(z_i(x_k)/c_1\big)E_i(x_k)+\varepsilon_i.$$

- **Inputs:** per-site maximal wind speeds (95 CRESTA centroids, 100 events), yearly exposure per site, industry losses per event, yearly event counts $N$.
- **Parameters:** $\beta=7.8$ (grid-searched 5–13 plus 0.1 steps near the optimum), $c_1$ (scale), extremal-$t$ $\nu=2.064$, Cauchy $\kappa=4.662$, $\psi=0.392$, nugget $a_0=0.006$; GEV means $\eta=16.916,\tau=5.029,\xi=-0.116$; negative-binomial frequency (size 3.955, mean 4.546, over-dispersion 2.149).
- **Observed effects:** $R^2=0.9307$ vs industry losses against 0.6923/0.7293/0.7390 for the benchmark triggers; 10-fold CV gives $\beta\in[7.6,8.1]$ and $\hat\beta_1=1.442\times10^{-16}$ (sd $3.421\times10^{-18}$); Friederike is under-predicted and Xavier over-predicted because the trigger ignores storm size and translation speed (arXiv:2609.22052v1).
- **Failure modes:** fitted on 20 loss events with exposure extrapolated backwards, inflating old damage ratios (Anatol/Lothar/Jeanett); trigger and benchmark both under-estimate the right tail; the authors state out-of-sample validation was impossible.

### 2.9 Coupon regression with climate indices
**Purpose.** Forecast the issuance spread and test whether large-scale climate variability adds information.

$$y_i=\beta^\top x_i+\varepsilon_i,\quad \hat y_{RF}(x)=\frac1T\sum_t h_t(x),\quad F_m(x)=F_{m-1}(x)+\nu\gamma_mh_m(x),$$
$$\Delta(S,f,\theta)=\mathrm{Var}(S)-\tfrac{|S_L|}{|S|}\mathrm{Var}(S_L)-\tfrac{|S_R|}{|S|}\mathrm{Var}(S_R)\ \text{(ETR)},\quad \hat y_i^{(k)}=\hat y_i+\epsilon_k,\ \epsilon_k\sim\hat N(0,\hat\sigma^2).$$

- **Inputs:** expected loss, attachment point/probability, size, term, trigger-type and peril×region dummies, cedent tenure, ROL index and its change, BB spread, equity/crypto returns, plus climate indices (ONI, AO, NAO, OLR, PNA, PDO, SOI, seven regional SST series) lagged 0–18 months.
- **Parameters:** Elastic Net feature selection; randomised search + 5-fold CV on the training set; 80:10:10 estimation/calibration/test split; test RMSE as ranking metric.
- **Observed effects:** OLS RMSE 0.01774→0.01682 with climate features (train $R^2$ 0.833→0.835); ETR best at 0.0123 vs 0.0142 (**−13.2%**); 5% VaR failure rates 4.35%→1.45%, all green under Basel; the selected climate terms are SOI shifted 15 months and OLR shifted 12 months (Tables 1–3).
- **Failure modes:** a 0.002 RMSE gain is economically small against a 0.077 spread; a single 10% test split (~73 tranches); lagged correlations near 0.2 invite spurious structure; the paper claims prediction only, not causality.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Equity index level/OHLCV (hybrid Lévy equity leg, $IS_T$) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily index/equity bars (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Insurer/reinsurer equity price (sponsor exposure) | `https://financialmodelingprep.com/stable/quote` | core_stock_apis | fmp | ok |
| SPX option quotes (embedded guarantee / GMAB overlaid put) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain incl. single names (local gateway) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move / implied guarantee inputs | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Treasury daily curve (discounting; $r_0$, $B(t,T)$) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Short-rate / macro series (Vasicek $\alpha,\mu$; inflation for loss trending) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Credit-spread hazard proxy (ICE BofA BB and CCC-and-lower HY OAS ⇒ $\mu_\ell,\mu_h$) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Corporate actions (adjusted equity returns) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| News/attention around catastrophe and mortality events | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| SEC filings (cat-bond SPV / insurer disclosure) | `https://data.sec.gov/submissions/CIK0000320193.json` | sec_filings | sec_edgar | ok |
| Global news tone (disaster salience) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| Swap/swaption/cap quotes (calibrate hybrid Lévy forward-rate model) | **gap** — no rates-derivative endpoint in the inventory | — | — | gap |
| Life tables / cohort mortality rates (HMD, national statistics) | **gap** — no mortality feed; $\lambda_i(0)$ must be supplied from files | — | — | gap |
| Insurer policy/death records (portfolio mortality experience) | **gap** — proprietary experience data | — | — | gap |
| Mortality-linked security prices ($q$-forward, longevity swap, mortality bond) | **gap** — no traded mortality-derivative quotes | — | — | gap |
| Longevity/mortality index level (LifeMetrics-type) | **gap** — no index provider in the inventory | — | — | gap |
| Cat-bond issuance records / primary-market coupons & spreads | **gap** — the 734-tranche Braun dataset is not served | — | — | gap |
| Cat-bond secondary quotes / ILS fund indices | **gap** — no ILS market-data endpoint | — | — | gap |
| Climate variability indices (ONI, SOI, AO, NAO, PDO, PNA, OLR) | **gap** — NOAA/CPC series absent from the inventory | — | — | gap |
| Regional sea-surface-temperature anomalies | **gap** — no SST feed | — | — | gap |
| Wind-speed / hazard fields per location (max gust, ERA5-like) | **gap** — no meteorological hazard endpoint | — | — | gap |
| Industry insured loss data per event (PERILS/PCS) | **gap** — no industry-loss feed | — | — | gap |
| Industry exposure / sums-insured fields (CRESTA) | **gap** — no exposure data source | — | — | gap |
| Natural-catastrophe event counts / frequency | **gap** — must be assembled externally | — | — | gap |
| Rate-on-Line (ROL) reinsurance pricing index | **gap** — no reinsurance-rate index feed | — | — | gap |
| Cat-linked derivatives (catastrophe equity put options) | **gap** — no listed cat-derivative quotes | — | — | gap |

**Tally:** 28 rows — `ok` 10, `gateway` 2, `fail` 1, `gap` 15.

## 4. Pitfalls, validation and measurement

- **One parameter can dominate the price; report its elasticity.** A 10% change in $\alpha$ moves the Wishart GAO fivefold (arXiv:2602.06415v1). Quote the local sensitivity to the state-price-density / risk-premium parameter, not just a point price.
- **"Independent lives" is not a harmless simplification.** Nulling the intensity correlation still leaves the common denominator $1+\operatorname{tr}[u_0v_s]$ coupling the intensities, and the price error reaches 40%; $v_{12}=0$ is not independence (arXiv:2602.06415v1).
- **Samples here are tiny and validation must be sample-efficient.** The vulnerability exponent comes from 20 events; CV moves the optimum over $\beta\in[7.6,8.1]$, and the authors explicitly could not run out-of-sample validation, with envelopes so wide that tail misfit is invisible (arXiv:2609.22052v1). Report ranges, not point estimates.
- **Tail underestimation is the default failure.** Both the cost-field trigger and the univariate benchmark under-predict the far right tail, leaving investors under-compensated; the Pareto-$\alpha$ rule of thumb is ≈2.55 with high uncertainty, and the largest historical adjusted loss (4.34bn, 22y) is far below the simulated 100y loss (7.861bn) (arXiv:2609.22052v1).
- **Model risk is first-order and vendor models hide it.** Alternate hazard models give par prices of 100.00 / 100.11 / 101.26 on identical cash flows; sponsors can arbitrage across vendor models, and observed ILS premia may be compensation for that very uncertainty (arXiv:2609.22052v1). Publish every assumption so a price can be recomputed independently.
- **Basis risk is a population problem.** A $q$-forward references an indexed population, so $\rho<1$, and the hedging benefit can vanish or invert even when $q^I<\eta$ (arXiv:1011.0248v1). Report the trigger's basis-risk regression ($R^2$ of realised vs trigger loss) with any price.
- **Information asymmetry biases prices in a predictable direction.** Under partial information the hazard estimate is too high before the shock and too low after, so partial-information prices sit below full-information prices pre-shock and above post-shock (arXiv:2505.13185v3). Any backtest must state its information set.
- **Leakage and in-sample traps.** Use disjoint estimation/calibration/test windows and fit residual distributions on the calibration window only (arXiv:2512.22660v1); two-step (marginals-then-dependence) calibration ignores parameter uncertainty while joint composite-likelihood estimation corrects it, and backwards-trended exposure inflates old damage ratios and biases the vulnerability fit (arXiv:2609.22052v1).
- **Numerical and statistical protocol.** Benchmark Monte Carlo against adaptive quadrature in low dimension and report bias and standard error — the corpus achieves <0.5% on GMAB/SB/DB components (arXiv:2410.11849v1). For coupon models report point error *and* interval calibration (Kupiec and Christoffersen $LR_{UC},LR_{IND},LR_{CC}$, Basel traffic light); both benchmarks land green, so the interval test alone does not discriminate (arXiv:2512.22660v1). Before simulating losses, run Pettitt's trend test ($p=0.1426$, no shift) and a Poisson over-dispersion test ($p=0.043$, factor 1.935 → negative binomial), then use bootstrap Q-Q envelopes (arXiv:2609.22052v1).
- **State the objective and the risk measure.** The mortality-hedging result compares *prices* (arXiv:1011.0248v1); the wider corpus states cat-bond design under expected disutility or a spectral risk measure, and the two need not rank designs identically.

## 5. Recommended first implementation in FinRobot

1. **(S) Credit-spread-implied hazard-rate engine with closed-form survival and pricing.** Implement $P(\tau>T\mid\mathcal{G}_t^Y)$ for both $\mu_h=\mu_\ell+\lambda$ and $\mu_h\neq\mu_\ell+\lambda$, the pivot $\kappa$, the conditional density and the defaultable-bond/CDS formulae, reading $\mu_\ell,\mu_h$ from the BB and CCC HY OAS series. `Data:` `fred` `macro_data` + `federal_reserve` `risk_free_curve` (both served). `Value:` the first genuinely priced life/credit-sensitive instrument FinRobot computes end-to-end from served data, and it demonstrates the partial-information mispricing sign. `Risk:` an OAS is a credit proxy for a mortality intensity, not a life table (arXiv:2505.13185v3).
2. **(S) Wang-distorted cat-bond tranche pricer with Vasicek discounting.** Implement $F_S^Q=g\circ F_S$, the piecewise-linear principal loss, the multi-year decoupled price and a par solver for $\lambda$ or the spread; expose attachment/exhaustion, attachment probability, expected loss and the multiple. `Data:` `federal_reserve` `risk_free_curve` + `fred` `macro_data` + an assumed annual-loss sample (loss feeds are `gap`). `Value:` reproduces the corpus' headline cat-bond analytics (par $\lambda\approx0.74$, tranche prices) from any input distribution. `Risk:` the loss distribution is an input, so the price demonstrates the mechanism only (arXiv:2609.22052v1).
3. **(S) OU + broken-heart joint-survival calculator.** Implement $m(t)$, $\sigma^2(t)$, the union probability and the bereavement-modified survivor intensity; report joint/last-survivor annuity factors and their sensitivity to $\epsilon_q,\kappa_q,\rho$. `Data:` parameters only (life tables are a `gap`). `Value:` quantifies the two effects that dominate this literature with closed-form code and no external feed. `Risk:` parameters must be sourced externally (arXiv:2410.11849v1, arXiv:2602.06415v1).
4. **(M) $Q\odot P$ equity-linked annuity pricer with surrender.** Implement GMAB+SB+DB as separate $Q\odot P$ expectations, a deterministic or affine curve for the finance leg, and the surrender intensity $\lambda^s_t=\beta|D(t_i)|+C$; use importance-sampling Monte Carlo with a low-dimensional quadrature benchmark. `Data:` `core_stock_apis` equity + `federal_reserve` curve + `cboe` `options_surface` for the embedded guarantee. `Value:` a full hybrid life-insurance valuation with explicit measure separation that later items reuse. `Risk:` the hybrid Lévy calibration needs a swap/swaption curve (`gap`) — start deterministic (arXiv:2410.11849v1).
5. **(M) Mortality-derivative hedging evaluator.** Implement the local-risk-minimisation $q$-forward holding, the residual-variance formula, the Sharpe-ratio PDE and the limiting linear-PDE price; scan $(q^I,\rho,\eta)$ and reproduce the "hedging raises the price" region. `Data:` prices from item 1 plus assumed $q^I,\rho,\eta$ ($q$-forward quotes are a `gap`). `Value:` turns "should we hedge?" into a reproducible, parameterised decision. `Risk:` no traded mortality derivative to calibrate $q^I$ (arXiv:1011.0248v1).
6. **(M) Linear-rational Wishart GAO pricer.** Implement the Wishart MGF, survival bond, annuity, Fourier option price, cumulants and gamma approximation; add VaR/ES from the annuity density. `Data:` inputs only. `Value:` an exact option price plus risk measures under flexible dependence — the strongest normative result in this category. `Risk:` matrix-parameter identification and the near-critical $\alpha$; calibrate by moments and report the $\alpha$ sensitivity (arXiv:2602.06415v1).
7. **(M) Cat-bond coupon model with climate features.** Implement the Elastic-Net selection, the OLS/RF/ETR/GBM/XGBoost comparison, the 80:10:10 split and the residual-based probabilistic forecast with Kupiec/Christoffersen VaR tests. `Data:` primary-market tranche data and climate indices — both `gap`; runs on an imported dataset only. `Value:` a testable climate–coupon link plus the validation harness any later coupon model must clear. `Risk:` gated on a proprietary dataset; RMSE gains are small against the 7.7% mean spread (arXiv:2512.22660v1).
8. **(L — deferred) Full parametric-modeled-loss cat bond with a max-stable hazard field.** Implement the cost field, extremal-$t$/Brown–Resnick fitting by pairwise composite likelihood with CLIC selection, the negative-binomial frequency and the full price. `Data:` wind-speed fields, CRESTA exposure and industry losses are all `gap`; only a licensed or uploaded dataset makes it runnable. `Value:` the complete transparent trigger-and-price pipeline ($R^2\approx0.93$). `Risk:` no served hazard/exposure feed exists and the source paper could not validate out of sample; keep out of scope until those feeds are in the inventory (arXiv:2609.22052v1).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2602.06415v1 | Joint survival annuity derivative valuation in the linear-rational Wishart mortality model | 2026 |
| 2609.22052v1 | Design and pricing of a transparent parametric-modeled loss CAT bond: application to German windstorm | 2026 |
| 2505.13185v3 | Filtering in a hazard rate change-point model with financial and life-insurance applications | 2025 |
| 2512.22660v1 | Machine learning models for predicting catastrophe bond coupons using climate data | 2025 |
| 2410.11849v1 | On the valuation of life insurance policies for dependent coupled lives | 2024 |
| 1011.0248v1 | Hedging Pure Endowments with Mortality Derivatives | 2010 |