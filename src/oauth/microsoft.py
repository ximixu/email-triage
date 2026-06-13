import os

import keyring
import msal

from ..config import Account

KEYRING_SERVICE = "email-triage"
SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]


def _build_app(account_name: str) -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    cached = keyring.get_password(KEYRING_SERVICE, account_name)
    if cached:
        cache.deserialize(cached)

    authority = "https://login.microsoftonline.com/common"
    return msal.PublicClientApplication(
        client_id=os.environ["MICROSOFT_CLIENT_ID"],
        authority=authority,
        token_cache=cache,
    )


def _persist_cache(app: msal.PublicClientApplication, account_name: str) -> None:
    cache: msal.SerializableTokenCache = app.token_cache  # type: ignore[assignment]
    if cache.has_state_changed:
        keyring.set_password(KEYRING_SERVICE, account_name, cache.serialize())


def get_access_token(account: Account) -> str:
    app = _build_app(account.name)

    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    _persist_cache(app, account.name)

    # Never fall into the interactive device flow here: this runs unattended (cron)
    # and would block forever. Fail fast so the caller skips the account instead.
    if not result or "access_token" not in result:
        raise RuntimeError(
            f"No valid token for {account.name}. "
            f"Run: cd ~/dev/email-triage && .venv/bin/python scripts/reauthorize.py {account.name}"
        )

    return result["access_token"]


def run_interactive_oauth(account_name: str) -> None:
    """Run the device-code flow interactively and store the token cache in keyring."""
    app = _build_app(account_name)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to start device flow: {flow}")
    print(flow["message"], flush=True)
    result = app.acquire_token_by_device_flow(flow)

    _persist_cache(app, account_name)

    if "access_token" not in result:
        raise RuntimeError(
            f"OAuth failed: {result.get('error')} - {result.get('error_description')}"
        )

    print(f"  Token saved for {account_name}")
