"""Deterministic season-path projection (floor / base / ceiling).

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §2.2, §1.2.

This is the load-bearing, fully-tested core of the preview truth layer. It is a
*pure* function of normalised inputs — it does not touch the database — so the
record math can be exercised exhaustively in unit tests without fixtures.

Guiding rules (spec §2.2, §10):
  * Lower-tier / low-projection teams do not get a bowl or CFP path unless the
    regular-season projection supports it.
  * Independents never get a conference title game.
  * A ``national_champion`` scenario has zero postseason losses (won out); any
    other CFP path carries exactly one postseason loss (the elimination game).
  * Elite teams can project beyond 12 games (CCG + multi-round CFP).
  * Nothing here is hard-coded per team — Alabama's ceiling is *derived* from a
    high strength scalar, not pinned.

The engine works on a single ``strength`` scalar in [0, 1] built upstream from
whatever deterministic signals are available (talent, recruiting, returning
production, power prior, prior record). Missing signals lower confidence rather
than inventing values.
"""

from __future__ import annotations

from dataclasses import dataclass, field

REGULAR_SEASON_GAMES = 12

# Strength thresholds (on the 0..1 composite scalar). Calibrated against the
# observed 2026 FBS distribution (blue bloods ~0.84-0.88, median ~0.65, weakest
# ~0.39) so the tiers map to roughly: title contenders (top ~10), CFP field
# (top ~20), conference contenders (top ~30).
_BOWL_ELIGIBLE_WINS = 6           # >= 6 regular-season wins => bowl plausible
_CCG_CONTENDER_STRENGTH = 0.78    # plausibly reaches a conference title game (ceiling)
_CCG_FAVORITE_STRENGTH = 0.88     # plausibly wins it in the base case
_CFP_STRENGTH = 0.80              # plausibly in the 12-team CFP field (ceiling)
_CFP_BASE_STRENGTH = 0.83         # plausibly in the CFP field in the base case
_NAT_TITLE_STRENGTH = 0.83        # plausibly makes a national-title run (ceiling)
_DEEP_CFP_BASE_STRENGTH = 0.88    # base-case deep run (semifinal)

MODEL_VERSION = "season_path_v1"


@dataclass(frozen=True)
class SeasonPathInputs:
    """Normalised, deterministic inputs for one team's projection.

    ``strength`` is the single most important field: a 0..1 scalar where 1.0 is
    a national-title-caliber roster and 0.0 is the weakest FBS team. It is built
    by :mod:`cfb_rankings.team_preview.evidence` from available signals.
    """

    slug: str
    season_year: int
    strength: float
    is_independent: bool = False
    # Uncertainty widens the floor/ceiling band and lowers the confidence band.
    # 0.0 = every signal present and consistent; 1.0 = almost nothing known.
    uncertainty: float = 0.0
    confidence_band: str = "unset"
    # Whether the team has enough roster-talent evidence to be projected into a
    # deep CFP / national-title path. Recent FCS->FBS programs with no talent or
    # recruiting data can inflate the raw strength scalar; gating title runs on
    # real talent evidence keeps them out of contender tiers (spec §7.4).
    cfp_eligible: bool = True

    def clamped_strength(self) -> float:
        return max(0.0, min(1.0, self.strength))


@dataclass(frozen=True)
class SeasonPathProjection:
    """One scenario row. Mirrors team_season_path_projection columns."""

    scenario: str                       # 'floor' | 'base' | 'ceiling'
    regular_season_wins: int
    regular_season_losses: int
    conference_title_game: bool
    conference_title_result: str        # 'win' | 'loss' | 'none'
    bowl_or_cfp_path: str               # see CHECK in migration 01
    postseason_wins: int
    postseason_losses: int
    final_wins: int
    final_losses: int
    final_ties: int = 0
    path_label: str = ""
    rationale: str = ""
    confidence_band: str = "unset"
    model_version: str = MODEL_VERSION


# --- strength -> expected regular-season record -----------------------------

def expected_regular_wins(strength: float) -> float:
    """Map a 0..1 strength scalar to an expected regular-season win total.

    Monotone in strength. Endpoints: strength 0 -> ~1.2 wins, strength 1 ->
    ~11 wins over a 12-game schedule. Deliberately conservative at the top so a
    *base* case never auto-implies an undefeated regular season.
    """
    strength = max(0.0, min(1.0, strength))
    win_rate = 0.10 + 0.82 * strength
    return win_rate * REGULAR_SEASON_GAMES


def _band_delta(uncertainty: float) -> int:
    """Half-width of the floor/ceiling win band, in games."""
    uncertainty = max(0.0, min(1.0, uncertainty))
    return 2 + round(uncertainty * 2)  # 2..4 games each side


def _confidence_from_uncertainty(uncertainty: float) -> str:
    if uncertainty <= 0.25:
        return "high"
    if uncertainty <= 0.55:
        return "medium"
    return "low"


# --- CFP bracket math -------------------------------------------------------
# 12-team format: the four highest-ranked conference champions get first-round
# byes (3 possible CFP games: QF, SF, final). Everyone else plays from the first
# round (up to 4 CFP games). We express each exit point as (wins, losses) so the
# arithmetic is explicit and consistent regardless of seeding.

def _cfp_record(path: str, has_bye: bool) -> tuple[int, int]:
    """Return (postseason_wins, postseason_losses) for a CFP exit point."""
    if path == "national_champion":
        return (3, 0) if has_bye else (4, 0)
    if path == "cfp_title":            # lost the title game
        return (2, 1) if has_bye else (3, 1)
    if path == "cfp_semifinal":        # lost in the semifinal
        return (1, 1) if has_bye else (2, 1)
    if path == "cfp_quarterfinal":     # lost in the quarterfinal
        return (0, 1) if has_bye else (1, 1)
    if path == "cfp_first_round":      # lost in the first round (bye teams skip it)
        return (0, 1)
    raise ValueError(f"not a CFP path: {path}")


def _assemble(
    scenario: str,
    reg_wins: int,
    ccg_game: bool,
    ccg_result: str,
    path: str,
    has_bye: bool,
    confidence_band: str,
    rationale: str,
) -> SeasonPathProjection:
    reg_wins = max(0, min(REGULAR_SEASON_GAMES, reg_wins))
    reg_losses = REGULAR_SEASON_GAMES - reg_wins

    if path == "none":
        pw, pl = 0, 0
    elif path == "bowl":
        # A single bowl game; result tracks the scenario optimism.
        if scenario == "floor":
            pw, pl = 0, 1
        else:
            pw, pl = 1, 0
    else:
        pw, pl = _cfp_record(path, has_bye)

    ccg_w = 1 if ccg_result == "win" else 0
    ccg_l = 1 if ccg_result == "loss" else 0

    final_wins = reg_wins + ccg_w + pw
    final_losses = reg_losses + ccg_l + pl

    label = _path_label(ccg_game, ccg_result, path, final_wins, final_losses)
    return SeasonPathProjection(
        scenario=scenario,
        regular_season_wins=reg_wins,
        regular_season_losses=reg_losses,
        conference_title_game=ccg_game,
        conference_title_result=ccg_result,
        bowl_or_cfp_path=path,
        postseason_wins=pw,
        postseason_losses=pl,
        final_wins=final_wins,
        final_losses=final_losses,
        path_label=label,
        rationale=rationale,
        confidence_band=confidence_band,
    )


def _path_label(ccg_game: bool, ccg_result: str, path: str, fw: int, fl: int) -> str:
    record = f"{fw}-{fl}"
    if path == "national_champion":
        return f"{record}, national champion"
    if path == "cfp_title":
        return f"{record}, CFP title game"
    if path == "cfp_semifinal":
        return f"{record}, CFP semifinal"
    if path == "cfp_quarterfinal":
        return f"{record}, CFP quarterfinal"
    if path == "cfp_first_round":
        return f"{record}, CFP first round"
    if path == "bowl":
        return f"{record}, bowl game"
    if ccg_game and ccg_result == "loss":
        return f"{record}, conference title game"
    return f"{record}, no postseason" if path == "none" else record


def _project_one(inp: SeasonPathInputs, scenario: str) -> SeasonPathProjection:
    strength = inp.clamped_strength()
    base_wins = expected_regular_wins(strength)
    delta = _band_delta(inp.uncertainty)
    confidence = inp.confidence_band if inp.confidence_band != "unset" \
        else _confidence_from_uncertainty(inp.uncertainty)

    if scenario == "floor":
        reg_wins = int(round(base_wins)) - delta
    elif scenario == "ceiling":
        reg_wins = int(round(base_wins)) + delta
    else:
        reg_wins = int(round(base_wins))
    reg_wins = max(0, min(REGULAR_SEASON_GAMES, reg_wins))

    indep = inp.is_independent
    cfp_ok = inp.cfp_eligible

    # Conference title game eligibility. Independents never qualify.
    ccg_game = False
    ccg_result = "none"
    if not indep:
        if scenario == "ceiling" and strength >= _CCG_CONTENDER_STRENGTH:
            ccg_game, ccg_result = True, "win"
        elif scenario == "base" and strength >= _CCG_FAVORITE_STRENGTH:
            ccg_game, ccg_result = True, "win"
        # floor never assumes a CCG appearance

    # Postseason path. Only awarded when the regular-season projection supports
    # it, and deep CFP / title runs require real talent evidence (cfp_ok).
    path = "none"
    if scenario == "ceiling":
        if ccg_result == "win":
            # A conference champion is in the CFP by definition (P4 auto-bid, or
            # the top G5 champ's auto-bid). How deep depends on tier.
            if cfp_ok and strength >= _NAT_TITLE_STRENGTH:
                path = "national_champion"
            elif cfp_ok and strength >= _CFP_STRENGTH:
                path = "cfp_quarterfinal"
            else:
                path = "cfp_first_round"
        elif cfp_ok and strength >= _NAT_TITLE_STRENGTH:
            path = "national_champion"          # elite at-large ceiling
        elif cfp_ok and strength >= _CFP_STRENGTH:
            path = "cfp_quarterfinal"
        elif reg_wins >= _BOWL_ELIGIBLE_WINS:
            path = "bowl"
    elif scenario == "base":
        if cfp_ok and strength >= _DEEP_CFP_BASE_STRENGTH:
            path = "cfp_semifinal"
        elif cfp_ok and strength >= _CFP_BASE_STRENGTH:
            path = "cfp_first_round"
        elif reg_wins >= _BOWL_ELIGIBLE_WINS:
            path = "bowl"
    else:  # floor
        if reg_wins >= _BOWL_ELIGIBLE_WINS:
            path = "bowl"

    # National champion via a conference: they won their title game and, as a
    # top-4 seed, earned a first-round bye. Independents/at-large get no bye.
    if path == "national_champion" and not indep and scenario == "ceiling":
        ccg_game, ccg_result = True, "win"

    # First-round byes go only to the four highest conference champions.
    has_bye = (
        (not indep)
        and ccg_result == "win"
        and strength >= _CFP_STRENGTH
        and (path == "national_champion" or path.startswith("cfp"))
    )

    rationale = _rationale(inp, scenario, strength, reg_wins, ccg_result, path)
    return _assemble(
        scenario, reg_wins, ccg_game, ccg_result, path, has_bye, confidence, rationale
    )


def _rationale(
    inp: SeasonPathInputs, scenario: str, strength: float,
    reg_wins: int, ccg_result: str, path: str,
) -> str:
    bits = [f"strength≈{strength:.2f}", f"{reg_wins}-win regular-season {scenario}"]
    if inp.is_independent:
        bits.append("independent (no conference title game)")
    if ccg_result == "win":
        bits.append("projected conference title")
    if path == "none":
        bits.append("no bowl path at this projection")
    elif path == "bowl":
        bits.append("bowl-eligible")
    elif path == "national_champion":
        bits.append("CFP title run")
    elif path.startswith("cfp"):
        bits.append(f"CFP path ({path.replace('cfp_', '').replace('_', ' ')})")
    return "; ".join(bits)


def project_season_path(inp: SeasonPathInputs) -> list[SeasonPathProjection]:
    """Return the floor, base, and ceiling projections for one team."""
    projections = [_project_one(inp, s) for s in ("floor", "base", "ceiling")]
    for p in projections:
        validate_projection(p, is_independent=inp.is_independent)
    _validate_monotonic(projections)
    return projections


# --- consistency validation (also asserted by tests) ------------------------

class PathConsistencyError(ValueError):
    """Raised when a projection violates an internal-consistency invariant."""


def validate_projection(p: SeasonPathProjection, *, is_independent: bool) -> None:
    """Assert the spec §1.2 internal-consistency rules for one scenario."""
    if p.regular_season_wins + p.regular_season_losses != REGULAR_SEASON_GAMES:
        raise PathConsistencyError(
            f"{p.scenario}: regular season must total {REGULAR_SEASON_GAMES} games, "
            f"got {p.regular_season_wins}-{p.regular_season_losses}"
        )
    if is_independent and p.conference_title_game:
        raise PathConsistencyError(
            f"{p.scenario}: independent team cannot have a conference title game"
        )
    if not p.conference_title_game and p.conference_title_result != "none":
        raise PathConsistencyError(
            f"{p.scenario}: conference_title_result must be 'none' without a CCG"
        )
    if p.bowl_or_cfp_path == "national_champion" and p.postseason_losses != 0:
        raise PathConsistencyError(
            f"{p.scenario}: national champion cannot carry a postseason loss"
        )
    if p.bowl_or_cfp_path.startswith("cfp_") and p.postseason_losses != 1:
        raise PathConsistencyError(
            f"{p.scenario}: a non-champion CFP path must have exactly one "
            f"postseason loss, got {p.postseason_losses}"
        )
    if p.bowl_or_cfp_path == "none" and (p.postseason_wins or p.postseason_losses):
        raise PathConsistencyError(
            f"{p.scenario}: no-postseason path cannot have postseason games"
        )
    # Final record must equal regular + conference title + postseason.
    ccg_w = 1 if p.conference_title_result == "win" else 0
    ccg_l = 1 if p.conference_title_result == "loss" else 0
    if p.final_wins != p.regular_season_wins + ccg_w + p.postseason_wins:
        raise PathConsistencyError(f"{p.scenario}: final_wins arithmetic mismatch")
    if p.final_losses != p.regular_season_losses + ccg_l + p.postseason_losses:
        raise PathConsistencyError(f"{p.scenario}: final_losses arithmetic mismatch")


def _validate_monotonic(projections: list[SeasonPathProjection]) -> None:
    """Floor <= base <= ceiling on final wins (a sanity guard, not a hard spec)."""
    by_scenario = {p.scenario: p for p in projections}
    floor, base, ceiling = (
        by_scenario["floor"], by_scenario["base"], by_scenario["ceiling"]
    )
    if not (floor.final_wins <= base.final_wins <= ceiling.final_wins):
        raise PathConsistencyError(
            "final wins must be non-decreasing floor<=base<=ceiling: "
            f"{floor.final_wins}/{base.final_wins}/{ceiling.final_wins}"
        )
