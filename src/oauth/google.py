import time

import keyring
import requests

from ..config import Account

KEYRING_SERVICE = "email-triage"
SCOPE = "https://mail.google.com/"
DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def _device_flow(client_id: str) -> str:
    resp = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": SCOPE},
        timeout=30,
    )
    resp.raise_for_status()
    flow = resp.json()

    print(
        f"To authorize, visit {flow['verification_url']} and enter code: {flow['user_code']}",
        flush=True,
    )

    interval = flow.get("interval", 5)
    deadline = time.time() + flow.get("expires_in", 600)
    device_code = flow["device_code"]

    while time.time() < deadline:
        time.sleep(interval)
        token_resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "device_code": device_code,
                "grant_type": DEVICE_GRANT,
            },
            timeout=30,
        )
        body = token_resp.json()
        if token_resp.ok and "refresh_token" in body:
            return body["refresh_token"]

        error = body.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise RuntimeError(f"Google device flow failed: {body}")

    raise RuntimeError("Google device flow timed out before authorization")


def _exchange_refresh_token(client_id: str, refresh_token: str) -> str | None:
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not resp.ok:
        return None
    body = resp.json()
    return body.get("access_token")


def get_access_token(account: Account) -> str:
    client_id = account.oauth_client_id
    refresh_token = keyring.get_password(KEYRING_SERVICE, account.name)

    if refresh_token:
        access = _exchange_refresh_token(client_id, refresh_token)
        if access:
            return access

    refresh_token = _device_flow(client_id)
    keyring.set_password(KEYRING_SERVICE, account.name, refresh_token)

    access = _exchange_refresh_token(client_id, refresh_token)
    if not access:
        raise RuntimeError("Failed to exchange new refresh token for access token")
    return access
