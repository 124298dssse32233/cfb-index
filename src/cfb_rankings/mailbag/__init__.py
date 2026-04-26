"""The Mailbag — Friday 09:00 ET fan-question editorial.

Public surface:
  - /mailbag/index.html          current edition
  - /mailbag/{edition_slug}/     archive pages
  - /mailbag/submit/             submission form (mailto-based until email infra lands)
  - /mailbag/archive.html        last 30 editions list

Pipeline:
  1. submissions.py   — intake + seeder
  2. curator.py       — question selection (Haiku-scored)
  3. synthesizer.py   — corpus-synthesis answers (Sonnet/Opus)
  4. renderer.py      — static HTML output
"""
