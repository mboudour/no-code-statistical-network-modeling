from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "app"))

from network_core import load_catalog, load_example
from r_engine import engine_status, fit_session12_ergm
from session1_2_options import WORKED_RECIPES, byod_terms, recipes_by_identifier


def test_session12_has_exactly_five_public_worked_recipes() -> None:
    catalog = load_catalog()
    recipes = recipes_by_identifier()
    assert len(WORKED_RECIPES) == 5
    assert set(recipes) == set(catalog)
    assert len({recipe.title for recipe in WORKED_RECIPES}) == 5
    assert all("edges" in recipe.formula_terms for recipe in WORKED_RECIPES)


def test_session12_recipes_preserve_support_specific_terms() -> None:
    recipes = recipes_by_identifier()
    assert recipes["florentine_business"].formula_terms == ("edges", "gwdegree")
    assert recipes["sampson_liking_wave3"].formula_terms == (
        "edges",
        "mutual",
        "gwidegree",
    )
    assert recipes["lazega_advice"].formula_terms == ("edges", "mutual")
    assert recipes["davis_affiliation"].formula_terms == ("edges", "b1degree2")
    assert recipes["kapferer_sociational"].formula_terms == ("edges", "gwesp")


def test_byod_starter_terms_match_declared_support() -> None:
    assert byod_terms(directed=True, bipartite=False, include_closure=False) == (
        "edges",
        "mutual",
        "gwidegree",
    )
    assert byod_terms(directed=False, bipartite=False, include_closure=True) == (
        "edges",
        "gwdegree",
        "gwesp",
    )
    assert byod_terms(directed=False, bipartite=True, include_closure=False) == (
        "edges",
    )


def test_session12_engine_returns_full_undirected_audit() -> None:
    status = engine_status()
    if not status["available"]:
        pytest.skip(status["reason"])
    spec = load_catalog()["florentine_business"]
    nodes, edges = load_example(spec)
    result = fit_session12_ergm(
        {
            "network": {"directed": False, "bipartite": False},
            "nodes": nodes.to_dict(orient="records"),
            "edges": edges[["source", "target"]].to_dict(orient="records"),
            "formula": {
                "terms": ["edges", "gwdegree"],
                "curve_controls": {"fixed_decay": True, "decay": 0.5},
            },
            "controls": {
                "seed": 20261028,
                "mcmc_burnin": 1200,
                "mcmc_interval": 200,
                "mcmle_maxit": 4,
                "mcmc_return_stats": 64,
                "gof_nsim": 10,
            },
        },
        timeout_seconds=600,
    )
    assert result["formula"] == "nw ~ edges + gwdegree(0.5, fixed=TRUE)"
    assert result["mcmc_diagnostics"]["sample_size"] > 0
    assert result["gof"]["status"] == "ok"
    assert [item["title"] for item in result["gof"]["tables"]] == [
        "Degree distribution",
        "Geodesic-distance distribution",
        "Edgewise shared-partner distribution",
        "Dyadwise shared-partner distribution",
    ]
    assert result["auxiliary_simulation_checks"]["status"] == "ok"
    assert {item["statistic"] for item in result["auxiliary_simulation_checks"]["summaries"]} >= {
        "isolate_count",
        "component_count",
        "triangle_count",
    }
    assert result["auxiliary_simulation_checks"]["component_size_distribution"]["title"] == (
        "Component-size distribution"
    )


def test_session12_engine_uses_generic_bipartite_overlap_labels() -> None:
    status = engine_status()
    if not status["available"]:
        pytest.skip(status["reason"])
    spec = load_catalog()["davis_affiliation"]
    nodes, edges = load_example(spec)
    result = fit_session12_ergm(
        {
            "network": {"directed": False, "bipartite": True},
            "nodes": nodes.to_dict(orient="records"),
            "edges": edges[["source", "target"]].to_dict(orient="records"),
            "formula": {
                "terms": ["edges", "b1degree2"],
                "curve_controls": {"fixed_decay": True, "decay": 0.5},
            },
            "controls": {
                "seed": 20261028,
                "mcmc_burnin": 1200,
                "mcmc_interval": 200,
                "mcmle_maxit": 4,
                "mcmc_return_stats": 64,
                "gof_nsim": 10,
            },
        },
        timeout_seconds=600,
    )
    names = {
        item["statistic"] for item in result["auxiliary_simulation_checks"]["summaries"]
    }
    assert "mean_first_mode_shared_neighbor_overlap" in names
    assert "mean_second_mode_shared_neighbor_overlap" in names


def test_session12_page_makes_all_worked_choices_visible() -> None:
    source = (PROJECT_DIR / "app" / "session1_2_ui.py").read_text()
    assert 'st.radio(' in source
    assert "Five Session 1.2 worked examples" in source
    assert "no hidden dropdown is used" in source
    assert "recipe_by_title = {recipe.title: recipe for recipe in WORKED_RECIPES}" in source
    assert "list(recipe_by_title)" in source


def test_session12_computation_uses_precise_trace_and_bipartite_labels() -> None:
    interface = (PROJECT_DIR / "app" / "session1_2_ui.py").read_text()
    engine = (PROJECT_DIR / "r" / "fit_session1_2_ergm.R").read_text()
    assert "standard diagnostic chain is over networks and their retained statistics" in interface
    assert "mean_first_mode_shared_neighbor_overlap" in interface
    assert "mean_second_mode_shared_neighbor_overlap" in interface
    assert "mean_first_mode_shared_neighbor_overlap" in engine
    assert "mean_second_mode_shared_neighbor_overlap" in engine


def test_session12_full_audit_includes_mixing_and_component_distributions() -> None:
    interface = (PROJECT_DIR / "app" / "session1_2_ui.py").read_text()
    engine = (PROJECT_DIR / "r" / "fit_session1_2_ergm.R").read_text()
    assert "Mixing matrices / assortative-mixing checks" in interface
    assert "Component-size distribution" in interface
    assert "mixing_diagnostics" in engine
    assert "component_size_distribution" in engine
