"""Branded fan-conversation metrics (Fan Intelligence suite).

One module per signature stat, computed from the conversation feature tables
into persistent weekly tables (the conversations purge; the aggregates must
not). Display layer follows docs/design-system/40-noir-subbrand.md.

- backometer.py  -> backometer_weekly      (fanbase belief, 0-100, named zones)
- (planned) aura.py, rent_free.py, delusion.py
"""
