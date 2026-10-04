"""Support-aware Session 1.2 ERGM specifications for exactly five public examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Session12Recipe:
    """One documented worked analysis, including its valid diagnostic profile."""

    identifier: str
    title: str
    formula_terms: tuple[str, ...]
    method_status: str
    curved_terms: tuple[str, ...]
    allow_free_decay: bool
    diagnostic_focus: tuple[str, ...]
    support_note: str
    interpretation_limit: str


WORKED_RECIPES: tuple[Session12Recipe, ...] = (
    Session12Recipe(
        identifier="florentine_business",
        title="Florentine Families: curved degree refinement",
        formula_terms=("edges", "gwdegree"),
        method_status="Fixed-decay geometrically weighted degree model; a one-term free-decay curved sensitivity fit is available.",
        curved_terms=("gwdegree",),
        allow_free_decay=True,
        diagnostic_focus=(
            "MCMC trace, autocorrelation, and sampled-statistic distribution",
            "degree, geodesic distance, edgewise shared partners, and dyadwise shared partners",
            "isolate count, component sizes, and triangle count as omitted structural checks",
        ),
        support_note="Keep all 16 declared families, including the five isolates. The undirected binary support is the observed business-tie encoding, not a directed flow network.",
        interpretation_limit="The small sparse support limits curvature precision. A warning or unstable sensitivity fit is a result to report, not a reason to remove isolates or force a term.",
    ),
    Session12Recipe(
        identifier="sampson_liking_wave3",
        title="Sampson Monastery: directed popularity and reciprocity",
        formula_terms=("edges", "mutual", "gwidegree"),
        method_status="Fixed-decay geometrically weighted in-degree model with reciprocity; a one-term free-decay curved sensitivity fit is available.",
        curved_terms=("gwidegree",),
        allow_free_decay=True,
        diagnostic_focus=(
            "MCMC trace, autocorrelation, and sampled-statistic distribution",
            "directed in-degree and out-degree distributions, reachability distance, and triad census",
            "mutual-dyad count, components, and isolates as simulation-based checks",
        ),
        support_note="Use the directed third-wave liking nominations exactly as recorded. The observed near-fixed choice pattern is a design caveat, so the app does not add a curved out-degree term.",
        interpretation_limit="This is one cross-sectional nomination wave. The analysis does not identify temporal change, peer influence, or a causal mechanism of liking.",
    ),
    Session12Recipe(
        identifier="lazega_advice",
        title="Lazega Law Firm: directed reciprocity baseline audit",
        formula_terms=("edges", "mutual"),
        method_status="Support-valid reciprocity baseline with the full directed diagnostic audit. Fixed-decay in-degree and out-degree refinements are not exposed as defaults because the reproducible pilot produced unconstrained MCMC nonmixing.",
        curved_terms=(),
        allow_free_decay=False,
        diagnostic_focus=(
            "MCMC trace, autocorrelation, and sampled-statistic distribution",
            "directed in-degree and out-degree distributions, reachability distance, and triad census",
            "reciprocity, weak components, isolates, and selected omitted attribute-mixing checks",
        ),
        support_note="The response is the directed advice layer among 71 lawyers. Coworker and friendship layers are not silently inserted as ordinary predictors.",
        interpretation_limit="A completed reciprocity baseline does not establish that degree heterogeneity is absent. Any refinement involving office, status, seniority, or popularity/activity must be theory-led and re-audited rather than added automatically.",
    ),
    Session12Recipe(
        identifier="davis_affiliation",
        title="Davis Southern Women: bipartite fit-boundary audit",
        formula_terms=("edges", "b1degree2"),
        method_status="Support-aware bipartite structural-degree baseline. A free bipartite curved refinement is intentionally blocked because preliminary term-space checks show boundary/linear-dependence problems for this small incidence support.",
        curved_terms=(),
        allow_free_decay=False,
        diagnostic_focus=(
            "MCMC trace, autocorrelation, and sampled-statistic distribution",
            "first-mode and second-mode degree distributions plus bipartite geodesic distances",
            "component sizes, isolates, and mode-specific two-path overlap checks",
        ),
        support_note="Preserve the woman--event incidence support: within-mode dyads are structural zeros. The app audits the original bipartite graph and never replaces it with a one-mode projection.",
        interpretation_limit="This worked example demonstrates a valid Session 1.2 decision: a diagnostic finding can rule out a proposed curved refinement. The result is not an invitation to fit unipartite closure terms.",
    ),
    Session12Recipe(
        identifier="kapferer_sociational",
        title="Kapferer Tailor Shop: closure stability check",
        formula_terms=("edges", "gwesp"),
        method_status="Fixed-decay edgewise shared-partner closure model. The fixed-decay degree-plus-closure pilot produced unconstrained MCMC nonmixing, so the app retains the support-valid closure candidate rather than presenting an unstable joint fit.",
        curved_terms=("gwesp",),
        allow_free_decay=False,
        diagnostic_focus=(
            "MCMC trace, autocorrelation, and sampled-statistic distribution",
            "degree, geodesic distance, edgewise shared partners, and dyadwise shared partners",
            "triangle count, components, and isolates as further simulated structural checks",
        ),
        support_note="Use the undirected binary first-period sociational relation for the documented 39-worker panel. It is neither valued interaction data nor a temporal sequence.",
        interpretation_limit="Closure, density, and degree concentration can be confounded. A degree refinement remains a future theory-led candidate, not an automatic addition after a stable closure fit.",
    ),
)


def recipes_by_identifier() -> dict[str, Session12Recipe]:
    """Return recipes keyed by the shared public-data catalog identifier."""
    return {recipe.identifier: recipe for recipe in WORKED_RECIPES}


def byod_terms(*, directed: bool, bipartite: bool, include_closure: bool) -> tuple[str, ...]:
    """Choose a transparent, support-valid Session 1.2 starter formula."""
    if bipartite:
        return ("edges",)
    if directed:
        return ("edges", "mutual", "gwidegree")
    if include_closure:
        return ("edges", "gwdegree", "gwesp")
    return ("edges", "gwdegree")


def byod_method_note(*, directed: bool, bipartite: bool, include_closure: bool) -> str:
    """State exactly what the BYOD starter specification can and cannot do."""
    if bipartite:
        return (
            "The starter is an edges-only bipartite audit. It preserves the two-mode support and reports mode-specific diagnostics; it does not force a curved term onto an unidentified or unsupported incidence structure."
        )
    if directed:
        return (
            "The starter combines density, reciprocity, and a fixed-decay geometrically weighted in-degree term. It does not model out-degree when a nomination design may constrain choices."
        )
    if include_closure:
        return (
            "The starter combines fixed-decay degree and edgewise shared-partner terms. It is a theory-led candidate, not a data-driven claim that all closure and degree terms are required."
        )
    return (
        "The starter is a fixed-decay geometrically weighted degree model. It offers a compact degree-heterogeneity check before any closure extension is considered."
    )
