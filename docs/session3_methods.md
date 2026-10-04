# Day 3 — actor-oriented network and coevolution computation design

## Scope

The Day 3 Streamlit pages implement **explicitly stated RSiena stochastic actor-oriented models (SAOMs)** for documented repeated binary networks. The code calls `r/fit_saom.R` in the pre-provisioned Docker image; it does not install R packages at request time or replace RSiena with a Python approximation.

- **Session 3.1** fits a network-only SAOM with period-specific network rates, density, reciprocity for directed networks, and a closure statistic: directed transitive triplets or undirected transitive triads.
- **Session 3.2** fits a joint network--behavior coevolution SAOM with the Session 3.1 directed network terms plus behavior alter, ego, and similarity selection effects, and linear shape, quadratic shape, and average-similarity behavior effects.

The app is a transparent seminar calculation, not a general automatic model-selection service, causal analysis, or a guarantee of a converged publication-quality fit.

## Data contract

Every Day 3 computation starts from:

1. a nodes table with `wave,id`;
2. a loopless binary edge list with `wave,source,target`; and
3. for Session 3.2, a behavior table with `wave,id` and a selected numeric behavior column.

The code retains actors observed in every selected wave. For public Session 3.2 workflows only, it then applies a **displayed complete-behavior restriction**: a retained actor must have one observed selected behavior value at every selected wave. The interface displays the number removed by this second restriction. It never recodes structural absence, an unobserved tie, or a missing behavior as zero. BYOD uploads with missing selected behavior are rejected rather than silently filtered.

## Model and estimation boundary

For network state \(X(t)\), the network evaluation objective is a stated sum of density, compatible reciprocity/closure, and, for Session 3.2, behavior-based selection statistics. For repeated behavior \(V(t)\), the behavior objective includes shape and neighbor-similarity terms. RSiena estimates method-of-moments parameters by simulating the declared actor-oriented process.

The app reports all returned estimates, approximate 95% Wald intervals, period-specific rate parameters, final individual-effect convergence t-ratios, and the overall maximum convergence ratio. In an RSiena network-only fit, period rates are returned separately from the evaluation-effect vector: their estimates and standard errors are displayed, while individual returned convergence t-ratios apply to evaluation effects and the overall maximum ratio remains visible. A convergence ratio or simulation p-value is a diagnostic. Neither establishes model truth, causal selection, nor causal peer influence.

## Audit design

### Session 3.1: dynamics

Before fitting, the interface displays observed ties and density by wave; successive-wave Jaccard overlap; maintained, formed, and dissolved ties; and a directionality-compatible observed structural summary (mutual dyads and transitive two-path closures for directed panels, triangles for undirected panels). These are descriptive panel summaries, not separately identified formation, dissolution, or causal processes.

After fitting, RSiena simulation diagnostics compare the observed panel with fitted simulations for:

- degree distributions (and in-degree plus out-degree distributions for directed networks);
- a directed triad census for directed panels;
- mutual-dyad count and reciprocal-tie share for directed panels;
- a fixed-bin geodesic-distance distribution;
- a closure-sensitive shared-partner or directed-two-path distribution; and
- isolate count, weak-component count, and largest weak-component size.

Thus, an undirected workflow is never described as having a degree-only structural audit: it includes the closure-sensitive shared-partner distribution and component/isolate diagnostics.

### Session 3.2: dynamics, selection, and influence

The Session 3.2 page deliberately keeps three components distinct.

1. **Dynamics** uses the same observed network panel and network simulation diagnostics as Session 3.1, together with a dedicated network-effect interval display.
2. **Selection** displays observed tie-rate associations by ego score, alter score, and absolute score difference; an observed ego-by-alter tie-rate mixing heatmap; a dedicated selection-effect interval plot; and a fitted selection-only contribution surface. The surface evaluates only ego, alter, and range-normalized similarity terms while holding other model terms fixed; it is not a tie-probability or causal-response surface. A simulated tied-actor behavior mixing matrix is shown alongside its observed counterpart.
3. **Influence** displays behavior-score distributions, means, variances, score-transition matrices, and change distributions by wave or interval. It also displays observed ego score versus average alter score and observed behavior change versus both average alter score and ego--alter discrepancy. In a directed network, an alter is an actor to whom the ego has an outgoing tie under the declared convention. The fitted average-similarity and behavior-shape contributions are displayed separately from observed associations.

For joint network--behavior diagnostics, RSiena compares fitted simulations with the observed behavior distribution, behavior-change distribution, tied-actor behavior mixing matrix, range-normalized tied-actor similarity, same-score-tie proportion, and score-specific ego, alter, and absolute-difference tie-rate summaries. A simulated score cell without an eligible actor or dyad contributes a documented zero to retain a fixed auxiliary-statistic vector; cell-level values should therefore be read with the displayed observed eligibility context, not as causal estimates.

RSiena’s exact similarity construction is governed by its software definition. The app’s explanatory selection surface labels its normalization explicitly from the retained displayed behavior scale; it is a visualization of fitted ego/alter/similarity contributions, not a replacement for RSiena’s exact statistic or an assertion that sample extrema define a substantive scale range.

## Public workflows

Each session has exactly five visible public workflows. The source, wave range, response definition, actor-support rule, behavior-support restriction if applicable, reuse disclosure, and interpretation limit are versioned in `data/day3_saom_catalog.json`. Several Session 3.2 behavior specifications intentionally reuse the same documented network release; the app labels this reuse and does not present them as independent studies.

## Reproducibility

Every fit receives an explicit random seed, RSiena `n3` setting, and goodness-of-fit simulation count. The app exports those settings, the declared data boundary, estimates, diagnostics, warnings, and interpretation boundary as a JSON computation record.
