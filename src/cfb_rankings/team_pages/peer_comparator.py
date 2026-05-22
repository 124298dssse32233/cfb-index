"""Program Peer Comparator — Brief §26 (static-attribute variant).

The full brief calls for cosine similarity over season-vector features
(SRS / SOS / turnover margin / recruiting rank / coach tenure / etc.).
That requires a nightly compute job + per-season vectors — out of scope
for the same-day ship.

This is the static-attribute analog: similarity across the profile-level
identity dimensions we DO have today:

  - program_tier   (1-10 internal scale)
  - fan_archetype_dominant  (cultural cluster)
  - conference     (geographic / competitive)
  - prestige_tier  (Brief §3.2)
  - voice_register (tonal cluster)

For each profile, ranks all other profiles by a weighted match score
and surfaces the top 3. The chip below the rail reads:

    Most-similar programs: Ole Miss · South Carolina · Stanford
    Shared tier, archetype, conference cluster

Screenshot-virality module — every fan's first question is "what does
this team remind us of?"

Public API:
    render_peer_comparator(profile, all_profiles) -> str
    PEER_COMPARATOR_CSS                            -> str
    compute_peer_score(a, b) -> float
"""
from __future__ import annotations

from html import escape
from typing import Iterable

from .profile_loader import Profile, load_profile, PROFILES_DIR


PEER_COMPARATOR_CSS = """
/* Program Peer Comparator — Brief §26 */
.peer-comparator {
  display: grid;
  gap: clamp(8px, 1.2vw, 14px);
  padding: clamp(14px, 1.8vw, 22px) clamp(16px, 2.0vw, 26px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.peer-comparator__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.peer-comparator__title {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(20px, 1.5vw + 9px, 26px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.peer-comparator__peers {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.peer-comparator__peer {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: transform 0.18s ease, border-color 0.18s ease;
}
.peer-comparator__peer:hover {
  transform: translateY(-1px);
  border-color: var(--accent-primary, #c9a24a);
}
.peer-comparator__peer-name {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 14px;
  font-weight: 700;
  color: var(--fg-primary);
}
.peer-comparator__peer-reason {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 11px;
  font-style: italic;
  color: var(--fg-secondary);
  line-height: 1.35;
}
.peer-comparator__caveat {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-style: italic;
  color: var(--fg-muted);
  margin: 0;
  opacity: 0.7;
}
@media (max-width: 640px) {
  .peer-comparator__peers { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Similarity scoring
# ---------------------------------------------------------------------------

# Weights per dimension. Tuned so program_tier dominates but archetype +
# conference can break ties.
_W_TIER = 4.0
_W_PRESTIGE = 3.0
_W_ARCH = 2.5
_W_CONF = 2.0
_W_VOICE = 1.5


def _val(profile: Profile, key: str) -> str:
    return str(profile.frontmatter.get(key, "") or "").strip().lower()


def compute_peer_score(a: Profile, b: Profile) -> tuple[float, list[str]]:
    """Compute similarity score and list of matched-on reasons."""
    if a.slug == b.slug:
        return (-1.0, [])

    score = 0.0
    reasons: list[str] = []

    # Tier exact match
    if a.program_tier == b.program_tier:
        score += _W_TIER
        reasons.append(f"Tier {b.program_tier}")
    elif abs(a.program_tier - b.program_tier) == 1:
        score += _W_TIER / 2.5
        reasons.append("Adjacent tier")

    # Prestige tier (Brief §3.2 override or computed default)
    a_prestige = a.frontmatter.get("prestige_tier")
    b_prestige = b.frontmatter.get("prestige_tier")
    if a_prestige is not None and b_prestige is not None and int(a_prestige) == int(b_prestige):
        score += _W_PRESTIGE
        reasons.append(f"Prestige T{int(b_prestige)}")

    # Fan archetype dominant
    a_arch = _val(a, "cultural_anchors") or ""
    b_arch = _val(b, "cultural_anchors") or ""
    a_fa = a.frontmatter.get("cultural_anchors", {})
    b_fa = b.frontmatter.get("cultural_anchors", {})
    if isinstance(a_fa, dict) and isinstance(b_fa, dict):
        a_arch_v = str(a_fa.get("fan_archetype_dominant", "") or "").lower()
        b_arch_v = str(b_fa.get("fan_archetype_dominant", "") or "").lower()
        if a_arch_v and a_arch_v == b_arch_v:
            score += _W_ARCH
            reasons.append("Same fanbase archetype")

    # Voice register
    if a.voice_register and a.voice_register == b.voice_register:
        score += _W_VOICE
        reasons.append("Same voice register")

    # Conference
    a_conf = _val(a, "conference") or ""
    b_conf = _val(b, "conference") or ""
    if a_conf and b_conf and a_conf == b_conf:
        score += _W_CONF
        reasons.append("Same conference")

    return (score, reasons)


def _top_peers(focal: Profile, candidates: Iterable[Profile], n: int = 3) -> list[tuple[Profile, list[str]]]:
    scored: list[tuple[float, Profile, list[str]]] = []
    for c in candidates:
        s, r = compute_peer_score(focal, c)
        if s > 0:
            scored.append((s, c, r))
    scored.sort(key=lambda t: (-t[0], t[1].program_name))
    return [(p, r) for (_, p, r) in scored[:n]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _load_all_profiles() -> list[Profile]:
    """Load every profile YAML in profiles/. Tolerates load failures."""
    out: list[Profile] = []
    for path in PROFILES_DIR.glob("*.md"):
        if path.name.startswith("_"):
            continue
        try:
            out.append(load_profile(path.stem, PROFILES_DIR))
        except Exception:
            continue
    return out


_PROFILE_CACHE: list[Profile] | None = None


def _cached_profiles() -> list[Profile]:
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = _load_all_profiles()
    return _PROFILE_CACHE


def render_peer_comparator(profile: Profile, all_profiles: list[Profile] | None = None) -> str:
    """Render the Program Peer Comparator chip (Brief §26)."""
    candidates = all_profiles if all_profiles is not None else _cached_profiles()
    if not candidates:
        return ""

    top = _top_peers(profile, candidates, n=3)
    if not top:
        return ""

    peer_html_parts: list[str] = []
    for peer, reasons in top:
        reasons_str = " · ".join(reasons[:3]) if reasons else "Profile-similar"
        peer_html_parts.append(
            f'<a class="peer-comparator__peer" href="/teams/{escape(peer.slug)}.html" '
            f'aria-label="Peer program: {escape(peer.program_name)}">'
            f'<span class="peer-comparator__peer-name">{escape(peer.program_name)}</span>'
            f'<span class="peer-comparator__peer-reason">{escape(reasons_str)}</span>'
            '</a>'
        )

    program = escape(profile.program_name)
    return f"""
<section class="peer-comparator" aria-labelledby="peer-comparator-h"
         data-module="peer-comparator" data-state="ready">
  <p class="peer-comparator__eyebrow">Most Similar Programs · {program}</p>
  <h2 id="peer-comparator-h" class="peer-comparator__title">Reads Like</h2>
  <div class="peer-comparator__peers" role="list" aria-label="Three most similar programs">
    {''.join(peer_html_parts)}
  </div>
  <p class="peer-comparator__caveat">Static-attribute similarity across tier, archetype, conference, and voice. Not a prediction — a calibration.</p>
</section>"""


__all__ = [
    "render_peer_comparator",
    "PEER_COMPARATOR_CSS",
    "compute_peer_score",
]
