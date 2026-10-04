"""Exact dyad-independent STERGM computations for Session 2.2.

This module deliberately implements the transparent baseline separable model: an
intercept-only formation component on previously absent dyads and an intercept-only
persistence component on previously present ties.  Each component factorizes over its
own support, so its conditional logistic likelihood is exact.  This is not presented as
a general STERGM with endogenous within-component dependence, which can require MCMC.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from scipy.special import logit
from scipy.stats import norm
from temporal_core import (
    TemporalNetwork,
    TemporalValidationError,
    _state_maps,
    _transition_pairs,
    temporal_profile,
)


def separable_design(network: TemporalNetwork) -> dict[str, pd.DataFrame]:
    """Construct formation and persistence supports for every observed transition.

    Formation rows are dyads that are absent at the previous wave.  Persistence rows
    are ties that are present at the previous wave.  Both are additionally restricted
    to dyads observed and admissible at both endpoints of the transition.
    """
    waves, active, edge_sets, risk = _state_maps(network)
    formation_rows: list[dict[str, Any]] = []
    persistence_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []

    for transition_index, (previous, current) in enumerate(
        _transition_pairs(network, waves), start=1
    ):
        joint_risk = sorted(risk[previous] & risk[current])
        if not joint_risk:
            continue
        formation_risk = [pair for pair in joint_risk if pair not in edge_sets[previous]]
        persistence_risk = [pair for pair in joint_risk if pair in edge_sets[previous]]
        formations = sum(pair in edge_sets[current] for pair in formation_risk)
        persistent_ties = sum(pair in edge_sets[current] for pair in persistence_risk)
        dissolutions = len(persistence_risk) - persistent_ties
        n00 = len(formation_risk) - formations
        active_vertices = len(active[previous] & active[current])
        for source, target in formation_risk:
            formation_rows.append(
                {
                    "transition_index": transition_index,
                    "from_wave": previous,
                    "to_wave": current,
                    "source": source,
                    "target": target,
                    "outcome": int((source, target) in edge_sets[current]),
                }
            )
        for source, target in persistence_risk:
            persistence_rows.append(
                {
                    "transition_index": transition_index,
                    "from_wave": previous,
                    "to_wave": current,
                    "source": source,
                    "target": target,
                    "outcome": int((source, target) in edge_sets[current]),
                }
            )
        transition_rows.append(
            {
                "transition_index": transition_index,
                "from_wave": previous,
                "to_wave": current,
                "joint_at_risk_dyads": len(joint_risk),
                "formation_risk_dyads": len(formation_risk),
                "formations_N01": formations,
                "persistent_nonties_N00": n00,
                "persistence_risk_ties": len(persistence_risk),
                "persistent_ties_N11": persistent_ties,
                "dissolutions_N10": dissolutions,
                "formation_rate": formations / len(formation_risk) if formation_risk else np.nan,
                "persistence_rate": persistent_ties / len(persistence_risk)
                if persistence_risk
                else np.nan,
                "dissolution_rate": dissolutions / len(persistence_risk)
                if persistence_risk
                else np.nan,
                "overall_stability": (n00 + persistent_ties) / len(joint_risk),
                "active_vertices": active_vertices,
            }
        )
    if not transition_rows:
        raise TemporalValidationError("No observed transition has any jointly admissible dyad.")
    return {
        "formation": pd.DataFrame(formation_rows),
        "persistence": pd.DataFrame(persistence_rows),
        "transitions": pd.DataFrame(transition_rows),
    }


def _fit_component(rows: pd.DataFrame, component: str) -> dict[str, float | int | str]:
    """Fit the exact intercept-only logistic likelihood for one separable component."""
    if rows.empty:
        raise TemporalValidationError(f"The {component} component has no at-risk dyads.")
    outcomes = rows["outcome"].to_numpy(dtype=float)
    if np.unique(outcomes).size < 2:
        state = "no events" if outcomes.mean() == 0 else "all at-risk dyads have events"
        raise TemporalValidationError(
            f"The {component} component has {state}; its finite intercept-only logit coefficient does not exist."
        )
    probability = float(outcomes.mean())
    estimate = float(logit(probability))
    standard_error = float(np.sqrt(1.0 / (len(outcomes) * probability * (1 - probability))))
    z_value = estimate / standard_error
    return {
        "component": component,
        "term": "edges",
        "estimate": estimate,
        "standard_error": standard_error,
        "z_value": z_value,
        "p_value": float(2 * norm.sf(abs(z_value))),
        "at_risk_dyads": len(outcomes),
        "events": int(outcomes.sum()),
        "event_probability": probability,
    }


def _process_rate_table(
    transitions: pd.DataFrame,
    formation_probability: float,
    persistence_probability: float,
) -> list[dict[str, Any]]:
    """Attach component-specific fitted probabilities to each transition summary."""
    rows: list[dict[str, Any]] = []
    for record in transitions.to_dict(orient="records"):
        rows.append(
            {
                "transition": f"{record['from_wave']} → {record['to_wave']}",
                "formation_risk_dyads": record["formation_risk_dyads"],
                "observed_formations": record["formations_N01"],
                "observed_formation_rate": record["formation_rate"],
                "fitted_formation_probability": formation_probability,
                "persistence_risk_ties": record["persistence_risk_ties"],
                "observed_persistent_ties": record["persistent_ties_N11"],
                "observed_persistence_rate": record["persistence_rate"],
                "fitted_persistence_probability": persistence_probability,
            }
        )
    return rows


def _simulate_transitions(
    transitions: pd.DataFrame,
    *,
    formation_probability: float,
    persistence_probability: float,
    directed: bool,
    simulations: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Run one-step simulations conditional on each observed previous network support."""
    rng = np.random.default_rng(seed + 2202)
    output: list[dict[str, Any]] = []
    for record in transitions.to_dict(orient="records"):
        formation_risk = int(record["formation_risk_dyads"])
        persistence_risk = int(record["persistence_risk_ties"])
        simulated_formations = rng.binomial(formation_risk, formation_probability, simulations)
        simulated_persistent = rng.binomial(persistence_risk, persistence_probability, simulations)
        simulated_dissolutions = persistence_risk - simulated_persistent
        simulated_ties = simulated_formations + simulated_persistent
        joint_risk = int(record["joint_at_risk_dyads"])
        n00 = int(record["persistent_nonties_N00"])
        active_vertices = max(int(record["active_vertices"]), 1)
        simulated_density = simulated_ties / joint_risk
        simulated_stability = (n00 + simulated_persistent) / joint_risk
        multiplier = 1 if directed else 2
        simulated_mean_degree = multiplier * simulated_ties / active_vertices
        observed_ties = int(record["formations_N01"] + record["persistent_ties_N11"])
        output.append(
            {
                "transition_index": int(record["transition_index"]),
                "transition": f"{record['from_wave']} → {record['to_wave']}",
                "joint_at_risk_dyads": joint_risk,
                "observed_formations": int(record["formations_N01"]),
                "observed_dissolutions": int(record["dissolutions_N10"]),
                "observed_persistent_ties": int(record["persistent_ties_N11"]),
                "observed_ties": observed_ties,
                "observed_density": observed_ties / joint_risk,
                "observed_stability": float(record["overall_stability"]),
                "observed_mean_degree": multiplier * observed_ties / active_vertices,
                "simulated_formations_mean": float(simulated_formations.mean()),
                "simulated_formations_lower_025": float(np.quantile(simulated_formations, 0.025)),
                "simulated_formations_upper_975": float(np.quantile(simulated_formations, 0.975)),
                "simulated_dissolutions_mean": float(simulated_dissolutions.mean()),
                "simulated_dissolutions_lower_025": float(np.quantile(simulated_dissolutions, 0.025)),
                "simulated_dissolutions_upper_975": float(np.quantile(simulated_dissolutions, 0.975)),
                "simulated_persistent_ties_mean": float(simulated_persistent.mean()),
                "simulated_persistent_ties_lower_025": float(np.quantile(simulated_persistent, 0.025)),
                "simulated_persistent_ties_upper_975": float(np.quantile(simulated_persistent, 0.975)),
                "simulated_ties_mean": float(simulated_ties.mean()),
                "simulated_ties_lower_025": float(np.quantile(simulated_ties, 0.025)),
                "simulated_ties_upper_975": float(np.quantile(simulated_ties, 0.975)),
                "simulated_density_mean": float(simulated_density.mean()),
                "simulated_density_lower_025": float(np.quantile(simulated_density, 0.025)),
                "simulated_density_upper_975": float(np.quantile(simulated_density, 0.975)),
                "simulated_stability_mean": float(simulated_stability.mean()),
                "simulated_stability_lower_025": float(np.quantile(simulated_stability, 0.025)),
                "simulated_stability_upper_975": float(np.quantile(simulated_stability, 0.975)),
                "simulated_mean_degree_mean": float(simulated_mean_degree.mean()),
                "simulated_mean_degree_lower_025": float(np.quantile(simulated_mean_degree, 0.025)),
                "simulated_mean_degree_upper_975": float(np.quantile(simulated_mean_degree, 0.975)),
            }
        )
    return output


def _tie_spell_audit(network: TemporalNetwork) -> dict[str, Any]:
    """Summarize complete and censored observed tie spells without inventing durations."""
    waves, _, edge_sets, risk = _state_maps(network)
    pairs = _transition_pairs(network, waves)
    complete: list[int] = []
    left_censored = right_censored = support_censored = 0
    open_spells: dict[tuple[str, str], dict[str, Any]] = {}
    last_current: str | None = None

    for previous, current in pairs:
        if previous != last_current:
            for spell in open_spells.values():
                if spell["left_censored"]:
                    left_censored += 1
                else:
                    right_censored += 1
            open_spells.clear()
            for pair in edge_sets[previous]:
                if pair in risk[previous]:
                    open_spells[pair] = {"length": 1, "left_censored": True}
        joint_risk = risk[previous] & risk[current]
        for pair in list(open_spells):
            if pair not in joint_risk:
                support_censored += 1
                del open_spells[pair]
                continue
            if pair in edge_sets[current]:
                open_spells[pair]["length"] += 1
            else:
                if open_spells[pair]["left_censored"]:
                    left_censored += 1
                else:
                    complete.append(int(open_spells[pair]["length"]))
                del open_spells[pair]
        for pair in edge_sets[current]:
            if pair in joint_risk and pair not in edge_sets[previous] and pair not in open_spells:
                open_spells[pair] = {"length": 1, "left_censored": False}
        last_current = current

    for spell in open_spells.values():
        if spell["left_censored"]:
            left_censored += 1
        else:
            right_censored += 1
    counts = Counter(complete)
    return {
        "complete_spell_distribution": [
            {"observed_duration_intervals": duration, "complete_spells": count}
            for duration, count in sorted(counts.items())
        ],
        "complete_spells": len(complete),
        "left_censored_spells": int(left_censored),
        "right_censored_spells": int(right_censored),
        "support_censored_spells": int(support_censored),
    }


def _histogram(values: list[int | str]) -> dict[str, int]:
    """Return JSON-safe category counts for an observed network statistic."""
    return {str(key): int(value) for key, value in Counter(values).items()}


def _finite_geodesic_histogram(graph: nx.Graph | nx.DiGraph, *, directed: bool) -> dict[str, int]:
    """Count finite observed geodesics, respecting ordered paths when directed."""
    index = {node: position for position, node in enumerate(graph.nodes)}
    distances: list[int] = []
    for source, reached in nx.all_pairs_shortest_path_length(graph):
        for target, distance in reached.items():
            if source == target:
                continue
            if directed or index[source] < index[target]:
                distances.append(int(distance))
    return _histogram(distances)


def _undirected_shared_partner_histograms(
    graph: nx.Graph, support: set[tuple[str, str]]
) -> tuple[dict[str, int], dict[str, int]]:
    """Return edgewise and dyadwise shared-partner distributions on observed support."""
    neighbors = {node: set(graph.neighbors(node)) for node in graph.nodes}
    edgewise = [len(neighbors[source] & neighbors[target]) for source, target in graph.edges]
    dyadwise = [
        len(neighbors[source] & neighbors[target])
        for source, target in support
        if not graph.has_edge(source, target)
    ]
    return _histogram(edgewise), _histogram(dyadwise)


def _categorical_group_map(
    network: TemporalNetwork, previous: str, current: str, nodes: list[str]
) -> tuple[str, dict[str, str]] | None:
    """Find one declared, time-stable categorical node attribute for optional mixing GOF."""
    reserved = {"wave", "id", "transition_block"}
    candidates = [column for column in network.nodes.columns if column not in reserved]
    for column in candidates:
        subset = network.nodes.loc[
            network.nodes["wave"].isin([previous, current]), ["wave", "id", column]
        ].dropna()
        if subset.empty:
            continue
        values_by_id = subset.groupby("id")[column].nunique()
        if not set(nodes).issubset(set(values_by_id.index)) or not (values_by_id == 1).all():
            continue
        values = subset.drop_duplicates("id").set_index("id")[column].astype(str).to_dict()
        groups = {str(values[node]) for node in nodes}
        if 1 < len(groups) <= 8:
            return column, {str(node): str(values[node]) for node in nodes}
    return None


def _mixing_matrix(
    edges: set[tuple[str, str]],
    groups: dict[str, str],
    *,
    directed: bool,
) -> dict[str, int]:
    """Count ties by a declared categorical attribute, symmetrizing undirected ties."""
    output: Counter[str] = Counter()
    for source, target in edges:
        if source not in groups or target not in groups:
            continue
        output[f"{groups[source]} → {groups[target]}"] += 1
        if not directed and groups[source] != groups[target]:
            output[f"{groups[target]} → {groups[source]}"] += 1
    return {key: int(value) for key, value in output.items()}


def _structural_histograms(
    edges: set[tuple[str, str]],
    nodes: list[str],
    support: set[tuple[str, str]],
    *,
    directed: bool,
    group_map: dict[str, str] | None,
) -> tuple[dict[str, dict[str, int]], dict[str, float]]:
    """Summarize omitted structural features of a simulated or observed endpoint network."""
    graph: nx.Graph | nx.DiGraph = nx.DiGraph() if directed else nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    distributions: dict[str, dict[str, int]] = {}
    scalars: dict[str, float] = {}
    if directed:
        distributions["in_degree_distribution"] = _histogram(
            [int(value) for _, value in graph.in_degree()]
        )
        distributions["out_degree_distribution"] = _histogram(
            [int(value) for _, value in graph.out_degree()]
        )
        distributions["directed_geodesic_distance_distribution"] = _finite_geodesic_histogram(
            graph, directed=True
        )
        edge_count = graph.number_of_edges()
        scalars["reciprocity_rate"] = (
            sum(graph.has_edge(target, source) for source, target in graph.edges) / edge_count
            if edge_count
            else 0.0
        )
        if len(nodes) <= 30:
            distributions["triad_census"] = {
                str(key): int(value) for key, value in nx.triadic_census(graph).items()
            }
    else:
        distributions["degree_distribution"] = _histogram(
            [int(value) for _, value in graph.degree()]
        )
        distributions["geodesic_distance_distribution"] = _finite_geodesic_histogram(
            graph, directed=False
        )
        edgewise, dyadwise = _undirected_shared_partner_histograms(graph, support)
        distributions["edgewise_shared_partner_distribution"] = edgewise
        distributions["dyadwise_shared_partner_distribution"] = dyadwise
    if group_map is not None:
        distributions["mixing_matrix"] = _mixing_matrix(
            edges, group_map, directed=directed
        )
    return distributions, scalars


def _distribution_envelope(
    observed: dict[str, int], simulated: list[dict[str, int]]
) -> list[dict[str, float | str]]:
    """Compare an observed count distribution to conditional simulation envelopes."""
    categories = sorted(
        set(observed) | set().union(*(set(item) for item in simulated)),
        key=lambda item: (not item.lstrip("-").isdigit(), item),
    )
    rows: list[dict[str, float | str]] = []
    for category in categories:
        values = np.asarray([item.get(category, 0) for item in simulated], dtype=float)
        rows.append(
            {
                "category": category,
                "observed": int(observed.get(category, 0)),
                "simulated_mean": float(values.mean()),
                "simulated_lower_025": float(np.quantile(values, 0.025)),
                "simulated_upper_975": float(np.quantile(values, 0.975)),
            }
        )
    return rows


def _scalar_envelope(observed: float, simulated: list[float]) -> dict[str, float]:
    """Compare one observed scalar statistic to a conditional simulation envelope."""
    values = np.asarray(simulated, dtype=float)
    return {
        "observed": float(observed),
        "simulated_mean": float(values.mean()),
        "simulated_lower_025": float(np.quantile(values, 0.025)),
        "simulated_upper_975": float(np.quantile(values, 0.975)),
    }


def _structural_gof(
    network: TemporalNetwork,
    design: dict[str, pd.DataFrame],
    *,
    formation_probability: float,
    persistence_probability: float,
    simulations: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Audit omitted endpoint structure against one-step baseline simulations."""
    rng = np.random.default_rng(seed + 4404)
    formation = design["formation"]
    persistence = design["persistence"]
    rows: list[dict[str, Any]] = []
    draws = max(20, min(int(simulations), 100))
    for transition in design["transitions"].to_dict(orient="records"):
        index = int(transition["transition_index"])
        previous = str(transition["from_wave"])
        current = str(transition["to_wave"])
        formation_rows = formation.loc[formation["transition_index"] == index]
        persistence_rows = persistence.loc[persistence["transition_index"] == index]
        formation_pairs = list(
            formation_rows[["source", "target"]].itertuples(index=False, name=None)
        )
        persistence_pairs = list(
            persistence_rows[["source", "target"]].itertuples(index=False, name=None)
        )
        support = set(formation_pairs) | set(persistence_pairs)
        nodes = sorted({node for pair in support for node in pair})
        if len(nodes) < 2:
            continue
        observed_edges = {
            pair
            for pair, outcome in zip(
                formation_pairs, formation_rows["outcome"].tolist(), strict=True
            )
            if outcome
        } | {
            pair
            for pair, outcome in zip(
                persistence_pairs, persistence_rows["outcome"].tolist(), strict=True
            )
            if outcome
        }
        group_info = _categorical_group_map(network, previous, current, nodes)
        attribute, group_map = group_info if group_info is not None else (None, None)
        observed_distributions, observed_scalars = _structural_histograms(
            observed_edges,
            nodes,
            support,
            directed=network.directed,
            group_map=group_map,
        )
        simulated_distributions: dict[str, list[dict[str, int]]] = {
            name: [] for name in observed_distributions
        }
        simulated_scalars: dict[str, list[float]] = {name: [] for name in observed_scalars}
        for _ in range(draws):
            simulated_edges = {
                pair for pair in formation_pairs if rng.random() < formation_probability
            } | {
                pair for pair in persistence_pairs if rng.random() < persistence_probability
            }
            distributions, scalars = _structural_histograms(
                simulated_edges,
                nodes,
                support,
                directed=network.directed,
                group_map=group_map,
            )
            for name, output in simulated_distributions.items():
                output.append(distributions.get(name, {}))
            for name, output in simulated_scalars.items():
                output.append(float(scalars.get(name, 0.0)))
        rows.append(
            {
                "transition": f"{previous} → {current}",
                "attribute": attribute,
                "distribution_metrics": {
                    name: _distribution_envelope(observed, simulated_distributions[name])
                    for name, observed in observed_distributions.items()
                },
                "scalar_metrics": {
                    name: _scalar_envelope(observed, simulated_scalars[name])
                    for name, observed in observed_scalars.items()
                },
                "notes": (
                    "Triad census is withheld above 30 active support vertices to avoid a misleadingly slow live calculation. "
                    "Mixing is unavailable unless the node table declares a time-stable categorical attribute."
                    if network.directed
                    else "Mixing is unavailable unless the node table declares a time-stable categorical attribute."
                ),
            }
        )
    return rows


def _bootstrap_components(
    formation: pd.DataFrame,
    persistence: pd.DataFrame,
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Resample whole transitions to give a clearly limited temporal sensitivity interval."""
    identifiers = sorted(set(formation["transition_index"]) | set(persistence["transition_index"]))
    if replicates <= 0:
        return {"status": "not_run", "reason": "The user selected zero whole-transition resamples."}
    if len(identifiers) < 5:
        return {
            "status": "not_run",
            "reason": "Fewer than five observed transitions are available; whole-transition resampling is withheld.",
        }
    rng = np.random.default_rng(seed + 3303)
    estimates: list[dict[str, float]] = []
    for _ in range(replicates):
        sampled = rng.choice(identifiers, size=len(identifiers), replace=True)
        sampled_formation = pd.concat(
            [formation.loc[formation["transition_index"] == identifier] for identifier in sampled],
            ignore_index=True,
        )
        sampled_persistence = pd.concat(
            [persistence.loc[persistence["transition_index"] == identifier] for identifier in sampled],
            ignore_index=True,
        )
        if sampled_formation["outcome"].nunique() < 2 or sampled_persistence["outcome"].nunique() < 2:
            continue
        estimates.append(
            {
                "formation_edges": float(logit(sampled_formation["outcome"].mean())),
                "persistence_edges": float(logit(sampled_persistence["outcome"].mean())),
            }
        )
    if len(estimates) < max(10, replicates // 2):
        return {
            "status": "unstable",
            "reason": "Too many resamples had a component with no outcome variation for a stable interval.",
            "successful_resamples": len(estimates),
        }
    table = pd.DataFrame(estimates)
    return {
        "status": "ok",
        "successful_resamples": len(table),
        "intervals": [
            {
                "component": name,
                "lower_025": float(table[name].quantile(0.025)),
                "median": float(table[name].median()),
                "upper_975": float(table[name].quantile(0.975)),
            }
            for name in ("formation_edges", "persistence_edges")
        ],
    }


def fit_separable_stergm(
    network: TemporalNetwork,
    *,
    seed: int = 20261029,
    bootstrap_replicates: int = 100,
    predictive_simulations: int = 100,
) -> dict[str, Any]:
    """Fit the transparent baseline formation–persistence STERGM and audit it."""
    profile = temporal_profile(network)
    design = separable_design(network)
    formation_fit = _fit_component(design["formation"], "formation")
    persistence_fit = _fit_component(design["persistence"], "persistence")
    formation_probability = float(formation_fit["event_probability"])
    persistence_probability = float(persistence_fit["event_probability"])
    expected_duration = float(1.0 / (1.0 - persistence_probability))
    flags: list[str] = []
    if profile["observed_transitions"] < 5:
        flags.append(
            "Fewer than five observed transitions are available. At-risk dyads provide information for the stated dyad-independent components, but temporal heterogeneity and transition-block uncertainty are limited."
        )
    if expected_duration > 10:
        flags.append(
            "The baseline persistence estimate implies a long geometric expected duration; inspect censoring and whether a homogeneous memoryless persistence process is plausible."
        )
    duration = _tie_spell_audit(network)
    if duration["left_censored_spells"] or duration["right_censored_spells"] or duration["support_censored_spells"]:
        flags.append(
            "Observed tie-spell summaries contain left-, right-, or support-censored spells and are displayed descriptively rather than as complete lifetimes."
        )
    simulations = _simulate_transitions(
        design["transitions"],
        formation_probability=formation_probability,
        persistence_probability=persistence_probability,
        directed=network.directed,
        simulations=max(20, min(int(predictive_simulations), 500)),
        seed=int(seed),
    )
    structural_gof = _structural_gof(
        network,
        design,
        formation_probability=formation_probability,
        persistence_probability=persistence_probability,
        simulations=max(20, min(int(predictive_simulations), 100)),
        seed=int(seed),
    )
    bootstrap = _bootstrap_components(
        design["formation"],
        design["persistence"],
        replicates=int(bootstrap_replicates),
        seed=int(seed),
    )
    return {
        "status": "ok",
        "model_class": "Baseline dyad-independent STERGM with exact component likelihoods",
        "formation_formula": "logit Pr(Y⁺_ij = 1 | Y^{t-1}_{ij} = 0, D_{t-1,t}) = θ⁺_edges",
        "persistence_formula": "logit Pr(Y⁻_ij = 1 | Y^{t-1}_{ij} = 1, D_{t-1,t}) = θ⁻_edges",
        "directed": network.directed,
        "observed_waves": profile["observed_waves"],
        "observed_transitions": profile["observed_transitions"],
        "formation": formation_fit,
        "persistence": persistence_fit,
        "expected_duration_intervals": expected_duration,
        "transition_support": design["transitions"].to_dict(orient="records"),
        "process_rate_audit": _process_rate_table(
            design["transitions"], formation_probability, persistence_probability
        ),
        "one_step_simulations": simulations,
        "structural_gof": structural_gof,
        "duration_audit": duration,
        "bootstrap": bootstrap,
        "diagnostic_flags": flags,
        "interpretation_note": (
            "The formation and persistence components are estimated separately on their respective risk sets. "
            "The two intercepts are not coefficients from one ordinary logistic regression, and they do not imply a general STERGM with endogenous formation or persistence dependence."
        ),
    }
