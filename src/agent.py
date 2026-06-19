"""
PayGuard Agent — Policy-constrained payment agent on Hedera.

Combines 4 custom policies + HCS audit trail hook with the Hedera Agent Kit
to create a payment agent that can transfer HBAR but is bound by:
  1. SpendLimitPolicy  — per-tx and daily caps
  2. WhitelistPolicy   — approved recipients only
  3. RateLimitPolicy   — max N transactions per time window
  4. TimeWindowPolicy  — business hours enforcement
  + HCS Audit Trail    — every action logged immutably
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import (
    Configuration,
    Context,
    AgentMode,
)
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_account_query_plugin,
    core_token_plugin,
    core_token_query_plugin,
    core_consensus_plugin,
    core_consensus_query_plugin,
)
from hedera_agent_kit.hooks.hcs_audit_trail_hook import HcsAuditTrailHook

from hiero_sdk_python import Client, Network, AccountId, PrivateKey

from src.policies.spend_limit_policy import SpendLimitPolicy
from src.policies.whitelist_policy import WhitelistPolicy
from src.policies.rate_limit_policy import RateLimitPolicy
from src.policies.time_window_policy import TimeWindowPolicy

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are PayGuard — a policy-constrained payment agent on the Hedera network.

Your job is to help users make payments and interact with Hedera, but you are STRICTLY 
bound by the following policies. You CANNOT bypass them:

1. **SpendLimitPolicy** — Each transaction is capped, and there's a daily cumulative limit.
2. **WhitelistPolicy** — You can only send funds to pre-approved recipient addresses.
3. **RateLimitPolicy** — You can only make a limited number of transactions per time window.
4. **TimeWindowPolicy** — Transactions are only allowed during configured hours.

When a user requests a transfer:
- Check if the amount is within limits
- Check if the recipient is whitelisted
- Inform the user clearly if any policy blocks the action and explain WHY
- If all policies pass, execute the transfer

When showing transaction results, include:
- Transaction ID
- HashScan verification link
- Which policies were evaluated

Always be transparent about what policies are active and their current state.
"""


def create_hedera_client(network: str = "testnet") -> Client:
    """Create a Hedera SDK client from environment variables."""
    account_id = os.getenv("HEDERA_ACCOUNT_ID")
    private_key = os.getenv("HEDERA_PRIVATE_KEY")

    if not account_id or not private_key:
        raise ValueError(
            "HEDERA_ACCOUNT_ID and HEDERA_PRIVATE_KEY must be set in .env"
        )

    client = Client(Network(network=network))
    client.set_operator(
        AccountId.from_string(account_id),
        PrivateKey.from_string(private_key),
    )
    return client


def build_policies_and_hooks() -> tuple[list, list]:
    """
    Build all policies and hooks from environment configuration.
    Returns (hooks_list, policies_list).
    """
    # --- Policies ---

    # 1. Spend Limit
    spend_policy = SpendLimitPolicy(
        max_per_tx=float(os.getenv("POLICY_MAX_PER_TX", "10.0")),
        daily_limit=float(os.getenv("POLICY_DAILY_LIMIT", "100.0")),
    )

    # 2. Whitelist
    whitelist_raw = os.getenv("POLICY_WHITELIST", "")
    whitelist_addrs = [
        a.strip() for a in whitelist_raw.split(",") if a.strip()
    ]
    whitelist_policy = WhitelistPolicy(allowed_recipients=whitelist_addrs)

    # 3. Rate Limit
    rate_policy = RateLimitPolicy(
        max_count=int(os.getenv("POLICY_RATE_MAX", "10")),
        window_seconds=int(os.getenv("POLICY_RATE_WINDOW", "60")),
    )

    # 4. Time Window
    time_policy = TimeWindowPolicy(
        start_hour=int(os.getenv("POLICY_TIME_START", "0")),
        end_hour=int(os.getenv("POLICY_TIME_END", "24")),
        allow_weekends=os.getenv("POLICY_ALLOW_WEEKENDS", "true").lower() == "true",
        timezone_offset=int(os.getenv("POLICY_TZ_OFFSET", "0")),
    )

    policies = [spend_policy, whitelist_policy, rate_policy, time_policy]

    # --- Hooks ---
    hooks = list(policies)  # Policies ARE hooks in the Agent Kit

    # Add HCS audit trail if topic is configured
    hcs_topic = os.getenv("HCS_AUDIT_TOPIC_ID")
    if hcs_topic:
        audit_hook = HcsAuditTrailHook(
            relevant_tools=[
                "transfer_hbar",
                "transfer_hbar_with_allowance",
                "create_token",
                "create_topic",
            ],
            hcs_topic_id=hcs_topic,
        )
        hooks.append(audit_hook)

    return hooks, policies


def create_agent(client: Client):
    """Create the policy-constrained LangChain agent."""
    hooks, policies = build_policies_and_hooks()

    configuration = Configuration(
        tools=[],
        plugins=[
            core_account_plugin,
            core_account_query_plugin,
            core_token_plugin,
            core_token_query_plugin,
            core_consensus_plugin,
            core_consensus_query_plugin,
        ],
        context=Context(
            mode=AgentMode.AUTONOMOUS,
            account_id=str(client.operator_account_id),
            hooks=hooks,
        ),
    )

    toolkit = HederaLangchainToolkit(
        client=client,
        configuration=configuration,
    )

    tools = toolkit.get_tools()

    # Choose LLM
    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    else:
        raise ValueError("Set GROQ_API_KEY or OPENAI_API_KEY in .env")

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    # Attach policies to agent for UI access
    agent._payguard_policies = policies
    return agent


def get_policy_statuses() -> list[dict]:
    """Get current status of all policies for UI display."""
    _, policies = build_policies_and_hooks()
    statuses = []
    for p in policies:
        if hasattr(p, "status"):
            statuses.append(p.status)
        else:
            statuses.append({"policy": p.name, "description": p.description})
    return statuses
