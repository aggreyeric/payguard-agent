"""
PayGuard UI — Gradio interface with policy dashboard + chat.

Shows the active policy layer clearly in the interface, as required by the bounty:
"policy layer clearly integrated into the interface and execution flow"
"""

import gradio as gr
import os
import json

# Lazy-import agent module (heavy deps: hedera-agent-kit, hiero-sdk-python)
# This allows the app to run in demo mode without those packages installed
try:
    from src.agent import create_agent, create_hedera_client, get_policy_statuses
    _HAS_AGENT = True
except ImportError:
    _HAS_AGENT = False
    def get_policy_statuses():
        return [
            {"policy": "SpendLimitPolicy", "max_per_tx_hbar": float(os.getenv("POLICY_MAX_PER_TX", "10.0")),
             "daily_limit_hbar": float(os.getenv("POLICY_DAILY_LIMIT", "100.0")),
             "daily_used_hbar": 0.0, "daily_remaining_hbar": float(os.getenv("POLICY_DAILY_LIMIT", "100.0")),
             "transaction_count_24h": 0},
            {"policy": "WhitelistPolicy", "count": len([a for a in os.getenv("POLICY_WHITELIST", "").split(",") if a.strip()]),
             "allowed_recipients": [a.strip() for a in os.getenv("POLICY_WHITELIST", "").split(",") if a.strip()]},
            {"policy": "RateLimitPolicy", "max_count": int(os.getenv("POLICY_RATE_MAX", "10")),
             "window_seconds": int(os.getenv("POLICY_RATE_WINDOW", "60")), "current_count": 0,
             "remaining": int(os.getenv("POLICY_RATE_MAX", "10"))},
            {"policy": "TimeWindowPolicy", "start_hour_utc_offset": int(os.getenv("POLICY_TIME_START", "0")),
             "end_hour_utc_offset": int(os.getenv("POLICY_TIME_END", "24")),
             "timezone_offset": int(os.getenv("POLICY_TZ_OFFSET", "0")),
             "current_local_hour": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).hour,
             "allow_weekends": os.getenv("POLICY_ALLOW_WEEKENDS", "true").lower() == "true",
             "transfers_allowed_now": True},
        ]
    def create_hedera_client(network="testnet"):
        raise RuntimeError("hedera-agent-kit not installed — running in demo mode")
    def create_agent(client):
        raise RuntimeError("hedera-agent-kit not installed — running in demo mode")

# Lazy-loaded singletons
_agent = None
_client = None


def get_client():
    global _client
    if _client is None:
        network = os.getenv("HEDERA_NETWORK", "testnet")
        _client = create_hedera_client(network)
    return _client


def get_agent():
    global _agent
    if _agent is None:
        client = get_client()
        _agent = create_agent(client)
    return _agent


def _is_demo_mode() -> bool:
    """Check if we're running without real keys (demo/simulation mode)."""
    has_hedera = bool(os.getenv("HEDERA_ACCOUNT_ID")) and bool(os.getenv("HEDERA_PRIVATE_KEY"))
    has_llm = bool(os.getenv("GROQ_API_KEY")) or bool(os.getenv("OPENAI_API_KEY"))
    return not (has_hedera and has_llm)


def _demo_chat_response(message: str) -> str:
    """Simulate policy enforcement responses when no keys are configured."""
    msg_lower = message.lower()

    if "balance" in msg_lower:
        return (
            "💳 **Demo Mode** — No Hedera keys configured.\n\n"
            "In production, I would query your HBAR balance from the testnet.\n\n"
            "To enable live mode, set `HEDERA_ACCOUNT_ID`, `HEDERA_PRIVATE_KEY`, "
            "and `GROQ_API_KEY` in the environment variables."
        )

    if any(w in msg_lower for w in ["send", "transfer", "pay"]):
        import re
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*hbar', msg_lower)
        amount = float(amount_match.group(1)) if amount_match else 5.0
        max_per_tx = float(os.getenv("POLICY_MAX_PER_TX", "10.0"))

        response = "🛡️ **Policy Evaluation (Demo Mode)**\n\n"
        response += f"Requested transfer: **{amount} HBAR**\n\n"
        response += "| Policy | Check | Result |\n|--------|-------|--------|\n"
        response += f"| 💰 SpendLimitPolicy | {amount} ≤ {max_per_tx} max/tx | {'✅ PASS' if amount <= max_per_tx else '❌ BLOCKED'} |\n"
        response += "| ✅ WhitelistPolicy | Recipient check | ⏳ Would verify |\n"
        response += "| ⚡ RateLimitPolicy | Throttle check | ✅ PASS |\n"
        response += "| 🕐 TimeWindowPolicy | Hours check | ✅ PASS |\n\n"

        if amount > max_per_tx:
            response += f"❌ **Transfer blocked:** Amount {amount} HBAR exceeds per-transaction limit of {max_per_tx} HBAR.\n\n"
        else:
            response += "✅ **All policies passed** — in production, this transfer would execute on Hedera testnet.\n\n"

        response += "---\n_Demo mode: No real transactions are made. Add Hedera keys to enable live transfers._"
        return response

    if any(w in msg_lower for w in ["policy", "policies", "active", "rules", "guardrail"]):
        statuses = get_policy_statuses()
        response = "🛡️ **Active Policy Layer**\n\n"
        for s in statuses:
            name = s.get("policy", "?")
            if name == "SpendLimitPolicy":
                response += f"- 💰 **SpendLimitPolicy** — max {s['max_per_tx_hbar']} HBAR/tx, {s['daily_limit_hbar']} HBAR/day\n"
            elif name == "WhitelistPolicy":
                response += f"- ✅ **WhitelistPolicy** — {s['count']} approved recipients\n"
            elif name == "RateLimitPolicy":
                response += f"- ⚡ **RateLimitPolicy** — {s['max_count']} txs per {s['window_seconds']}s\n"
            elif name == "TimeWindowPolicy":
                response += f"- 🕐 **TimeWindowPolicy** — hours {s['start_hour_utc_offset']:02d}–{s['end_hour_utc_offset']:02d}\n"
        response += "\n_Demo mode: policies are evaluated but no real transactions occur._"
        return response

    return (
        "🛡️ **PayGuard (Demo Mode)**\n\n"
        "I'm a policy-constrained payment agent on Hedera. In demo mode, I can show you "
        "how policies work without making real transactions.\n\n"
        "Try:\n"
        "- \"Send 15 HBAR to 0.0.5000\" — see policy enforcement in action\n"
        "- \"What's my balance?\" — simulated query\n"
        "- \"What policies are active?\" — view the policy layer\n\n"
        "Add `HEDERA_ACCOUNT_ID`, `HEDERA_PRIVATE_KEY`, and `GROQ_API_KEY` "
        "to enable live mode."
    )


def chat_with_agent(message: str, history: list) -> str:
    """Process a chat message through the policy-constrained agent."""
    # Demo mode: simulate responses without real keys
    if _is_demo_mode():
        return _demo_chat_response(message)

    try:
        agent = get_agent()
        result = agent.invoke({"messages": [("user", message)]})
        # Extract the last AI message
        ai_messages = [
            m for m in result["messages"] if m.type == "ai"
        ]
        if ai_messages:
            response = ai_messages[-1].content
            # Check if any policy was mentioned in tool calls
            tool_messages = [
                m for m in result["messages"] if m.type == "tool"
            ]
            policy_notes = []
            for tm in tool_messages:
                content = str(tm.content)
                if "blocked by policy" in content.lower():
                    policy_notes.append(f"🛡️ **Policy enforcement:** {content[:200]}")

            if policy_notes:
                response += "\n\n---\n" + "\n".join(policy_notes)
            return response
        return "No response from agent."
    except Exception as e:
        return f"❌ Error: {str(e)}"


def render_policy_dashboard() -> str:
    """Render the policy status dashboard as markdown."""
    try:
        statuses = get_policy_statuses()
        if not statuses:
            return "No policies configured."

        sections = ["## 🛡️ Active Policy Layer\n"]
        for s in statuses:
            policy_name = s.get("policy", "Unknown")
            sections.append(f"### {policy_name}\n")

            if policy_name == "SpendLimitPolicy":
                sections.append(f"| Setting | Value |")
                sections.append(f"|---------|-------|")
                sections.append(f"| Max per tx | {s['max_per_tx_hbar']} HBAR |")
                sections.append(f"| Daily limit | {s['daily_limit_hbar']} HBAR |")
                sections.append(f"| Used today | {s['daily_used_hbar']:.4f} HBAR |")
                sections.append(f"| Remaining | {s['daily_remaining_hbar']:.4f} HBAR |")
                sections.append(f"| Tx count (24h) | {s['transaction_count_24h']} |")

            elif policy_name == "WhitelistPolicy":
                sections.append(f"**Approved recipients:** {s['count']}\n")
                for addr in s.get("allowed_recipients", []):
                    sections.append(f"- `{addr}`")

            elif policy_name == "RateLimitPolicy":
                sections.append(f"| Setting | Value |")
                sections.append(f"|---------|-------|")
                sections.append(f"| Max transactions | {s['max_count']} |")
                sections.append(f"| Window | {s['window_seconds']}s |")
                sections.append(f"| Current count | {s['current_count']} |")
                sections.append(f"| Remaining | {s['remaining']} |")

            elif policy_name == "TimeWindowPolicy":
                status = "🟢 Allowed" if s["transfers_allowed_now"] else "🔴 Blocked"
                sections.append(f"| Setting | Value |")
                sections.append(f"|---------|-------|")
                sections.append(f"| Window | {s['start_hour_utc_offset']:02d}:00–{s['end_hour_utc_offset']:02d}:00 |")
                sections.append(f"| Timezone | UTC{s['timezone_offset']:+d} |")
                sections.append(f"| Current hour | {s['current_local_hour']:02d}:00 |")
                sections.append(f"| Weekends | {'✅' if s['allow_weekends'] else '❌'} |")
                sections.append(f"| **Status now** | {status} |")

            sections.append("")

        # HCS audit trail info
        hcs_topic = os.getenv("HCS_AUDIT_TOPIC_ID")
        if hcs_topic:
            sections.append("---")
            sections.append("### 📋 HCS Audit Trail")
            sections.append(f"All transactions logged to topic: `{hcs_topic}`")
            sections.append(
                f"[View on HashScan](https://hashscan.io/testnet/topic/{hcs_topic})"
            )

        return "\n".join(sections)
    except Exception as e:
        return f"Error loading policies: {e}"


def refresh_dashboard():
    return render_policy_dashboard()


def build_ui():
    """Build the Gradio interface."""
    with gr.Blocks(
        title="PayGuard — Policy-Constrained Payment Agent",
    ) as demo:
        gr.Markdown(
            "# 🛡️ PayGuard — Policy-Constrained Payment Agent on Hedera\n"
            "AI agent that makes HBAR payments on Hedera, constrained by "
            "multiple runtime policies. Built for **Hedera AI Bounty Week 5: Policy Agent**.\n\n"
            f"**Network:** {os.getenv('HEDERA_NETWORK', 'testnet')} | "
            f"**Operator:** `{os.getenv('HEDERA_ACCOUNT_ID', 'not set')}`"
        )

        if _is_demo_mode():
            gr.Markdown(
                "⚠️ **DEMO MODE** — No Hedera/Groq keys configured. "
                "The chat simulates policy enforcement. Add real keys for live transactions.\n"
                "See `.env.example` for configuration."
            )

        with gr.Row():
            # Left: Chat
            with gr.Column(scale=2):
                gr.Markdown("## 💬 Chat with PayGuard")
                chat = gr.ChatInterface(
                    fn=chat_with_agent,
                    examples=[
                        "What's my HBAR balance?",
                        "Send 2 HBAR to an approved recipient",
                        "What policies are currently active?",
                        "Create a new HCS topic for audit logging",
                    ],
                )

            # Right: Policy Dashboard
            with gr.Column(scale=1):
                gr.Markdown("## 🛡️ Policy Dashboard")
                dashboard = gr.Markdown(render_policy_dashboard())
                refresh_btn = gr.Button("🔄 Refresh Policy Status", variant="secondary")
                refresh_btn.click(fn=refresh_dashboard, outputs=dashboard)

        gr.Markdown("---")
        gr.Markdown(
            "Built with [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit-py) | "
            "Custom Policies: SpendLimit · Whitelist · RateLimit · TimeWindow | "
            "Audit: HCS Topic Logging\n\n"
            "**Hedera AI Agent Bounty — Week 5: Policy Agent**"
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
