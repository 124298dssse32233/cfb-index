"""Regression tests for PolymarketAdapter.parse (WP-1.4).

Polymarket's gamma API returns `outcomePrices` as a JSON-ENCODED STRING
(e.g. '["0.62", "0.38"]'), not a native array. The adapter previously indexed
the raw value, so `outcomes[0]` was the char '[' and `float('[')` raised ->
prob_yes was silently dropped for 100% of contracts (verified 2026-06-11:
source_observations had 0 prob_yes rows despite ~300 polymarket rows). These
tests pin the string-decoding behaviour and the native-list regression path.
"""
from __future__ import annotations

from cfb_rankings.ingest.sources.prediction_markets import PolymarketAdapter


def _prob_rows(rows):
    return [r for r in rows if r.get("metric") == "prob_yes"]


def test_outcomeprices_json_string_is_decoded():
    """The real Polymarket shape: outcomePrices as a JSON-encoded string."""
    adapter = PolymarketAdapter(db=None)  # parse() does not touch self.db
    raw = [(
        {"slug": "team-x-champ", "label": "Team X win title"},
        {"slug": "team-x-champ", "question": "Team X win title",
         "outcomePrices": '["0.125", "0.875"]', "volume": 1000},
    )]
    prob = _prob_rows(adapter.parse(raw))
    assert len(prob) == 1, "prob_yes row must be produced from a JSON-string payload"
    assert abs(prob[0]["value_numeric"] - 0.125) < 1e-9


def test_outcomeprices_native_list_still_works():
    """Regression: a native-array payload must keep working unchanged."""
    adapter = PolymarketAdapter(db=None)
    raw = [(
        {"slug": "y", "label": "Y"},
        {"slug": "y", "outcomePrices": ["0.4", "0.6"], "volume": 5},
    )]
    prob = _prob_rows(adapter.parse(raw))
    assert len(prob) == 1
    assert abs(prob[0]["value_numeric"] - 0.4) < 1e-9


def test_outcomeprices_malformed_string_is_safe():
    """A non-JSON / malformed string must not crash and must not emit prob_yes."""
    adapter = PolymarketAdapter(db=None)
    raw = [(
        {"slug": "z", "label": "Z"},
        {"slug": "z", "outcomePrices": "not-json", "volume": 7},
    )]
    rows = adapter.parse(raw)
    assert _prob_rows(rows) == []          # no bogus probability
    assert any(r["metric"] == "volume_usd" for r in rows)  # volume still captured
