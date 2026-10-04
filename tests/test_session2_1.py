from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "app"))

from session2_1_options import WORKED_RECIPES, byod_terms, recipes_by_identifier
from temporal_core import (
    fit_lagged_tergm,
    load_temporal_catalog,
    load_temporal_example,
    rejected_temporal_candidate,
    temporal_profile,
    transition_design,
)


def test_session21_has_exactly_five_public_worked_examples() -> None:
    catalog = load_temporal_catalog()
    recipes = recipes_by_identifier()
    assert len(WORKED_RECIPES) == 5
    assert set(recipes) == set(catalog)
    assert rejected_temporal_candidate()["name"] == "Newcomb Fraternity Sociometric Rankings"
    assert all(recipe.terms[0] == "edges" for recipe in WORKED_RECIPES)
    assert all("memory" in recipe.terms for recipe in WORKED_RECIPES)


def test_session21_public_panels_have_expected_observed_transitions() -> None:
    expected = {
        "knecht_friendship": 3,
        "sampson_liking": 2,
        "coleman_friendship": 1,
        "cow_alliances_1960_1970": 10,
        "windsurfers_interaction": 26,
    }
    catalog = load_temporal_catalog()
    for identifier, transitions in expected.items():
        profile = temporal_profile(load_temporal_example(catalog[identifier]))
        assert profile["observed_transitions"] == transitions
        assert not profile["transition_table"].empty


def test_windsurfer_missing_panel_is_never_bridged() -> None:
    network = load_temporal_example(load_temporal_catalog()["windsurfers_interaction"])
    profile = temporal_profile(network)
    table = profile["transition_table"]
    assert "transition_block" in network.nodes.columns
    assert not ((table["from_wave"] == "920") & (table["to_wave"] == "922")).any()


def test_lagged_design_uses_joint_risk_set_and_prior_history_only() -> None:
    network = load_temporal_example(load_temporal_catalog()["knecht_friendship"])
    design = transition_design(network)
    assert {"outcome", "memory", "delrecip", "lagged_twopath"}.issubset(design.columns)
    assert set(design["outcome"].unique()).issubset({0, 1})
    assert set(design["memory"].unique()).issubset({0, 1})
    assert (design["source"] != design["target"]).all()
    assert len(design) == int(temporal_profile(network)["transition_table"]["joint_at_risk_dyads"].sum())


def test_session21_computation_runs_directed_and_undirected_workflows() -> None:
    catalog = load_temporal_catalog()
    directed = fit_lagged_tergm(
        load_temporal_example(catalog["knecht_friendship"]),
        terms=("edges", "memory", "delrecip"),
        bootstrap_replicates=0,
        predictive_simulations=20,
    )
    undirected = fit_lagged_tergm(
        load_temporal_example(catalog["windsurfers_interaction"]),
        terms=("edges", "memory", "lagged_twopath"),
        bootstrap_replicates=10,
        predictive_simulations=20,
    )
    assert directed["status"] == "ok"
    assert directed["estimated_terms"] == ["edges", "memory", "delrecip"]
    assert directed["bootstrap"]["status"] == "not_run"
    assert len(directed["posterior_predictive"]) == 3
    assert undirected["status"] == "ok"
    assert undirected["estimated_terms"] == ["edges", "memory", "lagged_twopath"]
    assert len(undirected["posterior_predictive"]) == 26
    assert pd.DataFrame(undirected["coefficients"])["estimate"].notna().all()


def test_session21_byod_terms_do_not_silently_add_separable_components() -> None:
    assert byod_terms(
        directed=True,
        include_delayed_reciprocity=True,
        include_lagged_twopath=False,
    ) == ("edges", "memory", "delrecip")
    assert byod_terms(
        directed=False,
        include_delayed_reciprocity=False,
        include_lagged_twopath=True,
    ) == ("edges", "memory", "lagged_twopath")


def test_session21_page_exposes_visible_choices_and_exact_likelihood_boundary() -> None:
    source = (PROJECT_DIR / "app" / "session2_1_ui.py").read_text()
    assert "st.radio(" in source
    assert "five visible choices" in source
    assert "conditional likelihood is exact" in source
    assert "does not provide STERGM formation/dissolution components" in source
