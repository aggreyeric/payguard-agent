# CLAUDE.md — PayGuard Agent

## Project Overview
Policy-constrained payment agent on Hedera. 4 custom policies (spend limit, whitelist, rate limit, time window) gate every HBAR transfer, with an HCS audit trail.

## Tech Stack
- Python 3.11+ with httpx, pydantic
- Hedera SDK (HCS for audit trail)
- Gradio (optional demo UI)

## Status
✅ Submitted to Hedera AI Agent Bounty Week 5 ($1,500) — LIVE on HuggingFace Spaces

## Commands
```bash
pip install -r requirements.txt
python main.py
```

## Key Features
1. Spend limit — caps per-transaction HBAR amount
2. Whitelist — only approved recipients
3. Rate limit — prevents rapid transfers
4. Time window — restricts to designated periods
5. HCS audit trail — every decision logged immutably

## Architecture
- `main.py` — Entry point
- `src/` — Policy engine + Hedera integration
- `.env.example` — Required environment variables

## Notes
- Already submitted and won ($1,500)
- HF Space live at eritronics/payguard-demo
