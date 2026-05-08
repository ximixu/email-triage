from ..config import Account
from . import google, microsoft


def get_access_token(account: Account) -> str:
    if account.provider == "microsoft":
        return microsoft.get_access_token(account)
    if account.provider == "google":
        return google.get_access_token(account)
    raise ValueError(f"Unknown OAuth provider: {account.provider!r}")
