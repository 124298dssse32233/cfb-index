"""Hero finding pattern — daily/weekly findings per page archetype.

Sprint v5-7.5 foundation scaffold. The full generator is the v5-7.5
deliverable; this package locks in the API surface that Window A's
renderer work (v5-7) and Window B's full v5-7.5 generator land on.

The hero finding is the top-of-every-archetype primitive — a single
display-fonted number + 18-22px sentence + sample-size caption +
confidence chip. Locked spec: ``docs/design-system/30-page-archetypes.md``
+ ``docs/design-system/33-confidence-signaling.md``. Visual reference:
every mockup in ``docs/mockups/`` shows it.

Public API contract:

    from cfb_rankings.hero_findings import (
        HeroFinding,
        FindingKind,
        generate_hub_finding,
        generate_daily_finding,
        generate_heisman_finding,
        generate_team_finding,
        render_hero_finding_html,
    )

Each generator returns a ``HeroFinding`` dataclass; ``render_hero_finding_html``
emits the locked CSS structure. The full bodies are stubbed today and
return ``None`` — the v5-7.5 sprint fills them in.
"""

from .types import (
    FindingKind,
    HeroFinding,
)
from .render import render_hero_finding_html
from .generator import (
    generate_hub_finding,
    generate_daily_finding,
    generate_heisman_finding,
    generate_team_finding,
)


__all__ = [
    "FindingKind",
    "HeroFinding",
    "render_hero_finding_html",
    "generate_hub_finding",
    "generate_daily_finding",
    "generate_heisman_finding",
    "generate_team_finding",
]
