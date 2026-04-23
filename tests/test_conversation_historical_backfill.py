from __future__ import annotations

from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.conversation import (
    build_conversation_features,
    collect_reddit_comments_for_posts,
    collect_reddit_watchlist,
    purge_reddit_raw_content,
)
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.storage import Repository, TeamIdentity


class FakeHistoricalClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.counter = 0

    def search_posts(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "subreddit": subreddit, "after": after, "before": before})
        self.counter += 1
        return [
            {
                "name": f"t3_fake_{self.counter}",
                "id": f"fake_{self.counter}",
                "title": "Indiana football title talk",
                "selftext": "Indiana fans are still processing football history.",
                "author": f"fan{self.counter}",
                "author_fullname": f"t2_fan{self.counter}",
                "subreddit": subreddit or "CFB",
                "permalink": f"/r/{subreddit or 'CFB'}/comments/fake_{self.counter}/",
                "created_utc": 1770000000 + self.counter,
                "ups": 5,
                "num_comments": 2,
            }
        ]

    def list_post_comments(
        self,
        post_id: str,
        limit: int = 100,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": f"t1_comment_{post_id}",
                "id": f"comment_{post_id}",
                "body": "Indiana fans are loud and hopeful in the comments.",
                "author": "commenter1",
                "author_fullname": "t2_commenter1",
                "subreddit": "CFB",
                "permalink": f"/r/CFB/comments/{post_id}/_/{post_id}/",
                "created_utc": 1770000100,
                "ups": 3,
                "link_id": f"t3_{post_id}",
                "author_flair_text": "",
                "author_flair_css_class": "",
            }
        ]


class NeutralCommentClient(FakeHistoricalClient):
    def list_post_comments(
        self,
        post_id: str,
        limit: int = 100,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": f"t1_neutral_{post_id}",
                "id": f"neutral_{post_id}",
                "body": "What a wild thread.",
                "author": "neutral1",
                "author_fullname": "t2_neutral1",
                "subreddit": "CFB",
                "permalink": f"/r/CFB/comments/{post_id}/_/{post_id}/",
                "created_utc": 1770000100,
                "ups": 3,
                "link_id": f"t3_{post_id}",
                "author_flair_text": "",
                "author_flair_css_class": "",
            }
        ]


def _test_db(tmp_path: Path) -> tuple[Database, Repository]:
    db = Database(f"sqlite:///{tmp_path / 'test.db'}")
    schema = Path(__file__).resolve().parents[1] / "research" / "cfb-data-schema-sqlite.sql"
    db.apply_sql_file(schema)
    apply_runtime_migrations(db)
    repository = Repository(db)
    repository.seed_levels()
    repository.ensure_season(2025)
    team_id = repository.get_or_create_team(
        "test",
        "indiana",
        TeamIdentity(canonical_name="Indiana", level_code="FBS", conference_name="Big Ten"),
    )
    repository.upsert_team_season(team_id=team_id, season_year=2025, level_code="FBS", conference_name="Big Ten")
    return db, repository


def test_collect_watchlist_passes_historical_bounds_and_preserves_incremental_targets(tmp_path: Path) -> None:
    db, repository = _test_db(tmp_path)
    client = FakeHistoricalClient()

    first = collect_reddit_watchlist(
        repository=repository,
        db=db,
        client=client,
        season=2025,
        week=21,
        team_names=["Indiana"],
        subreddit="CFB",
        audience_bucket="national",
        search_limit=1,
        after=1768194000,
        before=1768280400,
        provider_name="arctic_shift",
        replace_existing=True,
    )
    second = collect_reddit_watchlist(
        repository=repository,
        db=db,
        client=client,
        season=2025,
        week=21,
        team_names=["Indiana"],
        subreddit="CFB",
        audience_bucket="national",
        search_limit=1,
        after=1768280400,
        before=1768366800,
        provider_name="arctic_shift",
        replace_existing=False,
    )

    assert first["target_count"] == 1
    assert second["target_count"] == 1
    assert client.calls[0]["after"] == 1768194000
    assert client.calls[1]["before"] == 1768366800
    target_count = db.query_one(
        """
        select count(*) as count
        from conversation_document_targets
        where season_year = 2025 and week = 21
        """
    )
    assert target_count is not None
    assert int(target_count["count"]) == 2
    run = db.query_one(
        """
        select raw_config_json
        from conversation_collection_runs
        order by conversation_collection_run_id desc
        limit 1
        """
    )
    assert run is not None
    assert '"provider": "arctic_shift"' in str(run["raw_config_json"])
    assert '"replace_existing": false' in str(run["raw_config_json"])


def test_collect_comments_inherits_parent_targets_and_purge_waits_for_features(tmp_path: Path) -> None:
    db, repository = _test_db(tmp_path)
    client = FakeHistoricalClient()
    collect_reddit_watchlist(
        repository=repository,
        db=db,
        client=client,
        season=2025,
        week=21,
        team_names=["Indiana"],
        subreddit="CFB",
        audience_bucket="national",
        search_limit=1,
        provider_name="arctic_shift",
        replace_existing=True,
    )

    summary = collect_reddit_comments_for_posts(
        db=db,
        client=client,
        season=2025,
        week=21,
        provider_name="arctic_shift",
        min_post_comments=1,
        comments_per_post=10,
    )

    assert summary["document_count"] == 1
    assert summary["target_count"] == 1
    comment_row = db.query_one(
        """
        select cd.content_type, cd.body_text, cdt.mention_role, cdt.target_label
        from conversation_documents cd
        join conversation_document_targets cdt on cdt.conversation_document_id = cd.conversation_document_id
        where cd.content_type = 'comment'
        """
    )
    assert comment_row is not None
    assert comment_row["mention_role"] == "comment-thread"
    assert comment_row["target_label"] == "Indiana"

    dry_before = purge_reddit_raw_content(
        db=db,
        source_name="reddit",
        cutoff_utc="2099-01-01 00:00:00",
        dry_run=True,
        require_weekly_features=True,
    )
    assert dry_before["documents_examined"] == 0

    build_conversation_features(db=db, season=2025, week=21, source_name="reddit")
    purged = purge_reddit_raw_content(
        db=db,
        source_name="reddit",
        cutoff_utc="2099-01-01 00:00:00",
        dry_run=False,
        require_weekly_features=True,
    )
    assert purged["documents_purged"] == 2
    retained = db.query_one(
        """
        select count(*) as count
        from conversation_documents
        where coalesce(body_text, '') <> ''
           or coalesce(title_text, '') <> ''
           or raw_payload_json is not null
           or coalesce(source_author_name, '') <> ''
        """
    )
    assert retained is not None
    assert int(retained["count"]) == 0


def test_collect_comments_skips_generic_comments_on_multi_team_threads(tmp_path: Path) -> None:
    db, repository = _test_db(tmp_path)
    oregon_id = repository.get_or_create_team(
        "test",
        "oregon",
        TeamIdentity(canonical_name="Oregon", level_code="FBS", conference_name="Big Ten"),
    )
    repository.upsert_team_season(team_id=oregon_id, season_year=2025, level_code="FBS", conference_name="Big Ten")
    client = NeutralCommentClient()
    collect_reddit_watchlist(
        repository=repository,
        db=db,
        client=client,
        season=2025,
        week=21,
        team_names=["Indiana"],
        subreddit="CFB",
        audience_bucket="national",
        search_limit=1,
        provider_name="arctic_shift",
        replace_existing=True,
    )
    parent = db.query_one("select conversation_document_id from conversation_documents where content_type = 'post' limit 1")
    assert parent is not None
    db.upsert_many(
        "conversation_document_targets",
        [
            {
                "conversation_document_id": parent["conversation_document_id"],
                "season_year": 2025,
                "week": 21,
                "game_id": None,
                "team_id": oregon_id,
                "player_id": None,
                "target_type": "team",
                "target_key": f"team:{oregon_id}",
                "target_label": "Oregon",
                "affiliation_team_id": None,
                "audience_bucket": "national",
                "mention_role": "query-match",
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "emotion_primary": "trust",
                "emotion_secondary": None,
                "sarcasm_score": 0.0,
                "toxicity_score": 0.0,
                "confidence_score": 0.5,
                "model_provider": "local",
                "model_name": "test",
                "model_version": "test",
                "is_primary_target": 1,
                "notes": "test",
            }
        ],
        conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
    )

    summary = collect_reddit_comments_for_posts(
        db=db,
        client=client,
        season=2025,
        week=21,
        provider_name="arctic_shift",
        min_post_comments=1,
        comments_per_post=10,
    )

    assert summary["document_count"] == 1
    assert summary["target_count"] == 0
    assert summary["skipped_no_target"] == 1
