"""Network loading, validation, profiling, and ERGM payload construction for Session 1.1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "public"
CATALOG_PATH = PROJECT_DIR / "data" / "dataset_catalog.json"


class NetworkValidationError(ValueError):
    """Raised when an uploaded or bundled network violates the Session 1.1 contract."""


@dataclass(frozen=True)
class NetworkSpec:
    identifier: str
    name: str
    source: str
    source_url: str
    citation: str
    network_type: str
    directed: bool
    bipartite: bool
    response_scope: str
    valid_terms: tuple[str, ...]
    default_terms: tuple[str, ...]
    caution: str
    rationale: str
    nodes_file: str
    edges_file: str


def load_catalog() -> dict[str, NetworkSpec]:
    """Load the versioned public-data catalog into immutable network specifications."""
    raw = json.loads(CATALOG_PATH.read_text())
    examples: dict[str, NetworkSpec] = {}
    for item in raw["examples"]:
        examples[item["id"]] = NetworkSpec(
            identifier=item["id"],
            name=item["name"],
            source=item["source"],
            source_url=item["source_url"],
            citation=item["citation"],
            network_type=item["network_type"],
            directed=bool(item["directed"]),
            bipartite=bool(item["bipartite"]),
            response_scope=item["response_scope"],
            valid_terms=tuple(item["valid_terms"]),
            default_terms=tuple(item["default_terms"]),
            caution=item["caution"],
            rationale=item["rationale"],
            nodes_file=item["nodes_file"],
            edges_file=item["edges_file"],
        )
    return examples


def load_example(spec: NetworkSpec) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read one public example and validate its documented static binary support."""
    nodes = pd.read_csv(DATA_DIR / spec.nodes_file)
    edges = pd.read_csv(DATA_DIR / spec.edges_file)
    validate_binary_network(
        nodes, edges, directed=spec.directed, bipartite=spec.bipartite
    )
    return nodes, edges


def _canonical_pair(source: str, target: str, directed: bool) -> tuple[str, str]:
    return (source, target) if directed or source < target else (target, source)


def validate_binary_network(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
) -> None:
    """Validate the strict binary static-network contract used by Session 1.1."""
    required_nodes = {"id"}
    required_edges = {"source", "target"}
    if not required_nodes.issubset(nodes.columns):
        raise NetworkValidationError("The node table must include an `id` column.")
    if not required_edges.issubset(edges.columns):
        raise NetworkValidationError(
            "The edge table must include `source` and `target` columns."
        )
    if nodes.empty:
        raise NetworkValidationError("The node table cannot be empty.")
    ids = nodes["id"].astype(str)
    if ids.isna().any() or (ids.str.strip() == "").any() or ids.duplicated().any():
        raise NetworkValidationError("Node identifiers must be non-empty and unique.")
    if edges.empty:
        raise NetworkValidationError(
            "The edge table cannot be empty for an ERGM computation."
        )
    source = edges["source"].astype(str)
    target = edges["target"].astype(str)
    if (
        source.isna().any()
        or target.isna().any()
        or (source.str.strip() == "").any()
        or (target.str.strip() == "").any()
    ):
        raise NetworkValidationError(
            "Every edge requires a non-empty source and target identifier."
        )
    if not set(source).issubset(set(ids)) or not set(target).issubset(set(ids)):
        raise NetworkValidationError(
            "Every edge endpoint must appear in the node table."
        )
    if (source == target).any():
        raise NetworkValidationError(
            "Session 1.1 supports loopless graphs only; remove self-ties."
        )
    if "tie" in edges.columns:
        tie = pd.to_numeric(edges["tie"], errors="coerce")
        if tie.isna().any() or not set(tie.unique()).issubset({0, 1}):
            raise NetworkValidationError(
                "The optional `tie` column must contain only 0 or 1. Valued/count ties require a different model family."
            )
    pairs = [
        _canonical_pair(a, b, directed) for a, b in zip(source, target, strict=True)
    ]
    if pd.Series(pairs).duplicated().any():
        raise NetworkValidationError(
            "The edge table contains duplicate dyads after accounting for directedness."
        )
    if bipartite:
        if "mode" not in nodes.columns:
            raise NetworkValidationError(
                "A bipartite network requires a `mode` column in the node table."
            )
        modes = nodes.set_index(ids)["mode"].astype(str)
        if modes.nunique() != 2:
            raise NetworkValidationError(
                "A bipartite network needs exactly two node modes."
            )
        if any(modes[a] == modes[b] for a, b in zip(source, target, strict=True)):
            raise NetworkValidationError(
                "Bipartite edges must connect nodes in different declared modes."
            )


def network_profile(
    nodes: pd.DataFrame, edges: pd.DataFrame, *, directed: bool, bipartite: bool
) -> dict[str, Any]:
    """Compute transparent descriptive checks without treating them as ERGM estimates."""
    graph: nx.Graph | nx.DiGraph = nx.DiGraph() if directed else nx.Graph()
    graph.add_nodes_from(nodes["id"].astype(str))
    graph.add_edges_from(
        zip(edges["source"].astype(str), edges["target"].astype(str), strict=True)
    )
    n = graph.number_of_nodes()
    if bipartite:
        first_mode_count = int(
            nodes["mode"].astype(str).eq(nodes["mode"].astype(str).iloc[0]).sum()
        )
        possible_dyads = first_mode_count * (n - first_mode_count)
    else:
        possible_dyads = n * (n - 1) if directed else n * (n - 1) // 2
    edge_count = graph.number_of_edges()
    profile: dict[str, Any] = {
        "nodes": n,
        "observed_edges": edge_count,
        "admissible_dyads": possible_dyads,
        "density": edge_count / possible_dyads if possible_dyads else np.nan,
        "directed": directed,
        "bipartite": bipartite,
        "degree_table": pd.DataFrame(
            {
                "id": list(graph.nodes()),
                "degree": [graph.degree(node) for node in graph.nodes()],
            }
        ).sort_values("degree", ascending=False),
    }
    if directed:
        profile["reciprocated_unordered_dyads"] = sum(
            1
            for source, target in graph.edges()
            if source < target and graph.has_edge(target, source)
        )
        profile["degree_table"] = pd.DataFrame(
            {
                "id": list(graph.nodes()),
                "outdegree": [graph.out_degree(node) for node in graph.nodes()],
                "indegree": [graph.in_degree(node) for node in graph.nodes()],
            }
        ).sort_values(["indegree", "outdegree"], ascending=False)
    return profile


def to_ergm_payload(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    directed: bool,
    bipartite: bool,
    terms: list[str],
    nodematch_attribute: str | None,
    nodecov_attribute: str | None,
    seed: int,
    mcmc_burnin: int = 5000,
    mcmc_interval: int = 1000,
    mcmle_maxit: int = 8,
) -> dict[str, Any]:
    """Create the JSON-safe payload accepted by r/fit_static_ergm.R."""
    validate_binary_network(nodes, edges, directed=directed, bipartite=bipartite)
    if "edges" not in terms:
        terms = ["edges", *terms]
    clean_nodes = nodes.copy()
    clean_edges = edges[["source", "target"]].copy()
    for column in clean_nodes.columns:
        if pd.api.types.is_bool_dtype(clean_nodes[column]):
            clean_nodes[column] = clean_nodes[column].astype(str)
        clean_nodes[column] = clean_nodes[column].where(
            clean_nodes[column].notna(), None
        )
    return {
        "network": {"directed": directed, "bipartite": bipartite},
        "nodes": clean_nodes.to_dict(orient="records"),
        "edges": clean_edges.to_dict(orient="records"),
        "formula": {
            "terms": terms,
            "nodematch_attribute": nodematch_attribute or "",
            "nodecov_attribute": nodecov_attribute or "",
        },
        "controls": {
            "seed": int(seed),
            "mcmc_burnin": int(mcmc_burnin),
            "mcmc_interval": int(mcmc_interval),
            "mcmle_maxit": int(mcmle_maxit),
        },
    }


def categorical_attributes(nodes: pd.DataFrame) -> list[str]:
    """Return suitable categorical actor attributes, excluding identifiers and bipartite mode labels."""
    return [
        column
        for column in nodes.columns
        if column not in {"id", "mode"}
        and not pd.api.types.is_numeric_dtype(nodes[column])
        and 2 <= nodes[column].nunique(dropna=True) <= 12
    ]


def numeric_attributes(nodes: pd.DataFrame) -> list[str]:
    """Return numeric actor attributes suitable for the basic nodecov term."""
    return [
        column
        for column in nodes.columns
        if column != "id" and pd.api.types.is_numeric_dtype(nodes[column])
    ]
