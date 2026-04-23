from __future__ import annotations

from typing import Any

from cfb_rankings.clients.reddit import RedditPublicClient
from cfb_rankings.clients.reddit_arctic_shift import ArcticShiftClient
from cfb_rankings.clients.reddit_pullpush import PullpushClient


def create_historical_reddit_client(provider: str, timeout_seconds: float) -> Any:
    normalized = normalize_historical_provider(provider)
    if normalized == "reddit":
        return RedditPublicClient(timeout_seconds=timeout_seconds)
    if normalized == "arctic_shift":
        return ArcticShiftClient(timeout_seconds=timeout_seconds)
    if normalized == "pullpush":
        return PullpushClient(timeout_seconds=timeout_seconds)
    raise ValueError(f"Unsupported Reddit provider: {provider}")


def normalize_historical_provider(provider: str) -> str:
    normalized = (provider or "arctic-shift").strip().lower().replace("-", "_")
    if normalized in {"arctic", "arcticshift"}:
        return "arctic_shift"
    if normalized in {"public", "reddit_public"}:
        return "reddit"
    return normalized
