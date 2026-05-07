import json
import time
from pathlib import Path

import msal

SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]
TOKEN_CACHE_PATH = Path.home() / ".cache" / "email-triage" / "token.json"


def _build_app(client_id: str, tenant: str) -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())

    authority = f"https://login.microsoftonline.com/{tenant}"
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
        token_cache=cache,
    )
    return app


def _persist_cache(app: msal.PublicClientApplication) -> None:
    cache: msal.SerializableTokenCache = app.token_cache  # type: ignore[assignment]
    if cache.has_state_changed:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(cache.serialize())
        TOKEN_CACHE_PATH.chmod(0o600)


def get_access_token(client_id: str, tenant: str = "consumers") -> str:
    app = _build_app(client_id, tenant)

    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to start device flow: {flow}")
        print(flow["message"], flush=True)
        result = app.acquire_token_by_device_flow(flow)

    _persist_cache(app)

    if "access_token" not in result:
        raise RuntimeError(
            f"OAuth failed: {result.get('error')} - {result.get('error_description')}"
        )

    return result["access_token"]
