"""Data validation and exact lag-only TERGM computations for Session 2.1.

The implemented model is the first-order, dyad-independent conditional subclass of a
TERGM.  All predictors are functions of the preceding observed network (and, where
provided, pre-transition support).  Therefore the conditional likelihood factorizes
across admissible dyads and the logistic likelihood fitted here is exact for this
restricted transition model; it is not presented as a replacement for MCMC estimation
of TERGMs containing contemporaneous structural dependence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import norm

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "public"
CATALOG_PATH = PROJECT_DIR / "data" / "session2_1_dataset_catalog.json"


class TemporalValidationError(ValueError):
    """Raised when temporal network data violate the Session 2.1 contract."""


@dataclass(frozen=True)
class TemporalNetworkSpec:
    """Versioned public temporal-network metadata and local file names."""

    identifier: str
    name: str
    source: str
    source_url: str
    citation: str
    network_type: str
    directed: bool
    response_scope: str
    method_status: str
    support_note: str
    interpretation_limit: str
    rationale: str
    nodes_file: str
    edges_file: str
    risk_file: str | None


@dataclass(frozen=True)
class TemporalNetwork:
    """A validated repeated binary network and an optional wave-specific risk set."""

    nodes: pd.DataFrame
    edges: pd.DataFrame
    risk: pd.DataFrame | None
    directed: bool
    label: str


def _ordered_waves(values: Iterable[Any]) -> list[str]:
    """Sort numeric wave labels numerically and otherwise use natural lexical order."""
    labels = [str(value) for value in values]
    unique = list(dict.fromkeys(labels))
    numeric = pd.to_numeric(pd.Series(unique), errors="coerce")
    if numeric.notna().all():
        return [item for _, item in sorted(zip(numeric.tolist(), unique, strict=True))]

    def natural_key(value: str) -> list[Any]:
        return [int(piece) if piece.isdigit() else piece.lower() for piece in re.split(r"(\d+)", value)]

    return sorted(unique, key=natural_key)


def _canonical_pair(source: str, target: str, directed: bool) -> tuple[str, str]:
    return (source, target) if directed or source < target else (target, source)


def _pairs_for_nodes(node_ids: list[str], directed: bool) -> set[tuple[str, str]]:
    if directed:
        return {(source, target) for source in node_ids for target in node_ids if source != target}
    return {
        (source, target)
        for index, source in enumerate(node_ids)
        for target in node_ids[index + 1 :]
    }


def load_temporal_catalog() -> dict[str, TemporalNetworkSpec]:
    """Load the Session 2.1 catalog without mixing it into static-network examples."""
    raw = json.loads(CATALOG_PATH.read_text())
    examples: dict[str, TemporalNetworkSpec] = {}
    for item in raw["examples"]:
        examples[item["id"]] = TemporalNetworkSpec(
            identifier=item["id"],
            name=item["name"],
            source=item["source"],
            source_url=item["source_url"],
            citation=item["citation"],
            network_type=item["network_type"],
            directed=bool(item["directed"]),
            response_scope=item["response_scope"],
            method_status=item["method_status"],
            support_note=item["support_note"],
            interpretation_limit=item["interpretation_limit"],
            rationale=item["rationale"],
            nodes_file=item["nodes_file"],
            edges_file=item["edges_file"],
            risk_file=item.get("risk_file") or None,
        )
    return examples


def rejected_temporal_candidate() -> dict[str, str]:
    """Return documented public data deliberately excluded from the binary TERGM workflows."""
    raw = json.loads(CATALOG_PATH.read_text())
    return dict(raw["rejected_candidate"])


def load_temporal_example(spec: TemporalNetworkSpec) -> TemporalNetwork:
    """Read and validate a catalogued public temporal network."""
    nodes = pd.read_csv(DATA_DIR / spec.nodes_file, dtype={"wave": str, "id": str})
    edges = pd.read_csv(
        DATA_DIR / spec.edges_file,
        dtype={"wave": str, "source": str, "target": str},
    )
    risk = None
    if spec.risk_file:
        risk = pd.read_csv(
            DATA_DIR / spec.risk_file,
            dtype={"wave": str, "source": str, "target": str},
        )
    validate_temporal_network(nodes, edges, directed=spec.directed, risk=risk)
    return TemporalNetwork(nodes=nodes, edges=edges, risk=risk, directed=spec.directed, label=spec.name)


def validate_temporal_network(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    risk: pd.DataFrame | None = None,
) -> None:
    """Validate repeated binary edge lists, active actors, and optional observed dyads.

    `nodes` defines actors present at each observed wave. `risk`, when supplied,
    lists the dyads observed at that wave and is necessary whenever mere presence
    does not imply that all within-wave dyads were observed (for example, incidental
    missingness in a sociometric matrix). A transition uses dyads observable at both
    its prior and current waves.
    """
    if not {"wave", "id"}.issubset(nodes.columns):
        raise TemporalValidationError("The node-presence table needs `wave` and `id` columns.")
    if not {"wave", "source", "target"}.issubset(edges.columns):
        raise TemporalValidationError("The temporal edge table needs `wave`, `source`, and `target` columns.")
    if nodes.empty:
        raise TemporalValidationError("The node-presence table cannot be empty.")
    if edges.empty:
        raise TemporalValidationError("The temporal edge table cannot be empty.")

    clean_nodes = nodes[["wave", "id"]].astype(str)
    if clean_nodes.isna().any().any() or (clean_nodes.apply(lambda column: column.str.strip() == "")).any().any():
        raise TemporalValidationError("Wave labels and node identifiers must be non-empty.")
    if clean_nodes.duplicated().any():
        raise TemporalValidationError("A node may appear at most once in a given wave.")
    waves = _ordered_waves(clean_nodes["wave"])
    if len(waves) < 2:
        raise TemporalValidationError("At least two observed waves are required for a transition model.")

    clean_edges = edges[["wave", "source", "target"]].astype(str)
    if clean_edges.isna().any().any() or (clean_edges.apply(lambda column: column.str.strip() == "")).any().any():
        raise TemporalValidationError("Every temporal edge requires non-empty wave, source, and target values.")
    if set(clean_edges["wave"]) - set(waves):
        raise TemporalValidationError("Every edge wave must occur in the node-presence table.")
    if (clean_edges["source"] == clean_edges["target"]).any():
        raise TemporalValidationError("Session 2.1 accepts loopless networks only.")

    active_by_wave = {
        wave: set(clean_nodes.loc[clean_nodes["wave"] == wave, "id"])
        for wave in waves
    }
    pair_rows: list[tuple[str, str, str]] = []
    for wave, source, target in clean_edges.itertuples(index=False, name=None):
        if source not in active_by_wave[wave] or target not in active_by_wave[wave]:
            raise TemporalValidationError("Every edge endpoint must be present at the edge's wave.")
        a, b = _canonical_pair(source, target, directed)
        pair_rows.append((wave, a, b))
    if pd.Series(pair_rows).duplicated().any():
        raise TemporalValidationError("The temporal edge table has duplicate dyads within a wave.")

    if risk is None:
        return
    if not {"wave", "source", "target"}.issubset(risk.columns):
        raise TemporalValidationError("The optional at-risk-dyad table needs `wave`, `source`, and `target` columns.")
    clean_risk = risk[["wave", "source", "target"]].astype(str)
    if clean_risk.empty:
        raise TemporalValidationError("The at-risk-dyad table cannot be empty when supplied.")
    if set(clean_risk["wave"]) - set(waves):
        raise TemporalValidationError("Every at-risk dyad wave must occur in the node-presence table.")
    risk_pairs: set[tuple[str, str, str]] = set()
    for wave, source, target in clean_risk.itertuples(index=False, name=None):
        if source == target:
            raise TemporalValidationError("At-risk dyads cannot be self-dyads.")
        if source not in active_by_wave[wave] or target not in active_by_wave[wave]:
            raise TemporalValidationError("At-risk dyad endpoints must be present at that wave.")
        a, b = _canonical_pair(source, target, directed)
        key = (wave, a, b)
        if key in risk_pairs:
            raise TemporalValidationError("The at-risk-dyad table has duplicate dyads within a wave.")
        risk_pairs.add(key)
    if not set(pair_rows).issubset(risk_pairs):
        raise TemporalValidationError("Every observed edge must occur in the at-risk-dyad table for its wave.")


def _state_maps(network: TemporalNetwork) -> tuple[list[str], dict[str, set[str]], dict[str, set[tuple[str, str]]], dict[str, set[tuple[str, str]]]]:
    nodes = network.nodes[["wave", "id"]].astype(str)
    edges = network.edges[["wave", "source", "target"]].astype(str)
    waves = _ordered_waves(nodes["wave"])
    active = {wave: set(nodes.loc[nodes["wave"] == wave, "id"]) for wave in waves}
    edge_sets = {
        wave: {
            _canonical_pair(source, target, network.directed)
            for _, source, target in edges.loc[edges["wave"] == wave].itertuples(
                index=False, name=None
            )
        }
        for wave in waves
    }
    if network.risk is None:
        risk = {wave: _pairs_for_nodes(sorted(active[wave]), network.directed) for wave in waves}
    else:
        table = network.risk[["wave", "source", "target"]].astype(str)
        risk = {
            wave: {
                _canonical_pair(source, target, network.directed)
                for _, source, target in table.loc[table["wave"] == wave].itertuples(
                    index=False, name=None
                )
            }
            for wave in waves
        }
    return waves, active, edge_sets, risk


def _transition_pairs(network: TemporalNetwork, waves: list[str]) -> list[tuple[str, str]]:
    """Return adjacent observed-wave pairs that represent one documented interval.

    A `transition_block` column is optional. It explicitly records a break caused by a
    missing/unobserved panel, so the interface never treats the next retained wave as
    a one-step transition across that gap.
    """
    adjacent = list(pairwise(waves))
    if "transition_block" not in network.nodes.columns:
        return adjacent
    blocks = network.nodes[["wave", "transition_block"]].astype(str).drop_duplicates()
    if blocks.duplicated("wave").any():
        raise TemporalValidationError("Every observed wave must have one transition-block label.")
    block_by_wave = dict(blocks.itertuples(index=False, name=None))
    return [
        (previous, current)
        for previous, current in adjacent
        if block_by_wave.get(previous) == block_by_wave.get(current)
    ]


def temporal_profile(network: TemporalNetwork) -> dict[str, Any]:
    """Return wave and transition counts before fitting any temporal model."""
    waves, active, edge_sets, risk = _state_maps(network)
    wave_rows: list[dict[str, Any]] = []
    for wave in waves:
        dyads = risk[wave]
        observed = edge_sets[wave]
        wave_rows.append(
            {
                "wave": wave,
                "active_vertices": len(active[wave]),
                "at_risk_dyads": len(dyads),
                "observed_ties": len(observed),
                "density": len(observed) / len(dyads) if dyads else np.nan,
            }
        )
    transition_rows: list[dict[str, Any]] = []
    for previous, current in _transition_pairs(network, waves):
        joint_risk = risk[previous] & risk[current]
        n00 = n01 = n10 = n11 = 0
        for pair in joint_risk:
            prior = pair in edge_sets[previous]
            outcome = pair in edge_sets[current]
            if not prior and not outcome:
                n00 += 1
            elif not prior and outcome:
                n01 += 1
            elif prior and not outcome:
                n10 += 1
            else:
                n11 += 1
        non_ties = n00 + n01
        prior_ties = n10 + n11
        transition_rows.append(
            {
                "from_wave": previous,
                "to_wave": current,
                "joint_at_risk_dyads": len(joint_risk),
                "persistent_nonties_N00": n00,
                "formations_N01": n01,
                "dissolutions_N10": n10,
                "persistent_ties_N11": n11,
                "overall_stability": (n00 + n11) / len(joint_risk) if joint_risk else np.nan,
                "tie_persistence": n11 / prior_ties if prior_ties else np.nan,
                "formation_rate": n01 / non_ties if non_ties else np.nan,
                "dissolution_rate": n10 / prior_ties if prior_ties else np.nan,
            }
        )
    return {
        "waves": waves,
        "wave_table": pd.DataFrame(wave_rows),
        "transition_table": pd.DataFrame(transition_rows),
        "observed_waves": len(waves),
        "observed_intervals": len(transition_rows),
        "observed_transitions": sum(
            item["joint_at_risk_dyads"] > 0 for item in transition_rows
        ),
    }


def transition_design(network: TemporalNetwork) -> pd.DataFrame:
    """Build exact sufficient-statistic covariates for first-order lagged TERGMs."""
    waves, active, edge_sets, risk = _state_maps(network)
    rows: list[pd.DataFrame] = []
    for transition_index, (previous, current) in enumerate(
        _transition_pairs(network, waves), start=1
    ):
        joint_risk = sorted(risk[previous] & risk[current])
        if not joint_risk:
            continue
        common_nodes = sorted(active[previous] & active[current])
        node_index = {node: index for index, node in enumerate(common_nodes)}
        prior_matrix = np.zeros((len(common_nodes), len(common_nodes)), dtype=np.int8)
        for source, target in edge_sets[previous]:
            if source in node_index and target in node_index:
                i, j = node_index[source], node_index[target]
                prior_matrix[i, j] = 1
                if not network.directed:
                    prior_matrix[j, i] = 1
        twopath = prior_matrix @ prior_matrix
        source_values = [pair[0] for pair in joint_risk]
        target_values = [pair[1] for pair in joint_risk]
        previous_tie = np.asarray([int(pair in edge_sets[previous]) for pair in joint_risk], dtype=int)
        outcome = np.asarray([int(pair in edge_sets[current]) for pair in joint_risk], dtype=int)
        if network.directed:
            delayed_reciprocity = np.asarray(
                [prior_matrix[node_index[target], node_index[source]] for source, target in joint_risk],
                dtype=int,
            )
        else:
            delayed_reciprocity = np.zeros(len(joint_risk), dtype=int)
        lagged_twopath = np.asarray(
            [twopath[node_index[source], node_index[target]] for source, target in joint_risk],
            dtype=int,
        )
        rows.append(
            pd.DataFrame(
                {
                    "transition_index": transition_index,
                    "from_wave": previous,
                    "to_wave": current,
                    "source": source_values,
                    "target": target_values,
                    "outcome": outcome,
                    "memory": previous_tie,
                    "delrecip": delayed_reciprocity,
                    "lagged_twopath": lagged_twopath,
                }
            )
        )
    if not rows:
        raise TemporalValidationError("No transition has any dyad observed at both adjacent waves.")
    return pd.concat(rows, ignore_index=True)


def _design_matrix(design: pd.DataFrame, terms: tuple[str, ...], directed: bool) -> tuple[np.ndarray, list[str], list[str]]:
    allowed = {"edges", "memory", "delrecip", "lagged_twopath"}
    if not terms or "edges" not in terms:
        raise TemporalValidationError("A Session 2.1 lagged TERGM must include the `edges` baseline term.")
    if len(set(terms)) != len(terms) or not set(terms).issubset(allowed):
        raise TemporalValidationError("The requested transition model contains unsupported or duplicated terms.")
    if "delrecip" in terms and not directed:
        raise TemporalValidationError("Delayed reciprocity requires a directed temporal network.")

    columns: list[np.ndarray] = []
    names: list[str] = []
    dropped: list[str] = []
    for term in terms:
        values = np.ones(len(design), dtype=float) if term == "edges" else design[term].to_numpy(dtype=float)
        if term != "edges" and np.nanstd(values) == 0:
            dropped.append(term)
            continue
        columns.append(values)
        names.append(term)
    if len(columns) == 1 and names[0] == "edges" and np.unique(design["outcome"]).size < 2:
        raise TemporalValidationError("The transition outcome is constant on the available risk set; a probability model cannot be fitted.")
    return np.column_stack(columns), names, dropped


def _fit_logistic(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool, str, float]:
    """Fit the exact conditional logistic likelihood for lag-only TERGM statistics."""
    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        linear = x @ beta
        negative_log_likelihood = float(np.sum(np.logaddexp(0.0, linear) - y * linear))
        gradient = x.T @ (expit(linear) - y)
        return negative_log_likelihood, gradient

    fitted = minimize(
        fun=lambda beta: objective(beta)[0],
        x0=np.zeros(x.shape[1], dtype=float),
        jac=lambda beta: objective(beta)[1],
        method="L-BFGS-B",
        options={"maxiter": 1000, "gtol": 1e-9, "ftol": 1e-12, "maxls": 100},
    )
    beta = np.asarray(fitted.x, dtype=float)
    probabilities = expit(x @ beta)
    weights = np.clip(probabilities * (1.0 - probabilities), 1e-12, None)
    information = x.T @ (x * weights[:, None])
    covariance = np.linalg.pinv(information, hermitian=True)
    return beta, covariance, bool(fitted.success), str(fitted.message), float(fitted.fun)


def _coefficient_rows(beta: np.ndarray, covariance: np.ndarray, names: list[str]) -> list[dict[str, Any]]:
    standard_errors = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
    rows: list[dict[str, Any]] = []
    for name, estimate, standard_error in zip(names, beta, standard_errors, strict=True):
        z_value = estimate / standard_error if standard_error > 0 else np.nan
        p_value = float(2 * norm.sf(abs(z_value))) if np.isfinite(z_value) else np.nan
        rows.append(
            {
                "term": name,
                "estimate": float(estimate),
                "standard_error": float(standard_error),
                "z_value": float(z_value) if np.isfinite(z_value) else None,
                "p_value": p_value if np.isfinite(p_value) else None,
            }
        )
    return rows


def _bootstrap(
    design: pd.DataFrame,
    terms: tuple[str, ...],
    directed: bool,
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Resample whole transitions, never individual dyads, for a limited uncertainty check."""
    transition_ids = design["transition_index"].unique()
    if len(transition_ids) < 8 or replicates <= 0:
        return {
            "status": "not_run",
            "reason": "Transition-block bootstrap is withheld because fewer than eight observed transitions are available; model-based standard errors are reported with a temporal-replication warning.",
            "replicates_requested": int(replicates),
            "replicates_completed": 0,
            "intervals": [],
        }
    x, names, dropped = _design_matrix(design, terms, directed)
    if dropped:
        return {
            "status": "not_run",
            "reason": "At least one requested term was constant on the observed transition design.",
            "replicates_requested": int(replicates),
            "replicates_completed": 0,
            "intervals": [],
        }
    rng = np.random.default_rng(seed)
    results: list[np.ndarray] = []
    index_by_transition = {
        identifier: np.flatnonzero(design["transition_index"].to_numpy() == identifier)
        for identifier in transition_ids
    }
    for _ in range(int(replicates)):
        sample_ids = rng.choice(transition_ids, size=len(transition_ids), replace=True)
        rows = np.concatenate([index_by_transition[identifier] for identifier in sample_ids])
        try:
            beta, _, succeeded, _, _ = _fit_logistic(x[rows], design["outcome"].to_numpy(dtype=float)[rows])
            if succeeded and np.isfinite(beta).all() and np.max(np.abs(beta)) < 30:
                results.append(beta)
        except (FloatingPointError, ValueError, np.linalg.LinAlgError):
            continue
    if len(results) < max(10, int(replicates * 0.5)):
        return {
            "status": "unstable",
            "reason": "Too few transition-block bootstrap resamples yielded stable estimates; inspect coefficient magnitude and the limited transition count.",
            "replicates_requested": int(replicates),
            "replicates_completed": len(results),
            "intervals": [],
        }
    sampled = np.vstack(results)
    intervals = [
        {
            "term": term,
            "lower_025": float(np.quantile(sampled[:, index], 0.025)),
            "median": float(np.quantile(sampled[:, index], 0.5)),
            "upper_975": float(np.quantile(sampled[:, index], 0.975)),
        }
        for index, term in enumerate(names)
    ]
    return {
        "status": "ok",
        "reason": "Whole observed transitions were resampled; this is a limited block bootstrap, not dyad-independent resampling.",
        "replicates_requested": int(replicates),
        "replicates_completed": len(results),
        "intervals": intervals,
    }


def _posterior_predictive(
    design: pd.DataFrame,
    x: np.ndarray,
    beta: np.ndarray,
    *,
    simulations: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Simulate one-step outcomes conditional on every observed prior network state."""
    rng = np.random.default_rng(seed + 7001)
    probabilities = expit(x @ beta)
    output: list[dict[str, Any]] = []
    for identifier, group in design.groupby("transition_index", sort=True):
        row_indices = group.index.to_numpy(dtype=int)
        group_probabilities = probabilities[row_indices]
        y_observed = group["outcome"].to_numpy(dtype=int)
        previous = group["memory"].to_numpy(dtype=int)
        draws = rng.binomial(1, group_probabilities, size=(int(simulations), len(group)))
        observed_ties = int(y_observed.sum())
        simulated_ties = draws.sum(axis=1)
        absent = previous == 0
        prior_ties = previous == 1
        observed_formations = int(((y_observed == 1) & absent).sum())
        simulated_formations = ((draws == 1) & absent).sum(axis=1)
        observed_persistence = float(y_observed[prior_ties].mean()) if prior_ties.any() else np.nan
        simulated_persistence = draws[:, prior_ties].mean(axis=1) if prior_ties.any() else np.full(int(simulations), np.nan)
        output.append(
            {
                "transition": f"{group['from_wave'].iloc[0]} → {group['to_wave'].iloc[0]}",
                "observed_ties": observed_ties,
                "simulated_ties_mean": float(simulated_ties.mean()),
                "simulated_ties_lower_025": float(np.quantile(simulated_ties, 0.025)),
                "simulated_ties_upper_975": float(np.quantile(simulated_ties, 0.975)),
                "observed_formations": observed_formations,
                "simulated_formations_mean": float(simulated_formations.mean()),
                "simulated_formations_lower_025": float(np.quantile(simulated_formations, 0.025)),
                "simulated_formations_upper_975": float(np.quantile(simulated_formations, 0.975)),
                "observed_tie_persistence": observed_persistence if np.isfinite(observed_persistence) else None,
                "simulated_tie_persistence_mean": float(np.nanmean(simulated_persistence)) if np.isfinite(simulated_persistence).any() else None,
                "simulated_tie_persistence_lower_025": float(np.nanquantile(simulated_persistence, 0.025)) if np.isfinite(simulated_persistence).any() else None,
                "simulated_tie_persistence_upper_975": float(np.nanquantile(simulated_persistence, 0.975)) if np.isfinite(simulated_persistence).any() else None,
            }
        )
    return output


def fit_lagged_tergm(
    network: TemporalNetwork,
    *,
    terms: tuple[str, ...],
    seed: int = 20261029,
    bootstrap_replicates: int = 100,
    predictive_simulations: int = 100,
) -> dict[str, Any]:
    """Fit a first-order lag-only TERGM and return transparent computation records."""
    profile = temporal_profile(network)
    design = transition_design(network)
    x, names, dropped = _design_matrix(design, terms, network.directed)
    y = design["outcome"].to_numpy(dtype=float)
    if np.unique(y).size < 2:
        raise TemporalValidationError("The current-wave outcome has no observed variation on the usable transition risk set.")
    beta, covariance, converged, optimizer_message, negative_log_likelihood = _fit_logistic(x, y)
    probabilities = expit(x @ beta)
    diagnostic_flags: list[str] = []
    if dropped:
        diagnostic_flags.append("Dropped constant requested terms: " + ", ".join(dropped) + ".")
    if not converged:
        diagnostic_flags.append("The likelihood optimizer did not report convergence: " + optimizer_message)
    if np.max(np.abs(beta)) > 12:
        diagnostic_flags.append("At least one coefficient exceeds absolute value 12; inspect possible separation or sparse transition cells.")
    if probabilities.min() < 1e-6 or probabilities.max() > 1 - 1e-6:
        diagnostic_flags.append("Some fitted conditional probabilities are numerically near 0 or 1; inspect sparse cells and separation.")
    information = x.T @ (x * np.clip(probabilities * (1 - probabilities), 1e-12, None)[:, None])
    condition_number = float(np.linalg.cond(information)) if information.size else np.nan
    if np.isfinite(condition_number) and condition_number > 1e8:
        diagnostic_flags.append("The observed-information matrix is ill-conditioned; requested transition effects may be weakly identified.")
    if profile["observed_transitions"] < 5:
        diagnostic_flags.append("Fewer than five observed transitions are available; temporal replication is very limited and model-based standard errors require strong caution.")

    bootstrap = _bootstrap(
        design,
        terms,
        network.directed,
        replicates=int(bootstrap_replicates),
        seed=int(seed) + 401,
    )
    predictive = _posterior_predictive(
        design,
        x,
        beta,
        simulations=max(20, min(int(predictive_simulations), 500)),
        seed=int(seed),
    )
    return {
        "status": "ok",
        "model_class": "First-order lag-only TERGM with exact conditional dyadic likelihood",
        "formula": "logit Pr(Y_ij^t = 1 | Y^{t-1}, D_t) = " + " + ".join(names),
        "requested_terms": list(terms),
        "estimated_terms": names,
        "dropped_terms": dropped,
        "directed": network.directed,
        "observed_waves": profile["observed_waves"],
        "observed_transitions": profile["observed_transitions"],
        "dyad_observations": len(design),
        "coefficients": _coefficient_rows(beta, covariance, names),
        "log_likelihood": float(-negative_log_likelihood),
        "aic": float(2 * negative_log_likelihood + 2 * len(beta)),
        "optimizer": {"converged": converged, "message": optimizer_message, "information_condition_number": condition_number},
        "diagnostic_flags": diagnostic_flags,
        "wave_profile": profile["wave_table"].to_dict(orient="records"),
        "transition_counts": profile["transition_table"].to_dict(orient="records"),
        "bootstrap": bootstrap,
        "posterior_predictive": predictive,
        "interpretation_note": (
            "This computation estimates a first-order TERGM whose included statistics depend only on the preceding observed network. "
            "Because no contemporaneous structural term is included, its conditional likelihood factorizes over at-risk dyads. "
            "It does not identify microstep timing, causal effects, or distinct formation and dissolution mechanisms; Session 2.2 treats separable transition components."
        ),
    }
