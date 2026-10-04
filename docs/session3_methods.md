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

The app reports:

- all returned estimates and standard errors;
- approximate 95% Wald intervals in the coefficient plot;
- final per-effect and maximum convergence ratios;
- simulated degree and, for directed panels, in-degree plus directed-triad-census goodness-of-fit distributions; and
- for Session 3.2, a simulated behavior-distribution goodness-of-fit audit.

A convergence ratio or simulation p-value is a diagnostic. Neither establishes model truth, causal selection, nor causal peer influence.

## Public workflows

Each session has exactly five visible public workflows. The source, wave range, response definition, actor-support rule, behavior-support restriction if applicable, reuse disclosure, and interpretation limit are versioned in `data/day3_saom_catalog.json`. Several Session 3.2 behavior specifications intentionally reuse the same documented network release; the app labels this reuse and does not present them as independent studies.

## Reproducibility

Every fit receives an explicit random seed, RSiena `n3` setting, and goodness-of-fit simulation count. The app exports those settings, the declared data boundary, estimates, diagnostics, warnings, and interpretation boundary as a JSON computation record.
