"""Support-aware Session 2.1 specifications for exactly five public temporal examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Session21Recipe:
    """A documented binary discrete-time transition workflow."""

    identifier: str
    title: str
    terms: tuple[str, ...]
    method_status: str
    diagnostic_focus: tuple[str, ...]
    support_note: str
    interpretation_limit: str


WORKED_RECIPES: tuple[Session21Recipe, ...] = (
    Session21Recipe(
        identifier="knecht_friendship",
        title="Knecht classroom: persistence and delayed reciprocity",
        terms=("edges", "memory", "delrecip"),
        method_status="Directed first-order lag-only TERGM. The exact conditional likelihood uses current dyads observed at both adjacent waves; delayed reciprocity is estimated only where the prior reverse dyad is also observed and admissible.",
        diagnostic_focus=(
            "four-wave support profile and three observed transition tables",
            "formation, dissolution, persistent-tie, and persistent-non-tie counts on the joint risk set",
            "one-step fitted-model simulations conditional on every observed prior wave",
        ),
        support_note="Codes 9 and 10 in the source are not zero ties. Incidental missingness, structural nonmembership, and the documented departure are excluded from the dyadic risk set.",
        interpretation_limit="Three transitions from one small classroom cannot identify rich lag structures, peer influence, or a continuous-time friendship process.",
    ),
    Session21Recipe(
        identifier="sampson_liking",
        title="Sampson monastery: persistence, delayed reciprocity, and prior two-path exposure",
        terms=("edges", "memory", "delrecip", "lagged_twopath"),
        method_status="Directed first-order lag-only TERGM. Delayed reciprocity uses only an observed, admissible prior reverse dyad; a lagged two-path exposure uses observed, admissible prior-wave paths and is not a contemporaneous triangle term.",
        diagnostic_focus=(
            "two directed transitions and their four dyadic transition counts",
            "conditional effects of the previous same-dyad tie, previous reverse tie, and previous directed two-path exposure",
            "one-step simulated tie totals, formations, and persistence conditional on each prior panel",
        ),
        support_note="The three Statnet liking panels are preserved as distinct observations on the same 18 labelled actors; they are never pooled into a cumulative relation.",
        interpretation_limit="Two transitions offer limited temporal replication. A lagged two-path association does not prove closure behavior or an unconfounded social mechanism.",
    ),
    Session21Recipe(
        identifier="coleman_friendship",
        title="Coleman high school: one Fall-to-Spring conditional transition",
        terms=("edges", "memory", "delrecip"),
        method_status="Directed first-order lag-only TERGM for exactly one observed Fall-to-Spring transition. The app intentionally withholds a transition-block bootstrap because one transition cannot be resampled as temporal replication.",
        diagnostic_focus=(
            "the single documented Fall-to-Spring joint risk set",
            "persistence and delayed reciprocity with explicit one-transition warning",
            "conditional simulated counts for ties, formations, and persistence",
        ),
        support_note="The source supplies a common 73-position roster but no wave-specific presence file. The fixed risk set is an explicit assumption, not an inference from recorded zeros.",
        interpretation_limit="This is a valid but sharply limited teaching calculation. It cannot estimate time heterogeneity, lag-two effects, reliable temporal uncertainty, or population change.",
    ),
    Session21Recipe(
        identifier="cow_alliances_1960_1970",
        title="COW alliances: annual persistence with prior shared-partner exposure",
        terms=("edges", "memory", "lagged_twopath"),
        method_status="Undirected annual first-order lag-only TERGM on a changing COW-state risk set. The prior shared-partner exposure is a lagged association, not a static closure term or a formation/dissolution decomposition.",
        diagnostic_focus=(
            "eleven annual networks and ten state-system-adjusted transitions",
            "annual formations, dissolutions, persistence, and overall stability without treating nonmember states as zeros",
            "transition-block bootstrap and one-step annual conditional simulations",
        ),
        support_note="A tie is any active formal alliance for an unordered pair of contemporaneous COW-system states. Pre-entry and post-exit dyads are structurally unavailable, not absent alliances.",
        interpretation_limit="Annual panels do not reveal within-year treaty timing. Strong persistence can reflect long treaty spells, left/right censoring, and annual coding rather than a causal dyadic response.",
    ),
    Session21Recipe(
        identifier="windsurfers_interaction",
        title="Windsurfers: daily interaction persistence with attendance-aware risk sets",
        terms=("edges", "memory", "lagged_twopath"),
        method_status="Undirected daily first-order lag-only TERGM restricted to dyads jointly present in adjacent observed panels. The documented missing day is excluded as a transition break.",
        diagnostic_focus=(
            "28 documented adjacent-day intervals, of which 26 contain jointly at-risk dyads and contribute to the conditional likelihood",
            "observed daily formation, dissolution, persistence, and stability counts",
            "transition-block bootstrap and conditional one-day simulations",
        ),
        support_note="Beach absence is not a non-tie. Only dyads with both actors present at both adjacent waves enter a conditional transition; the observed gap from date 920 to 922 is never bridged.",
        interpretation_limit="Observed daily interaction presence is not a stable friendship tie. The small joint-risk sets on some days limit fine-grained structural interpretation.",
    ),
)


def recipes_by_identifier() -> dict[str, Session21Recipe]:
    """Return public examples keyed by the shared Session 2.1 data catalog ID."""
    return {recipe.identifier: recipe for recipe in WORKED_RECIPES}


def byod_terms(*, directed: bool, include_delayed_reciprocity: bool, include_lagged_twopath: bool) -> tuple[str, ...]:
    """Return only first-order support-valid lag-only terms for a BYOD starter model."""
    terms: list[str] = ["edges", "memory"]
    if directed and include_delayed_reciprocity:
        terms.append("delrecip")
    if include_lagged_twopath:
        terms.append("lagged_twopath")
    return tuple(terms)


def byod_method_note(*, directed: bool, include_delayed_reciprocity: bool, include_lagged_twopath: bool) -> str:
    """State the scope of the Session 2.1 BYOD calculation precisely."""
    terms = ["edges baseline", "lagged same-dyad persistence"]
    if directed and include_delayed_reciprocity:
        terms.append("lagged delayed reciprocity")
    if include_lagged_twopath:
        terms.append("prior-wave two-path exposure")
    return (
        "The stated first-order lag-only TERGM contains "
        + ", ".join(terms)
        + ". Its exact conditional likelihood applies because every included statistic is a function of the prior observed network; delayed reciprocity, when selected, is evaluated only where the prior reverse dyad is observed and admissible. It does not estimate contemporaneous structural dependence or separate formation and dissolution processes."
    )
