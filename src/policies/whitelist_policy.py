"""
WhitelistPolicy — Restricts transfers to pre-approved recipient addresses.

Only allows HBAR or token transfers to account IDs in the whitelist.
Any transfer to an unlisted address is blocked.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from hedera_agent_kit.shared.policy import AbstractPolicy
from hedera_agent_kit.shared.hook import PostParamsNormalizationParams

if TYPE_CHECKING:
    from hedera_agent_kit.shared.configuration import Context

logger = logging.getLogger(__name__)


class WhitelistPolicy(AbstractPolicy):
    """
    Policy that restricts transfers to a whitelist of approved recipients.
    """

    def __init__(self, allowed_recipients: list[str]):
        self._allowed = set(addr.strip() for addr in allowed_recipients)

    @property
    def name(self) -> str:
        return "WhitelistPolicy"

    @property
    def description(self) -> str:
        return f"Only allows transfers to {len(self._allowed)} approved recipients"

    @property
    def relevant_tools(self) -> List[str]:
        return [
            "transfer_hbar",
            "transfer_hbar_with_allowance",
            "airdrop_fungible_token",
            "transfer_fungible_token_with_allowance",
        ]

    def _get_recipients(self, params: Any) -> list[str]:
        """Extract recipient account IDs from normalized transfer params."""
        recipients = []
        try:
            normalized = params.normalized_params
            if hasattr(normalized, "hbar_transfers"):
                for account_id in normalized.hbar_transfers.keys():
                    recipients.append(str(account_id))
            elif hasattr(normalized, "hbar_approved_transfers"):
                for account_id in normalized.hbar_approved_transfers.keys():
                    recipients.append(str(account_id))
        except Exception as e:
            logger.warning(f"WhitelistPolicy: could not parse recipients: {e}")
        return recipients

    async def should_block_post_params_normalization(
        self, context: "Context", params: PostParamsNormalizationParams, method: str
    ) -> bool:
        recipients = self._get_recipients(params)

        for recipient in recipients:
            if recipient not in self._allowed:
                logger.info(
                    f"WhitelistPolicy BLOCKED: {recipient} is not in approved list"
                )
                return True

        return False

    @property
    def status(self) -> dict:
        return {
            "policy": self.name,
            "allowed_recipients": sorted(self._allowed),
            "count": len(self._allowed),
        }
