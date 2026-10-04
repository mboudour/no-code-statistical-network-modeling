"""Shared Streamlit interface for the two Day 3 SAOM sessions."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
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


def _plotly_layout(figure: go.Figure, *, title: str, y_title: str, height: int = 340) -> go.Figure:
    """Apply a consistent, compact layout to descriptive Day 3 figures."""
    figure.update_layout(
        title=title,
        template="plotly_white",
        yaxis_title=y_title,
        height=height,
        margin={"l": 45, "r": 25, "t": 55, "b": 75},
        legend={"orientation": "h", "y": -0.25},
    )
    return figure


def _network_dynamics_profile(profile: dict[str, Any]) -> None:
    """Render all observed network-dynamics plots before any estimation."""
    wave = pd.DataFrame(profile["wave_table"])
    transitions = pd.DataFrame(profile["network_transitions"])
    structure = pd.DataFrame(profile["network_structure"])
    st.markdown("### Dynamics: observed network panel")
    st.caption(
        "These are observed descriptive summaries. Formations, dissolutions, maintenance, and Jaccard overlap describe the recorded panels; they are not separately estimated causal processes."
    )
    st.dataframe(wave, hide_index=True, width="stretch")
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=wave["wave"], y=wave["ties"], mode="lines+markers", name="Observed ties", line={"color": PALETTE["purple"]}
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=wave["wave"], y=wave["density"], mode="lines+markers", name="Observed density", line={"color": PALETTE["teal"]}
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title="Observed tie count and density by wave", template="plotly_white", height=340,
        margin={"l": 45, "r": 45, "t": 55, "b": 75}, legend={"orientation": "h", "y": -0.25},
    )
    figure.update_yaxes(title_text="Tie count", secondary_y=False)
    figure.update_yaxes(title_text="Density", secondary_y=True)
    st.plotly_chart(figure, width="stretch")
    if not transitions.empty:
        left, right = st.columns(2)
        with left:
            turnover = go.Figure()
            for column, label, color in (
                ("maintained_ties", "Maintained", PALETTE["teal"]),
                ("formed_ties", "Formed", PALETTE["purple"]),
                ("dissolved_ties", "Dissolved", PALETTE["orange"]),
            ):
                turnover.add_trace(go.Bar(x=transitions["transition"], y=transitions[column], name=label, marker_color=color))
            turnover.update_layout(barmode="group")
            st.plotly_chart(_plotly_layout(turnover, title="Observed tie turnover by transition", y_title="Ties"), width="stretch")
        with right:
            overlap = go.Figure(go.Scatter(x=transitions["transition"], y=transitions["jaccard_index"], mode="lines+markers", line={"color": PALETTE["purple"]}, name="Jaccard"))
            st.plotly_chart(_plotly_layout(overlap, title="Successive-wave Jaccard overlap", y_title="Jaccard index"), width="stretch")
        st.dataframe(transitions, hide_index=True, width="stretch")
    if not structure.empty:
        figure = go.Figure()
        if profile["directed"]:
            figure.add_trace(go.Bar(x=structure["wave"], y=structure["mutual_dyads"], name="Mutual dyads", marker_color=PALETTE["purple"]))
            figure.add_trace(go.Bar(x=structure["wave"], y=structure["transitive_two_path_closures"], name="Transitive two-path closures", marker_color=PALETTE["teal"]))
            figure.update_layout(barmode="group")
            title = "Observed directed reciprocity and closure summaries"
        else:
            figure.add_trace(go.Bar(x=structure["wave"], y=structure["triangles"], name="Triangles", marker_color=PALETTE["teal"]))
            title = "Observed undirected triangle (closure) count"
        st.plotly_chart(_plotly_layout(figure, title=title, y_title="Count"), width="stretch")


def _selection_profile(profile: dict[str, Any]) -> None:
    """Render observed selection associations without presenting them as effects."""
    st.markdown("### Selection: observed network–behavior associations")
    st.caption(
        "Every plot in this section is descriptive. It compares observed ties and behavior scores before model adjustment and does not identify a selection mechanism or a causal effect."
    )
    matrix = pd.DataFrame(profile["selection_matrix"])
    if not matrix.empty:
        pivot = matrix.pivot(index="ego_behavior", columns="alter_behavior", values="tie_rate").sort_index().sort_index(axis=1)
        heatmap = go.Figure(go.Heatmap(z=pivot.to_numpy(), x=pivot.columns, y=pivot.index, colorscale="Viridis", colorbar={"title": "Tie rate"}, hovertemplate="ego=%{y}<br>alter=%{x}<br>tie rate=%{z:.3f}<extra></extra>"))
        heatmap.update_layout(title="Observed tie-rate mixing matrix", template="plotly_white", xaxis_title="Alter behavior score", yaxis_title="Ego behavior score", height=390, margin={"l": 55, "r": 25, "t": 55, "b": 55})
        st.plotly_chart(heatmap, width="stretch")
    tabs = st.tabs(["Ego score", "Alter score", "Absolute score difference"])
    for tab, key, label in zip(
        tabs,
        ("selection_ego_rates", "selection_alter_rates", "selection_difference_rates"),
        ("Ego behavior score", "Alter behavior score", "Absolute ego–alter difference"),
        strict=True,
    ):
        with tab:
            rows = pd.DataFrame(profile[key])
            if rows.empty:
                st.info("No observed dyads were available for this descriptive association.")
                continue
            x_column = {"selection_ego_rates": "ego_behavior", "selection_alter_rates": "alter_behavior", "selection_difference_rates": "absolute_difference"}[key]
            figure = go.Figure()
            for wave, group in rows.groupby("wave", sort=False):
                figure.add_trace(go.Scatter(x=group[x_column], y=group["tie_rate"], mode="lines+markers", name=str(wave)))
            figure.update_layout(xaxis_title=label)
            st.plotly_chart(_plotly_layout(figure, title=f"Observed tie rate by {label.lower()}", y_title="Tie rate"), width="stretch")


def _influence_profile(profile: dict[str, Any]) -> None:
    """Render observed behavior and alter-exposure summaries for Session 3.2."""
    behavior = pd.DataFrame(profile["behavior_table"])
    distribution = pd.DataFrame(profile["behavior_distribution"])
    transitions = pd.DataFrame(profile["behavior_transitions"])
    changes = pd.DataFrame(profile["behavior_changes"])
    exposure = pd.DataFrame(profile["behavior_exposure"])
    change_exposure = pd.DataFrame(profile["behavior_change_exposure"])
    name = profile["behavior_name"]
    st.markdown("### Influence: observed behavior and exposure patterns")
    st.caption(
        "The actor-level outcome may be a state, attitude, score, or behavior. These plots are descriptive; they do not make a peer-influence or causal claim. For directed networks, alters are those to whom the ego is tied under the explicitly declared outgoing-tie convention."
    )
    st.dataframe(behavior, hide_index=True, width="stretch")
    left, right = st.columns(2)
    with left:
        figure = go.Figure()
        for score, group in distribution.groupby("score", sort=True):
            figure.add_trace(go.Bar(x=group["wave"], y=group["count"], name=f"Score {score}"))
        figure.update_layout(barmode="stack")
        st.plotly_chart(_plotly_layout(figure, title=f"Observed {name} score distribution by wave", y_title="Actors"), width="stretch")
    with right:
        figure = make_subplots(specs=[[{"secondary_y": True}]])
        figure.add_trace(go.Scatter(x=behavior["wave"], y=behavior["mean"], mode="lines+markers", name="Mean", line={"color": PALETTE["teal"]}), secondary_y=False)
        figure.add_trace(go.Scatter(x=behavior["wave"], y=behavior["variance"], mode="lines+markers", name="Variance", line={"color": PALETTE["orange"]}), secondary_y=True)
        figure.update_layout(title=f"Observed {name} mean and variance", template="plotly_white", height=340, margin={"l": 45, "r": 45, "t": 55, "b": 75}, legend={"orientation": "h", "y": -0.25})
        figure.update_yaxes(title_text="Mean", secondary_y=False)
        figure.update_yaxes(title_text="Variance", secondary_y=True)
        st.plotly_chart(figure, width="stretch")
    if not transitions.empty:
        option = st.selectbox("Behavior-transition interval", transitions["transition"].drop_duplicates().tolist(), key="s32_behavior_transition")
        table = transitions.loc[transitions["transition"] == option]
        pivot = table.pivot(index="from_score", columns="to_score", values="count").fillna(0).sort_index().sort_index(axis=1)
        figure = go.Figure(go.Heatmap(z=pivot.to_numpy(), x=pivot.columns, y=pivot.index, colorscale="Blues", colorbar={"title": "Actors"}, hovertemplate="from=%{y}<br>to=%{x}<br>actors=%{z}<extra></extra>"))
        figure.update_layout(title=f"Observed {name} transition matrix: {option}", template="plotly_white", xaxis_title="Current score", yaxis_title="Previous score", height=390, margin={"l": 55, "r": 25, "t": 55, "b": 55})
        st.plotly_chart(figure, width="stretch")
    if not changes.empty:
        figure = go.Figure()
        for transition, group in changes.groupby("transition", sort=False):
            figure.add_trace(go.Bar(x=group["behavior_change"], y=group["count"], name=transition))
        figure.update_layout(barmode="group", xaxis_title="Behavior change")
        st.plotly_chart(_plotly_layout(figure, title=f"Observed {name} change distribution", y_title="Actors"), width="stretch")
    if not exposure.empty:
        figure = go.Figure()
        for wave, group in exposure.groupby("wave", sort=False):
            figure.add_trace(go.Scatter(x=group["ego_behavior"], y=group["average_alter_behavior"], mode="markers", name=str(wave), text=group["actor"], hovertemplate="actor=%{text}<br>ego=%{x}<br>mean alters=%{y:.2f}<extra></extra>"))
        figure.update_layout(xaxis_title="Ego behavior score")
        st.plotly_chart(_plotly_layout(figure, title="Observed ego score versus mean alter score", y_title="Mean alter score"), width="stretch")
    if not change_exposure.empty:
        left, right = st.columns(2)
        with left:
            figure = go.Figure(go.Scatter(x=change_exposure["average_alter_behavior"], y=change_exposure["behavior_change"], mode="markers", text=change_exposure["actor"], marker={"color": PALETTE["purple"]}, hovertemplate="actor=%{text}<br>mean alters=%{x:.2f}<br>change=%{y}<extra></extra>"))
            figure.update_layout(xaxis_title="Previous-wave mean alter score")
            st.plotly_chart(_plotly_layout(figure, title="Observed change versus mean alter score", y_title="Behavior change"), width="stretch")
        with right:
            figure = go.Figure(go.Scatter(x=change_exposure["ego_alter_discrepancy"], y=change_exposure["behavior_change"], mode="markers", text=change_exposure["actor"], marker={"color": PALETTE["orange"]}, hovertemplate="actor=%{text}<br>ego − mean alters=%{x:.2f}<br>change=%{y}<extra></extra>"))
            figure.update_layout(xaxis_title="Previous-wave ego − mean alter score")
            st.plotly_chart(_plotly_layout(figure, title="Observed change versus ego–alter discrepancy", y_title="Behavior change"), width="stretch")


def _profile_charts(profile: dict[str, Any]) -> None:
    """Separate observed diagnostics by the model component to be audited."""
    _network_dynamics_profile(profile)
    if "behavior_table" in profile:
        _selection_profile(profile)
        _influence_profile(profile)


def _coefficient_plot(
    rows: list[dict[str, Any]], *, title: str = "RSiena estimates with approximate 95% Wald intervals"
) -> None:
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
        title=title,
        xaxis_title="Estimate",
        yaxis_title="Effect",
        height=max(360, 44 * len(data)),
        margin={"l": 20, "r": 20, "t": 55, "b": 35},
    )
    st.plotly_chart(figure, width="stretch")


def _effects_with(rows: list[dict[str, Any]], fragments: tuple[str, ...]) -> list[dict[str, Any]]:
    """Select effect rows by transparent, RSiena-returned effect-name fragments."""
    return [
        row
        for row in rows
        if any(fragment.lower() in str(row["effect"]).lower() for fragment in fragments)
    ]


def _rate_parameter_plot(rows: list[dict[str, Any]]) -> None:
    """Make rate parameters visibly distinct from evaluation-function effects."""
    rates = _effects_with(rows, ("rate (period",))
    if not rates:
        return
    st.markdown("#### Period-specific rate parameters")
    st.caption(
        "Rate parameters govern opportunities for microsteps between observed waves. They are displayed separately from the evaluation-function effects and are not probabilities of an observed tie."
    )
    if all(row.get("convergence_t_ratio") is None for row in rates):
        st.caption(
            "For a network-only fit, RSiena returns these period rates separately from the evaluation-effect vector; the all-effect convergence chart therefore reports the individual t-ratios returned for evaluation effects together with RSiena's overall maximum ratio."
        )
    _coefficient_plot(rates, title="RSiena rate parameters with approximate 95% Wald intervals")


def _selection_surface(rows: list[dict[str, Any]], profile: dict[str, Any]) -> None:
    """Show the fitted ego/alter/similarity contribution holding other effects fixed."""
    behavior_rows = pd.DataFrame(profile.get("behavior_distribution", []))
    if behavior_rows.empty:
        return
    levels = np.sort(behavior_rows["score"].unique())
    estimates = {str(row["effect"]).lower(): float(row["estimate"]) for row in rows}
    ego = next((value for key, value in estimates.items() if " ego" in key and "average" not in key), None)
    alter = next((value for key, value in estimates.items() if " alter" in key), None)
    similarity = next((value for key, value in estimates.items() if " similarity" in key and "average" not in key), None)
    if ego is None and alter is None and similarity is None:
        return
    span = float(levels.max() - levels.min())
    grid = np.zeros((len(levels), len(levels)))
    for i, ego_score in enumerate(levels):
        for j, alter_score in enumerate(levels):
            normalized_similarity = 1.0 if span == 0 else 1.0 - abs(ego_score - alter_score) / span
            grid[i, j] = (ego or 0.0) * ego_score + (alter or 0.0) * alter_score + (similarity or 0.0) * normalized_similarity
    figure = go.Figure(go.Heatmap(z=grid, x=levels, y=levels, colorscale="RdBu", zmid=0, colorbar={"title": "Contribution"}, hovertemplate="ego=%{y}<br>alter=%{x}<br>selection contribution=%{z:.3f}<extra></extra>"))
    figure.update_layout(title="Fitted selection contribution surface", template="plotly_white", xaxis_title="Alter behavior score", yaxis_title="Ego behavior score", height=400, margin={"l": 55, "r": 25, "t": 55, "b": 55})
    st.plotly_chart(figure, width="stretch")
    st.caption(
        "This surface evaluates only the fitted behavior ego, alter, and range-normalized similarity terms, holding structural and rate effects fixed. It is not a fitted tie probability and does not establish selection causation."
    )


def _influence_function_plot(rows: list[dict[str, Any]], profile: dict[str, Any]) -> None:
    """Visualize fitted average-similarity and behavior-shape contributions separately."""
    behavior_rows = pd.DataFrame(profile.get("behavior_distribution", []))
    if behavior_rows.empty:
        return
    levels = np.sort(behavior_rows["score"].unique())
    estimates = {str(row["effect"]).lower(): float(row["estimate"]) for row in rows}
    average_similarity = next((value for key, value in estimates.items() if "average similarity" in key), None)
    linear = next((value for key, value in estimates.items() if "linear shape" in key), None)
    quadratic = next((value for key, value in estimates.items() if "quadratic shape" in key), None)
    if average_similarity is None and linear is None and quadratic is None:
        return
    figure = make_subplots(rows=1, cols=2, subplot_titles=("Average-similarity contribution", "Behavior-shape contribution"))
    if average_similarity is not None:
        similarity = np.linspace(0, 1, 51)
        figure.add_trace(go.Scatter(x=similarity, y=average_similarity * similarity, mode="lines", line={"color": PALETTE["purple"]}, name="Average similarity"), row=1, col=1)
    shape = (linear or 0.0) * levels + (quadratic or 0.0) * np.square(levels)
    figure.add_trace(go.Scatter(x=levels, y=shape, mode="lines+markers", line={"color": PALETTE["teal"]}, name="Behavior shape"), row=1, col=2)
    figure.update_xaxes(title_text="Similarity", row=1, col=1)
    figure.update_xaxes(title_text="Behavior score", row=1, col=2)
    figure.update_yaxes(title_text="Evaluation contribution", row=1, col=1)
    figure.update_yaxes(title_text="Evaluation contribution", row=1, col=2)
    figure.update_layout(title="Fitted influence and behavior-shape contributions", template="plotly_white", height=370, margin={"l": 45, "r": 25, "t": 75, "b": 55}, legend={"orientation": "h", "y": -0.25})
    st.plotly_chart(figure, width="stretch")
    st.caption(
        "The first panel evaluates the average-similarity influence term; the second evaluates the behavior linear and quadratic shape terms. Both are model contributions, not observed causal response functions."
    )


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


def _mixing_matrix_gof(table: pd.DataFrame) -> go.Figure | None:
    """Turn fixed RSiena mixing-cell labels into observed/simulated heatmaps."""
    parsed = table["statistic"].str.extract(r"ego=(?P<ego>.+) \| alter=(?P<alter>.+)")
    if parsed.isna().any().any():
        return None
    data = pd.concat([table.reset_index(drop=True), parsed], axis=1)
    observed = data.pivot(index="ego", columns="alter", values="observed").sort_index().sort_index(axis=1)
    simulated = data.pivot(index="ego", columns="alter", values="simulated_mean").reindex(index=observed.index, columns=observed.columns)
    figure = make_subplots(rows=1, cols=2, subplot_titles=("Observed", "Fitted-simulation mean"))
    figure.add_trace(go.Heatmap(z=observed.to_numpy(), x=observed.columns, y=observed.index, colorscale="Viridis", colorbar={"title": "Ties", "x": 0.43}, hovertemplate="ego=%{y}<br>alter=%{x}<br>ties=%{z}<extra></extra>"), row=1, col=1)
    figure.add_trace(go.Heatmap(z=simulated.to_numpy(), x=simulated.columns, y=simulated.index, colorscale="Viridis", colorbar={"title": "Ties", "x": 1.0}, hovertemplate="ego=%{y}<br>alter=%{x}<br>mean ties=%{z:.2f}<extra></extra>"), row=1, col=2)
    figure.update_xaxes(title_text="Alter score", row=1, col=1)
    figure.update_xaxes(title_text="Alter score", row=1, col=2)
    figure.update_yaxes(title_text="Ego score", row=1, col=1)
    figure.update_yaxes(title_text="Ego score", row=1, col=2)
    figure.update_layout(title="Tied-actor behavior mixing: observed versus fitted simulations", template="plotly_white", height=420, margin={"l": 55, "r": 55, "t": 75, "b": 55})
    return figure


def _gof_y_axis(label: str) -> str:
    """Avoid implying every RSiena auxiliary statistic is a frequency count."""
    lowered = label.lower()
    if "selection" in lowered or "association" in lowered:
        return "Association statistic / tie rate"
    if "reciprocity" in lowered or "structural" in lowered or "triad" in lowered:
        return "Structural count"
    return "Frequency / count"


def _gof_plots(
    result: dict[str, Any], *, title: str, include_keywords: tuple[str, ...] | None = None
) -> None:
    """Render a deliberately named subset of the returned simulation diagnostics."""
    st.subheader(title)
    audits = result.get("goodness_of_fit", [])
    if include_keywords:
        audits = [
            item
            for item in audits
            if any(keyword in item.get("label", "").lower() for keyword in include_keywords)
        ]
    available = [
        item for item in audits if item.get("status") == "ok" and item.get("rows")
    ]
    unavailable = [item for item in audits if item.get("status") != "ok"]
    if available:
        tabs = st.tabs([item["label"] for item in available])
        for tab, audit in zip(tabs, available, strict=True):
            with tab:
                table = pd.DataFrame(audit["rows"])
                if "mixing matrix" in audit["label"].lower():
                    mixing = _mixing_matrix_gof(table)
                    if mixing is not None:
                        st.plotly_chart(mixing, width="stretch")
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
                    yaxis_title=_gof_y_axis(audit["label"]),
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


def _result_panel(result: dict[str, Any], profile: dict[str, Any]) -> None:
    st.success(f"Completed: {result['model_class']}.")
    st.caption(result["interpretation_boundary"])
    st.subheader("All RSiena estimates")
    st.dataframe(pd.DataFrame(result["coefficients"]), hide_index=True, width="stretch")
    _coefficient_plot(result["coefficients"])
    _rate_parameter_plot(result["coefficients"])
    if result.get("behavior_name"):
        st.markdown("### Dynamics: fitted network effects")
        dynamics = _effects_with(
            result["coefficients"],
            ("rate (period", "outdegree", "reciprocity", "transitive"),
        )
        _coefficient_plot(
            dynamics,
            title="Network-dynamics effects with approximate 95% Wald intervals",
        )
        _gof_plots(
            result,
            title="Dynamics: network simulation audits",
            include_keywords=("degree", "triad", "reciprocity", "geodesic"),
        )
        st.markdown("### Selection: fitted network–behavior effects")
        selection = [
            row
            for row in result["coefficients"]
            if any(f" {term}" in str(row["effect"]).lower() for term in ("alter", "ego", "similarity"))
            and "average similarity" not in str(row["effect"]).lower()
        ]
        _coefficient_plot(
            selection,
            title="Selection effects with approximate 95% Wald intervals",
        )
        _selection_surface(result["coefficients"], profile)
        _gof_plots(
            result,
            title="Selection: observed-versus-simulated mixing audit",
            include_keywords=("mixing matrix",),
        )
        st.markdown("### Influence: fitted behavior effects")
        influence = _effects_with(
            result["coefficients"], ("linear shape", "quadratic shape", "average similarity")
        )
        _coefficient_plot(
            influence,
            title="Influence and behavior-shape effects with approximate 95% Wald intervals",
        )
        _influence_function_plot(result["coefficients"], profile)
        behavior_name = str(result["behavior_name"]).lower()
        _gof_plots(
            result,
            title="Influence: behavior simulation audits",
            include_keywords=(f"{behavior_name} distribution", "change distribution"),
        )
        _gof_plots(
            result,
            title="Selection and influence: joint network–behavior association audit",
            include_keywords=("joint network-behavior",),
        )
    else:
        _gof_plots(
            result,
            title="Dynamics: simulation-based goodness-of-fit audits",
        )
    st.subheader("Convergence audit: all effects")
    _convergence_plot(result)
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


def _run_panel(panel: Any, *, profile: dict[str, Any], key_prefix: str) -> None:
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
        _result_panel(st.session_state[f"{key_prefix}_result"], profile)


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
    _run_panel(panel, profile=profile, key_prefix=f"public_{entry['id']}")


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
    profile = panel_profile(panel)
    _profile_charts(profile)
    _run_panel(panel, profile=profile, key_prefix=f"byod_{session}")


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
