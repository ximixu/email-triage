import os

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..config import Account

KEYRING_SERVICE = "email-triage"
SCOPES = ["https://mail.google.com/"]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config() -> dict:
    return {
        "installed": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }


def get_access_token(account: Account) -> str:
    refresh_token = keyring.get_password(KEYRING_SERVICE, account.name)
    cfg = _client_config()["installed"]

    if refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=TOKEN_URI,
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            scopes=SCOPES,
        )
        try:
            creds.refresh(Request())
            return creds.token
        except Exception:
            # Token is invalid. Clear it and raise so caller can skip the account.
            keyring.delete_password(KEYRING_SERVICE, account.name)
            raise

    raise RuntimeError(
        f"No refresh token for {account.name}. "
        f"Run: cd ~/dev/email-triage && .venv/bin/python scripts/reauthorize.py {account.name}"
    )


def run_interactive_oauth(account_name: str) -> None:
    """Run OAuth flow interactively and store refresh token in keyring."""
    flow = InstalledAppFlow.from_client_config(_client_config(), scopes=SCOPES)
    creds = flow.run_local_server(port=8765, open_browser=False)
    keyring.set_password(KEYRING_SERVICE, account_name, creds.refresh_token)
    print(f"  Token saved for {account_name}")
