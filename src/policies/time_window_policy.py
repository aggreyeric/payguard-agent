"""
TimeWindowPolicy — Restricts transactions to specific time windows.

Enforces business-hours-only or configurable time windows for agent payments.
Useful for enterprise scenarios where transfers should only happen during
operational hours.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List

from hedera_agent_kit.shared.policy import AbstractPolicy
from hedera_agent_kit.shared.hook import PreToolExecutionParams

if TYPE_CHECKING:
    from hedera_agent_kit.shared.configuration import Context

logger = logging.getLogger(__name__)


class TimeWindowPolicy(AbstractPolicy):
    """
    Policy that restricts transactions to a time window.

    - start_hour: Hour (UTC) when the window opens (inclusive)
    - end_hour: Hour (UTC) when the window closes (exclusive)
    - weekends: Whether to allow transactions on weekends

    Example: start_hour=9, end_hour=17, weekends=False
    → Only Mon-Fri, 9AM-5PM UTC (classic business hours)
    """

    def __init__(
        self,
        start_hour: int = 0,
        end_hour: int = 24,
        allow_weekends: bool = True,
        timezone_offset: int = 0,
    ):
        self._start_hour = start_hour
        self._end_hour = end_hour
        self._allow_weekends = allow_weekends
        self._tz_offset = timezone_offset

    @property
    def name(self) -> str:
        return "TimeWindowPolicy"

    @property
    def description(self) -> str:
        weekend_rule = "including weekends" if self._allow_weekends else "weekdays only"
        return (
            f"Transactions allowed {self._start_hour:02d}:00–{self._end_hour:02d}:00 "
            f"(UTC{self._tz_offset:+d}), {weekend_rule}"
        )

    @property
    def relevant_tools(self) -> List[str]:
        return [
            "transfer_hbar",
            "transfer_hbar_with_allowance",
            "create_token",
            "airdrop_fungible_token",
        ]

    async def should_block_pre_tool_execution(
        self, context: "Context", params: PreToolExecutionParams, method: str
    ) -> bool:
        now = datetime.now(timezone.utc)
        local_hour = (now.hour + self._tz_offset) % 24
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6

        # Check time window
        if not (self._start_hour <= local_hour < self._end_hour):
            logger.info(
                f"TimeWindowPolicy BLOCKED: current hour {local_hour:02d}:00 "
                f"is outside allowed window "
                f"{self._start_hour:02d}:00–{self._end_hour:02d}:00"
            )
            return True

        # Check weekend
        if is_weekend and not self._allow_weekends:
            logger.info("TimeWindowPolicy BLOCKED: weekend transactions not allowed")
            return True

        return False

    @property
    def status(self) -> dict:
        now = datetime.now(timezone.utc)
        local_hour = (now.hour + self._tz_offset) % 24
        is_weekend = now.weekday() >= 5
        in_window = self._start_hour <= local_hour < self._end_hour
        allowed_now = in_window and (self._allow_weekends or not is_weekend)

        return {
            "policy": self.name,
            "start_hour_utc_offset": self._start_hour,
            "end_hour_utc_offset": self._end_hour,
            "timezone_offset": self._tz_offset,
            "current_local_hour": local_hour,
            "allow_weekends": self._allow_weekends,
            "is_weekend": is_weekend,
            "transfers_allowed_now": allowed_now,
        }
