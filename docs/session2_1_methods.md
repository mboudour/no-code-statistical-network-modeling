# Session 2.1 computation design

## Scope

Session 2.1 implements a transparent **first-order, lag-only, dyad-independent temporal ERGM subclass** for repeated binary networks. For each observed transition, all fitted predictors are functions of the preceding observed network and the dyad-specific transition risk set. Conditional on that history, current dyads factorize; hence the displayed logistic conditional likelihood is **exact for this stated subclass**.

This is not a silent substitute for:

- a general TERGM with contemporaneous structural dependence and an intractable normalizing constant;
- Monte Carlo maximum likelihood for such a general TERGM;
- a separable temporal ERGM (STERGM) with distinct formation and dissolution components;
- a continuous-time relational-event or survival model; or
- a causal model.

## Transition support and response

For adjacent observed waves `previous` and `current`, a dyad enters the calculation only when it is admissible and observed at both endpoints. The four descriptive counts are:

\[
N_{ab}^{(t)}=\sum_{(i,j)\in D_{t-1,t}}\mathbf{1}\{Y_{ij}^{t-1}=a,\;Y_{ij}^{t}=b\},\quad a,b\in\{0,1\}.
\]

Thus `N00` is a persistent non-tie, `N01` a formation, `N10` a dissolution, and `N11` a persistent tie. An optional node-level `transition_block` prevents the model from bridging a documented missing panel.

## Model

For a dyad in the transition risk set, the implemented conditional logit is

\[
\operatorname{logit}\Pr(Y_{ij}^{t}=1\mid Y^{t-1},D_{t-1,t})
=\beta_0+\beta_{\mathrm{mem}}Y_{ij}^{t-1}
+\beta_{\mathrm{drecip}}Y_{ji}^{t-1}
+\beta_{\mathrm{2path}}h_{ij}(Y^{t-1}).
\]

- `edges` supplies \(\beta_0\), a current-wave baseline.
- `memory` supplies \(\beta_{\mathrm{mem}}\), a lagged same-dyad persistence association.
- `delrecip` is allowed only for a directed response and supplies \(\beta_{\mathrm{drecip}}\), delayed reciprocity from the prior reverse tie.
- `lagged_twopath` uses a preceding-wave directed two-path count, or an undirected prior shared-neighbor count. It is not a current-wave triangle statistic.

The estimator maximizes the exact conditional logistic likelihood with L-BFGS-B and reports an observed-information covariance only when it can be stably inverted. Coefficients are conditional associations under the complete displayed model and do not identify behavioral mechanisms or causal effects.

## Diagnostic family

Each fit returns:

1. numerical optimizer status and information-matrix condition number;
2. the transition-by-transition joint-risk-set counts;
3. conditional one-step simulation envelopes for current tie totals, formation counts, and tie-persistence rates; and
4. a whole-transition bootstrap where enough observed transitions exist.

The bootstrap resamples whole transition blocks rather than independent dyads. It is deliberately not run below five modeled transitions. It is a finite-sample sensitivity calculation and does not turn a short panel into abundant temporal replication.

## Exactly five public worked examples

| Example | Support-aware specification | Why it is valid for Session 2.1 |
|---|---|---|
| Knecht classroom friendship | Directed edges + memory + delayed reciprocity | Four panels with documented missingness and departure recoded as unavailable risk, not zeros. |
| Sampson liking nominations | Directed edges + memory + delayed reciprocity + prior two-path exposure | Three separate repeated positive-affect panels for the same labelled actors. |
| Coleman Fall-to-Spring nominations | Directed edges + memory + delayed reciprocity | One valid transition with a stated fixed-roster assumption; computation exposes its severe replication limit. |
| COW formal alliances | Undirected edges + memory + prior shared-partner exposure | Eleven annual panels with a changing state-system risk set. |
| Windsurfers interactions | Undirected edges + memory + prior shared-neighbor exposure | Repeated daily panels with attendance-aware risk and a documented missing-panel break. |

The catalog records Newcomb fraternity rankings as an excluded public candidate because its fixed-choice ordinal response would require a separately justified constrained ranking or choice model.
