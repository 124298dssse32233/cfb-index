from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database
from cfb_rankings.storage import Repository

_CONTENT_TYPE_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _ext_from_response(resp: requests.Response, url: str) -> str:
    """Determine file extension from Content-Type header or URL suffix."""
    ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if ct in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[ct]
    # Fall back to URL suffix
    url_path = url.split("?")[0]
    suffix = Path(url_path).suffix.lower()
    if suffix in {".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif"}:
        return suffix
    return ".png"


def _fetch_with_retry(url: str, max_retries: int = 3) -> requests.Response | None:
    """HTTP GET with up to 3 retries and exponential backoff (2→4→8s)."""
    delays = [2, 4, 8]
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                timeout=3,
                stream=False,
                headers={"User-Agent": "cfb-index/1.0"},
            )
            if resp.ok:
                return resp
            print(
                f"[team-brand] HTTP {resp.status_code} fetching {url} (attempt {attempt + 1}/{max_retries})",
                flush=True,
            )
        except requests.RequestException as exc:
            print(
                f"[team-brand] request error fetching {url}: {exc} (attempt {attempt + 1}/{max_retries})",
                flush=True,
            )
        if attempt < max_retries - 1:
            time.sleep(delays[attempt])
    return None


def _upsert_brand_row(db: Database, team_id: int, team: dict[str, Any]) -> None:
    """DELETE + INSERT for team_brand row."""
    db.execute("DELETE FROM team_brand WHERE team_id = %(team_id)s", {"team_id": team_id})
    db.execute(
        """
        INSERT INTO team_brand
            (team_id, primary_color, secondary_color, mascot_name, abbreviation_short,
             source_name, source_updated_utc)
        VALUES
            (%(team_id)s, %(primary_color)s, %(secondary_color)s, %(mascot_name)s,
             %(abbreviation_short)s, %(source_name)s, %(source_updated_utc)s)
        """,
        {
            "team_id": team_id,
            "primary_color": team.get("color"),
            "secondary_color": team.get("altColor"),
            "mascot_name": team.get("mascot"),
            "abbreviation_short": team.get("abbreviation"),
            "source_name": "cfbd",
            "source_updated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )


def _upsert_asset_row(
    db: Database,
    team_id: int,
    asset_kind: str,
    variant: str | None,
    source_url: str,
    local_path: str,
    content_hash: str,
    width: int | None,
    height: int | None,
) -> None:
    """DELETE + INSERT for team_brand_assets row."""
    db.execute(
        """
        DELETE FROM team_brand_assets
        WHERE team_id = %(team_id)s
          AND asset_kind = %(asset_kind)s
          AND variant IS %(variant)s
          AND source_name = 'cfbd'
        """,
        {"team_id": team_id, "asset_kind": asset_kind, "variant": variant},
    )
    db.execute(
        """
        INSERT INTO team_brand_assets
            (team_id, asset_kind, variant, source_name, source_url, local_path,
             content_hash, width, height, fetched_at_utc, is_active)
        VALUES
            (%(team_id)s, %(asset_kind)s, %(variant)s, 'cfbd', %(source_url)s, %(local_path)s,
             %(content_hash)s, %(width)s, %(height)s, %(fetched_at_utc)s, 1)
        """,
        {
            "team_id": team_id,
            "asset_kind": asset_kind,
            "variant": variant,
            "source_url": source_url,
            "local_path": local_path,
            "content_hash": content_hash,
            "width": width,
            "height": height,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )


def sync_team_brand_assets(
    *,
    repository: Repository,
    db: Database,
    client: CfbdClient,
    year: int | None = None,
    classification: str = "fbs",
    refresh_assets: bool = False,
    site_root: Path = Path("output/site"),
) -> None:
    """Sync team brand data and logos from CFBD into the local DB and site assets."""
    if year is None:
        year = datetime.utcnow().year

    print(f"[team-brand] fetching teams year={year} classification={classification}", flush=True)
    teams = client.get_teams(year=year, classification=classification)
    if not teams:
        print("[team-brand] no teams returned from CFBD", flush=True)
        return

    synced_teams = 0
    new_files = 0
    skipped = 0
    failed = 0

    # manifest: slug -> {asset_kind: site_relative_path}
    manifest: dict[str, dict[str, str]] = {}

    for team in teams:
        cfbd_id = team.get("id")
        school = team.get("school", "")

        # Resolve local team_id via team_source_ids
        row = db.query_one(
            """
            SELECT team_id FROM team_source_ids
            WHERE source_name = 'cfbd' AND source_team_id = %(sid)s
            """,
            {"sid": str(cfbd_id)},
        )
        if not row:
            print(f"[team-brand] skip unresolved cfbd_id={cfbd_id} school={school}", flush=True)
            continue

        team_id: int = row["team_id"]

        # Fetch slug from teams table
        slug_row = db.query_one(
            "SELECT slug FROM teams WHERE team_id = %(team_id)s",
            {"team_id": team_id},
        )
        slug: str = slug_row["slug"] if slug_row and slug_row.get("slug") else str(team_id)

        # Upsert team_brand row
        _upsert_brand_row(db, team_id, team)

        # Update teams.cfbd_classification
        db.execute(
            "UPDATE teams SET cfbd_classification = %(cls)s WHERE team_id = %(team_id)s",
            {"cls": team.get("classification"), "team_id": team_id},
        )

        synced_teams += 1

        # Process logos
        logos = team.get("logos") or []
        primary_logo_cached = False  # track whether primary logo succeeded this iteration
        team_art_dir = site_root / "assets" / "team-art" / slug

        if not logos:
            pass  # fallback block below will handle mkdir if needed
        else:
            team_art_dir.mkdir(parents=True, exist_ok=True)

        for idx, logo_url in enumerate(logos):
            if idx == 0:
                asset_kind = "logo_primary"
                variant: str | None = None
            elif idx == 1:
                asset_kind = "logo_dark"
                variant = None
            else:
                asset_kind = "logo_alt"
                variant = str(idx - 1)  # '1', '2', ...

            # Check existing active row with matching hash (only if not refresh_assets)
            if not refresh_assets:
                # We need to check AFTER fetching the new hash; instead, check current row
                existing = db.query_one(
                    """
                    SELECT content_hash FROM team_brand_assets
                    WHERE team_id = %(team_id)s
                      AND asset_kind = %(asset_kind)s
                      AND ((variant IS NULL AND %(variant)s IS NULL) OR variant = %(variant)s)
                      AND source_name = 'cfbd'
                      AND is_active = 1
                    """,
                    {"team_id": team_id, "asset_kind": asset_kind, "variant": variant},
                )
            else:
                existing = None

            # Fetch the asset
            resp = _fetch_with_retry(logo_url)
            if resp is None:
                print(
                    f"[team-brand] failed to fetch {asset_kind} for {school} ({logo_url})",
                    flush=True,
                )
                failed += 1
                continue

            data = resp.content
            new_hash = hashlib.sha256(data).hexdigest()

            # Skip if hash matches and not forcing refresh
            if existing and existing.get("content_hash") == new_hash and not refresh_assets:
                skipped += 1
                if idx == 0:
                    primary_logo_cached = True
                # Still populate manifest from existing DB row
                local_row = db.query_one(
                    """
                    SELECT local_path FROM team_brand_assets
                    WHERE team_id = %(team_id)s
                      AND asset_kind = %(asset_kind)s
                      AND ((variant IS NULL AND %(variant)s IS NULL) OR variant = %(variant)s)
                      AND source_name = 'cfbd'
                      AND is_active = 1
                    """,
                    {"team_id": team_id, "asset_kind": asset_kind, "variant": variant},
                )
                if local_row and local_row.get("local_path"):
                    manifest.setdefault(slug, {})[asset_kind] = local_row["local_path"]
                continue

            # Determine extension and build paths
            ext = _ext_from_response(resp, logo_url)
            variant_suffix = f"_{variant}" if variant else ""
            filename = f"{asset_kind}{variant_suffix}{ext}"
            final_path = team_art_dir / filename
            tmp_path = team_art_dir / f"{filename}.tmp"
            site_relative_path = f"/assets/team-art/{slug}/{filename}"

            # Atomic write
            tmp_path.write_bytes(data)
            os.replace(tmp_path, final_path)

            # Upsert DB row
            _upsert_asset_row(
                db=db,
                team_id=team_id,
                asset_kind=asset_kind,
                variant=variant,
                source_url=logo_url,
                local_path=site_relative_path,
                content_hash=new_hash,
                width=None,
                height=None,
            )

            manifest.setdefault(slug, {})[asset_kind] = site_relative_path
            new_files += 1
            if idx == 0:
                primary_logo_cached = True

        # ESPN CDN fallback: attempt if primary logo was not cached from CFBD
        if not primary_logo_cached and cfbd_id:
            espn_url = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{cfbd_id}.png"
            try:
                espn_resp = _fetch_with_retry(espn_url)
                if espn_resp is not None and espn_resp.status_code == 200:
                    espn_data = espn_resp.content
                    espn_hash = hashlib.sha256(espn_data).hexdigest()
                    team_art_dir.mkdir(parents=True, exist_ok=True)
                    espn_filename = "logo_primary.png"
                    espn_final_path = team_art_dir / espn_filename
                    espn_tmp_path = team_art_dir / f"{espn_filename}.tmp"
                    espn_site_path = f"/assets/team-art/{slug}/{espn_filename}"
                    espn_tmp_path.write_bytes(espn_data)
                    os.replace(espn_tmp_path, espn_final_path)
                    # Upsert DB row with source_name='espn_cdn'
                    db.execute(
                        """
                        DELETE FROM team_brand_assets
                        WHERE team_id = %(team_id)s
                          AND asset_kind = 'logo_primary'
                          AND variant IS NULL
                          AND source_name = 'espn_cdn'
                        """,
                        {"team_id": team_id},
                    )
                    db.execute(
                        """
                        INSERT INTO team_brand_assets
                            (team_id, asset_kind, variant, source_name, source_url, local_path,
                             content_hash, width, height, fetched_at_utc, is_active)
                        VALUES
                            (%(team_id)s, 'logo_primary', NULL, 'espn_cdn', %(source_url)s,
                             %(local_path)s, %(content_hash)s, NULL, NULL, %(fetched_at_utc)s, 1)
                        """,
                        {
                            "team_id": team_id,
                            "source_url": espn_url,
                            "local_path": espn_site_path,
                            "content_hash": espn_hash,
                            "fetched_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        },
                    )
                    manifest.setdefault(slug, {})["logo_primary"] = espn_site_path
                    new_files += 1
                    print(f"[team_brand] ESPN fallback succeeded for {slug}: {espn_url}", flush=True)
                else:
                    status = espn_resp.status_code if espn_resp is not None else "no response"
                    print(f"[team_brand] ESPN fallback failed for {slug}: HTTP {status}", flush=True)
            except Exception as exc:
                print(f"[team_brand] ESPN fallback failed for {slug}: HTTP {exc}", flush=True)

    # Write manifest
    manifest_dir = site_root / "assets" / "team-art"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "_manifest.json"
    manifest_data = {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "teams": manifest,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    print(
        f"[team-brand] synced {synced_teams} teams, {new_files} new files, "
        f"{skipped} skipped (hash match), {failed} failed",
        flush=True,
    )
