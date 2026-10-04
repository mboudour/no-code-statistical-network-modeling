"""Streamlit page for Session 1.2: curved ERGMs, fit, and degeneracy."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from network_core import (
    NetworkValidationError,
    load_catalog,
    load_example,
    network_profile,
    to_ergm_payload,
    validate_binary_network,
)
from r_engine import ErgMRuntimeError, engine_status, fit_session12_ergm
from session1_2_options import (
    WORKED_RECIPES,
    Session12Recipe,
    byod_method_note,
    byod_terms,
    recipes_by_identifier,
)

CURVED_TERMS = {"gwdegree", "gwesp", "gwidegree", "gwodegree"}

AUXILIARY_STATISTIC_LABELS = {
    "edges": "Edge count",
    "isolate_count": "Isolate count",
    "largest_component": "Largest component size",
    "component_count": "Component count",
    "mutual_dyads": "Mutual-dyad count",
    "triangle_count": "Triangle count",
    "mean_first_mode_shared_neighbor_overlap": "Mean first-mode shared-neighbor overlap",
    "mean_second_mode_shared_neighbor_overlap": "Mean second-mode shared-neighbor overlap",
}


def _auxiliary_statistic_label(statistic: Any) -> str:
    """Convert stable engine keys into methodologically explicit labels."""
    value = str(statistic)
    return AUXILIARY_STATISTIC_LABELS.get(value, value.replace("_", " ").title())


def _read_upload(uploaded: Any) -> pd.DataFrame:
    """Read a UTF-8 CSV upload without guessing data transformations."""
    return pd.read_csv(StringIO(uploaded.getvalue().decode("utf-8")))


def _profile_panel(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
) -> dict[str, Any]:
    """Display transparent descriptive support facts before any ERGM fit."""
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
    st.dataframe(profile["degree_table"].head(20), width="stretch", hide_index=True)
    st.caption(
        "These are descriptive support checks. They motivate a stated model but do not select terms automatically."
    )
    return profile


def _engine_ready() -> bool:
    status = engine_status()
    if status["available"]:
        st.success("The pre-provisioned R/statnet ERGM engine is available.")
        return True
    st.error(
        "The R/statnet ERGM engine is unavailable. This deployment must provide it before a Session 1.2 fit can run."
    )
    st.code(status["reason"])
    return False


def _controls(
    recipe: Session12Recipe | None,
    *,
    directed: bool,
    bipartite: bool,
    key: str,
) -> tuple[bool, float, dict[str, int]]:
    """Expose reproducible settings without masking their statistical role."""
    curved_count = 0 if recipe is None else len(recipe.curved_terms)
    allow_free = recipe is not None and recipe.allow_free_decay and curved_count == 1
    use_free_decay = False
    if allow_free:
        use_free_decay = st.checkbox(
            "Estimate the single curved-term decay as a sensitivity fit",
            value=False,
            key=f"{key}_free_decay",
            help=(
                "Unchecked means a pre-specified fixed decay of 0.5. Checked means the decay is estimated as a curved ERGM parameter. "
                "The output must then be reviewed for projected-score convergence, MCMC mixing, and repeated-fit stability."
            ),
        )
    elif curved_count > 1:
        st.caption(
            "This worked specification fixes its multiple decay values at 0.5. Estimating several decay parameters together is not automated because it can create an unstable or weakly identified refinement.")
    elif bipartite:
        st.caption(
            "This bipartite workflow deliberately does not force a curved degree refinement. The full diagnostic audit remains available for the support-valid baseline.")

    with st.expander("Reproducible estimation and diagnostic settings", expanded=False):
        first, second, third, fourth, fifth = st.columns(5)
        seed = first.number_input("Random seed", 1, 99999999, 20261028, 1, key=f"{key}_seed")
        burnin = second.select_slider(
            "MCMC burn-in", options=[2000, 5000, 10000, 20000], value=5000, key=f"{key}_burnin"
        )
        interval = third.select_slider(
            "MCMC interval", options=[250, 500, 1000, 2000], value=500, key=f"{key}_interval"
        )
        maxit = fourth.select_slider(
            "MCMLE maximum iterations", options=[4, 8, 12, 16], value=8, key=f"{key}_maxit"
        )
        gof_nsim = fifth.select_slider(
            "Simulated networks for GOF", options=[10, 25, 50, 100], value=25, key=f"{key}_gof_nsim"
        )
    st.caption(
        "The app always runs the full support-appropriate diagnostic family. The simulation count controls Monte Carlo resolution, not which diagnostic categories are shown; use 50 or 100 for a final documented audit when runtime permits."
    )
    return (
        bool(use_free_decay),
        0.5,
        {
            "seed": int(seed),
            "mcmc_burnin": int(burnin),
            "mcmc_interval": int(interval),
            "mcmle_maxit": int(maxit),
            "mcmc_return_stats": 128,
            "gof_nsim": int(gof_nsim),
        },
    )


def _payload(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    terms: tuple[str, ...],
    free_decay: bool,
    decay: float,
    controls: dict[str, int],
) -> dict[str, Any]:
    """Build the common validated payload and extend it with Session 1.2 controls."""
    payload = to_ergm_payload(
        nodes,
        edges,
        directed=directed,
        bipartite=bipartite,
        terms=list(terms),
        nodematch_attribute=None,
        nodecov_attribute=None,
        seed=controls["seed"],
        mcmc_burnin=controls["mcmc_burnin"],
        mcmc_interval=controls["mcmc_interval"],
        mcmle_maxit=controls["mcmle_maxit"],
    )
    payload["formula"]["curve_controls"] = {
        "fixed_decay": not free_decay,
        "decay": float(decay),
    }
    payload["controls"].update(
        {
            "mcmc_return_stats": controls["mcmc_return_stats"],
            "gof_nsim": controls["gof_nsim"],
        }
    )
    return payload


def _envelope_figure(table: dict[str, Any]) -> go.Figure:
    """Create an observed-versus-simulated distribution envelope plot."""
    labels = table["labels"]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[*labels, *reversed(labels)],
            y=[*table["upper_975"], *reversed(table["lower_025"])],
            fill="toself",
            fillcolor="rgba(78,42,132,0.16)",
            line={"color": "rgba(78,42,132,0)"},
            name="95% simulated envelope",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=labels,
            y=table["simulated_mean"],
            mode="lines+markers",
            line={"color": "#4E2A84", "width": 2},
            name="Simulated mean",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=labels,
            y=table["observed"],
            mode="lines+markers",
            line={"color": "#C95500", "width": 2},
            name="Observed",
        )
    )
    figure.update_layout(
        title=table["title"],
        template="plotly_white",
        height=360,
        margin={"l": 20, "r": 20, "t": 50, "b": 45},
        xaxis_title="Statistic category",
        yaxis_title="Frequency / statistic value",
        legend={"orientation": "h", "y": -0.25},
    )
    return figure


def _mcmc_panels(result: dict[str, Any], *, key: str) -> None:
    """Render trace, autocorrelation, and sampled-statistic distributions."""
    diagnostics = result["mcmc_diagnostics"]
    st.markdown("#### 1. MCMC diagnostics")
    st.caption(
        "The traces below are the sampled sufficient statistics retained from the final MCMLE diagnostic sample. Examine them for apparent stationarity, long excursions, and high autocorrelation; no panel provides an automatic convergence verdict."
    )
    if diagnostics["sample_size"] == 0:
        st.warning("No retained MCMC statistic sample was available for plotting.")
        return
    for index, statistic in enumerate(diagnostics["statistics"]):
        trace, autocorrelation, distribution = st.tabs(
            [
                f"{statistic['statistic']} — trace",
                f"{statistic['statistic']} — autocorrelation",
                f"{statistic['statistic']} — distribution",
            ]
        )
        with trace:
            figure = go.Figure(
                go.Scatter(
                    x=list(range(1, len(statistic["trace"]) + 1)),
                    y=statistic["trace"],
                    mode="lines",
                    line={"color": "#4E2A84"},
                    name="Sampled statistic",
                )
            )
            figure.update_layout(
                template="plotly_white",
                height=280,
                margin={"l": 20, "r": 20, "t": 25, "b": 40},
                xaxis_title="Retained MCMC sample index",
                yaxis_title=statistic["statistic"],
            )
            st.plotly_chart(figure, width="stretch", key=f"{key}_trace_{index}")
        with autocorrelation:
            if statistic["lags"]:
                figure = go.Figure(
                    go.Bar(
                        x=statistic["lags"],
                        y=statistic["autocorrelation"],
                        marker_color="#4E2A84",
                    )
                )
                figure.update_layout(
                    template="plotly_white",
                    height=280,
                    margin={"l": 20, "r": 20, "t": 25, "b": 40},
                    xaxis_title="Lag",
                    yaxis_title="Autocorrelation",
                )
                st.plotly_chart(figure, width="stretch", key=f"{key}_acf_{index}")
            else:
                st.info("Autocorrelation is unavailable because the retained sample is too short or constant.")
        with distribution:
            figure = go.Figure(
                go.Histogram(x=statistic["trace"], marker_color="#4E2A84", nbinsx=20)
            )
            figure.update_layout(
                template="plotly_white",
                height=280,
                margin={"l": 20, "r": 20, "t": 25, "b": 40},
                xaxis_title=statistic["statistic"],
                yaxis_title="Retained MCMC samples",
            )
            st.plotly_chart(figure, width="stretch", key=f"{key}_hist_{index}")


def _gof_panels(result: dict[str, Any], *, key: str) -> None:
    """Render the full support-appropriate standard GOF set."""
    gof = result["gof"]
    st.markdown("#### 2. Simulation-based goodness of fit")
    if gof["status"] != "ok":
        st.error(f"The standard GOF calculation was unavailable: {gof['message']}")
        return
    st.caption(
        f"{gof['nsim']} networks were simulated from the fitted ERGM. The observed line is compared with the simulated distribution; agreement on fitted terms alone is not enough for an adequacy claim."
    )
    for index, table in enumerate(gof["tables"]):
        st.plotly_chart(_envelope_figure(table), width="stretch", key=f"{key}_gof_{index}")
    if gof.get("warnings"):
        st.warning("GOF warnings returned by R:\n\n" + "\n".join(f"- {item}" for item in gof["warnings"]))


def _auxiliary_panel(result: dict[str, Any]) -> None:
    """Display omitted-feature simulation checks outside the fitted term list."""
    auxiliary = result["auxiliary_simulation_checks"]
    st.markdown("#### 3. Network- and model-specific simulated checks")
    if auxiliary["status"] != "ok":
        st.error(f"The auxiliary simulation checks were unavailable: {auxiliary['message']}")
        return
    data = pd.DataFrame(auxiliary["summaries"])
    data["statistic"] = data["statistic"].map(_auxiliary_statistic_label)
    data = data.rename(
        columns={
            "statistic": "Omitted/substantive statistic",
            "simulated_mean": "Simulated mean",
            "lower_025": "2.5%",
            "upper_975": "97.5%",
        }
    )
    st.dataframe(data, width="stretch", hide_index=True)
    st.caption(
        "These checks include network features that may not be directly fitted. A discrepancy is evidence for review, not a command to add terms automatically.")
    if auxiliary.get("warnings"):
        st.warning("Auxiliary simulation warnings returned by R:\n\n" + "\n".join(f"- {item}" for item in auxiliary["warnings"]))


def _record(
    label: str,
    profile: dict[str, Any],
    result: dict[str, Any],
    *,
    terms: tuple[str, ...],
    method_status: str,
    support_note: str,
    interpretation_limit: str,
) -> str:
    """Create a transparent Markdown record for download."""
    coefficient_table = pd.DataFrame(result["coefficients"]).to_markdown(index=False)
    warnings = "\n".join(f"- {item}" for item in result["diagnostic_flags"]) or "- No diagnostic flags were returned by R."
    gof_titles = ", ".join(item["title"] for item in result["gof"].get("tables", []))
    auxiliary_titles = ", ".join(
        _auxiliary_statistic_label(item["statistic"])
        for item in result["auxiliary_simulation_checks"].get("summaries", [])
    )
    return f"""# Session 1.2 ERGM computation and diagnostic record

## Dataset and support
- **Dataset:** {label}
- **Vertices:** {profile['nodes']}
- **Observed ties:** {profile['observed_edges']}
- **Admissible dyads:** {profile['admissible_dyads']}
- **Density:** {profile['density']:.6f}
- **Directed:** {profile['directed']}
- **Bipartite:** {profile['bipartite']}

## Stated model
- **Formula fitted:** `{result['formula']}`
- **Requested model components:** {', '.join(terms)}
- **Method status:** {method_status}
- **MCMC and simulation controls:** `{result['mcmc_settings']}`

## Coefficients
{coefficient_table}

## Standard diagnostic family completed
- **MCMC retained sample size:** {result['mcmc_diagnostics']['sample_size']}
- **GOF panels:** {gof_titles or 'Unavailable'}
- **Auxiliary simulated checks:** {auxiliary_titles or 'Unavailable'}

## Diagnostic flags and warnings
{warnings}

## Support note
{support_note}

## Interpretation boundary
{interpretation_limit}

{result['interpretation_note']}
"""


def _run_fit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    terms: tuple[str, ...],
    method_status: str,
    support_note: str,
    interpretation_limit: str,
    label: str,
    recipe: Session12Recipe | None,
    key: str,
) -> None:
    """Render controls, execute the audited fit, and display its actual outputs."""
    ready = _engine_ready()
    profile = _profile_panel(nodes, edges, directed=directed, bipartite=bipartite)
    free_decay, decay, controls = _controls(
        recipe, directed=directed, bipartite=bipartite, key=key
    )
    if free_decay and sum(term in CURVED_TERMS for term in terms) != 1:
        st.error("A free-decay sensitivity fit is available only for a one-curved-term specification.")
        return
    if not ready:
        return
    if st.button("Fit and run the full standard ERGM audit", type="primary", key=f"{key}_run"):
        try:
            payload = _payload(
                nodes,
                edges,
                directed=directed,
                bipartite=bipartite,
                terms=terms,
                free_decay=free_decay,
                decay=decay,
                controls=controls,
            )
            with st.spinner(
                "Fitting the stated ERGM and running MCMC, GOF, and support-specific simulation checks..."
            ):
                result = fit_session12_ergm(payload)
        except (NetworkValidationError, ErgMRuntimeError) as error:
            st.error(str(error))
            return
        st.success("The Session 1.2 computation finished. Review every diagnostic panel before drawing an interpretation.")
        st.code(result["formula"], language="r")
        st.dataframe(pd.DataFrame(result["coefficients"]), width="stretch", hide_index=True)
        st.info(result["estimation"]["diagnostic_rule"])
        if result["diagnostic_flags"]:
            st.warning("Diagnostic flags returned by R:\n\n" + "\n".join(f"- {item}" for item in result["diagnostic_flags"]))
        _mcmc_panels(result, key=key)
        _gof_panels(result, key=key)
        _auxiliary_panel(result)
        st.download_button(
            "Download Session 1.2 computation record (Markdown)",
            _record(
                label,
                profile,
                result,
                terms=terms,
                method_status=method_status,
                support_note=support_note,
                interpretation_limit=interpretation_limit,
            ),
            file_name=f"{key}_session1_2_ergm_audit.md",
            mime="text/markdown",
            key=f"{key}_record",
        )


def _worked_examples() -> None:
    """Present all five documented public examples as visible choices."""
    catalog = load_catalog()
    st.markdown("#### Select a worked public network")
    st.info(
        "Click one of the five visible network choices. The formula, support note, and full diagnostic profile change with the selected data; no hidden dropdown is used."
    )
    recipe_by_title = {recipe.title: recipe for recipe in WORKED_RECIPES}
    selected_title = st.radio(
        "Five Session 1.2 worked examples",
        list(recipe_by_title),
        index=0,
        key="session12_worked_example",
    )
    recipe = recipe_by_title[selected_title]
    spec = catalog[recipe.identifier]
    nodes, edges = load_example(spec)
    st.subheader(recipe.title)
    st.caption(spec.network_type)
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Method appropriateness:** {recipe.method_status}")
        st.markdown("**Full diagnostic family for this support:**")
        st.markdown("\n".join(f"- {item}" for item in recipe.diagnostic_focus))
    with right:
        st.markdown(f"**Support note:** {recipe.support_note}")
        st.warning(f"**Interpretation limit:** {recipe.interpretation_limit}")
        st.link_button("Open public source documentation", spec.source_url)
    _run_fit(
        nodes,
        edges,
        directed=spec.directed,
        bipartite=spec.bipartite,
        terms=recipe.formula_terms,
        method_status=recipe.method_status,
        support_note=recipe.support_note,
        interpretation_limit=recipe.interpretation_limit,
        label=spec.name,
        recipe=recipe,
        key=f"session12_worked_{recipe.identifier}",
    )
    with st.expander("Inspect documented data tables", expanded=False):
        first, second = st.columns(2)
        with first:
            st.markdown("**Node table**")
            st.dataframe(nodes, width="stretch", hide_index=True)
        with second:
            st.markdown("**Edge table**")
            st.dataframe(edges, width="stretch", hide_index=True)


def _byod() -> None:
    """Offer a constrained BYOD audit path with support-valid starter formulas."""
    st.subheader("Bring Your Own Data (BYOD)")
    st.write(
        "Upload a binary static edge list and a matching node table. The app validates the declared support and then uses only a support-valid starter specification; it does not recode valued data, infer missingness, or select a model automatically."
    )
    with st.expander("Required files and boundary decisions", expanded=True):
        st.markdown(
            "- **Nodes CSV:** `id` plus optional attributes; include `mode` for a bipartite graph.\n- **Edges CSV:** `source`, `target`, and optional binary `tie` column.\n- **Declare:** directedness, bipartite structure, actor boundary, structural zeros, and observation window.\n- **Not supported here:** valued/count ties, temporal sequences, multiplex relations, implicit projections, or silent treatment of missing ties as zeros."
        )
    first, second = st.columns(2)
    nodes_upload = first.file_uploader("Node table (CSV)", type=["csv"], key="session12_byod_nodes")
    edges_upload = second.file_uploader("Edge table (CSV)", type=["csv"], key="session12_byod_edges")
    directed = st.checkbox("Directed network", value=True, key="session12_byod_directed")
    bipartite = st.checkbox("Bipartite / two-mode network", value=False, key="session12_byod_bipartite")
    closure = False
    if not directed and not bipartite:
        closure = st.checkbox(
            "Include a fixed-decay edgewise shared-partner closure candidate",
            value=False,
            key="session12_byod_closure",
        )
    if nodes_upload is None or edges_upload is None:
        st.caption("Upload both CSV files to open the BYOD Session 1.2 workspace.")
        return
    try:
        nodes = _read_upload(nodes_upload)
        edges = _read_upload(edges_upload)
        validate_binary_network(nodes, edges, directed=directed, bipartite=bipartite)
    except (UnicodeDecodeError, pd.errors.ParserError, NetworkValidationError) as error:
        st.error(f"The uploaded network cannot enter this binary static-ERGM audit: {error}")
        return
    terms = byod_terms(directed=directed, bipartite=bipartite, include_closure=closure)
    method_status = byod_method_note(directed=directed, bipartite=bipartite, include_closure=closure)
    st.success("Upload checks passed. The calculation remains conditional on the declared support and data boundary.")
    st.info(f"**Starter formula components:** {', '.join(terms)}")
    _run_fit(
        nodes,
        edges,
        directed=directed,
        bipartite=bipartite,
        terms=terms,
        method_status=method_status,
        support_note="The uploaded edge list and declared support are supplied by the participant. Retain a data dictionary and justify structural zeros, missingness, and the actor boundary outside the app.",
        interpretation_limit="A completed MCMC and GOF audit does not establish a causal process, an automatic best model, or validity beyond the stated data-generating and observation assumptions.",
        label="Participant-uploaded network",
        recipe=None,
        key="session12_byod",
    )


def render_session1_2() -> None:
    """Render the complete Session 1.2 computation-first interface."""
    st.title("Session 1.2 — Curved ERGMs, Fit, and Degeneracy")
    st.caption("Day 1 · October 28, 2026 · 4:30–6:00 PM GMT")
    st.info(
        "This page implements a full standard ERGM audit: MCMC trace/autocorrelation/distribution diagnostics, simulation-based GOF, and support-specific omitted-statistic checks. It does not reduce model adequacy to coefficients or a minimal fixed checklist."
    )
    overview, worked, byod, methods = st.tabs(
        ["Computation map", "Five worked public networks", "BYOD", "Methods and data"]
    )
    with overview:
        st.markdown("### Curved and stable ERGM workflow")
        st.markdown(
            "1. Preserve the observed network support and define a theory-led stable or curved candidate.\n2. Fit the stated ERGM with recorded MCMC controls and seed.\n3. Inspect retained MCMC statistic traces, autocorrelation, and distributions.\n4. Simulate networks and compare support-appropriate GOF distributions.\n5. Inspect omitted or substantively relevant network features in simulations.\n6. Distinguish nonconvergence, MCMC nonmixing, nonidentification, and degeneracy rather than treating them as one warning."
        )
        st.latex(r"\Pr_{\theta}(Y=y)=\frac{\exp\{\eta(\theta)^{\mathsf T}g(y)\}}{\kappa\{\eta(\theta)\}}")
        st.latex(r"U(\theta)=D_{\eta}(\theta)^{\mathsf T}\left[g(y)-\mathbb{E}_{\theta}\{g(Y)\}\right]")
        st.caption(
            "A curved ERGM has a natural parameter η(θ) in R^q that depends nonlinearly on a lower-dimensional parameter θ in R^p, typically with p < q. The score condition is projected through the Jacobian; it is not a componentwise equality of every underlying configuration count.")
    with worked:
        _worked_examples()
    with byod:
        _byod()
    with methods:
        catalog = load_catalog()
        st.markdown("### Public-data provenance")
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
        st.markdown("### Interpretation rule")
        st.write(
            "The simulation checks evaluate compatibility with the fitted graph distribution on the stated support. They are not a held-out classifier score, a causal validation, or a mechanical instruction to add terms until every observed statistic is reproduced."
        )
        st.markdown("### Computation boundaries")
        st.markdown(
            "- **Degeneracy:** a model distribution places most probability on a relatively small set of graph configurations, often far from the observed network; it is not merely an estimation warning.\n"
            "- **Finite-MLE nonexistence:** the observed sufficient-statistic vector lies on the relevant convex-support boundary, so an ordinary finite canonical maximum-likelihood estimate does not exist.\n"
            "- **MCMC traces:** the standard diagnostic chain is over networks and their retained statistics. Parameter trajectories may arise separately when an estimation procedure updates parameters iteratively.\n"
            "- **Information criteria:** the app does not treat BIC as an automatic selector. For a single dependent network, its N is not uniquely determined by the ERGM likelihood; actors or admissible dyads require an explicit asymptotic justification."
        )
