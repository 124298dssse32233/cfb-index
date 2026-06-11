# Re-export shim: tests import from cfb_rankings.discourse.player_descriptors
from cfb_rankings.discourse.descriptors import compute_player_descriptors  # noqa: F401

__all__ = ["compute_player_descriptors"]
