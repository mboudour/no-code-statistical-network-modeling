# Session 1.1 — Correction and post-revision audit

**Scope:** `slides/session1_1/session1_1.tex`, its compiled PDF, the Session 1.1 Streamlit boundary text, and the repository documentation.

## Applied corrections

| Item | Frame / material | Applied correction |
|---|---|---|
| 1 | Directed, undirected, and loopless support | The undirected loopless-dyad count now states `\binom{n}{2}=n(n-1)/2`. |
| 2 | Conditional-logit identity | Coefficients are now described as weighting their corresponding **change statistics** in conditional tie log-odds. The odds statement is restricted to a toggle with `\Delta_{ij}g_k=1`. |
| 3 | Toggle interpretation requires support | Fixed-degree support is distinguished from bipartite support: degree-preserving moves may be necessary under fixed degrees, while bipartite toggles are permitted only across modes. |
| 4 | Maximum pseudolikelihood | MPLE is now defined as a product of individual-dyad full conditional probabilities, explicitly distinguished from the joint ERGM likelihood. |
| 5 | Homophily and mixing | The potentially ambiguous generic mixing formula was removed. The slide now explains category-pair statistics and warns that undirected representations must not double-count dyads. |
| 6 | New ERGM diagnostic audit frame | A new frame identifies MCMC trace, autocorrelation, and sampled-statistic diagnostics; simulation-based degree, geodesic-distance, edgewise shared-partner, and dyadwise shared-partner checks; and model-specific audit features. It distinguishes convergence from goodness of fit. |
| 7 | Florentine families worked example | The computation wording now directs attention to estimation diagnostics and substantively relevant observed features compared with simulated-network distributions, rather than merely fitted sufficient statistics. |
| 8 | Session 1.1 synthesis | The absolute claim that MCMC is always required was replaced with the qualified statement that most nontrivial dependent ERGMs use simulation-based methods because the normalizing constant cannot be evaluated directly. |
| Additional audit finding | Companion-app link | The deck's obsolete `streamlit.app` URL was replaced with the live Render application URL: `https://no-code-statistical-network-modeling.onrender.com/`. |

## Curriculum boundary

Session 1.1 now introduces the standard diagnostic-audit framework without claiming that its interface has already performed every diagnostic. Session 1.2 is explicitly designated for the full standard ERGM analysis: MCMC diagnostics, simulation-based goodness of fit, model- and network-specific checks, curved terms, and degeneracy-aware refinement.

## Verification results

| Check | Result |
|---|---|
| Active Beamer frames | 50, with the diagnostic-audit frame in position 37 |
| Rendered document | 53 PDF pages: 50 Beamer frames plus the three supplied template pages |
| LaTeX compilation | Two clean `pdflatex -halt-on-error` passes |
| Layout review | No overfull or underfull box warnings, and no LaTeX warnings on the final pass |
| Rendered-page inspection | Verified the public-app link, dyad-count correction, conditional-logit and support corrections, mixing correction, MPLE correction, diagnostic-audit frame, Florentine revision, synthesis, and closing-contact slide |
| Regression guard | `tests/test_session1_1_materials.py` asserts all eight requested corrections, absence of the superseded wording, the live app link, and the 50-frame count |
| Application checks | Ruff completed cleanly; Session 1.1 data, ERGM, and material tests passed |
| Independent academic audit | Structured source-grounded audit returned `pass` with no additional concrete statistical or logical correction required |

## Result

The requested corrections are applied, rendered, and re-audited. No further correction was identified in the completed post-revision audit.
