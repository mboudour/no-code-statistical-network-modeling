# Session 1.2 computation design

## Academic scope

Session 1.2 implements **curved ERGMs, fit, and degeneracy-aware auditing** for binary static networks. It follows Session 1.1 rather than replacing it: every computation remains conditional on an explicitly declared graph support, actor boundary, directionality, and mode structure.

For a curved exponential family,

\[
\Pr_{\theta}(Y=y)=\frac{\exp\{\eta(\theta)^{\mathsf T}g(y)\}}{\kappa\{\eta(\theta)\}},
\]

where \(\eta(\theta)\) is a nonlinear natural-parameter map. With Jacobian \(D_\eta(\theta)\), the relevant curved-model estimating condition is the **projected score**

\[
U(\theta)=D_\eta(\theta)^{\mathsf T}\left[g(y)-\mathbb{E}_\theta\{g(Y)\}\right],
\]

assessed relative to Monte Carlo uncertainty. It is not a demand for componentwise equality of every statistic in an expanded natural-parameter representation.

## Implemented model terms

The R engine is `r/fit_session1_2_ergm.R`; it invokes the standard `ergm` implementation through a versioned Python subprocess bridge. It supports only the following support-checked terms:

| Term identifier | R formula term | Permitted support |
|---|---|---|
| `edges` | `edges` | Binary static one-mode or bipartite |
| `mutual` | `mutual` | Directed, one-mode |
| `gwdegree` | `gwdegree(decay, fixed=TRUE/FALSE)` | Undirected, one-mode |
| `gwesp` | `gwesp(decay, fixed=TRUE/FALSE)` | One-mode; used in the guided app only for undirected closure |
| `gwidegree` | `gwidegree(decay, fixed=TRUE/FALSE)` | Directed, one-mode |
| `gwodegree` | `gwodegree(decay, fixed=TRUE/FALSE)` | Directed, one-mode |
| `b1degree2` | `b1degree(2)` | Bipartite |
| `b2degree2` | `b2degree(2)` | Bipartite |

A fixed decay is a stated canonical term. The only exposed free-decay sensitivity fits are the single-curve Florentine and Sampson workflows. The application does not estimate multiple decay parameters automatically.

## Exactly five public worked workflows

The public-network catalog from Session 1.1 is reused, but the Session 1.2 recipe registry (`app/session1_2_options.py`) assigns a different, method-appropriate calculation to each item:

1. **Florentine business ties** — fixed-decay geometrically weighted degree; one free-decay curved sensitivity fit; undirected degree, distance, ESP, DSP, components, isolates, and triangles.
2. **Sampson Wave 3 liking nominations** — edges, reciprocity, and fixed-decay geometrically weighted in-degree; one free-decay sensitivity fit; directed degree, distance, triad, reciprocity, component, and isolate diagnostics.
3. **Lazega advice** — an edges-plus-reciprocity baseline with the full directed diagnostic suite. The documented fixed-decay in-degree/out-degree pilot produced unconstrained MCMC nonmixing, so it is not presented as a default worked fit.
4. **Davis Southern Women** — a support-aware bipartite baseline using edges and a first-mode degree statistic; bipartite degree/distance/overlap diagnostics. A curved bipartite refinement is deliberately not forced because the documented support check reveals boundary or linear-dependence concerns.
5. **Kapferer tailor-shop sociational ties** — a fixed-decay edgewise shared-partner closure model and undirected diagnostic suite. The documented fixed-decay degree-plus-closure pilot produced unconstrained MCMC nonmixing, so it is not presented as a default worked fit.

The five examples are **not** automatic model recommendations. Their support notes and limits appear in the interface and downloaded computation records.

## Required standard audit

Every completed Session 1.2 fit returns the following, rather than a minimal subset:

1. **MCMC diagnostics:** retained sufficient-statistic trace plots, autocorrelation plots, and sampled-statistic distributions.
2. **Simulation-based GOF:**
   - undirected one-mode — degree, geodesic distance, edgewise shared partners, dyadwise shared partners;
   - directed one-mode — in-degree, out-degree, directed geodesic distance, triad census;
   - bipartite — first-mode degree, second-mode degree, bipartite geodesic distance.
3. **Additional simulation checks:** edges, isolates, component count, largest component, and a support-specific omitted statistic: triangles for undirected one-mode, mutual dyads for directed one-mode, or mode-specific two-path overlap for bipartite networks.

The app displays observed values against simulated means and 95% empirical envelopes. It states explicitly that an optimizer result or a false failure flag is **not proof of convergence**.

## Interpretation and failure boundaries

The interface distinguishes:

- MCMC mixing from MCMLE convergence;
- finite-MLE/boundary concerns from degeneracy;
- simulation-based generative GOF from prediction;
- conditional ERGM coefficient interpretation from causal inference.

A warning, nonconverged estimate, unavailable diagnostic, boundary coefficient, or unstable free-decay sensitivity fit remains part of the output record. The app never hides these outcomes or uses them as a prompt to fit more terms automatically.

## BYOD

BYOD accepts loopless binary static node/edge CSV tables only. It proposes a support-valid transparent starter formula: directed data receive `edges + mutual + gwidegree`, undirected data receive `edges + gwdegree` (with an optional fixed-decay closure candidate), and bipartite data receive an edges-only audit. Participants must justify the data boundary, structural zeros, missingness, and model choice outside the app.
