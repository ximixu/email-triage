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
class Account:
    name: str
    provider: str
    host: str
    user: str
    junk_folder: str
    oauth_client_id: str


@dataclass
class AppConfig:
    openrouter_api_key: str
    openrouter_model: str
    accounts: list[Account] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)

    def get_account(self, name: str) -> Account:
        for a in self.accounts:
            if a.name == name:
                return a
        raise KeyError(f"No account named {name!r} in config")


def load_config(
    accounts_path: str | Path = "accounts.yaml",
    categories_path: str | Path = "categories.yaml",
) -> AppConfig:
    with open(categories_path) as f:
        raw_categories = yaml.safe_load(f)
    categories = [
        Category(name=c["name"], description=c["description"], action=c["action"])
        for c in raw_categories
    ]

    with open(accounts_path) as f:
        raw_accounts = yaml.safe_load(f)

    accounts: list[Account] = []
    for entry in raw_accounts:
        name = entry["name"]
        env_key = f"ACCOUNT_{name.upper()}_CLIENT_ID"
        client_id = os.environ.get(env_key)
        if not client_id:
            raise RuntimeError(f"Missing {env_key} in environment for account {name!r}")

        accounts.append(
            Account(
                name=name,
                provider=entry["provider"],
                host=entry["host"],
                user=entry["user"],
                junk_folder=entry["junk_folder"],
                oauth_client_id=client_id,
            )
        )

    return AppConfig(
        openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
        openrouter_model=os.environ["OPENROUTER_MODEL"],
        accounts=accounts,
        categories=categories,
    )
