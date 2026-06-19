"""
SpendLimitPolicy — Enforces per-transaction and daily cumulative spend limits.

Blocks any transfer that exceeds:
  - max_per_tx:  maximum HBAR per single transaction
  - daily_limit: cumulative HBAR across all transactions in a 24h window
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, List

from hedera_agent_kit.shared.policy import AbstractPolicy
from hedera_agent_kit.shared.hook import PostParamsNormalizationParams

if TYPE_CHECKING:
    from hedera_agent_kit.shared.configuration import Context

logger = logging.getLogger(__name__)


class SpendLimitPolicy(AbstractPolicy):
    """
    Policy that enforces spend limits on HBAR transfers.

    - max_per_tx: Maximum HBAR allowed in a single transaction
    - daily_limit: Maximum cumulative HBAR in a rolling 24h window
    """

    def __init__(
        self,
        max_per_tx: float = 10.0,
        daily_limit: float = 100.0,
    ):
        self._max_per_tx = max_per_tx
        self._daily_limit = daily_limit
        self._spend_history: list[tuple[datetime, float]] = []

    @property
    def name(self) -> str:
        return "SpendLimitPolicy"

    @property
    def description(self) -> str:
        return (
            f"Enforces spend limits — max {self._max_per_tx} HBAR per tx, "
            f"{self._daily_limit} HBAR daily cap"
        )

    @property
    def relevant_tools(self) -> List[str]:
        return [
            "transfer_hbar_tool",
            "transfer_hbar_with_allowance_tool",
        ]

    def _get_transfer_amount(self, params: Any) -> float:
        """Extract total HBAR amount from normalized transfer params."""
        try:
            normalized = params.normalized_params
            if hasattr(normalized, "hbar_transfers"):
                # Sum positive values (outgoing)
                return sum(
                    v for v in normalized.hbar_transfers.values() if v > 0
                ) / 100_000_000  # tinybars → HBAR
            elif hasattr(normalized, "hbar_approved_transfers"):
                return sum(
                    v for v in normalized.hbar_approved_transfers.values() if v > 0
                ) / 100_000_000
        except Exception as e:
            logger.warning(f"SpendLimitPolicy: could not parse amount: {e}")
        return 0.0

    def _prune_history(self) -> None:
        """Remove spend entries older than 24 hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._spend_history = [
            (ts, amt) for ts, amt in self._spend_history if ts > cutoff
        ]

    def _daily_total(self) -> float:
        self._prune_history()
        return sum(amt for _, amt in self._spend_history)

    async def should_block_post_params_normalization(
        self, context: "Context", params: PostParamsNormalizationParams, method: str
    ) -> bool:
        amount = self._get_transfer_amount(params)

        if amount <= 0:
            return False

        # Check per-transaction limit
        if amount > self._max_per_tx:
            logger.info(
                f"SpendLimitPolicy BLOCKED: {amount} HBAR exceeds "
                f"per-tx limit of {self._max_per_tx} HBAR"
            )
            return True

        # Check daily cumulative limit
        daily_used = self._daily_total()
        if daily_used + amount > self._daily_limit:
            logger.info(
                f"SpendLimitPolicy BLOCKED: {amount} HBAR would push "
                f"daily total to {daily_used + amount} HBAR "
                f"(limit: {self._daily_limit} HBAR)"
            )
            return True

        return False

    def record_spend(self, amount_hbar: float) -> None:
        """Record a successful spend for daily limit tracking."""
        self._spend_history.append((datetime.now(timezone.utc), amount_hbar))

    @property
    def status(self) -> dict:
        """Current policy state for UI display."""
        self._prune_history()
        return {
            "policy": self.name,
            "max_per_tx_hbar": self._max_per_tx,
            "daily_limit_hbar": self._daily_limit,
            "daily_used_hbar": self._daily_total(),
            "daily_remaining_hbar": self._daily_limit - self._daily_total(),
            "transaction_count_24h": len(self._spend_history),
        }
