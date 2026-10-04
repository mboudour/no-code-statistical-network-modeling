from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "app"))

from network_core import (
    NetworkValidationError,
    load_catalog,
    load_example,
    network_profile,
    to_ergm_payload,
    validate_binary_network,
)
from r_engine import engine_status, fit_static_ergm

EXPECTED_SIZES = {
    "florentine_business": (16, 15),
    "sampson_liking_wave3": (18, 56),
    "lazega_advice": (71, 892),
    "davis_affiliation": (32, 89),
    "kapferer_sociational": (39, 158),
}


def test_catalog_has_exactly_five_validated_session_examples() -> None:
    catalog = load_catalog()
    assert set(catalog) == set(EXPECTED_SIZES)
    for identifier, (expected_nodes, expected_edges) in EXPECTED_SIZES.items():
        spec = catalog[identifier]
        nodes, edges = load_example(spec)
        assert (len(nodes), len(edges)) == (expected_nodes, expected_edges)
        assert "edges" in spec.valid_terms


def test_davis_profile_uses_bipartite_dyad_support() -> None:
    spec = load_catalog()["davis_affiliation"]
    nodes, edges = load_example(spec)
    profile = network_profile(
        nodes, edges, directed=spec.directed, bipartite=spec.bipartite
    )
    assert profile["admissible_dyads"] == 18 * 14
    assert profile["density"] == pytest.approx(89 / 252)


def test_binary_validation_rejects_valued_ties() -> None:
    spec = load_catalog()["florentine_business"]
    nodes, edges = load_example(spec)
    valued = edges.copy()
    valued["tie"] = 2
    with pytest.raises(NetworkValidationError, match="Valued/count"):
        validate_binary_network(nodes, valued, directed=False, bipartite=False)


def test_r_engine_fits_undirected_directed_and_bipartite_baselines() -> None:
    status = engine_status()
    if not status["available"]:
        pytest.skip(status["reason"])
    catalog = load_catalog()
    expected_formulas = {
        "florentine_business": "nw ~ edges",
        "sampson_liking_wave3": "nw ~ edges + mutual",
        "davis_affiliation": "nw ~ edges + b1degree(1) + b2degree(1)",
    }
    for identifier, expected_formula in expected_formulas.items():
        spec = catalog[identifier]
        nodes, edges = load_example(spec)
        payload = to_ergm_payload(
            nodes,
            edges,
            directed=spec.directed,
            bipartite=spec.bipartite,
            terms=list(spec.default_terms),
            nodematch_attribute=None,
            nodecov_attribute=None,
            seed=20261028,
            mcmc_burnin=2000,
            mcmc_interval=500,
            mcmle_maxit=4,
        )
        result = fit_static_ergm(payload, timeout_seconds=420)
        assert result["formula"] == expected_formula
        assert result["network"]["vertices"] == EXPECTED_SIZES[identifier][0]
        assert result["network"]["edges"] == EXPECTED_SIZES[identifier][1]
        assert result["network"]["density"] > 0
