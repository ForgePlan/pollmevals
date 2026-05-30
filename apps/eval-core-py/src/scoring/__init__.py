"""POLLMEVALS scoring module.

Public API:
    component_score  — deterministic component score from requirement pass-rate (RFC-004).
"""

from .requirements import component_score

__all__ = ["component_score"]
