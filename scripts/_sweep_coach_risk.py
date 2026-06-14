"""
Identify highest-risk programs for coach-name hallucination sweep.
Target: D2 (tier 6) and D3 (tier 7) programs with 'savior' coach_relationship
or named current coaches in legends.
"""
import os
import yaml

EC_DIR = "profiles/emotional_core"

candidates = []
for f in sorted(os.listdir(EC_DIR)):
    if not f.endswith('.yaml'):
        continue
    fpath = os.path.join(EC_DIR, f)
    try:
        data = yaml.safe_load(open(fpath, encoding='utf-8').read())
    except Exception:
        continue
    if not data:
        continue
    tier = data.get('program_tier', 0)
    if tier not in (6, 7):
        continue
    slug = f[:-5]
    coach_rel = data.get('the_coach_relationship', '')
    canon = data.get('story_canon', {}) or {}
    legends = canon.get('legends', []) or []
    named_coaches = [
        l['name'] for l in legends
        if isinstance(l, dict) and l.get('role') == 'coach' and l.get('name')
    ]
    candidates.append({
        'slug': slug,
        'tier': tier,
        'coach_rel': coach_rel,
        'named_coaches': named_coaches,
        'program': data.get('program_name', slug),
    })

saviors = [c for c in candidates if c['coach_rel'] == 'savior']
print(f"Tier 6/7 total: {len(candidates)}")
print(f"Tier 6/7 savior coach_rel: {len(saviors)}")
print()
print("First 40 savior programs + named coaches:")
for c in saviors[:40]:
    nc = c['named_coaches'] if c['named_coaches'] else ['(none named)']
    print(f"  {c['slug']} ({c['program']}) — {', '.join(nc)}")
