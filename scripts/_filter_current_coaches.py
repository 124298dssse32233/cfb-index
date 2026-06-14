"""
Filter to coaches that appear to be current/active (not historical legends).
Risk pattern: 'since XXXX', 'head coach', 'hired', 'year N', no end year.
"""
import os
import yaml
import json
import re

EC_DIR = "profiles/emotional_core"

current_coach_markers = [
    r'\bsince \d{4}\b',
    r'\b\d+(?:st|nd|rd|th) (?:year|season)\b',
    r'\bhired\b',
    r'\btasked with\b',
    r'\bcurrent\b',
    r'\bhead coach\b',
    r'rebuilding',
    r'\bfirst season\b',
    r'\bnew coach\b',
    r'\bnew head\b',
]
historical_markers = [
    r'\(\d{4}[–\-]\d{4}\)',   # date range like (1953-1980)
    r'\d{4}[–\-]\d{4}',       # year range
    r'\bformer\b',
    r'\blegend\b',
    r'\barchitect of the.*dynasty\b',
    r'\b(?:19[0-9][0-9]|200[0-9]|201[0-4])\b.*(?:win|career)',
]

def is_likely_current(why_text):
    why = why_text.lower()
    # If contains a historical date range, probably not current
    for h in historical_markers:
        if re.search(h, why, re.IGNORECASE):
            return False
    # If contains current markers, flag it
    for c in current_coach_markers:
        if re.search(c, why, re.IGNORECASE):
            return True
    return False

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
    for l in legends:
        if not isinstance(l, dict):
            continue
        if l.get('role') != 'coach':
            continue
        name = l.get('name', '')
        why = l.get('why', '')
        if not name:
            continue
        if is_likely_current(why):
            output.append({
                'slug': slug,
                'program': data.get('program_name', slug),
                'tier': tier,
                'coach_name': name,
                'why': why,
            })

print(f"Likely-current named coaches to verify: {len(output)}")
for item in output[:80]:
    tier_label = "D2" if item['tier'] == 6 else "D3"
    print(f"  {item['slug']} ({tier_label}) | {item['coach_name']} | {item['why'][:90]}")

with open('scripts/_current_coach_targets.json', 'w') as jf:
    json.dump(output, jf, indent=2)
print(f"\nWrote {len(output)} targets to scripts/_current_coach_targets.json")
