"""Chronicle pipeline runtime configuration flags.

These module-level globals are set once at process startup (by cli.py after
argument parsing) and read by any chronicle sub-module that needs to respect
emergency / LKG-only mode.

Usage in any chronicle module:
    from cfb_rankings.chronicle.config import USE_LKG_ONLY, NO_LLM

    if USE_LKG_ONLY:
        # skip fresh generation, read from LKG cache only
        ...
    if NO_LLM:
        # hard-disable any API call to an LLM
        raise RuntimeError("LLM calls disabled via --no-llm flag")
"""
from __future__ import annotations

# Set to True by --use-lkg-only flag in build-site.
# When True, the chronicle module reads cards only from LKG, skipping fresh
# generation entirely.
USE_LKG_ONLY: bool = False

# Set to True by --no-llm flag in build-site.
# Belt-and-suspenders guard: hard-disables every LLM call path.  LKG mode
# should already skip LLM calls, but this flag makes the constraint explicit
# and enforced at the call site rather than relying on control-flow.
NO_LLM: bool = False


def configure(use_lkg_only: bool = False, no_llm: bool = False) -> None:
    """Set the module-level flags.  Call once from cli.py after arg parsing."""
    global USE_LKG_ONLY, NO_LLM
    USE_LKG_ONLY = use_lkg_only
    NO_LLM = no_llm
