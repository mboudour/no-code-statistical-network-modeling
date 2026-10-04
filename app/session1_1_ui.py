"""Streamlit page for Session 1.1: Foundations of static ERGMs."""

from __future__ import annotations

from io import StringIO
from typing import Any

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from network_core import (
    NetworkSpec,
    NetworkValidationError,
    categorical_attributes,
    load_catalog,
    load_example,
    network_profile,
    numeric_attributes,
    to_ergm_payload,
    validate_binary_network,
)
from r_engine import ErgMRuntimeError, engine_status, fit_static_ergm, install_engine

TERM_LABELS = {
    "edges": "Edges — baseline conditional tie propensity",
    "mutual": "Mutual — directed reciprocity",
    "triangle": "Triangle — undirected local closure (use only as an explicitly cautious introductory comparison)",
    "b1degree": "b1degree(1) — degree-one count in the first bipartite mode",
    "b2degree": "b2degree(1) — degree-one count in the second bipartite mode",
}


def _graph_figure(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    key: str,
) -> None:
    graph: nx.Graph | nx.DiGraph = nx.DiGraph() if directed else nx.Graph()
    graph.add_nodes_from(nodes["id"].astype(str))
    graph.add_edges_from(
        zip(edges["source"].astype(str), edges["target"].astype(str), strict=True)
    )
    if bipartite:
        mode_values = nodes["mode"].astype(str)
        positions = {
            str(identifier): (0 if mode == mode_values.iloc[0] else 1, index)
            for index, (identifier, mode) in enumerate(
                zip(nodes["id"], mode_values, strict=True)
            )
        }
    else:
        positions = nx.spring_layout(graph, seed=20261028)
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    node_x = [positions[node][0] for node in graph.nodes()]
    node_y = [positions[node][1] for node in graph.nodes()]
    hover = []
    node_lookup = nodes.copy()
    node_lookup["id"] = node_lookup["id"].astype(str)
    for node in graph.nodes():
        row = node_lookup.loc[node_lookup["id"] == node].iloc[0]
        attributes = "<br>".join(
            f"{column}: {row[column]}"
            for column in node_lookup.columns
            if column != "id" and pd.notna(row[column])
        )
        hover.append(
            f"<b>{node}</b><br>{attributes}" if attributes else f"<b>{node}</b>"
        )
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"width": 0.8, "color": "#9AA5B1"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            marker={
                "size": 10,
                "color": "#4E2A84",
                "line": {"width": 0.5, "color": "#FFFFFF"},
            },
            text=hover,
            hoverinfo="text",
            showlegend=False,
        )
    )
    figure.update_layout(
        title="Network view for structural orientation — not a fitted-model diagnostic",
        height=440,
        margin={"l": 10, "r": 10, "t": 45, "b": 10},
        template="plotly_white",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    st.plotly_chart(figure, width="stretch", key=key)


def _profile_panel(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    key: str,
) -> dict[str, Any]:
    profile = network_profile(nodes, edges, directed=directed, bipartite=bipartite)
    columns = st.columns(4)
    columns[0].metric("Actors / vertices", profile["nodes"])
    columns[1].metric("Observed ties", profile["observed_edges"])
    columns[2].metric("Admissible dyads", profile["admissible_dyads"])
    columns[3].metric("Density", f"{profile['density']:.3f}")
    if directed:
        st.caption(
            f"Reciprocated unordered dyads: {profile['reciprocated_unordered_dyads']}"
        )
    left, right = st.columns([3, 2])
    with left:
        _graph_figure(
            nodes,
            edges,
            directed=directed,
            bipartite=bipartite,
            key=f"{key}_network_plot",
        )
    with right:
        st.markdown("**Degree check**")
        st.dataframe(profile["degree_table"].head(15), width="stretch", hide_index=True)
        st.caption(
            "Degree structure is descriptive. It motivates questions but does not select an ERGM term automatically."
        )
    return profile


def _engine_panel() -> bool:
    status = engine_status()
    if status["available"]:
        st.success("Standard R/statnet ERGM engine is available.")
        return True
    st.warning(status["reason"])
    with st.expander("Install the R/statnet ERGM engine", expanded=False):
        st.write(
            "The application calls the documented `network` and `ergm` R packages. Installation is explicit; it installs only essential runtime dependencies (not optional suggested packages) and uses available parallel workers."
        )
        if st.button("Install essential ERGM runtime packages", key="install_ergm_runtime"):
            with st.spinner(
                "Installing essential ERGM runtime packages. This is a one-time setup for this deployed environment."
            ):
                try:
                    result = install_engine()
                except ErgMRuntimeError as error:
                    st.error(str(error))
                else:
                    if result["available"]:
                        st.success("The R/statnet ERGM engine is now ready.")
                        st.rerun()
                    else:
                        st.error(result["reason"])
    return False


def _formula_controls(
    nodes: pd.DataFrame,
    spec: NetworkSpec | None,
    *,
    directed: bool,
    bipartite: bool,
    key: str,
) -> tuple[list[str], str | None, str | None, dict[str, int]]:
    options = (
        list(spec.valid_terms)
        if spec is not None
        else [
            "edges",
            *(["mutual"] if directed else []),
            *(["triangle"] if not directed and not bipartite else []),
            *(["b1degree", "b2degree"] if bipartite else []),
        ]
    )
    defaults = list(spec.default_terms) if spec is not None else ["edges"]
    selected = st.multiselect(
        "Session 1.1 ERGM statistics",
        options,
        default=[item for item in defaults if item in options],
        format_func=lambda item: TERM_LABELS[item],
        key=f"{key}_terms",
    )
    if "edges" not in selected:
        selected.insert(0, "edges")
        st.info(
            "The baseline edges statistic is included for the stated Session 1.1 computation."
        )
    if "triangle" in selected:
        st.warning(
            "A raw triangle term is shown only to teach the change statistic. It can produce unstable or degenerate specifications; Session 1.2 covers curved alternatives and the full standard ERGM diagnostic audit."
        )
    category_options = categorical_attributes(nodes)
    numeric_options = numeric_attributes(nodes)
    match = st.selectbox(
        "Optional categorical matching attribute",
        ["— None —", *category_options],
        key=f"{key}_match",
    )
    covariate = st.selectbox(
        "Optional numeric actor covariate",
        ["— None —", *numeric_options],
        key=f"{key}_covariate",
    )
    with st.expander("Computation settings", expanded=False):
        first, second, third, fourth = st.columns(4)
        seed = first.number_input(
            "Random seed", 1, 99999999, 20261028, 1, key=f"{key}_seed"
        )
        burnin = second.select_slider(
            "MCMC burn-in",
            options=[2000, 5000, 10000, 20000],
            value=5000,
            key=f"{key}_burnin",
        )
        interval = third.select_slider(
            "MCMC interval",
            options=[500, 1000, 2000, 5000],
            value=1000,
            key=f"{key}_interval",
        )
        maxit = fourth.select_slider(
            "MCMLE maximum iterations",
            options=[4, 8, 12, 16],
            value=8,
            key=f"{key}_maxit",
        )
    return (
        selected,
        (None if match == "— None —" else match),
        (None if covariate == "— None —" else covariate),
        {
            "seed": int(seed),
            "mcmc_burnin": int(burnin),
            "mcmc_interval": int(interval),
            "mcmle_maxit": int(maxit),
        },
    )


def _result_record(
    spec_name: str,
    profile: dict[str, Any],
    result: dict[str, Any],
    selections: dict[str, Any],
    caution: str,
) -> str:
    coefficient_table = pd.DataFrame(result["coefficients"]).to_markdown(index=False)
    warnings = (
        "\n".join(f"- {warning}" for warning in result.get("warnings", []))
        or "- No R warnings were returned by the fit."
    )
    return f"""# Session 1.1 static ERGM computation record

## Dataset and support
- **Dataset:** {spec_name}
- **Vertices:** {profile["nodes"]}
- **Observed ties:** {profile["observed_edges"]}
- **Admissible dyads:** {profile["admissible_dyads"]}
- **Density:** {profile["density"]:.6f}
- **Directed:** {profile["directed"]}
- **Bipartite:** {profile["bipartite"]}

## Stated model
- **Formula:** `{result["formula"]}`
- **Selected statistics:** {", ".join(selections["terms"])}
- **Categorical matching attribute:** {selections["nodematch"] or "None"}
- **Numeric actor covariate:** {selections["nodecov"] or "None"}
- **MCMC controls:** `{result["mcmc_settings"]}`

## Coefficients
{coefficient_table}

## Warnings returned by R
{warnings}

## Interpretation boundary
Coefficients are conditional log-odds contributions for the stated change statistics, network support, and model specification. They are neither marginal tie probabilities nor causal effects.

## Dataset-specific caution
{caution}
"""


def _render_fit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    spec: NetworkSpec | None,
    label: str,
    key: str,
) -> None:
    ready = _engine_panel()
    profile = _profile_panel(
        nodes, edges, directed=directed, bipartite=bipartite, key=key
    )
    st.markdown("#### Specify the Session 1.1 model")
    terms, match, covariate, controls = _formula_controls(
        nodes, spec, directed=directed, bipartite=bipartite, key=key
    )
    st.caption(
        "The formula is deliberately limited to foundational binary static-ERGM terms. It does not select a model or validate a causal explanation."
    )
    if not ready:
        st.info(
            "Install or configure the R/statnet engine above before running the computation."
        )
        return
    if st.button("Fit the static ERGM", type="primary", key=f"{key}_fit"):
        try:
            payload = to_ergm_payload(
                nodes,
                edges,
                directed=directed,
                bipartite=bipartite,
                terms=terms,
                nodematch_attribute=match,
                nodecov_attribute=covariate,
                **controls,
            )
            with st.spinner(
                "Fitting the specified ERGM with R/statnet MCMC maximum likelihood estimation..."
            ):
                result = fit_static_ergm(payload)
        except (NetworkValidationError, ErgMRuntimeError) as error:
            st.error(str(error))
            return
        st.success(
            "The requested static ERGM finished. Inspect warnings and model limits before interpreting coefficients."
        )
        st.code(result["formula"], language="r")
        st.dataframe(
            pd.DataFrame(result["coefficients"]), width="stretch", hide_index=True
        )
        if result.get("warnings"):
            st.warning(
                "R returned the following warning(s):\n\n"
                + "\n".join(f"- {warning}" for warning in result["warnings"])
            )
        else:
            st.info(
                "R returned no warning messages. This does not replace convergence and simulation-based goodness-of-fit review."
            )
        st.write(result["interpretation_note"])
        record = _result_record(
            label,
            profile,
            result,
            {"terms": terms, "nodematch": match, "nodecov": covariate},
            spec.caution
            if spec
            else "For BYOD, retain the uploaded data dictionary and justify all boundary/support decisions.",
        )
        st.download_button(
            "Download computation record (Markdown)",
            record,
            file_name=f"{key}_static_ergm_record.md",
            mime="text/markdown",
            key=f"{key}_record",
        )


def _render_worked_examples() -> None:
    catalog = load_catalog()
    selected_id = st.selectbox(
        "Public static-network worked example",
        list(catalog),
        format_func=lambda identifier: catalog[identifier].name,
    )
    spec = catalog[selected_id]
    nodes, edges = load_example(spec)
    st.subheader(spec.name)
    st.caption(spec.network_type)
    first, second = st.columns(2)
    with first:
        st.markdown(f"**Why this example fits Session 1.1:** {spec.rationale}")
        st.markdown(f"**Support and scope:** {spec.response_scope}")
    with second:
        st.markdown(
            f"**Method appropriateness:** binary static ERGM with {('directed' if spec.directed else 'undirected')} support{'; bipartite' if spec.bipartite else ''}."
        )
        st.warning(f"**Use with care:** {spec.caution}")
        st.link_button("Open public source documentation", spec.source_url)
    _render_fit(
        nodes,
        edges,
        directed=spec.directed,
        bipartite=spec.bipartite,
        spec=spec,
        label=spec.name,
        key=f"worked_{spec.identifier}",
    )
    with st.expander("Inspect documented data tables", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown("**Node table**")
            st.dataframe(nodes, width="stretch", hide_index=True)
        with right:
            st.markdown("**Edge table**")
            st.dataframe(edges, width="stretch", hide_index=True)


def _read_upload(uploaded: Any) -> pd.DataFrame:
    if uploaded is None:
        return pd.DataFrame()
    raw = uploaded.getvalue().decode("utf-8")
    return pd.read_csv(StringIO(raw))


def _render_byod() -> None:
    st.subheader("Bring Your Own Data (BYOD)")
    st.write(
        "Upload a binary edge list and a matching node table. The exact validation contract mirrors the worked examples; the app does not silently recode valued ties or infer structural zeros."
    )
    with st.expander("Required files and columns", expanded=True):
        st.markdown(
            "- **Nodes CSV:** `id` and optional actor attributes; add `mode` for a bipartite network.\n- **Edges CSV:** `source`, `target`, and an optional binary `tie` column.\n- **No self-ties or duplicate dyads.** For an undirected network, `A,B` and `B,A` are duplicates.\n- **Valued/count relations:** Session 1.1 rejects them rather than silently dichotomizing them; use an explicitly justified later workflow."
        )
    first, second = st.columns(2)
    nodes_upload = first.file_uploader(
        "Node table (CSV)", type=["csv"], key="byod_nodes"
    )
    edges_upload = second.file_uploader(
        "Edge table (CSV)", type=["csv"], key="byod_edges"
    )
    directed = st.checkbox("Directed network", value=True, key="byod_directed")
    bipartite = st.checkbox(
        "Bipartite / two-mode network", value=False, key="byod_bipartite"
    )
    if nodes_upload is None or edges_upload is None:
        st.caption("Upload both CSV files to open the BYOD computation workspace.")
        return
    try:
        nodes = _read_upload(nodes_upload)
        edges = _read_upload(edges_upload)
        validate_binary_network(nodes, edges, directed=directed, bipartite=bipartite)
    except (UnicodeDecodeError, pd.errors.ParserError, NetworkValidationError) as error:
        st.error(
            f"The uploaded network cannot enter the Session 1.1 binary static-ERGM workflow: {error}"
        )
        return
    st.success(
        "Upload checks passed. The resulting calculation is conditional on the boundary, support, and coding you selected."
    )
    _render_fit(
        nodes,
        edges,
        directed=directed,
        bipartite=bipartite,
        spec=None,
        label="Participant-uploaded network",
        key="byod",
    )


def render_session1_1() -> None:
    st.title("Session 1.1 — Foundations of Static ERGMs")
    st.caption("Day 1 · October 28, 2026 · 3:00–4:30 PM GMT")
    st.info(
        "This computation page treats a static ERGM as a binary graph distribution on an explicitly declared support. It does not turn one network observation into a causal finding."
    )
    learn, worked, byod, resources = st.tabs(
        ["Conceptual map", "Five worked public networks", "BYOD", "Data and methods"]
    )
    with learn:
        st.markdown("### Computation map")
        st.markdown(
            "1. Define actors, relation, boundary, directionality, mode structure, and structural zeros.\n2. Inspect observed density and degree structure.\n3. Specify a small set of justified sufficient statistics.\n4. Fit the standard R/statnet ERGM.\n5. Inspect MCMC warnings and preserve a reproducible computation record."
        )
        st.markdown("### Formal model")
        st.latex(
            r"\Pr_{\theta}(Y=y\mid X)=\frac{\exp\{\theta^{\mathsf T}g(y,X)\}}{\kappa(\theta,X)}"
        )
        st.latex(
            r"\logit\Pr_{\theta}(Y_{ij}=1\mid Y_{-ij}=y_{-ij},X)=\theta^{\mathsf T}\Delta_{ij}g(y,X)"
        )
        st.caption(
            "The conditional-logit identity applies only when both tie states are admissible under the specified graph support."
        )
    with worked:
        _render_worked_examples()
    with byod:
        _render_byod()
    with resources:
        catalog = load_catalog()
        st.markdown("### Public-data provenance")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Example": item.name,
                        "Network type": item.network_type,
                        "Source": item.source,
                        "Citation": item.citation,
                    }
                    for item in catalog.values()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.markdown("### Session boundary")
        st.write(
            "Session 1.1 establishes a bounded specification-and-fit workflow. Session 1.2 introduces curved ERGMs, geometrically weighted terms, degeneracy-aware refinement, and the full standard ERGM audit: MCMC diagnostics, simulation-based goodness of fit, and network- and model-specific checks. Temporal ERGMs, STERGMs, and SAOMs are not substituted for static ERGMs on this page."
        )
