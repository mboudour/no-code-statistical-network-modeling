"""Support-aware Session 2.2 specifications for five public STERGM examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Session22Recipe:
    """A documented baseline separable formation–persistence workflow."""

    identifier: str
    title: str
    method_status: str
    diagnostic_focus: tuple[str, ...]
    support_note: str
    interpretation_limit: str


WORKED_RECIPES: tuple[Session22Recipe, ...] = (
    Session22Recipe(
        identifier="knecht_friendship",
        title="Knecht classroom: friendship formation versus persistence",
        method_status="Directed baseline STERGM. Newly absent dyads enter the formation component; existing nomination ties enter the persistence component. Both components use the documented joint risk set, including its missingness and departure exclusions.",
        diagnostic_focus=(
            "three component-specific transition supports across four observed school waves",
            "formation, dissolution, persistence, and stability rates with one-step simulation envelopes",
            "tie-spell censoring and the restricted homogeneous geometric-duration interpretation",
        ),
        support_note="Codes 9 and 10, incidental missingness, structural nonmembership, and the documented departure are unavailable dyads, not non-ties and not dissolution events.",
        interpretation_limit="Three transitions cannot identify temporal heterogeneity, peer influence, or a general dependence model. The displayed intercept-only components do not estimate a behavioral mechanism.",
    ),
    Session22Recipe(
        identifier="sampson_liking",
        title="Sampson monastery: process-specific liking turnover",
        method_status="Directed baseline STERGM on repeated positive-affect nominations. Formation and persistence have distinct support sets, but the app does not introduce an unsupported current-wave reciprocity or closure effect.",
        diagnostic_focus=(
            "separate opportunity sets for newly created and retained liking nominations",
            "two one-step transition audits for formation, dissolution, and retained ties",
            "component coefficients and explicitly limited duration information",
        ),
        support_note="The three Statnet liking panels remain separate observations for the same 18 labelled actors; they are not pooled or replaced with a different relation layer.",
        interpretation_limit="Only two transitions are available. A contrast between baseline formation and persistence probabilities is descriptive under the stated model, not proof of a social mechanism.",
    ),
    Session22Recipe(
        identifier="coleman_friendship",
        title="Coleman high school: one Fall-to-Spring separable transition",
        method_status="Directed baseline STERGM for exactly one Fall-to-Spring transition, with separate formation support for prior non-ties and persistence support for prior ties. The fixed 73-position roster is an explicit source-data support assumption, not an inference from recorded zeros.",
        diagnostic_focus=(
            "the distinct formation and persistence supports within the documented Fall-to-Spring transition",
            "formation, dissolution, and survival counts rather than a combined stability coefficient",
            "a mandatory warning that transition-block resampling and duration inference are unavailable",
        ),
        support_note="The public package has no wave-specific attendance file. Every roster dyad is treated as observed only under the stated fixed-risk-set assumption.",
        interpretation_limit="One transition can illustrate separable supports but cannot establish time heterogeneity, a reliable temporal uncertainty distribution, or observed tie-duration dynamics.",
    ),
    Session22Recipe(
        identifier="cow_alliances_1960_1970",
        title="COW alliances: annual incidence and survival of treaties",
        method_status="Undirected baseline STERGM on annual state-system-adjusted supports. It separates alliance formation among absent at-risk dyads from the persistence of previously active alliances.",
        diagnostic_focus=(
            "ten annual formation and persistence supports with state entry and exit excluded from risk",
            "one-step state and transition simulations, including alliance turnover and mean degree",
            "whole-transition bootstrap sensitivity plus censored annual tie-spell summaries",
        ),
        support_note="Pre-entry and post-exit state dyads are structurally unavailable. A formal alliance tie is binary treaty presence, not a count of treaties or a defence-only relation.",
        interpretation_limit="Annual endpoints do not reveal within-year formation, dissolution, or reformation. The baseline components do not attribute alliance change to state covariates or geopolitical causes.",
    ),
    Session22Recipe(
        identifier="windsurfers_interaction",
        title="Windsurfers: daily interaction incidence and survival",
        method_status="Undirected baseline STERGM with separate formation and persistence supports restricted to dyads jointly present on adjacent observed beach days. The documented missing day remains a break, not a long observation interval.",
        diagnostic_focus=(
            "formation and persistence supports under day-specific attendance",
            "conditional daily simulations for ties, density, formation, dissolution, persistence, stability, and mean degree",
            "whole-transition bootstrap sensitivity and observed tie-spell censoring",
        ),
        support_note="Beach absence is not an observed non-tie. The gap from date 920 to 922 is never treated as one separable transition.",
        interpretation_limit="Observed daily interaction is not a durable friendship state. Short, attendance-dependent supports limit the interpretation of a homogeneous duration process.",
    ),
)


def recipes_by_identifier() -> dict[str, Session22Recipe]:
    """Return the five public STERGM workflows keyed by catalog identifier."""
    return {recipe.identifier: recipe for recipe in WORKED_RECIPES}


def byod_method_note(*, directed: bool) -> str:
    """State the precise boundary of the Session 2.2 uploaded-data computation."""
    direction = "directed" if directed else "undirected"
    return (
        f"The stated {direction} baseline STERGM fits an intercept-only formation component on dyads absent at the prior wave "
        "and an intercept-only persistence component on ties present at the prior wave. Each component has an exact dyad-factorizing conditional likelihood on its own observed risk set. The page does not fit general STERGM dependence, separate dissolution-network statistics, or continuous-time hazards."
    )
