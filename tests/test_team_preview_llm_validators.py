from __future__ import annotations

from cfb_rankings.chronicle.runtime import GenerationConfig, GenerationResult
from cfb_rankings.team_preview import llm_synthesis
from cfb_rankings.team_preview.prompts import PreviewClaimCandidate
from cfb_rankings.team_preview.validators import validate_preview_claim


def _evidence(fan_ready: bool = False) -> dict:
    return {
        "team": {
            "team_id": 1,
            "slug": "alabama",
            "name": "Alabama",
            "season_year": 2026,
            "as_of_date": "2026-05-26",
        },
        "season_path": {
            "base": {"final_wins": 11, "final_losses": 2},
            "ceiling": {"final_wins": 16, "final_losses": 0},
        },
        "roster_reload_summary": {
            "transfer_in_count": 17,
            "transfer_out_count": 24,
            "drafted_count": 10,
            "recruiting_rank": 3,
            "returning_total_pct": 43,
        },
        "fan_intel": {"ready": fan_ready, "effective_n": 0},
        "evidence_hash": "abc123",
    }


def test_valid_preview_claim_passes_when_numbers_are_supported() -> None:
    candidate = {
        "headline": "Alabama has a 16-0 ceiling if the reload lands",
        "body": "The base case sits at 11-2, but the roster math still carries a 16-0 top end. Portal movement is split: 17 additions, 24 losses, and 10 draft exits.",
        "supporting_claims": [
            {
                "kind": "record_projection",
                "text": "Base projects to 11-2 and ceiling projects to 16-0.",
                "evidence_key": "season_path.ceiling.final_wins",
                "numeric_values": [11, 2, 16, 0],
            },
            {
                "kind": "portal",
                "text": "Portal flow is 17 additions and 24 losses.",
                "evidence_key": "roster_reload_summary.transfer_in_count",
                "numeric_values": [17, 24],
            },
            {
                "kind": "draft",
                "text": "Draft exits total 10.",
                "evidence_key": "roster_reload_summary.drafted_count",
                "numeric_values": [10],
            },
        ],
        "confidence_band": "medium",
    }

    result = validate_preview_claim(candidate, _evidence())

    assert result.passed
    assert result.fact_score == 1.0


def test_unsupported_numeric_claim_is_rejected() -> None:
    candidate = {
        "headline": "Alabama should go 15-0",
        "body": "The preview says 15-0, which is not one of the deterministic paths.",
        "supporting_claims": [
            {
                "kind": "record_projection",
                "text": "Unsupported 15-0 claim.",
                "evidence_key": "season_path.ceiling.final_wins",
                "numeric_values": [15, 0],
            }
        ],
        "confidence_band": "high",
    }

    result = validate_preview_claim(candidate, _evidence())

    assert not result.passed
    assert "unsupported_numeric_value:15" in result.errors
    assert "unsupported_numeric_text:15" in result.errors


def test_fan_intel_claim_is_rejected_when_readiness_is_false() -> None:
    candidate = {
        "headline": "Fans expect the reload to hit",
        "body": "The fanbase expects the portal reset to work.",
        "supporting_claims": [
            {
                "kind": "fan_intel",
                "text": "Fans expect improvement.",
                "evidence_key": "fan_intel.ready",
                "numeric_values": [],
            }
        ],
        "confidence_band": "low",
    }

    result = validate_preview_claim(candidate, _evidence(fan_ready=False))

    assert not result.passed
    assert "fan_intel_not_ready" in result.errors


def test_non_ascii_claim_text_is_rejected() -> None:
    candidate = {
        "headline": "Alabama's reload hinges on 尽管",
        "body": "The base case sits at 11-2.",
        "supporting_claims": [
            {
                "kind": "record_projection",
                "text": "Base case is 11-2.",
                "evidence_key": "season_path.base.final_wins",
                "numeric_values": [11, 2],
            }
        ],
        "confidence_band": "medium",
    }

    result = validate_preview_claim(candidate, _evidence())

    assert not result.passed
    assert "non_ascii_text" in result.errors


def test_sentence_fragments_are_rejected() -> None:
    candidate = {
        "headline": "Alabama has a 16-0 ceiling despite",
        "body": "a base case that sits at 11-2.",
        "supporting_claims": [
            {
                "kind": "record_projection",
                "text": "Base case is 11-2.",
                "evidence_key": "season_path.base.final_wins",
                "numeric_values": [11, 2],
            }
        ],
        "confidence_band": "medium",
    }

    result = validate_preview_claim(candidate, _evidence())

    assert not result.passed
    assert "headline_fragment" in result.errors
    assert "body_fragment" in result.errors


def test_approximate_rank_and_missing_numeric_receipts_are_rejected() -> None:
    candidate = {
        "headline": "Alabama leans on a top-10 recruiting class",
        "body": "The reload includes 17 transfer additions.",
        "supporting_claims": [
            {
                "kind": "recruiting",
                "text": "Recruiting rank is #3.",
                "evidence_key": "roster_reload_summary.recruiting_rank",
                "numeric_values": [],
            }
        ],
        "confidence_band": "medium",
    }

    result = validate_preview_claim(candidate, _evidence())

    assert not result.passed
    assert "approximate_rank_phrase" in result.errors
    assert "numeric_text_missing_receipt:3" in result.errors
    assert "numeric_text_missing_receipt:17" in result.errors


class _FakeBackend:
    name = "fake-local"
    model_id = "fake-model"

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[PreviewClaimCandidate],
        config: GenerationConfig,
    ):
        candidate = schema_model(
            headline="Alabama has a 16-0 ceiling if the reload lands",
            body="The base case sits at 11-2, while the ceiling remains 16-0. The roster picture is separated cleanly: 17 portal additions, 24 portal losses, and 10 draft exits.",
            supporting_claims=[
                {
                    "kind": "record_projection",
                    "text": "Base projects to 11-2 and ceiling projects to 16-0.",
                    "evidence_key": "season_path.ceiling.final_wins",
                    "numeric_values": [11, 2, 16, 0],
                },
                {
                    "kind": "draft",
                    "text": "Draft exits total 10.",
                    "evidence_key": "roster_reload_summary.drafted_count",
                    "numeric_values": [10],
                },
                {
                    "kind": "portal",
                    "text": "Portal flow is 17 additions and 24 losses.",
                    "evidence_key": "roster_reload_summary.transfer_in_count",
                    "numeric_values": [17, 24],
                }
            ],
            confidence_band="medium",
        )
        return candidate, GenerationResult(
            text=candidate.model_dump_json(),
            tokens_in=100,
            tokens_out=60,
            wall_clock_ms=10,
            finish_reason="stop",
            model_id=self.model_id,
            model_version="test",
            backend=self.name,
        )


class _FakeRouter:
    def select(self, tier, role):
        return _FakeBackend()


class _RetryBackend:
    name = "fake-local"
    model_id = "fake-model"

    def __init__(self):
        self.calls = 0

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[PreviewClaimCandidate],
        config: GenerationConfig,
    ):
        self.calls += 1
        if self.calls == 1:
            candidate = schema_model(
                headline="Alabama should go 15-0",
                body="The preview says 15-0.",
                supporting_claims=[
                    {
                        "kind": "record_projection",
                        "text": "Unsupported 15-0 claim.",
                        "evidence_key": "season_path.ceiling.final_wins",
                        "numeric_values": [15, 0],
                    }
                ],
                confidence_band="medium",
            )
        else:
            candidate = schema_model(
                headline="Alabama has a 16-0 ceiling if the reload lands",
                body="The base case sits at 11-2, while the ceiling remains 16-0.",
                supporting_claims=[
                    {
                        "kind": "record_projection",
                        "text": "Base projects to 11-2 and ceiling projects to 16-0.",
                        "evidence_key": "season_path.ceiling.final_wins",
                        "numeric_values": [11, 2, 16, 0],
                    }
                ],
                confidence_band="medium",
            )
        return candidate, GenerationResult(
            text=candidate.model_dump_json(),
            tokens_in=100,
            tokens_out=60,
            wall_clock_ms=10,
            finish_reason="stop",
            model_id=self.model_id,
            model_version="test",
            backend=self.name,
        )


class _RetryRouter:
    def __init__(self):
        self.backend = _RetryBackend()

    def select(self, tier, role):
        return self.backend


def test_generate_claims_writes_only_validated_cache_rows(monkeypatch) -> None:
    writes: list[dict] = []
    monkeypatch.setattr(
        llm_synthesis,
        "build_preview_evidence",
        lambda db, slug, season_year, as_of_date: _evidence(),
    )

    def fake_write(db, **kwargs):
        writes.append(kwargs)
        return "claim-key"

    monkeypatch.setattr(llm_synthesis, "write_preview_claim_cache", fake_write)
    monkeypatch.setattr(llm_synthesis, "_log_usage", lambda **kwargs: None)

    report = llm_synthesis.generate_team_preview_claims(
        object(),
        season_year=2026,
        as_of_date="2026-05-26",
        slugs=["alabama"],
        router=_FakeRouter(),
    )

    assert report.approved == 1
    assert report.rejected == 0
    assert writes[0]["confidence_band"] == "medium"
    assert writes[0]["model_backend"] == "fake-local"


def test_generate_claims_retries_once_after_validator_reject(monkeypatch) -> None:
    writes: list[dict] = []
    router = _RetryRouter()
    monkeypatch.setattr(
        llm_synthesis,
        "build_preview_evidence",
        lambda db, slug, season_year, as_of_date: _evidence(),
    )
    monkeypatch.setattr(
        llm_synthesis,
        "write_preview_claim_cache",
        lambda db, **kwargs: writes.append(kwargs) or "claim-key",
    )
    monkeypatch.setattr(llm_synthesis, "_log_usage", lambda **kwargs: None)

    report = llm_synthesis.generate_team_preview_claims(
        object(),
        season_year=2026,
        as_of_date="2026-05-26",
        slugs=["alabama"],
        router=router,
    )

    assert router.backend.calls == 2
    assert report.approved == 1
    assert report.rejected == 0
    assert writes[0]["claim_payload"]["headline"].startswith("Alabama has a 16-0")
