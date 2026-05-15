"""Cross-cutting utilities shared across product surfaces.

Modules here have no upstream deps on team_pages / editions / wire / etc.
They're called from many places — so they MUST stay narrow, fast, and
have no side effects beyond emitting logs.
"""
