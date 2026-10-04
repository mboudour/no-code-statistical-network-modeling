# No-Code Statistical Network Modeling

Public computation and Beamer-material repository for the **instats seminar, A Guide to Statistical Network Modeling** by **Moses Boudourides**.

[![Streamlit App](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://no-code-statistical-network-modeling.onrender.com/) [Open the Streamlit App](https://no-code-statistical-network-modeling.onrender.com/)

---

## Interactive Companion App

The **[Streamlit application](https://no-code-statistical-network-modeling.onrender.com/)** is the public no-code companion for the seminar. It provides implemented Day 1 workflows for Sessions 1.1 and 1.2:

1. **Five worked public networks per session** — documented static-network examples selected only where that session's stated method is valid for the declared support and data structure.
2. **Guided model specification** — Session 1.1 provides foundational terms; Session 1.2 adds support-checked geometrically weighted terms, fixed-decay stability models, and bounded single-decay sensitivity fits.
3. **Standard R/statnet estimation and audit** — reproducible maximum-likelihood estimation through the `network` and `ergm` packages, including the full Session 1.2 MCMC, GOF, and support-specific simulation audit.
4. **Bring Your Own Data (BYOD)** — node-table and edge-list upload validation that mirrors the worked examples and rejects unsupported valued, temporal, duplicate, or structurally invalid networks.
5. **Computation record** — a downloadable record of the declared support, stated formula, MCMC settings, diagnostic outputs, warnings, and interpretation boundary.

The public companion will expand session by session as the seminar materials are implemented. It does not run participant-supplied code, and it does not silently recode data or select a model.

---

## Current delivery: Day 1 — Sessions 1.1 and 1.2

**Foundations of Static Exponential-Family Random Graph Models (ERGMs)**

Session 1.1 provides:

- a Streamlit no-code computation page for documented **binary static ERGMs**;
- exactly five publicly sourced, pre-validated network examples;
- BYOD edge-list and node-table validation that does not silently recode valued, temporal, or structurally incomplete data;
- a standard R/**statnet** calculation engine (`network` + `ergm`); and
- a 50-frame Beamer deck, including **47 substantive content frames**, compiled from the supplied seminar template.

### Session 1.2 — Curved ERGMs, Fit, and Degeneracy

The second unit provides:

- exactly five public, support-checked curved/stable ERGM workflows;
- a full standard audit: MCMC trace/autocorrelation/distribution panels, simulation-based GOF, and support-specific omitted-statistic checks;
- fixed-decay geometrically weighted degree and closure models, plus carefully bounded one-decay curved sensitivity fits;
- a BYOD audit workflow that preserves declared network support rather than applying inappropriate terms; and
- a 49-frame Beamer source deck, plus supplied repeating opening and closing template pages, compiled from the seminar template.

> **Academic boundary:** An ERGM coefficient is a conditional, model-based log-odds contribution on the declared graph support. It is not a marginal tie probability and is not, by itself, a causal effect.

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

### 4. Verify the implemented Day 1 units

```bash
PYTHONPATH=app .venv/bin/pytest -q
cd slides/session1_1
pdflatex -interaction=nonstopmode -halt-on-error session1_1.tex
cd ../session1_2
pdflatex -interaction=nonstopmode -halt-on-error session1_2.tex
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
```

The script extracts Florentine, Sampson, and Kapferer objects from the installed `ergm` version; downloads the Lazega public archive from the Oxford RSiena source; and reads NetworkX's documented Davis affiliation graph. It checks the documented counts before writing the files.

## Slides

The Beamer sources and supplied template assets are under [`slides/session1_1/`](slides/session1_1/) and [`slides/session1_2/`](slides/session1_2/). The opening, agenda, and closing template PDFs are retained; all substantive slides use itemized academic content and bold purple key terms. The Session 1.2 computation contract and audit boundary are documented in [`docs/session1_2_methods.md`](docs/session1_2_methods.md).

## License and data attribution

Repository code and original seminar text are available under the repository license. The public teaching datasets remain subject to their respective sources and citations; see the catalog and source documentation before reuse beyond this seminar context.
