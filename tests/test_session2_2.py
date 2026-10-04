from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "app"))

from session2_2_options import WORKED_RECIPES, byod_method_note, recipes_by_identifier
from stergm_core import fit_separable_stergm, separable_design
from temporal_core import (
    TemporalNetwork,
    load_temporal_catalog,
    load_temporal_example,
    temporal_profile,
)


def test_session22_has_exactly_five_public_worked_examples() -> None:
    catalog = load_temporal_catalog()
    assert len(WORKED_RECIPES) == 5
    assert set(recipes_by_identifier()) == set(catalog)
    assert all("formation" in recipe.method_status.lower() for recipe in WORKED_RECIPES)
    assert all("persistence" in recipe.method_status.lower() for recipe in WORKED_RECIPES)


def test_separable_design_partitions_every_joint_risk_dyad() -> None:
    network = load_temporal_example(load_temporal_catalog()["knecht_friendship"])
    design = separable_design(network)
    transitions = design["transitions"]
    formation_keys = set(
        design["formation"][["transition_index", "source", "target"]].itertuples(
            index=False, name=None
        )
    )
    persistence_keys = set(
        design["persistence"][["transition_index", "source", "target"]].itertuples(
            index=False, name=None
        )
    )
    assert not (formation_keys & persistence_keys)
    assert (
        transitions["formation_risk_dyads"] + transitions["persistence_risk_ties"]
        == transitions["joint_at_risk_dyads"]
    ).all()
    assert (design["formation"]["outcome"].isin([0, 1])).all()
    assert (design["persistence"]["outcome"].isin([0, 1])).all()
    assert len(transitions) == temporal_profile(network)["observed_transitions"]


def test_session22_computation_runs_all_five_public_workflows() -> None:
    catalog = load_temporal_catalog()
    for identifier, spec in catalog.items():
        result = fit_separable_stergm(
            load_temporal_example(spec),
            bootstrap_replicates=10,
            predictive_simulations=20,
        )
        assert result["status"] == "ok", identifier
        assert 0 < result["formation"]["event_probability"] < 1, identifier
        assert 0 < result["persistence"]["event_probability"] < 1, identifier
        assert len(result["one_step_simulations"]) == result["observed_transitions"], identifier
        assert {"observed_formations", "observed_dissolutions", "observed_mean_degree"}.issubset(
            result["one_step_simulations"][0]
        )
        assert result["expected_duration_intervals"] > 1
        assert {"left_censored_spells", "right_censored_spells", "support_censored_spells"}.issubset(
            result["duration_audit"]
        )


def test_session22_component_rates_match_transition_counts() -> None:
    network = load_temporal_example(load_temporal_catalog()["cow_alliances_1960_1970"])
    result = fit_separable_stergm(network, bootstrap_replicates=10, predictive_simulations=20)
    support = pd.DataFrame(result["transition_support"])
    assert (support["formations_N01"] <= support["formation_risk_dyads"]).all()
    assert (support["persistent_ties_N11"] <= support["persistence_risk_ties"]).all()
    assert (support["dissolutions_N10"] + support["persistent_ties_N11"] == support["persistence_risk_ties"]).all()
    assert result["bootstrap"]["status"] == "ok"


def test_session22_structural_gof_covers_network_type_specific_audits() -> None:
    catalog = load_temporal_catalog()
    directed = fit_separable_stergm(
        load_temporal_example(catalog["knecht_friendship"]),
        bootstrap_replicates=0,
        predictive_simulations=20,
    )
    directed_metrics = directed["structural_gof"][0]
    assert {
        "in_degree_distribution",
        "out_degree_distribution",
        "directed_geodesic_distance_distribution",
        "triad_census",
    }.issubset(directed_metrics["distribution_metrics"])
    assert "reciprocity_rate" in directed_metrics["scalar_metrics"]

    undirected = fit_separable_stergm(
        load_temporal_example(catalog["cow_alliances_1960_1970"]),
        bootstrap_replicates=0,
        predictive_simulations=20,
    )
    undirected_metrics = undirected["structural_gof"][0]
    assert {
        "degree_distribution",
        "geodesic_distance_distribution",
        "edgewise_shared_partner_distribution",
        "dyadwise_shared_partner_distribution",
    }.issubset(undirected_metrics["distribution_metrics"])


def test_session22_structural_gof_uses_declared_categorical_attribute_for_mixing() -> None:
    nodes = pd.DataFrame(
        [
            {"wave": wave, "id": actor, "group": group}
            for wave in ["1", "2", "3"]
            for actor, group in [("A", "red"), ("B", "red"), ("C", "blue")]
        ]
    )
    edges = pd.DataFrame(
        [
            {"wave": "1", "source": "A", "target": "B"},
            {"wave": "2", "source": "A", "target": "B"},
            {"wave": "2", "source": "A", "target": "C"},
            {"wave": "3", "source": "A", "target": "C"},
        ]
    )
    network = TemporalNetwork(
        nodes=nodes,
        edges=edges,
        risk=None,
        directed=False,
        label="Synthetic categorical-mixing panel",
    )
    result = fit_separable_stergm(network, bootstrap_replicates=0, predictive_simulations=20)
    assert result["structural_gof"][0]["attribute"] == "group"
    assert "mixing_matrix" in result["structural_gof"][0]["distribution_metrics"]


def test_session22_byod_boundary_and_page_expose_full_audit() -> None:
    assert "intercept-only formation component" in byod_method_note(directed=True)
    source = (PROJECT_DIR / "app" / "session2_2_ui.py").read_text()
    assert "Day 2 · October 29, 2026 · 4:30–6:00 PM GMT" in source
    assert "separate intercept-only, dyad-factorizing formation and persistence components" in source
    for required in [
        "_support_figure",
        "_rate_figure(result, \"formation\")",
        "_rate_figure(result, \"persistence\")",
        "_simulation_figure(rows, \"formations\"",
        "_simulation_figure(rows, \"dissolutions\"",
        "_simulation_figure(rows, \"persistent_ties\"",
        "_simulation_figure(rows, \"stability\"",
        "_simulation_figure(rows, \"mean_degree\"",
        "_duration_figure",
        "_duration_survival_figure",
        "_render_structural_gof",
        "_structural_distribution_figure",
        "_structural_scalar_figure",
        "_mixing_figures",
        "_bootstrap_figure",
    ]:
        assert required in source


def test_session22_page_renders_all_baseline_diagnostic_plots() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(
        PROJECT_DIR
        / "app"
        / "pages"
        / "4_Session2_2_Separable_TERGMs_for_Formation_and_Dissolution.py",
        default_timeout=120,
    )
    app.run()
    button = next(
        item
        for item in app.button
        if item.label == "Fit the stated separable formation–persistence model"
    )
    button.click().run(timeout=120)
    assert len(app.exception) == 0
    assert len(app.get("plotly_chart")) >= 19
    assert any("expected duration" in item.label.lower() for item in app.metric)
