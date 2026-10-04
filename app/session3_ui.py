"""Shared Streamlit interface for the two Day 3 SAOM sessions."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from r_engine import SAOMRuntimeError, fit_saom, saom_engine_status
from saom_core import (
    SAOMValidationError,
    load_byod_panel,
    load_public_workflow,
    panel_profile,
    r_payload,
    workflows,
)

PALETTE = {
    "purple": "#4E2A84",
    "teal": "#0F766E",
    "orange": "#B45309",
    "gray": "#6B7280",
}


def _read_upload(upload: Any) -> pd.DataFrame:
    return pd.read_csv(StringIO(upload.getvalue().decode("utf-8")))


def _profile_charts(profile: dict[str, Any]) -> None:
    wave = pd.DataFrame(profile["wave_table"])
    st.dataframe(wave, hide_index=True, width="stretch")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=wave["wave"],
            y=wave["density"],
            mode="lines+markers",
            name="Observed density",
            line={"color": PALETTE["purple"]},
        )
    )
    figure.update_layout(
        title="Observed density by wave",
        xaxis_title="Wave",
        yaxis_title="Density",
        height=320,
        margin={"l": 35, "r": 20, "t": 55, "b": 35},
    )
    st.plotly_chart(figure, width="stretch")
    if "behavior_table" in profile:
        behavior = pd.DataFrame(profile["behavior_table"])
        st.dataframe(behavior, hide_index=True, width="stretch")
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=behavior["wave"],
                y=behavior["mean"],
                mode="lines+markers",
                name="Observed mean",
                line={"color": PALETTE["teal"]},
            )
        )
        figure.update_layout(
            title=f"Observed {profile['behavior_name']} mean by wave",
            xaxis_title="Wave",
            yaxis_title="Mean behavior score",
            height=320,
            margin={"l": 35, "r": 20, "t": 55, "b": 35},
        )
        st.plotly_chart(figure, width="stretch")


def _coefficient_plot(rows: list[dict[str, Any]]) -> None:
    data = pd.DataFrame(rows)
    if data.empty:
        st.info("No coefficient rows were returned.")
        return
    data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
    data["standard_error"] = pd.to_numeric(data["standard_error"], errors="coerce")
    data = data.dropna(subset=["estimate"]).iloc[::-1]
    errors = 1.96 * data["standard_error"].fillna(0)
    figure = go.Figure(
        go.Scatter(
            x=data["estimate"],
            y=data["effect"],
            mode="markers",
            marker={"size": 9, "color": PALETTE["purple"]},
            error_x={"type": "data", "array": errors, "visible": True},
            hovertemplate="%{y}<br>estimate=%{x:.3f}<extra></extra>",
        )
    )
    figure.add_vline(x=0, line_dash="dash", line_color=PALETTE["gray"])
    figure.update_layout(
        title="RSiena estimates with approximate 95% Wald intervals",
        xaxis_title="Estimate",
        yaxis_title="Effect",
        height=max(360, 44 * len(data)),
        margin={"l": 20, "r": 20, "t": 55, "b": 35},
    )
    st.plotly_chart(figure, width="stretch")


def _convergence_plot(result: dict[str, Any]) -> None:
    rows = pd.DataFrame(result["convergence"]["per_effect_t_ratios"])
    if rows.empty:
        return
    rows["t_ratio"] = pd.to_numeric(rows["t_ratio"], errors="coerce")
    figure = go.Figure(
        go.Bar(x=rows["effect"], y=rows["t_ratio"], marker_color=PALETTE["orange"])
    )
    figure.add_hline(
        y=0.25,
        line_dash="dash",
        line_color="firebrick",
        annotation_text="0.25 reference",
    )
    figure.add_hline(y=-0.25, line_dash="dash", line_color="firebrick")
    figure.update_layout(
        title="Final convergence t-ratios",
        xaxis_title="Effect",
        yaxis_title="Convergence t-ratio",
        height=360,
        margin={"l": 45, "r": 20, "t": 55, "b": 115},
    )
    st.plotly_chart(figure, width="stretch")
    maximum = result["convergence"].get("maximum_convergence_ratio")
    st.caption(
        f"Maximum convergence ratio reported by RSiena: {maximum}. For a final analysis, inspect the complete RSiena diagnostics and do not treat a short classroom pilot as converged merely because it produced estimates."
    )


def _gof_plots(result: dict[str, Any]) -> None:
    st.subheader("Simulation-based goodness-of-fit audits")
    audits = result.get("goodness_of_fit", [])
    available = [
        item for item in audits if item.get("status") == "ok" and item.get("rows")
    ]
    unavailable = [item for item in audits if item.get("status") != "ok"]
    if available:
        tabs = st.tabs([item["label"] for item in available])
        for tab, audit in zip(tabs, available, strict=True):
            with tab:
                table = pd.DataFrame(audit["rows"])
                figure = go.Figure()
                figure.add_trace(
                    go.Scatter(
                        x=table["statistic"],
                        y=table["simulated_mean"],
                        mode="lines+markers",
                        name="Simulated mean",
                        line={"color": PALETTE["teal"]},
                    )
                )
                figure.add_trace(
                    go.Scatter(
                        x=list(table["statistic"]) + list(table["statistic"])[::-1],
                        y=list(table["simulated_upper_975"])
                        + list(table["simulated_lower_025"])[::-1],
                        fill="toself",
                        fillcolor="rgba(15,118,110,0.16)",
                        line={"color": "rgba(0,0,0,0)"},
                        name="95% simulation envelope",
                    )
                )
                figure.add_trace(
                    go.Scatter(
                        x=table["statistic"],
                        y=table["observed"],
                        mode="markers",
                        marker={"size": 9, "color": PALETTE["purple"]},
                        name="Observed",
                    )
                )
                figure.update_layout(
                    title=f"{audit['label']} — observed versus fitted simulations",
                    xaxis_title="Statistic",
                    yaxis_title="Frequency / count",
                    height=370,
                    margin={"l": 45, "r": 20, "t": 55, "b": 75},
                )
                st.plotly_chart(figure, width="stretch")
                st.caption(
                    f"Joint RSiena GOF p-value: {audit.get('joint_p_value')}. This is a simulation diagnostic, not a standalone model-selection rule."
                )
                st.dataframe(table, hide_index=True, width="stretch")
    for audit in unavailable:
        st.warning(f"{audit['label']}: {audit.get('reason', 'unavailable')}")


def _result_panel(result: dict[str, Any]) -> None:
    st.success(f"Completed: {result['model_class']}.")
    st.caption(result["interpretation_boundary"])
    st.subheader("Model estimates")
    st.dataframe(pd.DataFrame(result["coefficients"]), hide_index=True, width="stretch")
    _coefficient_plot(result["coefficients"])
    st.subheader("Convergence audit")
    _convergence_plot(result)
    _gof_plots(result)
    if result.get("notes"):
        with st.expander("RSiena effect and diagnostic notes"):
            for note in result["notes"]:
                st.warning(note)
    download = json.dumps(
        {
            key: value
            for key, value in result.items()
            if key not in {"r_stdout", "r_stderr"}
        },
        indent=2,
    )
    st.download_button(
        "Download the reproducible computation record",
        data=download,
        file_name="day3_saom_computation_record.json",
        mime="application/json",
    )


def _run_panel(panel: Any, *, key_prefix: str) -> None:
    st.markdown("#### Reproducible pilot settings")
    st.caption(
        "The engine is RSiena in the Render Docker image. These settings control a classroom pilot; a publication analysis requires a documented convergence assessment and, where appropriate, larger simulation settings."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        n3 = st.number_input(
            "RSiena n3",
            min_value=40,
            max_value=2000,
            value=100,
            step=20,
            key=f"{key_prefix}_n3",
        )
    with col2:
        gof_simulations = st.number_input(
            "GOF simulations",
            min_value=20,
            max_value=200,
            value=40,
            step=10,
            key=f"{key_prefix}_gof",
        )
    with col3:
        seed = st.number_input(
            "Random seed",
            min_value=1,
            max_value=2_147_483_000,
            value=20261030,
            step=1,
            key=f"{key_prefix}_seed",
        )
    status = saom_engine_status()
    if not status["available"]:
        st.warning(
            f"This execution environment does not have RSiena ready: {status['reason']}. The deployed Render Docker app is provisioned with RSiena; the button is intentionally unavailable only in this local test environment."
        )
        return
    if st.button(
        "Run the stated RSiena computation", type="primary", key=f"{key_prefix}_run"
    ):
        payload = r_payload(
            panel, n3=int(n3), gof_simulations=int(gof_simulations), seed=int(seed)
        )
        with st.spinner("Running the stated RSiena estimation and simulation audits…"):
            try:
                result = fit_saom(payload)
            except SAOMRuntimeError as error:
                st.error(str(error))
                return
        st.session_state[f"{key_prefix}_result"] = result
    if f"{key_prefix}_result" in st.session_state:
        _result_panel(st.session_state[f"{key_prefix}_result"])


def _public_workflows(session: str) -> None:
    entries = workflows(session)
    option_map = {entry["label"]: entry["id"] for entry in entries}
    selected_label = st.radio(
        "Choose one visible public workflow",
        list(option_map),
        key=f"s{session}_workflow",
    )
    entry, panel = load_public_workflow(session, option_map[selected_label])
    st.markdown(f"**Public source:** [{panel.spec.source}]({panel.spec.source_url})")
    st.markdown(f"**Network response:** {panel.spec.network_type}")
    st.info(f"**Support rule:** {panel.spec.support_rule}")
    if entry.get("reuse_note"):
        st.warning(f"**Source-reuse disclosure:** {entry['reuse_note']}")
    st.warning(f"**Interpretation limit:** {panel.spec.limit}")
    st.subheader("Observed data before fitting")
    profile = panel_profile(panel)
    if profile["excluded_for_incomplete_behavior"]:
        st.warning(
            f"**Behavior-completeness support rule applied:** {profile['excluded_for_incomplete_behavior']} actor(s) observed in the network panel were excluded because the selected behavior was not observed at every selected wave. They were not recoded as a zero behavior or a non-tie."
        )
    _profile_charts(profile)
    _run_panel(panel, key_prefix=f"public_{entry['id']}")


def _byod(session: str) -> None:
    behavior_required = session == "3.2"
    st.markdown(
        "Upload CSV files with no hidden recoding. Nodes must contain `wave,id`; edges must contain `wave,source,target` and represent loopless binary ties. For Session 3.2, behavior must contain `wave,id` and one repeatedly measured numeric behavior column."
    )
    col1, col2 = st.columns(2)
    with col1:
        nodes_upload = st.file_uploader(
            "Nodes CSV", type="csv", key=f"byod_{session}_nodes"
        )
        edges_upload = st.file_uploader(
            "Edges CSV", type="csv", key=f"byod_{session}_edges"
        )
    with col2:
        behavior_upload = st.file_uploader(
            "Behavior CSV" + (" (required)" if behavior_required else " (optional)"),
            type="csv",
            key=f"byod_{session}_behavior",
        )
        directed = st.toggle(
            "Directed network", value=True, key=f"byod_{session}_directed"
        )
    if (
        not nodes_upload
        or not edges_upload
        or (behavior_required and not behavior_upload)
    ):
        return
    try:
        nodes = _read_upload(nodes_upload)
        edges = _read_upload(edges_upload)
        behavior = _read_upload(behavior_upload) if behavior_upload else None
        behavior_name = None
        if behavior is not None:
            candidates = [
                column for column in behavior.columns if column not in {"wave", "id"}
            ]
            if not candidates:
                raise SAOMValidationError(
                    "Behavior CSV needs at least one column besides `wave` and `id`."
                )
            behavior_name = st.selectbox(
                "Behavior to model", candidates, key=f"byod_{session}_behavior_name"
            )
        panel = load_byod_panel(
            nodes=nodes,
            edges=edges,
            behavior=behavior,
            behavior_name=behavior_name,
            directed=directed,
        )
    except (
        UnicodeDecodeError,
        pd.errors.ParserError,
        SAOMValidationError,
        ValueError,
    ) as error:
        st.error(str(error))
        return
    st.success("The upload satisfies the explicit Day 3 balanced-panel contract.")
    _profile_charts(panel_profile(panel))
    _run_panel(panel, key_prefix=f"byod_{session}")


def render_day3(session: str) -> None:
    """Render either Day 3 page with the same transparent computation structure."""
    title = (
        "SAOMs for Actor-Driven Network Dynamics"
        if session == "3.1"
        else "SAOMs for Selection and Influence"
    )
    time = (
        "Friday, October 30, 2026 · 3:00–4:30 PM GMT"
        if session == "3.1"
        else "Friday, October 30, 2026 · 4:30–6:00 PM GMT"
    )
    st.title(f"Session {session}: {title}")
    st.caption(time)
    if session == "3.1":
        st.info(
            "This page estimates a stated network-only RSiena SAOM with rate parameters plus density, reciprocity when directed, and a closure effect: transitive triplets for directed networks or transitive triads for undirected networks. It does not transform the result into a causal actor-level claim."
        )
    else:
        st.info(
            "This page estimates a stated joint RSiena network–behavior SAOM: structural network effects, behavior alter/ego/similarity selection effects, behavior shape effects, and average-similarity influence. It explicitly does not equate a fitted influence parameter with a causal peer effect."
        )
    tabs = st.tabs(
        [
            "Method and data boundary",
            "Five worked public workflows",
            "BYOD and reproducibility",
        ]
    )
    with tabs[0]:
        st.markdown("### What the app computes")
        if session == "3.1":
            st.markdown(
                "- A **network-only actor-oriented model** on a balanced repeated binary panel.\n- The model includes a **rate parameter** for each observation period, plus density, reciprocity for directed networks, and a closure effect: transitive triplets for directed networks or transitive triads for undirected networks.\n- The app reports estimates, final convergence ratios, and RSiena simulation-based degree/triad goodness-of-fit diagnostics.\n- The actor microstep order is simulated rather than observed; estimates describe the stated model, not causal effects."
            )
        else:
            st.markdown(
                "- A **joint network–behavior coevolution SAOM** on a balanced repeated binary network plus a complete repeated behavior.\n- Network selection effects are behavior ego, alter, and similarity; behavior influence is average network similarity, with linear and quadratic shape controls.\n- The app reports estimates, final convergence ratios, degree/triad and behavior-distribution simulation diagnostics.\n- The five specifications transparently reuse documented public releases when they model different repeated behaviors; they are not presented as five independent studies."
            )
        st.markdown("### Standard audit sequence")
        st.markdown(
            "1. Verify actors, waves, directionality, and the response boundary.\n2. Read the support rule and interpretation limit.\n3. Inspect observed density and, when relevant, behavior summaries.\n4. Run the stated RSiena computation.\n5. Audit coefficient uncertainty, final convergence ratios, and every returned simulation envelope before interpreting effects."
        )
    with tabs[1]:
        _public_workflows(session)
    with tabs[2]:
        _byod(session)
