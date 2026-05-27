from __future__ import annotations

from cfb_rankings.team_pages.profile_loader import list_real_fbs_slugs
from cfb_rankings.team_preview import resolve_slugs
from cfb_rankings.team_preview import evidence as evidence_module


class _FbsDB:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def query_all(self, sql: str, params: dict | None = None) -> list[dict]:
        self.queries.append(sql)
        return [{"slug": "akron"}, {"slug": "kennesaw-state"}]


def test_preview_default_targets_union_profiles_with_db_real_fbs(monkeypatch) -> None:
    monkeypatch.setattr(
        evidence_module,
        "canonical_fbs_slugs",
        lambda: frozenset({"alabama", "bowling-green"}),
    )

    slugs = evidence_module.canonical_fbs_slugs_for_db(_FbsDB())

    assert slugs == ["akron", "alabama", "bowling-green", "kennesaw-state"]


def test_preview_resolve_slugs_uses_db_aware_default(monkeypatch) -> None:
    monkeypatch.setattr(
        evidence_module,
        "canonical_fbs_slugs",
        lambda: frozenset({"alabama"}),
    )

    assert resolve_slugs(_FbsDB(), None) == ["akron", "alabama", "kennesaw-state"]
    assert resolve_slugs(_FbsDB(), ["notre-dame"]) == ["notre-dame"]


def test_team_page_real_fbs_filter_includes_mid_american_alias() -> None:
    db = _FbsDB()

    assert list_real_fbs_slugs(db) == ["akron", "kennesaw-state"]
    assert "Mid-American" in db.queries[0]
