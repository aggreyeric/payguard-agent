---
title: PayGuard
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.0.0"
app_file: main.py
pinned: false
license: mit
---

# 🛡️ PayGuard — Policy-Constrained Payment Agent on Hedera

Built for [Hedera AI Agent Bounty — Week 5: Policy Agent](https://ai-bounties.hedera.com)

A payment agent that can transfer HBAR on the Hedera network, but is **strictly constrained by 4 custom runtime policies**:
1. **SpendLimitPolicy** — per-tx and daily caps
2. **WhitelistPolicy** — approved recipients only
3. **RateLimitPolicy** — max N transactions per time window
4. **TimeWindowPolicy** — business hours enforcement

Plus an immutable HCS (Hedera Consensus Service) audit trail for every action.

## Demo Mode
This Space runs in **demo mode** without real Hedera credentials — the policy enforcement engine is fully functional, showing how each policy evaluates transactions. To enable live mode, add `HEDERA_ACCOUNT_ID`, `HEDERA_PRIVATE_KEY`, and `GROQ_API_KEY` as Space secrets.
