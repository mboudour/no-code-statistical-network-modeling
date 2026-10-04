# Session 1.2 — implementation and post-revision audit

## Scope

This audit covers the Session 1.2 code, five worked public workflows, and the Beamer deck for **Curved ERGMs, Fit, and Degeneracy**.

## Workflow corrections made during validation

The first predeclared formulas were not accepted blindly. Reproducible low-budget smoke runs exposed two default refinements with **unconstrained MCMC nonmixing**:

| Public network | Initial candidate rejected | Published Session 1.2 candidate | Rationale |
|---|---|---|---|
| Lazega advice | `edges + mutual + gwidegree(0.5, fixed=TRUE) + gwodegree(0.5, fixed=TRUE)` | `edges + mutual` | The degree-augmented candidate did not mix under the documented reproducible pilot. The public app preserves the directed reciprocity baseline and full audit instead of presenting an unstable degree model as a result. |
| Kapferer sociational ties | `edges + gwdegree(0.5, fixed=TRUE) + gwesp(0.5, fixed=TRUE)` | `edges + gwesp(0.5, fixed=TRUE)` | The joint degree-plus-closure candidate did not mix under the documented pilot. The app retains the support-valid closure candidate, documents the rejected joint refinement, and keeps degree as an omitted diagnostic. |

This follows the session’s academic rule: a failed or unstable refinement is evidence to report, not an output to conceal or a reason to fabricate a substitute result.

## Final five-workflow smoke test

`docs/session1_2_workflow_smoke_test.json` records a final run for all five published recipes with fixed seed `20261028`, MCMC burn-in `1200`, MCMC interval `200`, maximum MCMLE iterations `4`, 64 retained statistic samples, and 10 GOF simulations. Every final recipe produced:

- a retained MCMC statistic sample;
- its full support-appropriate GOF set; and
- its support-specific simulation checks.

The small settings are a **smoke test**, not final inferential settings. The public app defaults to more conservative fit controls and lets presenters increase the GOF simulation count.

## Slide audit findings and adjudication

A structured independent review identified three useful missing definitions; the deck now defines:

1. **MCMLE** as Monte Carlo maximum likelihood estimation;
2. **relative interior** as the interior within the affine hull of the convex support; and
3. **projectivity** as marginal-family consistency under actor subsampling.

The review also questioned the leading \(e^{\alpha}\) factor in the displayed GWD, GWESP, and GWDSP formulas. That proposed correction was **not applied**, because the supplied source guide, **§2.2.2**, explicitly defines all three statistics with the leading \(e^{\alpha}\) scaling. The deck is therefore source-faithful and already states that alternative software parameterizations require an explicit decay convention.

## Precision corrections applied after subsequent review

The following seven refinements were applied without adding slides or changing the five published worked-network formulas:

1. The curved-ERGM definition now says that \(\eta(\theta)\in\mathbb{R}^q\) depends nonlinearly on \(\theta\in\mathbb{R}^p\), **typically** with \(p<q\), rather than treating \(q>p\) as an unconditional defining requirement.
2. Degeneracy is now defined as a model distribution that concentrates most probability on a relatively small set of configurations, often far from the observed network.
3. Finite-MLE nonexistence now refers precisely to the observed sufficient-statistic vector on the relevant convex-support boundary.
4. MCMC trace plots are now described primarily as retained **network-statistic** traces; parameter trajectories are distinguished as a possible iterative-estimation display.
5. The undirected GOF slide explicitly identifies edgewise and dyadwise **shared-partner distributions** as observed-versus-simulated distributional checks.
6. Bipartite overlap is now named generically as first-mode and second-mode **shared-neighbor overlap**, with the Davis women/event examples only as illustrations.
7. The BIC caution now states that no unique \(N\) is determined by a single dependent-network ERGM likelihood; any choice of actors or admissible dyads requires an explicit asymptotic justification.

The public app and computation records now use the same terminology. In particular, its bipartite simulation output labels first-mode and second-mode shared-neighbor overlap explicitly, and its methods tab distinguishes curvature, degeneracy, finite-MLE nonexistence, network-statistic MCMC traces, and the BIC boundary.

## Mechanical verification

- **Beamer source frames:** 49 authored frames, exceeding the required 35 substantive-frame minimum.
- **Repeating template pages:** supplied opening, agenda, and closing PDFs retained.
- **Compile status:** `pdflatex` succeeds twice without fatal errors or overfull-box warnings.
- **App visibility:** the Streamlit test harness confirms the five worked examples appear as a visible radio list, not a hidden selector.
- **Regression suite:** checks formula/support mapping, all five visible recipes, full undirected audit output, deck requirements, and the public app route.
