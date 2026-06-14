"""
Export all D2/D3 programs with named coaches for fact-check sweep.
"""
import os
import yaml
import json

EC_DIR = "profiles/emotional_core"

output = []
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
    canon = data.get('story_canon', {}) or {}
    legends = canon.get('legends', []) or []
    named_coaches = [
        {'name': l['name'], 'why': l.get('why', '')}
        for l in legends
        if isinstance(l, dict) and l.get('role') == 'coach' and l.get('name')
    ]
    if named_coaches:
        output.append({
            'slug': slug,
            'program': data.get('program_name', slug),
            'tier': tier,
            'coaches': named_coaches,
        })

print(f"Total D2/D3 programs with named coaches: {len(output)}")
print()
for item in output:
    tier_label = "D2" if item['tier'] == 6 else "D3"
    for c in item['coaches']:
        print(f"{item['slug']} ({tier_label}) | {item['program']} | Coach: {c['name']} | {c['why'][:80]}")

# Also write JSON for agent consumption
with open('scripts/_coach_check_targets.json', 'w') as jf:
    json.dump(output, jf, indent=2)
print(f"\nWrote scripts/_coach_check_targets.json")
