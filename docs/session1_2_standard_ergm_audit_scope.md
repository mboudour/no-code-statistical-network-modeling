# Session 1.2 — Standard ERGM analysis and audit scope

## Purpose

Session 1.2 will implement a **standard ERGM analysis**, not a reduced or fixed minimum checklist. Each fitted binary static ERGM will be assessed with the diagnostics that are appropriate to its support, directionality, mode structure, fitted statistics, and substantive purpose. A coefficient table without warnings is not treated as sufficient evidence of estimation quality or model adequacy.

## Estimation and MCMC diagnostics

For every fitted model, the app will provide the standard MCMC diagnostic output available from the `ergm` R ecosystem. This includes trace plots for monitored parameter or network statistics, autocorrelation plots, and sampled-statistic distribution or density summaries. The interface will preserve the estimation controls, diagnostic warnings, and a reproducible record of the diagnostic run.

## Simulation-based goodness-of-fit

The standard goodness-of-fit workflow will simulate networks from the fitted ERGM and compare their distributions with the observed network. The core comparisons will include degree distribution, geodesic-distance distribution, edgewise shared-partner distribution, and dyadwise shared-partner distribution whenever those statistics are meaningful for the network support.

## Model- and network-specific checks

The application will add diagnostics whenever they are relevant rather than presenting them as decorative defaults. These include in-degree and out-degree distributions for directed networks; mixing matrices or assortative-mixing checks when nodal attributes are substantively relevant; triad census for appropriate directed or small-network settings; component-size distribution when connectivity matters; and further substantively important statistics that were deliberately omitted from the fitted model.

## Interpretation rule

Observed statistics will be compared with distributions computed from networks simulated from the fitted model. Particular emphasis will be placed on meaningful omitted statistics, because agreement only on terms already fitted does not establish broader adequacy. The Session 1.2 interface will distinguish estimation diagnostics, goodness-of-fit comparisons, and substantive interpretation; it will not imply causal effects or automatic model selection.

## Session boundary

Session 1.1 remains the introductory specification-and-fit workflow. Session 1.2 introduces curved alternatives, degeneracy-aware refinement, and the full standard diagnostic and goodness-of-fit analysis described here. Temporal ERGMs, separable temporal ERGMs, and stochastic actor-oriented models remain later-session material.
