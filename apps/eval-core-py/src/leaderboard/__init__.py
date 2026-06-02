"""POLLMEVALS leaderboard data layer.

Turns an immutable Run manifest into a stable, publishable `leaderboard.json`
aggregate — one row per (model, stack) — the data contract the public site
(apps/site) consumes. UI-agnostic and deterministic.

Honesty rule (CONTEXT.md "never hide variance" + "always a distribution"):
cost / latency / tokens are reported whenever a run exists; quality fields
(mean_score, pass@1, pass@k, pass^k, flaky) are reported ONLY when the run
carries real scores (`final_score`), and are `null` otherwise — never fabricated.
This makes the schema forward-complete (it always has the quality columns) while
staying truthful about what a given run actually measured.

Public API:
    build_leaderboard(manifest, *, solved_threshold) -> Leaderboard
    Leaderboard / LeaderboardEntry — the publishable models.
"""

from .aggregate import (
    Leaderboard,
    LeaderboardEntry,
    build_leaderboard,
)

__all__ = ["Leaderboard", "LeaderboardEntry", "build_leaderboard"]
