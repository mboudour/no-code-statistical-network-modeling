from __future__ import annotations

import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DECK = PROJECT_DIR / "slides" / "session2_1" / "session2_1.tex"


def _frames(source: str) -> list[str]:
    return re.findall(r"\\begin\{frame\}(.*?)\\end\{frame\}", source, flags=re.DOTALL)


def _frame_title(frame: str) -> str:
    match = re.search(r"\{([^{}]+)\}", frame)
    return match.group(1) if match else ""


def test_session21_deck_exceeds_minimum_content_frame_requirement() -> None:
    frames = _frames(DECK.read_text())
    assert len(frames) >= 35
    titles = [_frame_title(frame) for frame in frames]
    assert len(titles) == len(set(titles))


def test_session21_deck_states_precise_temporal_and_computation_boundaries() -> None:
    source = DECK.read_text()
    required = [
        "Companion Streamlit app hosted on Render",
        "joint risk-set size",
        "Overall stability is not tie persistence",
        "Delayed reciprocity in a directed network",
        "Do not conflate current closure with inherited closure",
        "Exact conditional likelihood for a restricted lag-only model",
        "Pseudo-likelihood is not Monte Carlo likelihood",
        "Temporal replication is not the number of dyads",
        "Why the Newcomb ranking data are not a worked binary TERGM",
        "no artificial one-step transition is formed across it",
        "Moses.Boudourides@gmail.com",
    ]
    for phrase in required:
        assert phrase in source
    assert "separable formation--dissolution model" in source
    assert "\u201c" not in source


def test_session21_deck_has_exactly_five_worked_example_frames() -> None:
    source = DECK.read_text()
    titles = [_frame_title(frame) for frame in _frames(source)]
    assert sum(title.startswith("Worked example:") for title in titles) == 5
    for title in [
        "Worked example: Knecht classroom friendship",
        "Worked example: Sampson repeated liking nominations",
        "Worked example: Coleman Fall-to-Spring nominations",
        "Worked example: COW annual formal alliances",
        "Worked example: Windsurfers daily interactions",
    ]:
        assert title in titles


def test_session21_slide_assets_and_pdf_are_present() -> None:
    slide_dir = DECK.parent
    for name in ["first_slide.pdf", "second_slide.pdf", "last_slide.pdf", "session2_1.pdf"]:
        assert (slide_dir / name).is_file()
        assert (slide_dir / name).stat().st_size > 0
