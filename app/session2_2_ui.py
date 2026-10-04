"""Streamlit page for Session 2.2: separable formation–persistence TERGMs."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from session2_2_options import WORKED_RECIPES, byod_method_note, recipes_by_identifier
from stergm_core import fit_separable_stergm
from temporal_core import (
    TemporalNetwork,
    TemporalValidationError,
    load_temporal_catalog,
    load_temporal_example,
    rejected_temporal_candidate,
    temporal_profile,
    validate_temporal_network,
)

PALETTE = {
    "formation": "#F59E0B",
    "persistence": "#4E2A84",
    "dissolution": "#DC2626",
    "observed": "#111827",
    "mean": "#2563EB",
    "interval": "rgba(37, 99, 235, 0.20)",
}


def _read_csv(upload: Any) -> pd.DataFrame:
    """Read a UTF-8 CSV upload without any silent transformation."""
    return pd.read_csv(StringIO(upload.getvalue().decode("utf-8")))


def _transition_labels(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["transition"]) for row in rows]


def _profile_panel(network: TemporalNetwork, key: str) -> None:
    """Display source support before the separable fit is requested."""
    profile = temporal_profile(network)
    columns = st.columns(4)
    columns[0].metric("Observed waves", profile["observed_waves"])
    columns[1].metric("Transitions with joint at-risk dyads", profile["observed_transitions"])
    columns[2].metric("Directionality", "Directed" if network.directed else "Undirected")
    columns[3].metric("Observed edge rows", len(network.edges))
    st.markdown("##### Wave profile")
    st.dataframe(profile["wave_table"], width="stretch", hide_index=True)
    st.markdown("##### Four observed transition cells")
    st.caption(
        "N00 is a persistent non-tie, N01 a formation, N10 a dissolution, and N11 a persistent tie on the joint observed risk set. In Session 2.2, N01 and N11 have distinct component supports."
    )
    st.dataframe(profile["transition_table"], width="stretch", hide_index=True)
    data = profile["transition_table"].copy()
    labels = data["from_wave"].astype(str) + " → " + data["to_wave"].astype(str)
    figure = go.Figure()
    for column, label, color in [
        ("persistent_nonties_N00", "N00 persistent non-ties", "#CBD5E1"),
        ("formations_N01", "N01 formations", PALETTE["formation"]),
        ("dissolutions_N10", "N10 dissolutions", PALETTE["dissolution"]),
        ("persistent_ties_N11", "N11 persistent ties", PALETTE["persistence"]),
    ]:
        figure.add_trace(go.Bar(x=labels, y=data[column], name=label, marker_color=color))
    figure.update_layout(
        title="Observed transition composition before component fitting",
        barmode="stack",
        template="plotly_white",
        height=355,
        margin={"l": 35, "r": 20, "t": 55, "b": 85},
        xaxis_title="Observed transition",
        yaxis_title="Joint at-risk dyads",
        legend={"orientation": "h", "y": -0.30},
    )
    st.plotly_chart(figure, width="stretch", key=f"{key}_observed_composition")


def _coefficient_figure(result: dict[str, Any]) -> go.Figure:
    """Render process-specific intercept estimates and Wald intervals."""
    rows = pd.DataFrame([result["formation"], result["persistence"]])
    rows["label"] = ["Formation edges", "Persistence edges"]
    figure = go.Figure()
    for _, row in rows.iloc[::-1].iterrows():
        error = 1.96 * float(row["standard_error"])
        figure.add_trace(
            go.Scatter(
                x=[row["estimate"]],
                y=[row["label"]],
                mode="markers",
                marker={"size": 11, "color": PALETTE[str(row["component"])]},
                error_x={"type": "data", "array": [error], "visible": True},
                hovertemplate=(
                    "Component=%{y}<br>Estimate=%{x:.3f}<br>95% Wald interval="
                    f"[{float(row['estimate']) - error:.3f}, {float(row['estimate']) + error:.3f}]<extra></extra>"
                ),
                name=str(row["label"]),
            )
        )
    figure.add_vline(x=0, line_dash="dash", line_color="#64748B")
    figure.update_layout(
        title="Distinct formation and persistence intercepts (Wald 95% intervals)",
        template="plotly_white",
        height=290,
        margin={"l": 35, "r": 20, "t": 55, "b": 45},
        xaxis_title="Component-specific conditional log-odds",
        showlegend=False,
    )
    return figure


def _support_figure(result: dict[str, Any]) -> go.Figure:
    """Show the two separate component risk sets at every transition."""
    data = pd.DataFrame(result["transition_support"])
    labels = data["from_wave"].astype(str) + " → " + data["to_wave"].astype(str)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=labels,
            y=data["formation_risk_dyads"],
            name="Formation support: prior non-ties",
            marker_color=PALETTE["formation"],
        )
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=data["persistence_risk_ties"],
            name="Persistence support: prior ties",
            marker_color=PALETTE["persistence"],
        )
    )
    figure.update_layout(
        title="Formation and persistence supports are different risk sets",
        barmode="stack",
        template="plotly_white",
        height=350,
        margin={"l": 35, "r": 20, "t": 55, "b": 85},
        xaxis_title="Observed transition",
        yaxis_title="At-risk dyads or ties",
        legend={"orientation": "h", "y": -0.30},
    )
    return figure


def _rate_figure(result: dict[str, Any], component: str) -> go.Figure:
    """Compare observed transition-specific rates with the fitted homogeneous probability."""
    data = pd.DataFrame(result["process_rate_audit"])
    if component == "formation":
        observed, fitted, title = (
            "observed_formation_rate",
            "fitted_formation_probability",
            "Formation rate: observed versus fitted homogeneous component",
        )
    else:
        observed, fitted, title = (
            "observed_persistence_rate",
            "fitted_persistence_probability",
            "Persistence rate: observed versus fitted homogeneous component",
        )
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["transition"], y=data[observed], mode="lines+markers", name="Observed rate", line={"color": PALETTE["observed"], "width": 3}
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["transition"], y=data[fitted], mode="lines+markers", name="Fitted component probability", line={"color": PALETTE[component], "dash": "dash", "width": 3}
        )
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=340,
        margin={"l": 35, "r": 20, "t": 55, "b": 85},
        xaxis_title="Observed transition",
        yaxis_title="Probability on the component support",
        yaxis_range=[0, 1],
        legend={"orientation": "h", "y": -0.30},
    )
    return figure


def _simulation_figure(rows: list[dict[str, Any]], prefix: str, label: str, yaxis: str) -> go.Figure:
    """Plot one observed transition diagnostic against conditional simulation envelopes."""
    data = pd.DataFrame(rows)
    observed = f"observed_{prefix}"
    mean = f"simulated_{prefix}_mean"
    low = f"simulated_{prefix}_lower_025"
    high = f"simulated_{prefix}_upper_975"
    labels = _transition_labels(rows)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=labels + labels[::-1],
            y=data[high].tolist() + data[low].tolist()[::-1],
            fill="toself",
            fillcolor=PALETTE["interval"],
            line={"color": "rgba(0,0,0,0)"},
            name="95% conditional simulation envelope",
            hoverinfo="skip",
        )
    )
    figure.add_trace(go.Scatter(x=labels, y=data[mean], mode="lines+markers", name="Simulation mean", line={"color": PALETTE["mean"], "width": 3}))
    figure.add_trace(go.Scatter(x=labels, y=data[observed], mode="markers", name="Observed", marker={"color": PALETTE["observed"], "size": 10, "symbol": "diamond"}))
    figure.update_layout(
        title=label,
        template="plotly_white",
        height=335,
        margin={"l": 35, "r": 20, "t": 55, "b": 85},
        xaxis_title="Observed transition",
        yaxis_title=yaxis,
        legend={"orientation": "h", "y": -0.30},
    )
    return figure


def _duration_figure(result: dict[str, Any]) -> go.Figure:
    """Show only completed observed spells, never treating censored spells as complete."""
    data = pd.DataFrame(result["duration_audit"]["complete_spell_distribution"])
    figure = go.Figure()
    if data.empty:
        figure.add_annotation(
            text="No complete observed tie spells are available after support and endpoint censoring.",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
    else:
        figure.add_trace(
            go.Bar(
                x=data["observed_duration_intervals"],
                y=data["complete_spells"],
                marker_color=PALETTE["persistence"],
                name="Complete observed spells",
            )
        )
    figure.update_layout(
        title="Observed complete tie-spell durations (censored spells excluded)",
        template="plotly_white",
        height=330,
        margin={"l": 35, "r": 20, "t": 55, "b": 55},
        xaxis_title="Observed duration in panel intervals",
        yaxis_title="Complete observed spells",
        showlegend=False,
    )
    return figure


def _bootstrap_figure(result: dict[str, Any]) -> go.Figure | None:
    """Render the component-specific whole-transition bootstrap if it is available."""
    bootstrap = result["bootstrap"]
    if bootstrap["status"] != "ok":
        return None
    data = pd.DataFrame(bootstrap["intervals"])
    figure = go.Figure()
    for _, row in data.iloc[::-1].iterrows():
        figure.add_trace(
            go.Scatter(
                x=[row["median"]],
                y=[row["component"]],
                mode="markers",
                marker={"size": 10, "color": PALETTE["formation"] if row["component"] == "formation_edges" else PALETTE["persistence"]},
                error_x={
                    "type": "data",
                    "array": [row["upper_975"] - row["median"]],
                    "arrayminus": [row["median"] - row["lower_025"]],
                    "visible": True,
                },
                name=str(row["component"]),
            )
        )
    figure.add_vline(x=0, line_dash="dash", line_color="#64748B")
    figure.update_layout(
        title="Whole-transition bootstrap sensitivity intervals",
        template="plotly_white",
        height=270,
        margin={"l": 35, "r": 20, "t": 55, "b": 45},
        xaxis_title="Component log-odds estimate",
        showlegend=False,
    )
    return figure


def _record(label: str, recipe_note: str, result: dict[str, Any]) -> str:
    """Create a transparent download record without claiming a general STERGM fit."""
    return "\n".join(
        [
            f"# Session 2.2 baseline STERGM record — {label}",
            "",
            "## Scope",
            recipe_note,
            "",
            "## Component formulas",
            f"- {result['formation_formula']}",
            f"- {result['persistence_formula']}",
            "",
            "## Component estimates",
            pd.DataFrame([result["formation"], result["persistence"]]).to_markdown(index=False),
            "",
            "## Transition supports and rates",
            pd.DataFrame(result["transition_support"]).to_markdown(index=False),
            "",
            "## Diagnostic flags",
            *(
                [f"- {flag}" for flag in result["diagnostic_flags"]]
                or ["- None reported."]
            ),
            "",
            "## Interpretation boundary",
            result["interpretation_note"],
        ]
    )


def _render_results(result: dict[str, Any], key: str) -> None:
    """Render every baseline STERGM audit plot in a fixed, visible order."""
    st.success("The Session 2.2 separable calculation finished. Interpret formation and persistence only after inspecting their distinct supports and diagnostics.")
    st.code(result["formation_formula"] + "\n" + result["persistence_formula"], language="text")
    st.dataframe(pd.DataFrame([result["formation"], result["persistence"]]), width="stretch", hide_index=True)
    st.plotly_chart(_coefficient_figure(result), width="stretch", key=f"{key}_coefficients")
    st.warning("Diagnostic flags:\n\n" + "\n".join(f"- {item}" for item in result["diagnostic_flags"]))
    st.markdown("#### 1. Component-support audit")
    st.caption("A prior tie is never a formation opportunity, and a prior non-tie is never a persistence opportunity. The displayed supports are separate by construction.")
    st.dataframe(pd.DataFrame(result["transition_support"]), width="stretch", hide_index=True)
    st.plotly_chart(_support_figure(result), width="stretch", key=f"{key}_supports")
    st.markdown("#### 2. Process-rate and component-calibration audit")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_rate_figure(result, "formation"), width="stretch", key=f"{key}_formation_rates")
    with right:
        st.plotly_chart(_rate_figure(result, "persistence"), width="stretch", key=f"{key}_persistence_rates")
    st.dataframe(pd.DataFrame(result["process_rate_audit"]), width="stretch", hide_index=True)
    st.markdown("#### 3. Conditional one-step simulation audit")
    st.caption("Each simulation conditions on its observed preceding network and component supports. It is a generative check for this baseline model, not held-out causal validation.")
    rows = result["one_step_simulations"]
    tabs = st.tabs(["Current ties and density", "Formation and dissolution", "Persistence and stability", "Mean degree"])
    with tabs[0]:
        st.plotly_chart(_simulation_figure(rows, "ties", "Current tie count: observed versus separable simulations", "Ties on joint risk set"), width="stretch", key=f"{key}_ties")
        st.plotly_chart(_simulation_figure(rows, "density", "Current density: observed versus separable simulations", "Tie proportion on joint risk set"), width="stretch", key=f"{key}_density")
    with tabs[1]:
        st.plotly_chart(_simulation_figure(rows, "formations", "Formation count: observed versus separable simulations", "Formations"), width="stretch", key=f"{key}_formations")
        st.plotly_chart(_simulation_figure(rows, "dissolutions", "Dissolution count: observed versus separable simulations", "Dissolutions"), width="stretch", key=f"{key}_dissolutions")
    with tabs[2]:
        st.plotly_chart(_simulation_figure(rows, "persistent_ties", "Persistent ties: observed versus separable simulations", "Persistent ties"), width="stretch", key=f"{key}_persistence")
        st.plotly_chart(_simulation_figure(rows, "stability", "Overall stability: observed versus separable simulations", "Stability proportion"), width="stretch", key=f"{key}_stability")
    with tabs[3]:
        st.plotly_chart(_simulation_figure(rows, "mean_degree", "Mean degree: observed versus separable simulations", "Mean degree"), width="stretch", key=f"{key}_mean_degree")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown("#### 4. Tie-duration and censoring audit")
    duration = result["duration_audit"]
    st.metric("Baseline expected duration in panel intervals", f"{result['expected_duration_intervals']:.2f}")
    st.caption("The expected duration equals 1/(1−persistence probability) only for this homogeneous, dyad-independent, memoryless baseline persistence component. It is not a continuous-time duration estimate.")
    metrics = st.columns(4)
    metrics[0].metric("Complete observed spells", duration["complete_spells"])
    metrics[1].metric("Left-censored spells", duration["left_censored_spells"])
    metrics[2].metric("Right-censored spells", duration["right_censored_spells"])
    metrics[3].metric("Support-censored spells", duration["support_censored_spells"])
    st.plotly_chart(_duration_figure(result), width="stretch", key=f"{key}_duration")
    st.markdown("#### 5. Whole-transition bootstrap sensitivity")
    bootstrap_figure = _bootstrap_figure(result)
    if bootstrap_figure is None:
        st.info(result["bootstrap"]["reason"])
    else:
        st.caption(f"Successful resamples: {result['bootstrap']['successful_resamples']}")
        st.plotly_chart(bootstrap_figure, width="stretch", key=f"{key}_bootstrap")


def _fit_workspace(
    network: TemporalNetwork,
    *,
    method_status: str,
    support_note: str,
    interpretation_limit: str,
    label: str,
    key: str,
) -> None:
    """Render one transparent Session 2.2 computation workflow."""
    _profile_panel(network, key)
    st.markdown("##### Stated separable model")
    st.info("Formation component: prior non-ties only · Persistence component: prior ties only")
    st.caption(method_status)
    with st.expander("Reproducible computation settings", expanded=False):
        first, second, third = st.columns(3)
        seed = first.number_input("Random seed", 1, 99999999, 20261029, 1, key=f"{key}_seed")
        bootstrap_replicates = second.select_slider("Whole-transition bootstrap resamples", options=[0, 25, 50, 100, 200], value=100, key=f"{key}_bootstrap")
        simulations = third.select_slider("Conditional simulations per transition", options=[20, 50, 100, 200], value=100, key=f"{key}_simulations")
    st.warning(f"**Support note:** {support_note}")
    st.warning(f"**Interpretation limit:** {interpretation_limit}")
    if st.button("Fit the stated separable formation–persistence model", type="primary", key=f"{key}_fit"):
        try:
            with st.spinner("Fitting separate exact component likelihoods and producing every diagnostic plot..."):
                result = fit_separable_stergm(
                    network,
                    seed=int(seed),
                    bootstrap_replicates=int(bootstrap_replicates),
                    predictive_simulations=int(simulations),
                )
        except TemporalValidationError as error:
            st.error(str(error))
            return
        _render_results(result, key)
        st.download_button(
            "Download Session 2.2 computation record (Markdown)",
            _record(label, method_status, result),
            file_name=f"{key}_session2_2_stergm_record.md",
            mime="text/markdown",
            key=f"{key}_record",
        )


def _worked_examples() -> None:
    """Expose exactly five visible public STERGM workflows."""
    catalog = load_temporal_catalog()
    recipes = {recipe.title: recipe for recipe in WORKED_RECIPES}
    st.subheader("Five worked public networks for separable formation and persistence")
    st.info("Select one of the five visible public panels. A STERGM is appropriate only after the response is binary and repeated, the formation and persistence supports are explicit, and missingness or actor absence is excluded rather than recoded as change.")
    selected = st.radio("Select a Session 2.2 worked example", list(recipes), index=0, key="session22_worked_example")
    recipe = recipes[selected]
    spec = catalog[recipe.identifier]
    network = load_temporal_example(spec)
    st.subheader(recipe.title)
    st.caption(spec.network_type)
    left, right = st.columns(2)
    with left:
        st.markdown("**Method appropriateness**")
        st.write(recipe.method_status)
        st.markdown("**What the computation audits**")
        st.markdown("\n".join(f"- {item}" for item in recipe.diagnostic_focus))
    with right:
        st.markdown("**Response boundary**")
        st.write(spec.response_scope)
        st.link_button("Open public source documentation", spec.source_url)
    _fit_workspace(
        network,
        method_status=recipe.method_status,
        support_note=recipe.support_note,
        interpretation_limit=recipe.interpretation_limit,
        label=spec.name,
        key=f"session22_worked_{recipe.identifier}",
    )
    with st.expander("Inspect the documented temporal data tables", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown("**Node presence table**")
            st.dataframe(network.nodes, width="stretch", hide_index=True)
        with right:
            st.markdown("**Temporal edge table**")
            st.dataframe(network.edges, width="stretch", hide_index=True)
        if network.risk is not None:
            st.markdown("**Observed/at-risk dyad table**")
            st.dataframe(network.risk, width="stretch", hide_index=True)


def _byod() -> None:
    """Provide a support-aware participant upload calculation with no hidden recoding."""
    st.subheader("Bring Your Own Data (BYOD): repeated binary networks")
    st.write("Upload the same three support-aware tables used in Session 2.1. Session 2.2 splits every eligible transition into a formation support and a persistence support before fitting the two components.")
    with st.expander("Upload contract and computation boundary", expanded=True):
        st.markdown(
            "- **Nodes CSV:** `wave`, `id`, and optionally `transition_block`. Use different block labels on opposite sides of an observation gap.\n"
            "- **Edges CSV:** `wave`, `source`, `target` for observed binary ties.\n"
            "- **At-risk-dyads CSV (optional):** `wave`, `source`, `target` for all observed dyads whenever presence alone does not define observability.\n"
            "- **Not silently supported:** valued/count ties, rankings, unknown wave spacing, multiplex layers, or coding absence as a non-tie.\n"
            "- **Session boundary:** this page fits separate intercept-only, dyad-factorizing formation and persistence components; it does not fit a general STERGM with endogenous structural terms or continuous-time hazards."
        )
    first, second, third = st.columns(3)
    nodes_upload = first.file_uploader("Node-presence table (CSV)", type=["csv"], key="session22_byod_nodes")
    edges_upload = second.file_uploader("Temporal edge table (CSV)", type=["csv"], key="session22_byod_edges")
    risk_upload = third.file_uploader("At-risk dyads table (CSV, optional)", type=["csv"], key="session22_byod_risk")
    directed = st.checkbox("Directed temporal network", value=True, key="session22_byod_directed")
    if nodes_upload is None or edges_upload is None:
        st.caption("Upload both required CSV files to open the Session 2.2 separable calculation.")
        return
    try:
        nodes = _read_csv(nodes_upload)
        edges = _read_csv(edges_upload)
        risk = _read_csv(risk_upload) if risk_upload is not None else None
        validate_temporal_network(nodes, edges, directed=directed, risk=risk)
        network = TemporalNetwork(nodes=nodes, edges=edges, risk=risk, directed=directed, label="Participant-uploaded repeated network")
    except (UnicodeDecodeError, pd.errors.ParserError, TemporalValidationError) as error:
        st.error(f"The upload cannot enter a Session 2.2 separable analysis: {error}")
        return
    st.success("Upload support checks passed. Inspect the component supports before fitting.")
    _fit_workspace(
        network,
        method_status=byod_method_note(directed=directed),
        support_note="The participant supplies the network boundary, wave spacing, actor-presence rule, and any at-risk-dyad table. Omitting a risk table asserts that every dyad among actors present at a wave was observed.",
        interpretation_limit="A completed baseline STERGM calculation does not identify microstep timing, causal effects, endogenous formation/persistence dependence, or a continuous-time duration process.",
        label="Participant-uploaded repeated network",
        key="session22_byod",
    )


def render_session2_2() -> None:
    """Render the full computation-first Session 2.2 interface."""
    st.title("Session 2.2 — Separable TERGMs for Formation and Dissolution")
    st.caption("Day 2 · October 29, 2026 · 4:30–6:00 PM GMT")
    st.info("This page treats creation of a previously absent tie and survival of a previously present tie as different process supports. It never turns missingness, actor absence, an observation gap, or a rank-order outcome into a formation or dissolution event.")
    overview, worked, byod, methods = st.tabs(["Computation map", "Five worked public networks", "BYOD", "Methods and data"])
    with overview:
        st.markdown("### Baseline separable temporal ERGM computation")
        st.latex(r"Y^+=Y^{t-1}\cup Y^t,\qquad Y^-=Y^{t-1}\cap Y^t")
        st.markdown(
            "1. Declare the repeated binary response, observation interval, actor boundary, and transition-specific observed risk set.\n"
            "2. Separate prior non-ties at risk of formation from prior ties at risk of persistence.\n"
            "3. Fit separate component likelihoods and never label a persistence coefficient as a dissolution coefficient without reversing its implication.\n"
            "4. Audit component supports, observed process rates, coefficient stability, and numerical warnings.\n"
            "5. Simulate each next observed network conditionally and compare ties, density, formation, dissolution, persistence, stability, and mean degree.\n"
            "6. Inspect censored tie-spell summaries; use the geometric expected duration only under the stated homogeneous, dyad-independent, memoryless baseline."
        )
        st.warning("The implemented model is intentionally narrow: each component is intercept-only and factorizes over its own support, so its conditional likelihood is exact. A general STERGM may include endogenous formation or persistence statistics and can require MCMC estimation; this page does not silently approximate one.")
    with worked:
        _worked_examples()
    with byod:
        _byod()
    with methods:
        catalog = load_temporal_catalog()
        st.markdown("### Public-data provenance and Session 2.2 suitability")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Worked example": recipes_by_identifier()[identifier].title,
                        "Network type": spec.network_type,
                        "Public source": spec.source,
                        "Citation": spec.citation,
                    }
                    for identifier, spec in catalog.items()
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.markdown("### Excluded public candidate")
        rejected = rejected_temporal_candidate()
        st.write(rejected["name"] + ": " + rejected["reason"])
