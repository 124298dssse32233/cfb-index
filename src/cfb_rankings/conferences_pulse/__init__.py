"""Conference Pulse module — Pulse v2 rendering at the conference level.

Public API:
    render_conference_pulse_section(conference_slug, db_conn) → str (HTML fragment)
    render_all_conferences(db_conn, output_dir) → dict
"""
from .renderer import render_conference_pulse_section, render_all_conferences

__all__ = ["render_conference_pulse_section", "render_all_conferences"]
