from __future__ import annotations

import pytest

responses = pytest.importorskip(
    "responses",
    reason="responses package not installed in this environment",
)

from cfb_rankings.clients.reddit_arctic_shift import ArcticShiftClient  # noqa: E402


@responses.activate
def test_arctic_shift_search_posts_uses_date_bounds_and_normalizes_rows() -> None:
    responses.add(
        responses.GET,
        "https://arctic-shift.photon-reddit.com/api/posts/search",
        json={
            "data": [
                {
                    "id": "abc123",
                    "author": "fan1",
                    "subreddit": "CFB",
                    "title": "Indiana spring football",
                    "selftext": "Indiana still feels different.",
                    "created_utc": 1771000000,
                    "score": 42,
                    "num_comments": 7,
                }
            ]
        },
        status=200,
    )

    client = ArcticShiftClient(timeout_seconds=3)
    rows = client.search_posts(
        query='"Indiana"',
        subreddit="CFB",
        limit=250,
        after=1768194000,
        before=1768798800,
    )

    assert rows == [
        {
            "name": "t3_abc123",
            "id": "abc123",
            "title": "Indiana spring football",
            "selftext": "Indiana still feels different.",
            "author": "fan1",
            "author_fullname": "",
            "subreddit": "CFB",
            "permalink": "/r/CFB/comments/abc123/",
            "created_utc": 1771000000.0,
            "ups": 42,
            "num_comments": 7,
            "view_count": None,
            "removed_by_category": None,
            "_provider": "arctic_shift",
            "_raw": {
                "id": "abc123",
                "author": "fan1",
                "subreddit": "CFB",
                "title": "Indiana spring football",
                "selftext": "Indiana still feels different.",
                "created_utc": 1771000000,
                "score": 42,
                "num_comments": 7,
            },
        }
    ]
    request = responses.calls[0].request
    assert "after=1768194000" in request.url
    assert "before=1768798800" in request.url
    assert "limit=100" in request.url
    assert "subreddit=CFB" in request.url


@responses.activate
def test_arctic_shift_list_post_comments_flattens_tree() -> None:
    responses.add(
        responses.GET,
        "https://arctic-shift.photon-reddit.com/api/comments/tree",
        json={
            "data": [
                {
                    "id": "c1",
                    "kind": "t1",
                    "data": {
                        "id": "c1",
                        "author": "fan2",
                        "subreddit": "CFB",
                        "body": "Indiana fans are everywhere now.",
                        "created_utc": 1771000100,
                        "score": 8,
                        "link_id": "t3_abc123",
                        "children": [
                            {
                                "id": "c2",
                                "author": "fan3",
                                "subreddit": "CFB",
                                "body": "The title changed the whole mood.",
                                "created_utc": 1771000200,
                                "score": 3,
                                "link_id": "t3_abc123",
                            }
                        ],
                    },
                }
            ]
        },
        status=200,
    )

    client = ArcticShiftClient(timeout_seconds=3)
    rows = client.list_post_comments(post_id="abc123", limit=250)

    assert [row["name"] for row in rows] == ["t1_c1", "t1_c2"]
    assert rows[0]["body"] == "Indiana fans are everywhere now."
    assert rows[0]["link_id"] == "t3_abc123"
    assert rows[0]["author_flair_text"] == ""
    request = responses.calls[0].request
    assert "link_id=t3_abc123" in request.url
    assert "limit=250" in request.url
