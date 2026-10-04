# Session 1.1 computation design

## Model family

For an observed binary static graph \(y\) on a declared support \(\mathcal{Y}\), the session uses the canonical ERGM

\[
\Pr_{\boldsymbol\theta}(Y=y\mid X)=\frac{\exp\{\boldsymbol\theta^{\mathsf T}g(y,X)\}}{\kappa(\boldsymbol\theta,X)}.
\]

The engine reports MCMC maximum-likelihood estimates using the standard `ergm` R package. The app's Session 1.1 formula controls deliberately permit only a small foundational set: `edges`; `mutual` for directed data; `triangle` only as a labelled undirected teaching comparison; and `b1degree(1)`/`b2degree(1)` for bipartite data. It also permits one optional matching and one optional numeric actor-covariate term.

## Why the app does not automate model selection

A valid ERGM specification depends on the actor boundary, admissible dyads, observation mechanism, network type, scientific question, covariate timing, and model diagnostics. Therefore, the app:

1. profiles but does not infer a network boundary;
2. rejects non-binary ties rather than choosing an undisclosed threshold;
3. prevents a reciprocity term for undirected data and bipartite-degree terms for one-mode data;
4. declares raw triangles a cautious educational comparison, not a default recommendation; and
5. exports the source-specific caveat, formula, MCMC controls, warnings, and results alongside every completed calculation.

Curved terms, degeneracy, goodness-of-fit, temporal ERGMs, STERGMs, and SAOMs are developed in later sessions rather than folded misleadingly into this first static-ERGM interface.
