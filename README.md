# No-Code Statistical Network Modeling

Public computation repository for the **instats seminar, A Guide to Statistical Network Modeling** by **Moses Boudourides**.

[![Streamlit App](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://no-code-statistical-network-modeling.onrender.com/) [Open the Streamlit App](https://no-code-statistical-network-modeling.onrender.com/)

---

## Methodological Guide and Slides

- **[Methodological guide](methodological_guide_and_slides/Boudourides_AGuideToStatisticalNetworkModeling_0.pdf)**
- **Session slides:** [Session 1.1](methodological_guide_and_slides/session1_1.pdf) · [Session 1.2](methodological_guide_and_slides/session1_2.pdf) · [Session 2.1](methodological_guide_and_slides/session2_1.pdf) · [Session 2.2](methodological_guide_and_slides/session2_2.pdf) · [Session 3.1](methodological_guide_and_slides/session3_1.pdf) · [Session 3.2](methodological_guide_and_slides/session3_2.pdf)

## Interactive Companion App

The **[Streamlit application hosted on Render](https://no-code-statistical-network-modeling.onrender.com/)** is the public no-code companion for the seminar. It provides implemented Day 1 workflows for Sessions 1.1 and 1.2, Day 2 workflows for Sessions 2.1 and 2.2, and Day 3 workflows for Sessions 3.1 and 3.2:

1. **Five worked public networks per session** — documented static-network examples selected only where that session's stated method is valid for the declared support and data structure.
2. **Guided model specification** — Session 1.1 provides foundational terms; Session 1.2 adds support-checked geometrically weighted terms, fixed-decay stability models, and bounded single-decay sensitivity fits.
3. **Standard R/statnet estimation and audit** — reproducible maximum-likelihood estimation through the `network` and `ergm` packages, including the full Session 1.2 MCMC, GOF, and support-specific simulation audit.
4. **Session 2.1 temporal computation** — exactly five public repeated-network workflows, first-order lag-only TERGMs with explicitly constructed joint risk sets, transition-count audits, one-step conditional simulations, and transition-block bootstrap sensitivity checks where temporal replication permits them.
5. **Session 2.2 separable computation** — the same five public repeated-network workflows are evaluated through distinct formation and persistence supports, component-specific rate and coefficient audits, one-step simulation envelopes, tie-spell censoring, and a whole-transition bootstrap only where temporal replication permits it.
6. **Day 3 actor-oriented computation** — exactly five public RSiena network-only workflows for Session 3.1 and five public RSiena network--behavior coevolution workflows for Session 3.2, with explicit balanced-panel support; full observed dynamics turnover/Jaccard profiles; convergence diagnostics; structural, behavior, and joint network--behavior simulation audits; and clearly separated selection/influence views.
7. **Bring Your Own Data (BYOD)** — node-table and edge-list upload validation that mirrors the worked examples and rejects unsupported valued, rank-order, multiplex, duplicate, or structurally invalid networks. Session 3.2 also requires a complete repeated numeric behavior on the retained actor panel.
8. **Computation record** — a downloadable record of the declared support, stated formula, settings, diagnostic outputs, warnings, and interpretation boundary.

The public companion will expand session by session as the seminar materials are implemented. It does not run participant-supplied code, and it does not silently recode data or select a model.

---

## Current delivery: Day 1 — Sessions 1.1 and 1.2

**Foundations of Static Exponential-Family Random Graph Models (ERGMs)**

Session 1.1 provides:

- a Streamlit no-code computation page for documented **binary static ERGMs**;
- exactly five publicly sourced, pre-validated network examples;
- BYOD edge-list and node-table validation that does not silently recode valued, temporal, or structurally incomplete data;
- a standard R/**statnet** calculation engine (`network` + `ergm`); and
- a Beamer deck compiled from the supplied seminar template and delivered directly to the seminar owner; slide assets are not versioned in this GitHub repository.

### Session 1.2 — Curved ERGMs, Fit, and Degeneracy

The second unit provides:

- exactly five public, support-checked curved/stable ERGM workflows;
- a full standard audit: MCMC trace/autocorrelation/distribution panels, simulation-based GOF, and support-specific omitted-statistic checks;
- fixed-decay geometrically weighted degree and closure models, plus carefully bounded one-decay curved sensitivity fits;
- a BYOD audit workflow that preserves declared network support rather than applying inappropriate terms; and
- a Beamer deck compiled from the supplied seminar template and delivered directly to the seminar owner; slide assets are not versioned in this GitHub repository.

> **Academic boundary:** An ERGM coefficient is a conditional, model-based log-odds contribution on the declared graph support. It is not a marginal tie probability and is not, by itself, a causal effect.

## Current delivery: Day 2 — Session 2.1

### Session 2.1 — Temporal ERGMs for Network Change

The third unit provides:

- exactly five public repeated-network workflows: Knecht classroom friendship, Sampson liking nominations, Coleman Fall-to-Spring nominations, COW annual formal alliances, and Windsurfers daily interactions;
- explicit wave-specific actor presence, structural availability, missingness, and joint at-risk-dyad logic, including a documented nonbridged missing-panel break in the Windsurfers workflow;
- an exact conditional logistic calculation for a declared **first-order lag-only TERGM subclass**, with edges, same-dyad memory, directed delayed reciprocity, and/or prior-wave two-path exposure;
- transition-specific N00/N01/N10/N11 summaries, conditional one-step simulation envelopes, numerical checks, and whole-transition bootstrap sensitivity where enough transitions exist;
- repeated-network BYOD validation, including optional `transition_block` and at-risk-dyad tables; and
- a 44-authored-frame Beamer deck, plus supplied repeating opening and closing template pages, delivered directly to the seminar owner rather than versioned in GitHub.

> **Temporal boundary:** The Session 2.1 computation is not a general TERGM with contemporaneous structural dependence, a Monte Carlo likelihood implementation for such a model, a STERGM formation/dissolution decomposition, a continuous-time model, or a causal analysis. Its scope is stated in [`docs/session2_1_methods.md`](docs/session2_1_methods.md).

### Session 2.2 — Separable TERGMs for Formation and Dissolution

The fourth unit provides:

- the same five public repeated-network workflows only where a binary response, repeated observations, and an explicit formation/persistence support are defensible;
- two separate component supports: prior non-ties for formation and prior ties for persistence, excluding structural unavailability, actor absence, and missingness from both;
- an exact conditional likelihood only for the explicitly stated, **intercept-only dyad-factorizing baseline STERGM**;
- component-specific support, coefficient, observed-rate, one-step conditional-simulation, omitted structural goodness-of-fit, duration-censoring, and whole-transition bootstrap audit panels; and
- a support-aware repeated-network BYOD workflow with the same stated baseline and no silent conversion to a general MCMC-fitted STERGM.

> **Separable-model boundary:** The Session 2.2 computation distinguishes formation from persistence but does not claim that the components have endogenous ERGM dependence, continuous-time hazards, causal effects, or a general duration model. Its scope is stated in [`docs/session2_2_methods.md`](docs/session2_2_methods.md).

## Current delivery: Day 3 — Sessions 3.1 and 3.2

### Session 3.1 — SAOMs for Actor-Driven Network Dynamics

The fifth unit provides:

- exactly five public repeated-network workflows: Knecht classroom friendship, RSiena s50 friendship, full Glasgow friendship, Coleman high-school friendship, and annual COW alliances;
- an RSiena network-only actor-oriented model with period-specific rates, density, directed reciprocity where appropriate, and the compatible directed-triplet or undirected-triad closure effect;
- visible tie-count/density, Jaccard, tie-turnover, reciprocity/closure, rate-parameter, coefficient, all-effect convergence, degree, triad, geodesic, shared-partner/closure, and component/isolate audit plots; and
- support-aware BYOD validation for repeated loopless binary networks.

### Session 3.2 — SAOMs for Selection and Influence

The sixth unit provides:

- exactly five documented public coevolution workflows: Knecht friendship--delinquency, Knecht friendship--alcohol, Glasgow friendship--alcohol, Glasgow friendship--cannabis, and s50 friendship--smoking;
- an explicitly stated joint RSiena model with behavior alter, ego, and similarity selection effects; behavior linear and quadratic shape effects; and average-similarity influence;
- explicitly separated **Dynamics**, **Selection**, and **Influence** plots: observed network turnover/Jaccard and structural summaries; behavior distributions, transitions, changes, and alter-exposure summaries; dedicated selection/influence intervals and fitted contribution views; plus observed-versus-simulated degree/triad/geodesic/closure/component, behavior-distribution/change, tied-behavior mixing, and joint network--behavior association audits; and
- a conservative complete-behavior support rule that is displayed for public workflows and enforced without silent imputation for BYOD uploads.

> **Day 3 boundary:** The labels *selection* and *influence* locate effects in the stated joint stochastic model. They do not by themselves identify causal peer influence, remove common causes, or recover unobserved microstep ordering. See [`docs/session3_methods.md`](docs/session3_methods.md).

## Day 1 public worked examples

| Example | Static network type | Session 1.1 computation | Session 1.2 computation |
|---|---|---|
| Florentine families business ties | Undirected, binary, unipartite | Edges baseline; theory-led actor-covariate comparison | Fixed-decay geometrically weighted degree; one-decay curved sensitivity; full undirected audit |
| Sampson monastery liking nominations, Wave 3 | Directed, binary, unipartite | Edges + reciprocity; optional documented group matching | Edges + reciprocity + fixed-decay geometrically weighted in-degree; directed audit |
| Lazega law-firm advice | Directed, binary, unipartite | Edges + reciprocity; optional organizational-attribute hypothesis | Edges + reciprocity baseline with a full directed audit; unstable fixed-decay degree refinements are not presented as defaults |
| Davis Southern Women attendance | Undirected, binary, bipartite | Edges + bipartite degree terms on woman–event support | Support-aware bipartite baseline and full bipartite audit; no forced curved refinement |
| Kapferer tailor-shop sociational ties | Undirected, binary, unipartite | Edges baseline and carefully labelled closure comparison | Fixed-decay edgewise shared-partner closure model; degree-plus-closure pilot is documented as nonmixing |

Detailed provenance, data scope, and method-appropriateness limits are in [`data/dataset_catalog.json`](data/dataset_catalog.json) and the app.

## Run locally

### 1. Python application

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/streamlit run app/app.py
```

### 2. Standard R ERGM engine

The application invokes R through a subprocess and uses the mature `statnet` implementation; it does **not** substitute a simplified Python approximation.

```bash
# Install R first if required, then run this explicit bootstrap.
Rscript r/bootstrap_packages.R
```

The Streamlit page reports whether the R engine is available and provides an explicit installation control. It never installs software merely because a user opens a dataset. The bootstrap intentionally installs only required runtime dependencies—not optional suggested packages—and uses up to two available workers so first-use setup is substantially smaller and faster.

### 3. Public Docker deployment — recommended

For a public seminar service, use the repository's [`Dockerfile`](Dockerfile) and [`render.yaml`](render.yaml), rather than asking participants to install R packages. The image uses the r2u distribution's prebuilt R/statnet packages **while the image is built**. Consequently, the running application starts with `ergm` available and presents no participant-facing package-installation step.

Detailed local-validation and Render deployment instructions are in [`docs/docker-deployment.md`](docs/docker-deployment.md).

### 4. Verify the implemented units

```bash
PYTHONPATH=app .venv/bin/pytest -q
```

## BYOD contract for Session 1.1

- **Nodes CSV:** one unique `id` column and optional actor attributes; include `mode` for a bipartite graph.
- **Edges CSV:** `source`, `target`, and optionally a binary `tie` column.
- The session supports **loopless binary static networks** only. It rejects duplicate dyads, unknown actor IDs, unsupported within-mode bipartite edges, and non-binary values.
- A valued, temporal, multiplex, or missing-data design is not coerced to a binary static ERGM. It requires an explicitly justified model/data workflow, introduced in later sessions where appropriate.

## Rebuild bundled public data

The committed CSV files are reproducibly generated from publicly documented sources:

```bash
.venv/bin/python scripts/build_session1_1_public_data.py
.venv/bin/python scripts/build_session2_1_public_data.py
```

The Session 1.1 script extracts Florentine, Sampson, and Kapferer objects from the installed `ergm` version; downloads the Lazega public archive from the Oxford RSiena source; and reads NetworkX's documented Davis affiliation graph. The Session 2.1 script preserves each repeated relation, its relevant support rule, and its documented source rather than pooling waves. It reads public Statnet/RSiena panels and source archives for the COW annual series; each script checks its documented output before writing files. Day 3 public-panel extraction is documented in [`scripts/build_day3_public_data.R`](scripts/build_day3_public_data.R) and [`data/day3_saom_catalog.json`](data/day3_saom_catalog.json).

## Slide delivery

Beamer decks, their PDF exports, and supplied slide-template assets are deliberately **delivered directly to the seminar owner** and are not stored in this GitHub repository. The repository retains the application, computation engines, public-data provenance, and method documentation. The Session 1.2 computation contract is documented in [`docs/session1_2_methods.md`](docs/session1_2_methods.md); the Session 2.1 design and computation boundary are documented in [`docs/session2_1_methods.md`](docs/session2_1_methods.md); the Session 2.2 separable baseline is documented in [`docs/session2_2_methods.md`](docs/session2_2_methods.md); and the Day 3 RSiena boundary is documented in [`docs/session3_methods.md`](docs/session3_methods.md).

## License and data attribution

Repository code and original seminar text are available under the repository license. The public teaching datasets remain subject to their respective sources and citations; see the catalog and source documentation before reuse beyond this seminar context.
