"""Streamlit page for Session 2.1: discrete-time temporal ERGMs for network change."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from session2_1_options import (
    WORKED_RECIPES,
    byod_method_note,
    byod_terms,
    recipes_by_identifier,
)
from temporal_core import (
    TemporalNetwork,
    TemporalValidationError,
    fit_lagged_tergm,
    load_temporal_catalog,
    load_temporal_example,
    rejected_temporal_candidate,
    temporal_profile,
    validate_temporal_network,
)

TERM_LABELS = {
    "edges": "Edges baseline at the current wave",
    "memory": "Lagged same-dyad tie persistence",
    "delrecip": "Lagged delayed reciprocity",
    "lagged_twopath": "Lagged directed/undirected two-path exposure",
}


def _read_csv(upload: Any) -> pd.DataFrame:
    """Read a UTF-8 comma-separated upload without inferring data transformations."""
    return pd.read_csv(StringIO(upload.getvalue().decode("utf-8")))


def _term_caption(terms: tuple[str, ...]) -> str:
    return " · ".join(TERM_LABELS[term] for term in terms)


def _profile_panel(network: TemporalNetwork) -> dict[str, Any]:
    """Show observed waves and transition counts before any model calculation."""
    profile = temporal_profile(network)
    columns = st.columns(4)
    columns[0].metric("Observed waves", profile["observed_waves"])
    columns[1].metric("Transitions with joint at-risk dyads", profile["observed_transitions"])
    columns[2].metric("Directionality", "Directed" if network.directed else "Undirected")
    columns[3].metric("Observed edge rows", len(network.edges))
    st.markdown("##### Wave profile")
    st.dataframe(profile["wave_table"], width="stretch", hide_index=True)
    st.markdown("##### Four transition counts on the joint at-risk dyads")
    st.caption(
        "For an admissible dyad, N00 is a persistent non-tie, N01 a formation, N10 a dissolution, and N11 a persistent tie. Overall stability includes N00 and N11; tie persistence is N11 alone."
    )
    st.dataframe(profile["transition_table"], width="stretch", hide_index=True)
    if profile["observed_intervals"] > profile["observed_transitions"]:
        st.caption(
            f"{profile['observed_intervals']} adjacent observed-wave intervals were documented, but {profile['observed_intervals'] - profile['observed_transitions']} had no jointly at-risk dyad and therefore contribute no conditional likelihood information."
        )
    return profile


def _transition_figure(
    predictive: list[dict[str, Any]],
    *,
    observed_key: str,
    mean_key: str,
    lower_key: str,
    upper_key: str,
    title: str,
    yaxis_title: str,
) -> go.Figure:
    """Draw observed transition statistics against conditional simulation envelopes."""
    data = pd.DataFrame(predictive)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[*data["transition"], *reversed(data["transition"].tolist())],
            y=[*data[upper_key], *reversed(data[lower_key].tolist())],
            fill="toself",
            fillcolor="rgba(78,42,132,0.16)",
            line={"color": "rgba(78,42,132,0)"},
            name="95% conditional simulation envelope",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["transition"],
            y=data[mean_key],
            mode="lines+markers",
            line={"color": "#4E2A84", "width": 2},
            name="Fitted-model simulation mean",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["transition"],
            y=data[observed_key],
            mode="lines+markers",
            line={"color": "#C95500", "width": 2},
            name="Observed",
        )
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=350,
        margin={"l": 30, "r": 20, "t": 55, "b": 80},
        xaxis_title="Observed transition",
        yaxis_title=yaxis_title,
        legend={"orientation": "h", "y": -0.3},
    )
    return figure


def _predictive_panel(result: dict[str, Any], *, key: str) -> None:
    """Render one-step simulations conditioned on every observed previous network."""
    st.markdown("#### 3. Conditional one-step simulation checks")
    st.caption(
        "For each observed transition, the fitted model simulates the next network conditional on that transition's observed previous network and joint risk set. These are transition-model checks, not held-out causal or event-history validation."
    )
    predictive = result["posterior_predictive"]
    st.plotly_chart(
        _transition_figure(
            predictive,
            observed_key="observed_ties",
            mean_key="simulated_ties_mean",
            lower_key="simulated_ties_lower_025",
            upper_key="simulated_ties_upper_975",
            title="Current-wave tie count: observed versus conditional simulations",
            yaxis_title="Tie count",
        ),
        width="stretch",
        key=f"{key}_ties",
    )
    st.plotly_chart(
        _transition_figure(
            predictive,
            observed_key="observed_formations",
            mean_key="simulated_formations_mean",
            lower_key="simulated_formations_lower_025",
            upper_key="simulated_formations_upper_975",
            title="Formation count: observed versus conditional simulations",
            yaxis_title="Formation count",
        ),
        width="stretch",
        key=f"{key}_formations",
    )
    persistence = pd.DataFrame(predictive).dropna(subset=["observed_tie_persistence"])
    if not persistence.empty:
        st.plotly_chart(
            _transition_figure(
                persistence.to_dict(orient="records"),
                observed_key="observed_tie_persistence",
                mean_key="simulated_tie_persistence_mean",
                lower_key="simulated_tie_persistence_lower_025",
                upper_key="simulated_tie_persistence_upper_975",
                title="Tie persistence: observed versus conditional simulations",
                yaxis_title="Proportion of previous ties retained",
            ),
            width="stretch",
            key=f"{key}_persistence",
        )
    st.dataframe(pd.DataFrame(predictive), width="stretch", hide_index=True)


def _bootstrap_panel(result: dict[str, Any]) -> None:
    """Show transition-block bootstrap output or a principled non-run decision."""
    bootstrap = result["bootstrap"]
    st.markdown("#### 4. Transition-block uncertainty check")
    st.info(bootstrap["reason"])
    if bootstrap["status"] == "ok":
        st.caption(
            f"Completed {bootstrap['replicates_completed']} of {bootstrap['replicates_requested']} whole-transition resamples. Individual dyads were not treated as independent replications."
        )
        st.dataframe(pd.DataFrame(bootstrap["intervals"]), width="stretch", hide_index=True)
    elif bootstrap["status"] == "unstable":
        st.warning(
            f"Only {bootstrap['replicates_completed']} of {bootstrap['replicates_requested']} resamples produced a stable fit. The result is a numerical warning, not an interval estimate."
        )


def _record(
    *,
    label: str,
    recipe_note: str,
    profile: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """Create a source-transparent Session 2.1 computation record."""
    coefficients = pd.DataFrame(result["coefficients"]).to_markdown(index=False)
    transitions = profile["transition_table"].to_markdown(index=False)
    warnings = "\n".join(f"- {item}" for item in result["diagnostic_flags"]) or "- No automatic numerical flags were returned."
    return f"""# Session 2.1 temporal ERGM computation record

## Data and model boundary
- **Dataset:** {label}
- **Model class:** {result['model_class']}
- **Observed waves:** {result['observed_waves']}
- **Valid one-step transitions:** {result['observed_transitions']}
- **Joint-risk dyad observations:** {result['dyad_observations']}
- **Stated formula:** `{result['formula']}`
- **Method appropriateness:** {recipe_note}

## Coefficients
{coefficients}

## Observed transition counts
{transitions}

## Optimizer and flags
- **Optimizer converged:** {result['optimizer']['converged']}
- **Optimizer message:** {result['optimizer']['message']}
- **Observed-information condition number:** {result['optimizer']['information_condition_number']}
{warnings}

## Bootstrap
- **Status:** {result['bootstrap']['status']}
- **Reason:** {result['bootstrap']['reason']}
- **Replicates completed:** {result['bootstrap']['replicates_completed']}

## Interpretation boundary
{result['interpretation_note']}
"""


def _fit_workspace(
    network: TemporalNetwork,
    *,
    terms: tuple[str, ...],
    method_status: str,
    support_note: str,
    interpretation_limit: str,
    label: str,
    key: str,
) -> None:
    """Render controls and actual outputs for a lag-only temporal ERGM calculation."""
    profile = _profile_panel(network)
    st.markdown("##### Stated transition model")
    st.info(_term_caption(terms))
    st.caption(method_status)
    with st.expander("Reproducible computation settings", expanded=False):
        first, second, third = st.columns(3)
        seed = first.number_input("Random seed", 1, 99999999, 20261029, 1, key=f"{key}_seed")
        bootstrap_replicates = second.select_slider(
            "Transition-block bootstrap resamples", options=[0, 25, 50, 100, 200], value=100, key=f"{key}_bootstrap"
        )
        predictive_simulations = third.select_slider(
            "Conditional simulations per transition", options=[20, 50, 100, 200], value=100, key=f"{key}_predictive"
        )
    st.warning(f"**Support note:** {support_note}")
    st.warning(f"**Interpretation limit:** {interpretation_limit}")
    if st.button("Fit the stated first-order temporal ERGM", type="primary", key=f"{key}_run"):
        try:
            with st.spinner("Fitting the exact lag-only transition likelihood and conditional simulation checks..."):
                result = fit_lagged_tergm(
                    network,
                    terms=terms,
                    seed=int(seed),
                    bootstrap_replicates=int(bootstrap_replicates),
                    predictive_simulations=int(predictive_simulations),
                )
        except TemporalValidationError as error:
            st.error(str(error))
            return
        st.success("The Session 2.1 transition calculation finished. Inspect its support, warnings, and conditional simulations before interpreting coefficients.")
        st.code(result["formula"], language="text")
        st.dataframe(pd.DataFrame(result["coefficients"]), width="stretch", hide_index=True)
        if result["diagnostic_flags"]:
            st.warning("Diagnostic flags:\n\n" + "\n".join(f"- {item}" for item in result["diagnostic_flags"]))
        st.markdown("#### 1. Conditional-likelihood and identification checks")
        st.json(result["optimizer"], expanded=False)
        st.caption(
            "The included terms depend only on the preceding observed network. Therefore this restricted lag-only TERGM has an exact conditional dyadic likelihood. Adding contemporaneous structural dependence would require a different likelihood/simulation computation and is not silently approximated here."
        )
        st.markdown("#### 2. Transition-count audit")
        st.dataframe(pd.DataFrame(result["transition_counts"]), width="stretch", hide_index=True)
        _predictive_panel(result, key=key)
        _bootstrap_panel(result)
        st.download_button(
            "Download Session 2.1 computation record (Markdown)",
            _record(label=label, recipe_note=method_status, profile=profile, result=result),
            file_name=f"{key}_session2_1_tergm_record.md",
            mime="text/markdown",
            key=f"{key}_record",
        )


def _worked_examples() -> None:
    """Present exactly five clearly visible public temporal-network workflows."""
    catalog = load_temporal_catalog()
    recipe_by_title = {recipe.title: recipe for recipe in WORKED_RECIPES}
    st.subheader("Five worked public temporal networks")
    st.info(
        "Select one of the five visible choices. Each workflow is a valid binary discrete-time transition analysis only after its stated temporal support and risk-set rules are applied. The documented Newcomb rank data are intentionally not forced into this unrestricted binary TERGM page."
    )
    selected_title = st.radio(
        "Select a Session 2.1 worked example",
        list(recipe_by_title),
        index=0,
        key="session21_worked_example",
    )
    recipe = recipe_by_title[selected_title]
    spec = catalog[recipe.identifier]
    network = load_temporal_example(spec)
    st.subheader(recipe.title)
    st.caption(spec.network_type)
    first, second = st.columns(2)
    with first:
        st.markdown("**Method appropriateness**")
        st.write(recipe.method_status)
        st.markdown("**What the computation audits**")
        st.markdown("\n".join(f"- {item}" for item in recipe.diagnostic_focus))
    with second:
        st.markdown("**Response boundary**")
        st.write(spec.response_scope)
        st.link_button("Open public source documentation", spec.source_url)
    _fit_workspace(
        network,
        terms=recipe.terms,
        method_status=recipe.method_status,
        support_note=recipe.support_note,
        interpretation_limit=recipe.interpretation_limit,
        label=spec.name,
        key=f"session21_worked_{recipe.identifier}",
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
    """Offer a transparent repeated-network upload path with no silent recoding."""
    st.subheader("Bring Your Own Data (BYOD): repeated binary networks")
    st.write(
        "Upload a node-presence table and temporal edge list. A third, optional at-risk-dyad table is required whenever a present actor does not imply that every within-wave dyad was observed—for example, incidental missing nominations."
    )
    with st.expander("Upload contract and modeling boundary", expanded=True):
        st.markdown(
            "- **Nodes CSV:** `wave`, `id`, and optionally `transition_block`. A shared block label declares that adjacent listed waves form a valid one-step interval; use different labels on opposite sides of a missing panel.\n"
            "- **Edges CSV:** `wave`, `source`, `target` for observed binary ties.\n"
            "- **At-risk dyads CSV (optional but important):** `wave`, `source`, `target` for every observed dyad. Do not put unobserved, structurally unavailable, or absent-actor dyads into this file.\n"
            "- **Not silently supported:** valued/count ties, rank-order outcomes, multiplex layers, unknown wave spacing, or a model that treats actor absence as a non-tie.\n"
            "- **Session boundary:** this page fits only a first-order lag-only TERGM; it does not provide STERGM formation/dissolution components or contemporaneous structural TERGM terms."
        )
    first, second, third = st.columns(3)
    nodes_upload = first.file_uploader("Node-presence table (CSV)", type=["csv"], key="session21_byod_nodes")
    edges_upload = second.file_uploader("Temporal edge table (CSV)", type=["csv"], key="session21_byod_edges")
    risk_upload = third.file_uploader("At-risk dyads table (CSV, optional)", type=["csv"], key="session21_byod_risk")
    directed = st.checkbox("Directed temporal network", value=True, key="session21_byod_directed")
    delayed_reciprocity = False
    if directed:
        delayed_reciprocity = st.checkbox(
            "Include lagged delayed reciprocity", value=True, key="session21_byod_delrecip"
        )
    lagged_twopath = st.checkbox(
        "Include prior-wave two-path exposure", value=False, key="session21_byod_twopath"
    )
    if nodes_upload is None or edges_upload is None:
        st.caption("Upload both required CSV files to open the Session 2.1 BYOD calculation.")
        return
    try:
        nodes = _read_csv(nodes_upload)
        edges = _read_csv(edges_upload)
        risk = _read_csv(risk_upload) if risk_upload is not None else None
        validate_temporal_network(nodes, edges, directed=directed, risk=risk)
        network = TemporalNetwork(nodes=nodes, edges=edges, risk=risk, directed=directed, label="Participant-uploaded repeated network")
    except (UnicodeDecodeError, pd.errors.ParserError, TemporalValidationError) as error:
        st.error(f"The upload cannot enter a Session 2.1 transition analysis: {error}")
        return
    terms = byod_terms(
        directed=directed,
        include_delayed_reciprocity=delayed_reciprocity,
        include_lagged_twopath=lagged_twopath,
    )
    method_status = byod_method_note(
        directed=directed,
        include_delayed_reciprocity=delayed_reciprocity,
        include_lagged_twopath=lagged_twopath,
    )
    st.success("Upload support checks passed. Read the wave and transition tables before fitting the stated model.")
    _fit_workspace(
        network,
        terms=terms,
        method_status=method_status,
        support_note="The participant supplies the network boundary, wave spacing, actor-presence rule, and any at-risk-dyad table. An omitted risk table asserts that every dyad among actors present at a wave was observed.",
        interpretation_limit="A completed lag-only temporal calculation does not identify microstep timing, causal effects, a general dynamic process, or separate formation and dissolution mechanisms.",
        label="Participant-uploaded repeated network",
        key="session21_byod",
    )


def render_session2_1() -> None:
    """Render the full computation-first interface for Session 2.1."""
    st.title("Session 2.1 — Temporal ERGMs for Network Change")
    st.caption("Day 2 · October 28, 2026 · 4:30–6:00 PM GMT")
    st.info(
        "This page models a discrete-time network transition conditional on the preceding observed network and an explicit dyadic risk set. It never turns missingness, actor absence, an observation gap, or a rank-order outcome into an ordinary zero tie."
    )
    overview, worked, byod, methods = st.tabs(
        ["Computation map", "Five worked public networks", "BYOD", "Methods and data"]
    )
    with overview:
        st.markdown("### First-order temporal ERGM computation")
        st.latex(r"\Pr_{\theta}(Y^t=y^t\mid Y^{t-1}=y^{t-1},D_t) \propto \exp\{\theta^{\mathsf T}g(y^t,y^{t-1})\}")
        st.markdown(
            "1. Define the repeated response network, wave spacing, actor boundary, structural zeros, and each transition-specific at-risk dyad set.\n"
            "2. Distinguish N00 persistent non-ties, N01 formations, N10 dissolutions, and N11 persistent ties without assuming that these are separate STERGM processes.\n"
            "3. State a first-order history term: lagged same-dyad persistence, delayed reciprocity for directed networks, or prior-wave two-path exposure.\n"
            "4. Fit the stated lag-only transition model and inspect numerical identification warnings.\n"
            "5. Simulate one-step outcomes conditional on each observed previous network and compare tie totals, formations, and persistence.\n"
            "6. Use a whole-transition bootstrap only where enough observed transitions exist; never treat dyads as independent temporal replications."
        )
        st.warning(
            "The implemented calculation is deliberately narrow: every fitted statistic is a function of the prior observed network, so the displayed conditional likelihood is exact for this restricted first-order TERGM subclass. The page does not silently replace a general TERGM with pseudo-likelihood or a STERGM with a combined transition model."
        )
    with worked:
        _worked_examples()
    with byod:
        _byod()
    with methods:
        catalog = load_temporal_catalog()
        st.markdown("### Public-data provenance and Session 2.1 suitability")
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
        st.markdown("### Interpretation rule")
        st.write(
            "A lagged coefficient is a conditional association within the declared discrete observation schedule and risk set. It is neither a continuous-time hazard, proof of a behavioral mechanism, a causal effect, nor a separate formation/dissolution estimate."
        )
