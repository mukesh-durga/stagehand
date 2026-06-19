"""Execution context carried through a single workflow run."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionContext:
    run_id: str
    workflow_id: str
    workflow_version_id: str
    input: dict[str, Any]
    run_config: dict[str, Any]
    max_steps: int
    max_runtime_seconds: int
    max_cost_usd: float
    node_outputs: dict[str, Any] = field(default_factory=dict)
    step_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _started_monotonic: float = field(default_factory=time.monotonic)

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._started_monotonic
