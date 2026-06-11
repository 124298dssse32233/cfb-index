"""Discourse Atlas — Language Layer Wave 4.

Pure-Python cosine-similarity k-means clustering of fanbases by their
fan-discourse term vectors (``team_discourse_terms`` week=0 rows).

Results are written to ``team_discourse_clusters`` when commit=True.

No third-party numeric dependencies — all vector math uses sparse dicts so
the module works in the same environment as the rest of the discourse package.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from .keyness import _row_get

# ---------------------------------------------------------------------------
# Sparse-vector helpers
# ---------------------------------------------------------------------------

def _dot(a: dict, b: dict) -> float:
    """Dot product of two sparse vectors (represented as {term: weight} dicts)."""
    # Iterate over the shorter dict for efficiency
    if len(a) > len(b):
        a, b = b, a
    total = 0.0
    for k, v in a.items():
        if k in b:
            total += v * b[k]
    return total


def _norm(v: dict) -> float:
    """L2 norm of a sparse vector."""
    return math.sqrt(sum(x * x for x in v.values()))


def _cosine(a: dict, b: dict) -> float:
    """Cosine similarity between two sparse vectors.  Returns 0.0 if either
    vector has zero norm (avoids division by zero)."""
    na = _norm(a)
    nb = _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


def _centroid(vectors: list[dict]) -> dict:
    """Element-wise mean of a list of sparse dicts.  Returns {} for empty list."""
    if not vectors:
        return {}
    acc: dict[str, float] = {}
    for v in vectors:
        for k, val in v.items():
            acc[k] = acc.get(k, 0.0) + val
    n = len(vectors)
    return {k: val / n for k, val in acc.items()}


def _kmeans(vectors: list[dict], k: int, max_iter: int = 20) -> list[int]:
    """k-means clustering using cosine similarity.

    Initialisation: first centroid = first vector; each subsequent centroid is
    the vector *farthest* (lowest cosine similarity) from all already-chosen
    centroids.  This is a cosine-space variant of k-means++ spread init.

    Returns a list of cluster IDs (0 … k-1), one per input vector.
    """
    n = len(vectors)
    if n == 0:
        return []
    k = min(k, n)

    # --- initialise centroids via farthest-point spread ---
    centroid_indices: list[int] = [0]
    for _ in range(1, k):
        # for each candidate vector, compute min similarity to already chosen centroids
        min_sims = []
        for i, v in enumerate(vectors):
            min_sim = min(_cosine(v, vectors[ci]) for ci in centroid_indices)
            min_sims.append(min_sim)
        # pick the vector with the lowest max-similarity (i.e. farthest away)
        next_idx = min_sims.index(min(min_sims))
        centroid_indices.append(next_idx)

    centroids: list[dict] = [vectors[i].copy() for i in centroid_indices]

    assignments: list[int] = [0] * n

    for _iteration in range(max_iter):
        # --- assignment step ---
        new_assignments: list[int] = []
        for v in vectors:
            sims = [_cosine(v, c) for c in centroids]
            new_assignments.append(sims.index(max(sims)))

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # --- update step: recompute centroids ---
        for cid in range(k):
            members = [vectors[i] for i, a in enumerate(assignments) if a == cid]
            if members:
                centroids[cid] = _centroid(members)
            # if a cluster is empty keep its old centroid to avoid degenerate state

    return assignments


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_discourse_atlas(
    db,
    *,
    seasons: int | list[int],
    n_clusters: int = 8,
    commit: bool = False,
) -> dict:
    """Cluster fanbases by discourse term vectors and optionally persist results.

    Parameters
    ----------
    db:
        Open ``sqlite3`` connection (or compatible).
    seasons:
        Single season year (int) or list of season years.
    n_clusters:
        Desired number of clusters (reduced automatically when too few teams).
    commit:
        When True, DELETE existing rows and INSERT new rows into
        ``team_discourse_clusters`` for each processed season.

    Returns
    -------
    dict with keys:
        ``clusters_computed`` (int) — total distinct clusters written/computed
        ``teams_assigned``   (int) — total team-season rows assigned
        ``seasons``          (list[int]) — seasons actually processed
    """
    # --- normalise seasons arg ---
    if isinstance(seasons, int):
        seasons_list: list[int] = [seasons]
    else:
        seasons_list = list(seasons)

    cursor = db.cursor()
    cursor.row_factory = None  # we read via column index below

    total_clusters = 0
    total_assigned = 0
    processed_seasons: list[int] = []

    for season in seasons_list:
        # -----------------------------------------------------------------
        # 1. Load team_discourse_terms for week=0, this season
        # -----------------------------------------------------------------
        cursor.execute(
            """
            SELECT t.team_id, dt.term, dt.z_score
            FROM   team_discourse_terms dt
            JOIN   teams t ON t.team_id = dt.team_id
            WHERE  dt.week = 0
              AND  dt.season_year = ?
            ORDER  BY dt.team_id
            """,
            (season,),
        )
        rows = cursor.fetchall()

        # Build per-team vectors
        team_vectors: dict[int, dict[str, float]] = {}
        for row in rows:
            team_id = row[0]
            term    = row[1]
            z_score = float(row[2]) if row[2] is not None else 0.0
            if team_id not in team_vectors:
                team_vectors[team_id] = {}
            team_vectors[team_id][term] = z_score

        # Only teams with >= 5 terms
        qualified: dict[int, dict[str, float]] = {
            tid: vec for tid, vec in team_vectors.items() if len(vec) >= 5
        }

        n_teams = len(qualified)
        if n_teams < 4:
            # Not enough data for meaningful clustering
            continue

        processed_seasons.append(season)

        # -----------------------------------------------------------------
        # 2. Reduce k
        # -----------------------------------------------------------------
        k = min(n_clusters, max(2, n_teams // 2))

        team_ids_ordered: list[int] = list(qualified.keys())
        vectors_ordered: list[dict]  = [qualified[tid] for tid in team_ids_ordered]

        # -----------------------------------------------------------------
        # 3. Cluster
        # -----------------------------------------------------------------
        assignments = _kmeans(vectors_ordered, k)

        # -----------------------------------------------------------------
        # 4. Derive cluster metadata
        # -----------------------------------------------------------------
        # Group team indices by cluster id
        cluster_members: dict[int, list[int]] = {}
        for idx, cid in enumerate(assignments):
            cluster_members.setdefault(cid, []).append(idx)

        # Sort cluster ids by size descending for ranking
        sorted_cids = sorted(cluster_members.keys(), key=lambda c: -len(cluster_members[c]))
        cluster_rank_map: dict[int, int] = {
            cid: rank + 1 for rank, cid in enumerate(sorted_cids)
        }

        now_utc = datetime.now(timezone.utc).isoformat()

        # -----------------------------------------------------------------
        # 5. Compute shared_terms per cluster
        # -----------------------------------------------------------------
        cluster_shared_terms: dict[int, list[str]] = {}
        cluster_names: dict[int, str] = {}

        for cid, member_indices in cluster_members.items():
            member_vecs = [vectors_ordered[i] for i in member_indices]
            n_members   = len(member_vecs)
            threshold   = 0.5 * n_members  # >= 50% of members must have the term

            # Count presence and accumulate z_scores across members
            term_presence: dict[str, int]   = {}
            term_z_sum:    dict[str, float] = {}
            for vec in member_vecs:
                for term, z in vec.items():
                    term_presence[term] = term_presence.get(term, 0) + 1
                    term_z_sum[term]    = term_z_sum.get(term, 0.0) + z

            shared = [
                t for t, cnt in term_presence.items() if cnt >= threshold
            ]
            # Sort by descending sum of z_scores
            shared.sort(key=lambda t: -term_z_sum.get(t, 0.0))
            top6 = shared[:6]

            cluster_shared_terms[cid] = top6
            if top6:
                cluster_names[cid] = " / ".join(top6[:3])
            else:
                cluster_names[cid] = f"cluster {cid}"

        # -----------------------------------------------------------------
        # 6. Persist (if commit=True)
        # -----------------------------------------------------------------
        if commit:
            cursor.execute(
                "DELETE FROM team_discourse_clusters WHERE season_year = ?",
                (season,),
            )
            for idx, cid in enumerate(assignments):
                team_id     = team_ids_ordered[idx]
                shared_json = json.dumps(cluster_shared_terms[cid])
                cursor.execute(
                    """
                    INSERT INTO team_discourse_clusters
                        (team_id, season_year, cluster_id, cluster_name,
                         cluster_rank, cluster_size, shared_terms,
                         model_version, computed_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        team_id,
                        season,
                        cid,
                        cluster_names[cid],
                        cluster_rank_map[cid],
                        len(cluster_members[cid]),
                        shared_json,
                        "atlas_v1",
                        now_utc,
                    ),
                )
            db.commit()

        total_clusters += len(cluster_members)
        total_assigned += len(assignments)

    return {
        "clusters_computed": total_clusters,
        "teams_assigned":    total_assigned,
        "seasons":           processed_seasons,
    }
