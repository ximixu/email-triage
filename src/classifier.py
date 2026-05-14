import json
from dataclasses import dataclass

from openai import OpenAI

from .config import AppConfig
from .imap_client import Email

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class ClassificationResult:
    email: Email
    category: str
    summary: str


def classify_email(email: Email, config: AppConfig) -> ClassificationResult:
    client = OpenAI(api_key=config.openrouter_api_key, base_url=OPENROUTER_BASE_URL)

    category_lines = "\n".join(
        f"- {c.name}: {c.description}" for c in config.categories
    )
    valid_names = {c.name for c in config.categories}

    system_prompt = (
        "You triage emails into one of these categories:\n"
        f"{category_lines}\n\n"
        'Respond with JSON: {"category": "<name>", "summary": "<one-line summary>"}. '
        "The category must be one of the categories listed above. "
        "The summary must be a single short sentence describing the email."
    )
    user_prompt = (
        f"From: {email.from_}\n"
        f"Subject: {email.subject}\n\n"
        f"{email.body}"
    )

    response = client.chat.completions.create(
        model=config.openrouter_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    parsed = json.loads(response.choices[0].message.content or "{}")
    category = parsed.get("category", "")
    summary = parsed.get("summary", "")

    if category not in valid_names:
        category = "other" if "other" in valid_names else next(iter(valid_names))

    return ClassificationResult(email=email, category=category, summary=summary)
