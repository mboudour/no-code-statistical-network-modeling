from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "app"))

from saom_core import (
    SAOMValidationError,
    load_byod_panel,
    load_public_workflow,
    panel_profile,
    r_payload,
    workflows,
)


def test_day3_has_exactly_five_public_workflows_per_session() -> None:
    assert len(workflows("3.1")) == 5
    assert len(workflows("3.2")) == 5
    assert len({item["id"] for item in workflows("3.1")}) == 5
    assert len({item["id"] for item in workflows("3.2")}) == 5


def test_every_public_workflow_builds_a_valid_json_payload() -> None:
    for session in ("3.1", "3.2"):
        for item in workflows(session):
            selected, panel = load_public_workflow(session, item["id"])
            profile = panel_profile(panel)
            payload = r_payload(panel, n3=80, gof_simulations=20, seed=20261030)
            assert selected["id"] == item["id"]
            assert profile["actors"] >= 5
            assert profile["waves"] >= 2
            assert len(profile["network_transitions"]) == profile["waves"] - 1
            assert len(profile["network_structure"]) == profile["waves"]
            assert {
                "maintained_ties",
                "formed_ties",
                "dissolved_ties",
                "jaccard_index",
            }.issubset(profile["network_transitions"][0])
            assert len(payload["edges"]) == len(panel.edges)
            assert payload["directed"] == panel.spec.directed
            if session == "3.1":
                assert payload["behavior_name"] is None
                assert payload["behavior"] == []
            else:
                assert payload["behavior_name"] == item["behavior"]
                assert len(payload["behavior"]) == profile["actors"] * profile["waves"]
                for key in [
                    "behavior_distribution",
                    "behavior_transitions",
                    "behavior_changes",
                    "behavior_exposure",
                    "behavior_change_exposure",
                    "selection_ego_rates",
                    "selection_alter_rates",
                    "selection_difference_rates",
                    "selection_matrix",
                ]:
                    assert key in profile


def test_public_coevolution_workflows_report_behavior_support_restrictions() -> None:
    _, alcohol = load_public_workflow("3.2", "s32_glasgow_alcohol")
    _, cannabis = load_public_workflow("3.2", "s32_glasgow_cannabis")
    assert alcohol.excluded_for_incomplete_behavior > 0
    assert cannabis.excluded_for_incomplete_behavior > 0
    assert (
        panel_profile(alcohol)["excluded_for_incomplete_behavior"]
        == alcohol.excluded_for_incomplete_behavior
    )


def test_byod_refuses_missing_behavior_without_silent_case_filtering() -> None:
    nodes = pd.DataFrame(
        [
            {"wave": wave, "id": actor}
            for wave in ["1", "2"]
            for actor in ["A", "B", "C", "D", "E"]
        ]
    )
    edges = pd.DataFrame(
        [
            {"wave": "1", "source": "A", "target": "B"},
            {"wave": "2", "source": "B", "target": "A"},
        ]
    )
    behavior = pd.DataFrame(
        [
            {"wave": wave, "id": actor, "score": float(index)}
            for wave in ["1", "2"]
            for index, actor in enumerate(["A", "B", "C", "D", "E"], start=1)
        ]
    )
    behavior.loc[(behavior["wave"] == "2") & (behavior["id"] == "E"), "score"] = None
    with pytest.raises(SAOMValidationError, match="missing values"):
        load_byod_panel(
            nodes=nodes,
            edges=edges,
            behavior=behavior,
            behavior_name="score",
            directed=True,
        )


def test_day3_pages_expose_the_full_audit_contract() -> None:
    source = (PROJECT_DIR / "app" / "session3_ui.py").read_text()
    for required in [
        "Friday, October 30, 2026 · 3:00–4:30 PM GMT",
        "Friday, October 30, 2026 · 4:30–6:00 PM GMT",
        "Five worked public workflows",
        "Dynamics: observed network panel",
        "Successive-wave Jaccard overlap",
        "Observed tie turnover by transition",
        "Selection: observed network–behavior associations",
        "Observed tie-rate mixing matrix",
        "Fitted selection contribution surface",
        "Influence: observed behavior and exposure patterns",
        "Observed change versus mean alter score",
        "Period-specific rate parameters",
        "Dynamics: network simulation audits",
        "Selection and influence: joint network–behavior association audit",
        "approximate 95% Wald intervals",
        "Final convergence t-ratios",
        "Behavior-completeness support rule applied",
        "Download the reproducible computation record",
    ]:
        assert required in source
    r_source = (PROJECT_DIR / "r" / "fit_saom.R").read_text()
    for required in [
        "OutdegreeDistribution",
        "IndegreeDistribution",
        "TriadCensus",
        "BehaviorDistribution",
        "NetworkStructuralAudit",
        "DirectedReciprocityAudit",
        "TiedBehaviorMixingAudit",
        "SelectionAssociationAudit",
        "BehaviorDynamicsAudit",
        "Geodesic, closure, and component structural audit",
        "Observed-versus-simulated tied-actor behavior mixing matrix",
        "transTriads",
        "avSim",
    ]:
        assert required in r_source
