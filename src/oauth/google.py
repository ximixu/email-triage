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
        creds.refresh(Request())
        return creds.token

    flow = InstalledAppFlow.from_client_config(_client_config(), scopes=SCOPES)
    creds = flow.run_local_server(port=0)
    keyring.set_password(KEYRING_SERVICE, account.name, creds.refresh_token)
    return creds.token
