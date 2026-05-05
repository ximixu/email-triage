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
    imap_pass: str
    openrouter_api_key: str
    openrouter_model: str = "openai/gpt-4o-mini"
    categories: list[Category] = field(default_factory=list)


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    categories = [
        Category(name=c["name"], description=c["description"], action=c["action"])
        for c in raw["categories"]
    ]

    imap_host = os.environ["IMAP_HOST"]
    imap_user = os.environ["IMAP_USER"]
    imap_pass = os.environ["IMAP_PASS"]
    api_key = os.environ["OPENROUTER_API_KEY"]
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    return AppConfig(
        imap_host=imap_host,
        imap_user=imap_user,
        imap_pass=imap_pass,
        openrouter_api_key=api_key,
        openrouter_model=model,
        categories=categories,
    )
