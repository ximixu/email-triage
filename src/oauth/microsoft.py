import keyring
import msal

from ..config import Account

KEYRING_SERVICE = "email-triage"
SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]


def _build_app(account: Account) -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    cached = keyring.get_password(KEYRING_SERVICE, account.name)
    if cached:
        cache.deserialize(cached)

    authority = "https://login.microsoftonline.com/common"
    return msal.PublicClientApplication(
        client_id=account.oauth_client_id,
        authority=authority,
        token_cache=cache,
    )


def _persist_cache(app: msal.PublicClientApplication, account: Account) -> None:
    cache: msal.SerializableTokenCache = app.token_cache  # type: ignore[assignment]
    if cache.has_state_changed:
        keyring.set_password(KEYRING_SERVICE, account.name, cache.serialize())


def get_access_token(account: Account) -> str:
    app = _build_app(account)

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

    _persist_cache(app, account)

    if "access_token" not in result:
        raise RuntimeError(
            f"OAuth failed: {result.get('error')} - {result.get('error_description')}"
        )

    return result["access_token"]
