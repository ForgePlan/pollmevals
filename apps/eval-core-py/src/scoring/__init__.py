"""POLLMEVALS scoring module.

Public API:
    component_score  — deterministic component score from requirement pass-rate (RFC-004).
    pass_at_k / pass_hat_k / flaky_fraction — capability ceiling vs reliability vs
        flakiness over N independent runs (SWE-rebench prior art; pairs with best-of-N).
    pass_at_k_estimator — unbiased pass@k (Chen et al. 2021) for n samples.
"""

from .pass_k import (
    flaky_fraction,
    pass_at_k,
    pass_at_k_estimator,
    pass_hat_k,
    solved_at_least_once,
    solved_every_time,
)
from .requirements import component_score

__all__ = [
    "component_score",
    "flaky_fraction",
    "pass_at_k",
    "pass_at_k_estimator",
    "pass_hat_k",
    "solved_at_least_once",
    "solved_every_time",
]
