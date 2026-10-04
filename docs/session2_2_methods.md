# Session 2.2 computation design

## Scope

Session 2.2 implements a **baseline dyad-independent separable temporal exponential-family random graph model (STERGM)** for a binary network observed at ordered discrete waves. It is deliberately narrower than a general STERGM. It has an intercept-only formation component and an intercept-only persistence component, each fitted only on the support where its change is possible. The app states this boundary in the interface, computation record, and code; it does not claim to fit within-component closure, degree, mixing, covariate effects, or a Monte Carlo likelihood for those effects.

Let the preceding and current observed networks be `Y^(t-1)` and `Y^t`. The formation and persistence networks are

\[
Y^+ = Y^{t-1}\cup Y^t, \qquad Y^- = Y^{t-1}\cap Y^t.
\]

The endpoint reconstruction is `Y^t = Y^- ∪ (Y^+ \ Y^(t-1))`. A general STERGM additionally assumes conditional separability,

\[
\Pr(Y^+,Y^-\mid Y^{t-1}) = \Pr(Y^+\mid Y^{t-1})\Pr(Y^-\mid Y^{t-1}),
\]

with compatible component supports. This factorization is an assumption; it does not follow from the deterministic reconstruction and does not imply dyad independence within a general component.

## Implemented baseline

For every transition-specific, jointly observed and admissible dyad set `D_(t-1,t)`, the app uses two distinct risk sets:

- the **formation risk set** consists of dyads with `Y_ij^(t-1)=0`;
- the **persistence risk set** consists of dyads with `Y_ij^(t-1)=1`.

The implemented component equations are

\[
\logit\Pr(Y^+_{ij}=1\mid Y^{t-1}_{ij}=0,D_{t-1,t})=\theta^+_{\mathrm{edges}},
\]

and

\[
\logit\Pr(Y^-_{ij}=1\mid Y^{t-1}_{ij}=1,D_{t-1,t})=\theta^-_{\mathrm{edges}}.
\]

Because the terms are intercept-only and no contemporaneous dependence statistic is included, each component likelihood factorizes over its stated risk set. The reported conditional likelihoods and intercept standard errors are therefore exact **for this baseline model**. A missing outcome class in either component produces no finite intercept estimate, and the app stops rather than regularizing or silently modifying the model.

A positive persistence coefficient favors retention. It has the opposite verbal implication for dissolution. The app never calls the persistence network `Y^-` a dissolution network.

## Data support and public examples

Exactly five public repeated binary-network examples are available in Session 2.2: Knecht classroom friendship, Sampson monastery liking, Coleman high-school nominations, COW formal alliances, and Windsurfers daily interaction. Their public source, relation meaning, actor/risk-set treatment, and limitations are in `data/session2_1_dataset_catalog.json`; the same panel may be valid for more than one temporal session because the Session 2.2 computation is distinct from the Session 2.1 lag-only TERGM calculation.

The app excludes unavailable dyads rather than coding them as non-ties. This includes actor absence, structural nonmembership, documented incidental missingness, and the specified observation break in the Windsurfers panel. The app does not convert ranks, fixed-choice designs, counts, values, cumulative relations, or unknown-time-spacing data into the baseline model.

## Audit outputs

The app renders every following output after a successful fit:

1. the observed four-cell transition composition and the separate formation/persistence supports;
2. component coefficient estimates with Wald intervals;
3. observed formation and persistence rates against the fitted homogeneous probabilities;
4. one-step conditional simulation envelopes for current ties, density, formations, dissolutions, persistent ties, overall stability, and mean degree;
5. complete observed tie-spell duration counts, left-, right-, and support-censoring counts, and the expected duration under the homogeneous memoryless baseline; and
6. a whole-transition bootstrap sensitivity interval only when at least five observed transitions are available.

The duration quantity `1/(1-persistence probability)` is reported only as a **panel-interval expected duration** under the dyad-independent, time-homogeneous, memoryless persistence baseline. It is not a continuous-time hazard estimate, and it is not used to treat censored spells as complete lifetimes.

One-step simulations condition on the observed preceding network and its component supports. They are a model-adequacy check for the implemented baseline, not a causal analysis, multi-step validation, or proof that a general STERGM fits.

## BYOD boundary

The BYOD page accepts a node-presence table with `wave`, `id`, and optional `transition_block`; an edge table with `wave`, `source`, and `target`; and an optional observed-risk table. A `transition_block` prevents a missing panel from being bridged. The participant declares directionality, support, and measurement interval; the app validates but does not infer these design choices.

## References

- Krivitsky, P. N., & Handcock, M. S. (2014). A separable model for dynamic networks. *Journal of the Royal Statistical Society: Series B*, 76, 29–46.
- Carnegie, N. B., Krivitsky, P. N., Hunter, D. R., & Goodreau, S. M. (2015). Improving the fit of ERGMs. *Journal of Computational and Graphical Statistics*, 24, 502–520.
- Boudourides, M. (2026). *A Guide to Statistical Network Modeling*.
