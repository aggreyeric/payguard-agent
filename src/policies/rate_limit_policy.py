"""
RateLimitPolicy — Limits the number of transactions within a time window.

Prevents rapid-fire transfers that could indicate a compromise or runaway agent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, List

from hedera_agent_kit.shared.policy import AbstractPolicy
from hedera_agent_kit.shared.hook import PreToolExecutionParams

if TYPE_CHECKING:
    from hedera_agent_kit.shared.configuration import Context

logger = logging.getLogger(__name__)


class RateLimitPolicy(AbstractPolicy):
    """
    Policy that enforces a rate limit on transactions.
    Blocks execution if more than max_count transactions occur
    within window_seconds.
    """

    def __init__(self, max_count: int = 10, window_seconds: int = 60):
        self._max_count = max_count
        self._window_seconds = window_seconds
        self._timestamps: list[datetime] = []

    @property
    def name(self) -> str:
        return "RateLimitPolicy"

    @property
    def description(self) -> str:
        return (
            f"Max {self._max_count} transactions per {self._window_seconds}s window"
        )

    @property
    def relevant_tools(self) -> List[str]:
        return [
            "transfer_hbar_tool",
            "transfer_hbar_with_allowance_tool",
            "create_token_tool",
            "create_topic_tool",
        ]

    def _prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._window_seconds)
        self._timestamps = [ts for ts in self._timestamps if ts > cutoff]

    def _current_count(self) -> int:
        self._prune()
        return len(self._timestamps)

    async def should_block_pre_tool_execution(
        self, context: "Context", params: PreToolExecutionParams, method: str
    ) -> bool:
        count = self._current_count()
        if count >= self._max_count:
            logger.info(
                f"RateLimitPolicy BLOCKED: {count} transactions in "
                f"last {self._window_seconds}s (max: {self._max_count})"
            )
            return True
        return False

    def record_transaction(self) -> None:
        """Record a transaction timestamp."""
        self._timestamps.append(datetime.now(timezone.utc))

    @property
    def status(self) -> dict:
        self._prune()
        return {
            "policy": self.name,
            "max_count": self._max_count,
            "window_seconds": self._window_seconds,
            "current_count": self._current_count(),
            "remaining": self._max_count - self._current_count(),
        }
