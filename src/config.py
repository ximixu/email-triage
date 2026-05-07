import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Category:
    name: str
    description: str
    action: str


@dataclass
class AppConfig:
    imap_host: str
    imap_user: str
    openrouter_api_key: str
    imap_pass: str | None = None
    oauth_client_id: str | None = None
    oauth_tenant: str = "consumers"
    openrouter_model: str = "openai/gpt-4o-mini"
    categories: list[Category] = field(default_factory=list)

    @property
    def use_oauth(self) -> bool:
        return self.oauth_client_id is not None


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    categories = [
        Category(name=c["name"], description=c["description"], action=c["action"])
        for c in raw["categories"]
    ]

    imap_host = os.environ["IMAP_HOST"]
    imap_user = os.environ["IMAP_USER"]
    imap_pass = os.environ.get("IMAP_PASS") or None
    oauth_client_id = os.environ.get("OAUTH_CLIENT_ID") or None
    oauth_tenant = os.environ.get("OAUTH_TENANT", "consumers")
    api_key = os.environ["OPENROUTER_API_KEY"]
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    if not oauth_client_id and not imap_pass:
        raise RuntimeError(
            "Either OAUTH_CLIENT_ID or IMAP_PASS must be set in .env"
        )

    return AppConfig(
        imap_host=imap_host,
        imap_user=imap_user,
        imap_pass=imap_pass,
        oauth_client_id=oauth_client_id,
        oauth_tenant=oauth_tenant,
        openrouter_api_key=api_key,
        openrouter_model=model,
        categories=categories,
    )
