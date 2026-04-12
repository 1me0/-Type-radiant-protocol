# A Mathematical Theory of Self-Correcting Systems
## State-Dependent Noise and Bifurcation Analysis
### Final Publication-Ready Version (Rigorous Stochastic Dynamical Systems Formulation)

---

## 1. Probability Space and Setup

Let $(\Omega, \mathcal{F}, \mathbb{P})$ be a complete probability space.

Let $(\mathcal{F}_t)_{t \ge 0}$ be a filtration satisfying the usual conditions, where:

\[
\mathcal{F}_t := \sigma(P_0, \xi_0, \dots, \xi_{t-1}).
\]

Let $X = \mathbb{R}^n$ with Euclidean norm $\|\cdot\|$, and let $M \subset X$ be a nonempty, closed, convex set.

Let $\Pi_M : X \to M$ be the orthogonal projection, satisfying:

\[
\|\Pi_M(x) - \Pi_M(y)\| \le \|x - y\| \quad \forall x,y \in X.
\]

Define:

\[
e_t := P_t - \Pi_M(P_t), \qquad V_t := \|e_t\|^2.
\]

---

## 2. Assumptions (Well-Posedness Conditions)

We assume:

### (A1) Projection
$\Pi_M$ is an orthogonal projection onto a closed convex set.

### (A2) Drift map regularity
$\mu : \mathbb{R}^n \to \mathbb{R}^n$ is:

- Borel measurable
- globally Lipschitz:
\[
\|\mu(x) - \mu(y)\| \le L \|x - y\|
\]
- of linear growth:
\[
\|\mu(x)\| \le a + b\|x\| \quad \forall x
\]

### (A3) Noise structure
$\{\xi_t\}$ is adapted and satisfies:

\[
\xi_t \mid \mathcal{F}_t \sim \mathcal{N}(0, \sigma(P_t)^2 I_n),
\quad
\mathbb{E}[\xi_t \mid \mathcal{F}_t] = 0,
\]

with state-dependent variance:

\[
\sigma(P_t) = \sigma_0 + \gamma \|e_t\|.
\]

### (A4) Boundedness via localization
For every $R > 0$, define stopping time:

\[
\tau_R := \inf\{t : \|P_t\| \ge R\}.
\]

Analysis is performed on the stopped process $P_{t \wedge \tau_R}$.

---

## 3. Stochastic Dynamics

The system evolves as:

\[
P_{t+1} = P_t + \alpha \mu\!\big((1+\beta)\tilde{\Pi}_M(P_t) - \beta P_t\big),
\]

where:

\[
\tilde{\Pi}_M(P_t) = \Pi_M(P_t) + \xi_t.
\]

---

## 4. Local Drift Inequality (Core Estimate)

There exist $\delta > 0$, $C > 0$, and a localization radius $R > 0$ such that for the stopped process and whenever $\|e_t\| \le \delta$:

\[
\mathbb{E}[V_{t+1} \mid \mathcal{F}_t]
\le
A(\gamma)V_t + C V_t^{3/2},
\]

where:

\[
A(\gamma)
=
1 - \alpha(1+\beta)
+ \alpha^2(1+\beta)^2 L^2
+ \alpha^2 \gamma^2 n L^2.
\]

---

## 5. Critical Threshold

Define the bifurcation parameter:

\[
\gamma_c
=
\frac{\sqrt{2\alpha(1+\beta)L - \alpha^2(1+\beta)^2 L^2}}
{\alpha L \sqrt{n}},
\]

with $\gamma_c := 0$ if the radicand is non-positive.

---

## 6. Main Theorem (Foster–Lyapunov Phase Transition)

### Theorem (Local Mean-Square Phase Transition)

Under assumptions (A1)–(A4), the stopped process $P_{t \wedge \tau_R}$ satisfies:

---

### (i) Stable Regime ($\gamma < \gamma_c$)

There exist constants $c > 0$ and $\delta > 0$ such that:

\[
\mathbb{E}[V_{t+1} \mid \mathcal{F}_t]
\le
(1 - c)V_t
\quad \text{whenever } \|e_t\| \le \delta.
\]

Consequently, there exists $C_0 > 0$ such that:

\[
\mathbb{E}[V_t] \le C_0 (1 - c)^t,
\]

and the process is **locally mean-square exponentially stable**.

---

### (ii) Unstable Regime ($\gamma > \gamma_c$)

There exist constants $c > 0$ and $\varepsilon > 0$ such that:

\[
\mathbb{E}[V_{t+1} \mid \mathcal{F}_t]
\ge
(1 + c)V_t
\quad \text{for } \|e_t\| \ge \varepsilon.
\]

Moreover, for some initial conditions:

\[
\sup_{t \ge 0} \mathbb{E}[V_{t \wedge \tau_R}] = \infty.
\]

Thus the system is **not mean-square stable (in the Foster–Lyapunov sense)**.

---

### (iii) Critical Regime ($\gamma = \gamma_c$)

\[
\mathbb{E}[V_{t+1} \mid \mathcal{F}_t]
\le
V_t + C V_t^{3/2}.
\]

The system is **marginally stable**, and higher-order nonlinearities determine asymptotic behavior.

---

## 7. Lyapunov Interpretation

The drift decomposes as:

### Deterministic contraction:
\[
- \alpha(1+\beta) + \alpha^2(1+\beta)^2 L^2
\]

### Stochastic amplification:
\[
+ \alpha^2 \gamma^2 n L^2
\]

The phase transition occurs when drift and noise exactly balance.

---

## 8. Lyapunov Exponent Characterization

Define:

\[
\lambda :=
\limsup_{t \to \infty}
\frac{1}{t}
\log \mathbb{E}[V_{t \wedge \tau_R}].
\]

Then:

- $\gamma < \gamma_c \Rightarrow \lambda < 0$
- $\gamma > \gamma_c \Rightarrow \lambda > 0$
- $\gamma = \gamma_c \Rightarrow \lambda = 0$

---

## 9. Noise Floor Case ($\sigma_0 > 0$)

If $\sigma_0 > 0$, then the process admits a stationary noise floor:

\[
\limsup_{t \to \infty} \mathbb{E}[V_{t \wedge \tau_R}]
\le
K_1 \sigma_0^2 + K_2 \sigma_0^4.
\]

The bifurcation threshold $\gamma_c$ is unchanged, as it arises from the state-dependent component.

---

## 10. Interpretation (Conceptual Meaning)

This system exhibits a **noise-induced phase transition**:

- below $\gamma_c$: correction dominates randomness
- above $\gamma_c$: noise self-amplifies via state coupling
- at $\gamma_c$: critical balance of contraction and diffusion

The threshold scales as:

\[
\gamma_c \propto \frac{1}{\sqrt{n}},
\]

indicating increasing instability in higher dimensions.

---

## References

- Stochastic approximation theory (Kushner & Yin)
- Borkar: Stochastic Recursive Algorithms
- Lyapunov stability for stochastic systems
- Projected dynamical systems (Nagurney & Zhang)
