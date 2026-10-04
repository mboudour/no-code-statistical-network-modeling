"""Balanced-panel preparation and transparent payloads for the Day 3 SAOM sessions.

The RSiena computation itself runs in ``r/fit_saom.R`` inside the Docker image.  This
module performs only data-boundary work: it validates a repeated binary network,
keeps an explicitly balanced actor panel, and requires complete selected behavior values.
For documented public coevolution workflows it transparently reports any further
complete-behavior case restriction; BYOD uploads with missing behavior are refused.
It never replaces absence, structural unavailability, or a missing behavior with zero.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "public"
CATALOG_PATH = PROJECT_DIR / "data" / "day3_saom_catalog.json"


class SAOMValidationError(ValueError):
    """Raised when a panel cannot support the stated SAOM calculation."""


@dataclass(frozen=True)
class SAOMPanelSpec:
    identifier: str
    name: str
    nodes_file: str
    edges_file: str
    behavior_file: str | None
    directed: bool
    source: str
    source_url: str
    network_type: str
    support_rule: str
    limit: str


@dataclass(frozen=True)
class SAOMPanel:
    spec: SAOMPanelSpec
    actors: tuple[str, ...]
    waves: tuple[str, ...]
    nodes: pd.DataFrame
    edges: pd.DataFrame
    behavior: pd.DataFrame | None
    behavior_name: str | None
    excluded_for_incomplete_behavior: int = 0


def _ordered_waves(values: pd.Series | list[str]) -> list[str]:
    labels = [str(value) for value in values]
    unique = list(dict.fromkeys(labels))
    numbers = pd.to_numeric(pd.Series(unique), errors="coerce")
    if numbers.notna().all():
        return [item for _, item in sorted(zip(numbers.tolist(), unique, strict=True))]

    def natural_key(value: str) -> list[Any]:
        return [
            int(piece) if piece.isdigit() else piece.lower()
            for piece in re.split(r"(\d+)", value)
        ]

    return sorted(unique, key=natural_key)


def catalog() -> dict[str, Any]:
    """Return the versioned public-data catalog."""
    return json.loads(CATALOG_PATH.read_text())


def panel_specs() -> dict[str, SAOMPanelSpec]:
    """Read reusable Day 3 base panels from the source catalog."""
    return {
        item["id"]: SAOMPanelSpec(
            identifier=item["id"],
            name=item["name"],
            nodes_file=item["nodes_file"],
            edges_file=item["edges_file"],
            behavior_file=item.get("behavior_file"),
            directed=bool(item["directed"]),
            source=item["source"],
            source_url=item["source_url"],
            network_type=item["network_type"],
            support_rule=item["support_rule"],
            limit=item["limit"],
        )
        for item in catalog()["base_panels"]
    }


def workflows(session: str) -> list[dict[str, Any]]:
    """Return one of the explicitly curated five-workflow lists."""
    key = {"3.1": "session31_workflows", "3.2": "session32_workflows"}.get(session)
    if key is None:
        raise SAOMValidationError("Session must be `3.1` or `3.2`.")
    return list(catalog()[key])


def _clean_nodes(nodes: pd.DataFrame) -> pd.DataFrame:
    required = {"wave", "id"}
    if not required.issubset(nodes.columns):
        raise SAOMValidationError("Nodes must include `wave` and `id`.")
    result = nodes[["wave", "id"]].copy().astype(str)
    if (
        result.apply(lambda c: c.str.strip().eq("")).any().any()
        or result.duplicated().any()
    ):
        raise SAOMValidationError(
            "Each non-empty actor identifier may occur at most once per wave."
        )
    if result["wave"].nunique() < 2:
        raise SAOMValidationError(
            "An actor-oriented model requires at least two observed network waves."
        )
    return result


def _clean_edges(
    edges: pd.DataFrame, nodes: pd.DataFrame, *, directed: bool
) -> pd.DataFrame:
    required = {"wave", "source", "target"}
    if not required.issubset(edges.columns):
        raise SAOMValidationError("Edges must include `wave`, `source`, and `target`.")
    result = edges[["wave", "source", "target"]].copy().astype(str)
    if result.apply(lambda c: c.str.strip().eq("")).any().any():
        raise SAOMValidationError("Every edge field must be non-empty.")
    if (result["source"] == result["target"]).any():
        raise SAOMValidationError(
            "Loops are not accepted in the Day 3 binary SAOM workflow."
        )
    available = {
        (wave, actor) for wave, actor in nodes.itertuples(index=False, name=None)
    }
    if any(
        (wave, actor) not in available
        for wave, actor in result[["wave", "source"]].itertuples(index=False, name=None)
    ):
        raise SAOMValidationError("Every edge source must be present at that wave.")
    if any(
        (wave, actor) not in available
        for wave, actor in result[["wave", "target"]].itertuples(index=False, name=None)
    ):
        raise SAOMValidationError("Every edge target must be present at that wave.")
    if not directed:
        result[["source", "target"]] = np.sort(
            result[["source", "target"]].to_numpy(), axis=1
        )
    if result.duplicated().any():
        raise SAOMValidationError("Duplicate dyads within a wave are not accepted.")
    return result


def _balanced_panel(
    spec: SAOMPanelSpec,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    behavior: pd.DataFrame | None,
    behavior_name: str | None,
    selected_waves: list[str] | None,
    allow_behavior_complete_case_filter: bool,
) -> SAOMPanel:
    clean_nodes = _clean_nodes(nodes)
    waves = _ordered_waves(clean_nodes["wave"])
    if selected_waves is not None:
        requested = [str(value) for value in selected_waves]
        missing = set(requested) - set(waves)
        if missing:
            raise SAOMValidationError(
                f"Requested waves are absent from the panel: {sorted(missing)}."
            )
        waves = requested
    if len(waves) < 2:
        raise SAOMValidationError("At least two selected waves are required.")
    active = [set(clean_nodes.loc[clean_nodes["wave"] == wave, "id"]) for wave in waves]
    actors = tuple(sorted(set.intersection(*active)))
    if len(actors) < 5:
        raise SAOMValidationError(
            "Fewer than five actors are observed at every selected wave."
        )
    behavior_result: pd.DataFrame | None = None
    excluded_for_incomplete_behavior = 0
    if behavior_name is not None:
        if behavior is None or not {"wave", "id", behavior_name}.issubset(
            behavior.columns
        ):
            raise SAOMValidationError(
                f"Behavior data must include `wave`, `id`, and `{behavior_name}`."
            )
        behavior_result = behavior[["wave", "id", behavior_name]].copy()
        behavior_result[["wave", "id"]] = behavior_result[["wave", "id"]].astype(str)
        behavior_result[behavior_name] = pd.to_numeric(
            behavior_result[behavior_name], errors="coerce"
        )
        behavior_result = behavior_result.loc[
            behavior_result["wave"].isin(waves) & behavior_result["id"].isin(actors)
        ].copy()
        complete_actor_values = behavior_result.groupby("id", sort=False)[
            behavior_name
        ].agg(observations="size", missing=lambda values: int(values.isna().sum()))
        complete_ids = set(
            complete_actor_values.index[
                (complete_actor_values["observations"] == len(waves))
                & (complete_actor_values["missing"] == 0)
            ]
        )
        if len(complete_ids) != len(actors):
            if not allow_behavior_complete_case_filter:
                raise SAOMValidationError(
                    "The selected behavior has missing values after balancing; correct the upload or choose a complete wave range."
                )
            excluded_for_incomplete_behavior = len(actors) - len(complete_ids)
            actors = tuple(actor for actor in actors if actor in complete_ids)
            behavior_result = behavior_result.loc[
                behavior_result["id"].isin(actors)
            ].copy()
        if len(actors) < 5:
            raise SAOMValidationError(
                "Fewer than five actors remain after the stated behavior-completeness support rule."
            )
        expected = len(waves) * len(actors)
        if (
            len(behavior_result) != expected
            or behavior_result.duplicated(["wave", "id"]).any()
            or behavior_result[behavior_name].isna().any()
        ):
            raise SAOMValidationError(
                "The selected behavior must have exactly one observed value for every retained actor and wave."
            )
        values = behavior_result[behavior_name].to_numpy(dtype=float)
        if not np.isfinite(values).all() or len(np.unique(values)) < 2:
            raise SAOMValidationError(
                "The selected behavior must be finite and vary over the retained panel."
            )
    clean_edges = _clean_edges(edges, clean_nodes, directed=spec.directed)
    node_result = clean_nodes.loc[
        clean_nodes["wave"].isin(waves) & clean_nodes["id"].isin(actors)
    ].copy()
    edge_result = clean_edges.loc[
        clean_edges["wave"].isin(waves)
        & clean_edges["source"].isin(actors)
        & clean_edges["target"].isin(actors)
    ].copy()
    return SAOMPanel(
        spec=spec,
        actors=actors,
        waves=tuple(waves),
        nodes=node_result,
        edges=edge_result,
        behavior=behavior_result,
        behavior_name=behavior_name,
        excluded_for_incomplete_behavior=excluded_for_incomplete_behavior,
    )


def load_public_workflow(
    session: str, workflow_id: str
) -> tuple[dict[str, Any], SAOMPanel]:
    """Load a public workflow, enforcing its declared waves and behavior boundary."""
    selected = next(
        (item for item in workflows(session) if item["id"] == workflow_id), None
    )
    if selected is None:
        raise SAOMValidationError("Unknown Day 3 public workflow.")
    spec = panel_specs()[selected["panel"]]
    nodes = pd.read_csv(DATA_DIR / spec.nodes_file, dtype={"wave": str, "id": str})
    edges = pd.read_csv(
        DATA_DIR / spec.edges_file, dtype={"wave": str, "source": str, "target": str}
    )
    behavior = None
    if spec.behavior_file:
        behavior = pd.read_csv(
            DATA_DIR / spec.behavior_file, dtype={"wave": str, "id": str}
        )
    panel = _balanced_panel(
        spec,
        nodes,
        edges,
        behavior,
        selected.get("behavior"),
        selected.get("waves"),
        True,
    )
    return selected, panel


def load_byod_panel(
    *,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    behavior: pd.DataFrame | None,
    behavior_name: str | None,
    directed: bool,
) -> SAOMPanel:
    """Validate a participant upload under the same balanced-panel contract."""
    spec = SAOMPanelSpec(
        identifier="byod",
        name="Participant-supplied panel",
        nodes_file="",
        edges_file="",
        behavior_file=None,
        directed=directed,
        source="Participant upload",
        source_url="",
        network_type="Repeated loopless binary network declared by the participant.",
        support_rule="Only actors observed in every selected wave are retained.",
        limit="The upload is accepted only after explicit support and behavior checks.",
    )
    return _balanced_panel(spec, nodes, edges, behavior, behavior_name, None, False)


def _adjacency_for_wave(panel: SAOMPanel, wave: str) -> np.ndarray:
    """Build one observed adjacency matrix without inventing unavailable dyads."""
    index = {actor: position for position, actor in enumerate(panel.actors)}
    adjacency = np.zeros((len(panel.actors), len(panel.actors)), dtype=int)
    observed = panel.edges.loc[panel.edges["wave"] == wave]
    for source, target in observed[["source", "target"]].itertuples(
        index=False, name=None
    ):
        i, j = index[str(source)], index[str(target)]
        adjacency[i, j] = 1
        if not panel.spec.directed:
            adjacency[j, i] = 1
    return adjacency


def _network_transition_rows(
    panel: SAOMPanel, edge_sets: dict[str, set[tuple[str, str]]]
) -> list[dict[str, Any]]:
    """Count documented tie turnover and overlap between adjacent observed waves."""
    rows: list[dict[str, Any]] = []
    for previous, current in zip(panel.waves[:-1], panel.waves[1:], strict=True):
        prior, later = edge_sets[previous], edge_sets[current]
        maintained = prior & later
        union = prior | later
        rows.append(
            {
                "from_wave": previous,
                "to_wave": current,
                "transition": f"{previous} → {current}",
                "maintained_ties": len(maintained),
                "formed_ties": len(later - prior),
                "dissolved_ties": len(prior - later),
                "jaccard_index": len(maintained) / len(union) if union else np.nan,
            }
        )
    return rows


def _network_structure_rows(panel: SAOMPanel) -> list[dict[str, Any]]:
    """Report observed reciprocity and closure summaries with explicit directionality."""
    rows: list[dict[str, Any]] = []
    for wave in panel.waves:
        adjacency = _adjacency_for_wave(panel, wave)
        if panel.spec.directed:
            rows.append(
                {
                    "wave": wave,
                    "mutual_dyads": int((adjacency * adjacency.T).sum() / 2),
                    "transitive_two_path_closures": int(
                        ((adjacency @ adjacency) * adjacency).sum()
                    ),
                    "structure": "Directed reciprocity and transitive two-path closures",
                }
            )
        else:
            rows.append(
                {
                    "wave": wave,
                    "triangles": int(np.trace(adjacency @ adjacency @ adjacency) / 6),
                    "structure": "Undirected triangles",
                }
            )
    return rows


def _behavior_detail_rows(panel: SAOMPanel) -> dict[str, list[dict[str, Any]]]:
    """Prepare observed behavior, selection, and influence summaries for the app."""
    if panel.behavior is None or panel.behavior_name is None:
        return {}
    behavior_name = panel.behavior_name
    behavior_values = {
        wave: panel.behavior.loc[
            panel.behavior["wave"] == wave, ["id", behavior_name]
        ].set_index("id")[behavior_name]
        for wave in panel.waves
    }
    distribution_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    selection_records: list[dict[str, Any]] = []
    edge_sets = {
        wave: set(
            panel.edges.loc[panel.edges["wave"] == wave, ["source", "target"]]
            .astype(str)
            .itertuples(index=False, name=None)
        )
        for wave in panel.waves
    }
    for wave in panel.waves:
        values = behavior_values[wave]
        counts = values.value_counts().sort_index()
        for score, count in counts.items():
            distribution_rows.append(
                {
                    "wave": wave,
                    "score": float(score),
                    "count": int(count),
                    "proportion": float(count / len(values)),
                }
            )
        neighbors: dict[str, list[str]] = {actor: [] for actor in panel.actors}
        for source, target in edge_sets[wave]:
            neighbors[source].append(target)
            if not panel.spec.directed:
                neighbors[target].append(source)
        for actor in panel.actors:
            alters = neighbors[actor]
            if alters:
                exposure_rows.append(
                    {
                        "wave": wave,
                        "actor": actor,
                        "ego_behavior": float(values.loc[actor]),
                        "average_alter_behavior": float(values.loc[alters].mean()),
                        "alter_count": len(alters),
                    }
                )
        candidates = [
            (source, target)
            for source in panel.actors
            for target in panel.actors
            if source != target and (panel.spec.directed or source < target)
        ]
        for source, target in candidates:
            tied = (source, target) in edge_sets[wave]
            selection_records.append(
                {
                    "wave": wave,
                    "ego_behavior": float(values.loc[source]),
                    "alter_behavior": float(values.loc[target]),
                    "absolute_difference": float(
                        abs(values.loc[source] - values.loc[target])
                    ),
                    "tie": int(tied),
                }
            )
    behavior_transition_rows: list[dict[str, Any]] = []
    behavior_change_rows: list[dict[str, Any]] = []
    influence_change_rows: list[dict[str, Any]] = []
    exposure = pd.DataFrame(exposure_rows)
    for previous, current in zip(panel.waves[:-1], panel.waves[1:], strict=True):
        prior = behavior_values[previous].rename("previous")
        later = behavior_values[current].rename("current")
        joined = pd.concat([prior, later], axis=1).dropna()
        joined["change"] = joined["current"] - joined["previous"]
        transition = joined.groupby(["previous", "current"], sort=True).size()
        for (before, after), count in transition.items():
            behavior_transition_rows.append(
                {
                    "from_wave": previous,
                    "to_wave": current,
                    "transition": f"{previous} → {current}",
                    "from_score": float(before),
                    "to_score": float(after),
                    "count": int(count),
                }
            )
        changes = joined["change"].value_counts().sort_index()
        for change, count in changes.items():
            behavior_change_rows.append(
                {
                    "from_wave": previous,
                    "to_wave": current,
                    "transition": f"{previous} → {current}",
                    "behavior_change": float(change),
                    "count": int(count),
                }
            )
        prior_exposure = exposure.loc[exposure["wave"] == previous].set_index("actor")
        for actor, row in joined.iterrows():
            if actor in prior_exposure.index:
                mean_alter = float(prior_exposure.loc[actor, "average_alter_behavior"])
                influence_change_rows.append(
                    {
                        "from_wave": previous,
                        "to_wave": current,
                        "transition": f"{previous} → {current}",
                        "actor": actor,
                        "ego_behavior": float(row["previous"]),
                        "average_alter_behavior": mean_alter,
                        "behavior_change": float(row["change"]),
                        "ego_alter_discrepancy": float(row["previous"] - mean_alter),
                    }
                )
    selections = pd.DataFrame(selection_records)
    selection_ego = (
        selections.groupby(["wave", "ego_behavior"], as_index=False)["tie"]
        .agg(["sum", "count", "mean"])
        .reset_index()
        .rename(columns={"sum": "ties", "count": "eligible_dyads", "mean": "tie_rate"})
    )
    selection_alter = (
        selections.groupby(["wave", "alter_behavior"], as_index=False)["tie"]
        .agg(["sum", "count", "mean"])
        .reset_index()
        .rename(columns={"sum": "ties", "count": "eligible_dyads", "mean": "tie_rate"})
    )
    selection_difference = (
        selections.groupby(["wave", "absolute_difference"], as_index=False)["tie"]
        .agg(["sum", "count", "mean"])
        .reset_index()
        .rename(columns={"sum": "ties", "count": "eligible_dyads", "mean": "tie_rate"})
    )
    selection_matrix = (
        selections.groupby(["ego_behavior", "alter_behavior"], as_index=False)["tie"]
        .agg(["sum", "count", "mean"])
        .reset_index()
        .rename(columns={"sum": "ties", "count": "eligible_dyads", "mean": "tie_rate"})
    )
    return {
        "behavior_distribution": distribution_rows,
        "behavior_transitions": behavior_transition_rows,
        "behavior_changes": behavior_change_rows,
        "behavior_exposure": exposure_rows,
        "behavior_change_exposure": influence_change_rows,
        "selection_ego_rates": selection_ego.to_dict(orient="records"),
        "selection_alter_rates": selection_alter.to_dict(orient="records"),
        "selection_difference_rates": selection_difference.to_dict(orient="records"),
        "selection_matrix": selection_matrix.to_dict(orient="records"),
    }


def panel_profile(panel: SAOMPanel) -> dict[str, Any]:
    """Return observed network, selection, and influence summaries before fitting."""
    actor_index = {actor: position for position, actor in enumerate(panel.actors)}
    edge_sets = {
        wave: set(
            panel.edges.loc[panel.edges["wave"] == wave, ["source", "target"]]
            .astype(str)
            .itertuples(index=False, name=None)
        )
        for wave in panel.waves
    }
    wave_rows: list[dict[str, Any]] = []
    for wave in panel.waves:
        max_dyads = len(panel.actors) * (len(panel.actors) - 1)
        if not panel.spec.directed:
            max_dyads //= 2
        wave_rows.append(
            {
                "wave": wave,
                "actors": len(panel.actors),
                "ties": len(edge_sets[wave]),
                "density": len(edge_sets[wave]) / max_dyads if max_dyads else np.nan,
            }
        )
    result: dict[str, Any] = {
        "actors": len(panel.actors),
        "waves": len(panel.waves),
        "directed": panel.spec.directed,
        "wave_table": wave_rows,
        "network_transitions": _network_transition_rows(panel, edge_sets),
        "network_structure": _network_structure_rows(panel),
        "balanced_actor_rule": "All retained actors are observed at every selected wave.",
        "excluded_for_incomplete_behavior": panel.excluded_for_incomplete_behavior,
        "actor_index": actor_index,
    }
    if panel.behavior is not None and panel.behavior_name is not None:
        behavior_rows = []
        for wave in panel.waves:
            values = panel.behavior.loc[
                panel.behavior["wave"] == wave, panel.behavior_name
            ].to_numpy(dtype=float)
            behavior_rows.append(
                {
                    "wave": wave,
                    "mean": float(values.mean()),
                    "variance": float(values.var(ddof=0)),
                    "standard_deviation": float(values.std(ddof=0)),
                    "minimum": float(values.min()),
                    "maximum": float(values.max()),
                    "distinct_values": len(np.unique(values)),
                }
            )
        result["behavior_name"] = panel.behavior_name
        result["behavior_table"] = behavior_rows
        result.update(_behavior_detail_rows(panel))
    return result


def r_payload(
    panel: SAOMPanel, *, n3: int, gof_simulations: int, seed: int
) -> dict[str, Any]:
    """Build an explicit, JSON-safe payload for the RSiena subprocess."""
    behavior_records: list[dict[str, Any]] = []
    if panel.behavior is not None and panel.behavior_name is not None:
        behavior_records = [
            {"wave": str(wave), "id": str(actor), "value": float(value)}
            for wave, actor, value in panel.behavior[
                ["wave", "id", panel.behavior_name]
            ].itertuples(index=False, name=None)
        ]
    return {
        "label": panel.spec.name,
        "actors": list(panel.actors),
        "waves": list(panel.waves),
        "directed": panel.spec.directed,
        "edges": [
            {"wave": str(wave), "source": str(source), "target": str(target)}
            for wave, source, target in panel.edges[
                ["wave", "source", "target"]
            ].itertuples(index=False, name=None)
        ],
        "behavior_name": panel.behavior_name,
        "behavior": behavior_records,
        "n3": int(n3),
        "gof_simulations": int(gof_simulations),
        "seed": int(seed),
        "model_boundary": (
            "RSiena method-of-moments SAOM with stated structural and, when supplied, selection/influence effects. "
            "Actor microstep order is simulated and not observed; coefficient interpretation is not ordinary regression or automatic causal identification."
        ),
    }
