from __future__ import annotations

from pathlib import Path

from cfb_rankings import cli
from cfb_rankings.cli import build_parser


ROOT = Path(__file__).resolve().parents[1]


def test_build_team_preview_layer_parser_defaults_to_publish_context():
    parser = build_parser()
    args = parser.parse_args(["build-team-preview-layer"])

    assert args.season is None
    assert args.as_of is None
    assert args.slug is None
    assert args.allow_empty is False


def test_team_preview_claim_cli_commands_parse():
    parser = build_parser()
    args = parser.parse_args([
        "generate-team-preview-claims",
        "--season", "2026",
        "--as-of", "2026-05-26",
        "--slug", "alabama",
    ])
    assert args.season == 2026
    assert args.as_of == "2026-05-26"
    assert args.slug == ["alabama"]
    assert args.allow_cloud is False

    status_args = parser.parse_args(["team-preview-llm-status"])
    assert status_args.allow_cloud is False


def test_publish_outputs_refreshes_team_preview_layer_before_render(monkeypatch):
    events: list[str] = []

    def fake_preview(db):
        events.append("preview")

    def fake_report(*, db, output_path, limit):
        events.append("report")
        return Path(output_path)

    def fake_site(*, db, output_dir):
        events.append("site")
        return Path(output_dir)

    monkeypatch.setattr(cli, "_try_build_team_preview_layer_for_publish", fake_preview)
    monkeypatch.setattr("cfb_rankings.reporting.write_latest_rankings_report", fake_report)
    monkeypatch.setattr("cfb_rankings.reporting.build_static_site", fake_site)

    cli._publish_outputs(
        db=object(),
        output_path="output/rankings.html",
        site_output_dir="output/site",
        limit=100,
    )

    assert events == ["preview", "report", "site"]


def test_publish_workflow_runs_team_preview_layer_before_site_build():
    workflow = (ROOT / ".github" / "workflows" / "publish_site.yml").read_text()
    preview_idx = workflow.index("python -u manage.py build-team-preview-layer")
    claims_idx = workflow.index("python -u manage.py generate-team-preview-claims")
    build_idx = workflow.index("Build or incrementally sync")

    assert preview_idx < build_idx
    assert preview_idx < claims_idx < build_idx
    assert "continue-on-error: true" in workflow


def test_local_daily_ingest_runs_team_preview_layer_before_build_site():
    script = (ROOT / "scripts" / "daily_ingest.ps1").read_text()
    preview_idx = script.index("team-preview: build-team-preview-layer")
    claims_idx = script.index("team-preview: generate-team-preview-claims")
    build_idx = script.index("site: build-site")

    assert preview_idx < build_idx
    assert preview_idx < claims_idx < build_idx


def test_local_publish_script_generates_claims_before_build_published():
    script = (ROOT / "publish_site.ps1").read_text()
    preview_idx = script.index("build-team-preview-layer")
    claims_idx = script.index("generate-team-preview-claims")
    build_idx = script.index("build-published")

    assert preview_idx < claims_idx < build_idx
