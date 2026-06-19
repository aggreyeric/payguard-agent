# 🛡️ PayGuard — Policy-Constrained Payment Agent on Hedera

**Built for [Hedera AI Agent Bounty — Week 5: Policy Agent](https://ai-bounties.hedera.com)**

A payment agent that can transfer HBAR on the Hedera network, but is **strictly constrained by 4 custom runtime policies** plus an immutable HCS audit trail. Every transaction is validated against spend limits, recipient whitelists, rate limits, and time windows — before it ever reaches the chain.

## Why This Matters

Autonomous AI agents that can move money need guardrails. PayGuard demonstrates a practical policy layer where an agent can purchase services and make payments, but **cannot exceed its mandate** — no matter what the user asks.

> _"We're looking for practical use cases where agents purchase real services or APIs, with the policy layer clearly integrated into the interface and execution flow."_ — Hedera Bounty Week 5

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────┐     ┌──────────────────┐
│   Gradio UI      │────►│   LangChain Agent            │────►│  Hedera Testnet   │
│                  │     │   (policy-constrained)       │     │                   │
│  💬 Chat         │◄────│                              │◄────│  • HBAR transfers │
│  🛡️ Policy       │     │  ┌────────────────────────┐ │     │  • Token ops      │
│     Dashboard    │     │  │   4 Custom Policies     │ │     │  • HCS topics     │
│  📋 Audit Trail  │     │  │   ├── SpendLimit        │ │     └──────────────────┘
│                  │     │  │   ├── Whitelist         │ │
└─────────────────┘     │  │   ├── RateLimit          │ │     ┌──────────────────┐
                        │  │   └── TimeWindow         │ │────►│  HCS Audit Topic  │
                        │  └────────────────────────┘ │     │  (immutable log)  │
                        │       HCS Audit Hook         │     └──────────────────┘
                        └─────────────────────────────┘
```

## The 4 Custom Policies

### 1. 💰 SpendLimitPolicy
| Rule | Description |
|------|-------------|
| Per-transaction cap | Blocks any single transfer exceeding `max_per_tx` HBAR |
| Daily cumulative cap | Tracks all transfers in a rolling 24h window; blocks when `daily_limit` would be exceeded |

**Blocks at:** `PostParamsNormalization` (after amount is parsed, before execution)

### 2. ✅ WhitelistPolicy
| Rule | Description |
|------|-------------|
| Approved recipients only | Transfers can only go to pre-configured account IDs |

**Blocks at:** `PostParamsNormalization` (after recipients are identified)

### 3. ⚡ RateLimitPolicy
| Rule | Description |
|------|-------------|
| Transaction throttle | Max N transactions per configurable time window |

**Blocks at:** `PreToolExecution` (earliest possible checkpoint)

### 4. 🕐 TimeWindowPolicy
| Rule | Description |
|------|-------------|
| Business hours | Transactions only allowed during configured hours |
| Weekend control | Optionally block Saturday/Sunday |
| Timezone aware | Configurable UTC offset for local business hours |

**Blocks at:** `PreToolExecution`

## Policy Lifecycle (How It Works)

The Hedera Agent Kit executes hooks/policies at 4 lifecycle points:

```
User: "Send 15 HBAR to 0.0.5000"
         │
         ▼
┌─ PreToolExecution ──────────────────────────────┐
│  ⚡ RateLimitPolicy: 3/10 txs this minute → PASS │
│  🕐 TimeWindowPolicy: 14:00 UTC, weekday → PASS │
└──────────────────────────────────────────────────┘
         │
         ▼
┌─ PostParamsNormalization ───────────────────────┐
│  💰 SpendLimitPolicy: 15 HBAR > 10 max → ❌ BLOCKED │
│  ✅ WhitelistPolicy: 0.0.5000 in list → (skipped) │
└──────────────────────────────────────────────────┘
         │
         ▼
  ❌ "Transfer blocked: amount exceeds per-transaction limit of 10 HBAR"
```

## Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Hedera testnet account ([free at portal.hedera.com](https://portal.hedera.com/dashboard))
- Groq API key ([free tier](https://console.groq.com/keys)) or OpenAI key

### Setup

```bash
git clone https://github.com/aggreyeric/payguard-agent.git
cd payguard-agent

# Install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Configure
cp .env.example .env
# Edit .env with your Hedera credentials, AI key, and policy settings
```

### Run

```bash
python main.py
```

UI opens at `http://localhost:7860`

## Policy Configuration

All policies are configured via environment variables in `.env`:

```bash
# Spend limits
POLICY_MAX_PER_TX=10.0        # Max HBAR per single transfer
POLICY_DAILY_LIMIT=100.0      # Max cumulative HBAR per 24h

# Whitelist (comma-separated account IDs)
POLICY_WHITELIST=0.0.1001,0.0.1002,0.0.1003

# Rate limiting
POLICY_RATE_MAX=10            # Max transactions
POLICY_RATE_WINDOW=60         # Per this many seconds

# Time window (business hours)
POLICY_TIME_START=9           # Start hour (UTC+offset)
POLICY_TIME_END=17            # End hour (UTC+offset)
POLICY_ALLOW_WEEKENDS=false   # Block weekends
POLICY_TZ_OFFSET=1            # UTC+1 (e.g., West Africa Time)
```

## Tech Stack

- **Hedera Agent Kit** (Python) — blockchain interaction layer
- **LangChain + LangGraph** — agent reasoning and tool calling
- **Gradio** — web UI with integrated policy dashboard
- **HCS (Hedera Consensus Service)** — immutable audit trail
- **Groq / OpenAI** — LLM inference

## Built With

- [Hedera Agent Kit (Python)](https://github.com/hashgraph/hedera-agent-kit-py)
- [Hiero SDK Python](https://github.com/hashgraph/hiero-sdk-python)
- Custom policies extending `AbstractPolicy`
- HCS Audit Trail Hook

## License

MIT
