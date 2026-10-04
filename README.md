# No-Code Statistical Network Modeling

Public computation and Beamer-material repository for the **instats seminar, A Guide to Statistical Network Modeling** by **Moses Boudourides**.

## Current delivery: Session 1.1

**Foundations of Static Exponential-Family Random Graph Models (ERGMs)**

This first unit provides:

- a Streamlit no-code computation page for documented **binary static ERGMs**;
- exactly five publicly sourced, pre-validated network examples;
- BYOD edge-list and node-table validation that does not silently recode valued, temporal, or structurally incomplete data;
- a standard R/**statnet** calculation engine (`network` + `ergm`); and
- a 49-frame Beamer deck, including **46 substantive content frames**, compiled from the supplied seminar template.

> **Academic boundary:** An ERGM coefficient is a conditional, model-based log-odds contribution on the declared graph support. It is not a marginal tie probability and is not, by itself, a causal effect.

## Five public worked examples

| Example | Static network type | Session 1.1 computation |
|---|---|---|
| Florentine families business ties | Undirected, binary, unipartite | Edges baseline; theory-led actor-covariate comparison |
| Sampson monastery liking nominations, Wave 3 | Directed, binary, unipartite | Edges + reciprocity; optional documented group matching |
| Lazega law-firm advice | Directed, binary, unipartite | Edges + reciprocity; optional organizational-attribute hypothesis |
| Davis Southern Women attendance | Undirected, binary, bipartite | Edges + bipartite degree terms on woman–event support |
| Kapferer tailor-shop sociational ties | Undirected, binary, unipartite | Edges baseline and carefully labelled closure comparison |

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

### 4. Verify the current unit

```bash
PYTHONPATH=app .venv/bin/pytest -q
cd slides/session1_1
pdflatex -interaction=nonstopmode -halt-on-error session1_1.tex
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

The Beamer source and the three supplied template assets are under [`slides/session1_1/`](slides/session1_1/). The opening, agenda, and closing template PDFs are retained; all substantive slides use itemized academic content and bold purple key terms.

## License and data attribution

Repository code and original seminar text are available under the repository license. The public teaching datasets remain subject to their respective sources and citations; see the catalog and source documentation before reuse beyond this seminar context.
