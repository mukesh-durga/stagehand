"""UCB bandit model selection for adaptive agent nodes.

Reads per-(route_key, model) statistics from Postgres and selects a candidate
using the UCB1 formula. Untried candidates are selected first (cheap before
strong, by candidate order) so exploration is deterministic and testable.
"""

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from worker.models import ModelRoutingStats


def _load_stats(db: Session | None, route_key: str) -> dict[str, ModelRoutingStats]:
    if db is None:
        return {}
    rows = db.scalars(
        select(ModelRoutingStats).where(ModelRoutingStats.route_key == route_key)
    ).all()
    return {r.model_name: r for r in rows}


def select_model(
    db: Session | None,
    route_key: str,
    candidates: list[str],
    exploration_weight: float = 1.0,
) -> tuple[str, dict[str, float], str]:
    """Return (selected_model, ucb_scores, reason).

    ``candidates`` order matters: the first untried candidate wins ties, so pass
    [cheap, strong] to prefer cheap when both are untried.
    """
    stats = _load_stats(db, route_key)

    untried = [m for m in candidates if m not in stats or stats[m].pulls == 0]
    if untried:
        selected = untried[0]
        return selected, {}, f"exploration: '{selected}' untried"

    total_pulls = sum(stats[m].pulls for m in candidates)
    scores: dict[str, float] = {}
    for m in candidates:
        row = stats[m]
        exploration = exploration_weight * math.sqrt(
            math.log(total_pulls + 1) / row.pulls
        )
        scores[m] = round(row.average_reward + exploration, 6)

    selected = max(candidates, key=lambda m: scores[m])
    return selected, scores, "UCB: highest exploration-adjusted reward"


def compute_ucb_score(
    average_reward: float, pulls: int, total_pulls: int, exploration_weight: float = 1.0
) -> float:
    """Standalone UCB1 score (exposed for tests)."""
    return average_reward + exploration_weight * math.sqrt(
        math.log(total_pulls + 1) / pulls
    )
