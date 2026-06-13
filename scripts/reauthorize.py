#!/usr/bin/env python3
"""Re-authorize an account for email-triage by running its OAuth flow."""

import sys
from pathlib import Path

# Add project root to path so `src` is importable as a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import load_config
from src.oauth import run_interactive_oauth

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <account_name>")
        sys.exit(1)
    account = load_config().get_account(sys.argv[1])
    run_interactive_oauth(account)
