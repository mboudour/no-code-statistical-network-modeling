from __future__ import annotations

import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SLIDES = PROJECT_DIR / "slides" / "session1_1" / "session1_1.tex"
APP_UI = PROJECT_DIR / "app" / "session1_1_ui.py"


def active_tex() -> str:
    return "\n".join(
        line for line in SLIDES.read_text().splitlines() if not re.match(r"^\s*%", line)
    )


def test_session1_1_requested_slide_corrections_are_present() -> None:
    text = active_tex()

    assert text.count(r"\begin{frame}") == 50
    assert "no-code-statistical-network-modeling.onrender.com" in text
    assert "no-code-statistical-network-modeling.streamlit.app" not in text

    required = [
        r"\binom{n}{2}=n(n-1)/2",
        "Each coefficient weights the corresponding \\term{change statistic}",
        r"For a toggle with $\Delta_{ij}g_k=1$",
        "fixed-degree support generally requires degree-preserving moves",
        "Bipartite support permits toggles only across modes.",
        "A \\term{mixing matrix} represents ties through category-pair statistics",
        "must not double-count dyads.",
        "forms a pseudolikelihood by multiplying the full conditional probabilities",
        "not the joint ERGM likelihood",
        r"\begin{frame}{ERGM diagnostic audit}",
        "A converged MCMC chain does not imply good model fit",
        "substantively relevant observed network features with their distributions under simulated networks.",
        "For most nontrivial dependent ERGMs, simulation-based methods such as MCMC are used",
    ]
    for phrase in required:
        assert phrase in text


def test_session1_1_obsolete_or_misleading_slide_wording_is_absent() -> None:
    text = active_tex()
    forbidden = [
        "for a one-unit change in its statistic.",
        "only for a one-unit change in $g_k$",
        "Fixed-degree, bipartite, or other constrained supports can restrict",
        "as if they were an independent likelihood contribution.",
        r"g_{ab}(y)=\sum_{i,j}y_{ij}\ind(x_i=a,x_j=b)",
        "compare observed statistics to the model's simulated distribution",
        "MCMC computation is required because dependence makes the normalizing constant intractable in general.",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_session1_1_app_declares_full_standard_audit_as_session12_scope() -> None:
    text = APP_UI.read_text()
    assert "full standard ERGM diagnostic audit" in text
    assert "MCMC diagnostics, simulation-based goodness of fit" in text
