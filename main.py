"""Main entry point — starts the PayGuard agent UI."""
import os
import sys


def main():
    print("🛡️ PayGuard — Policy-Constrained Payment Agent")
    print("=" * 55)
    print(f"Network: {os.getenv('HEDERA_NETWORK', 'testnet')}")
    print(f"Operator: {os.getenv('HEDERA_ACCOUNT_ID', 'not set')}")
    print(f"Max per tx: {os.getenv('POLICY_MAX_PER_TX', '10')} HBAR")
    print(f"Daily limit: {os.getenv('POLICY_DAILY_LIMIT', '100')} HBAR")
    print("=" * 55)
    print("Starting Gradio UI on http://localhost:7860")

    from src.ui import build_ui
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
