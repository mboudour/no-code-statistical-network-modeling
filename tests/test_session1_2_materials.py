from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_DIR / "slides" / "session1_2" / "session1_2.tex"


def test_session12_deck_has_required_volume_and_template_assets() -> None:
    text = SOURCE.read_text()
    assert text.count(r"\begin{frame}") >= 35
    assert r"\includepdf[pages={1}]{first_slide.pdf}" in text
    assert r"\includepdf[pages={2}]{second_slide.pdf}" in text
    assert r"\includepdf[pages={8}]{last_slide.pdf}" in text


def test_session12_deck_has_public_app_link_and_contact() -> None:
    text = SOURCE.read_text()
    assert "Companion Streamlit app hosted on Render" in text
    assert "https://no-code-statistical-network-modeling.onrender.com/" in text
    assert "Moses.Boudourides@northwestern.edu" in text
    assert "Moses.Boudourides@gmail.com" in text


def test_session12_deck_states_full_audit_and_lazega_boundary() -> None:
    text = SOURCE.read_text()
    for phrase in (
        "MCMC traces, autocorrelation, and sampled-statistic distributions",
        "Edgewise shared partners",
        "Dyadwise shared partners",
        "directed triad census",
        "A geodesic-distance diagnostic must retain bipartite parity",
        "unconstrained MCMC nonmixing",
    ):
        assert phrase in text


def test_session12_deck_uses_corrected_conceptual_definitions() -> None:
    text = SOURCE.read_text()
    required = (
        "typically with $p<q$",
        "places most of its probability on a relatively small set of graph configurations",
        "observed sufficient-statistic vector lies on the relevant boundary of the convex support",
        "retained MCMC values of monitored network statistics",
        "Edgewise shared-partner distribution",
        "Dyadwise shared-partner distribution",
        "first-mode shared-neighbor overlap",
        "second-mode shared-neighbor overlap",
        "the $N$ entering BIC is not uniquely determined by the ERGM likelihood itself",
    )
    for phrase in required:
        assert phrase in text
    assert "$q>p=\\dim(\\theta)$" not in text
