# email-triage

My personal email triage system using an LLM to categorize and summarize emails.

## Configuration

- `accounts.yaml` (gitignored) — IMAP accounts. Copy `accounts.yaml.example` and fill in your addresses.
- `categories.yaml` (checked in) — triage categories and their actions.
- `.env` (gitignored) — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `MICROSOFT_CLIENT_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

## Microsoft (Outlook) setup

Create a public client app in Azure with the IMAP scope `https://outlook.office.com/IMAP.AccessAsUser.All`. Drop the application (client) ID into `.env` as `MICROSOFT_CLIENT_ID`. Make sure it supports all account types (Entra ID/Personal).

## Google (Gmail) setup

1. At [console.cloud.google.com](https://console.cloud.google.com), create or select a project.
2. **APIs & Services → Library** → enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen** → External → add your Gmail address as a test user.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → application type **Desktop app**.
5. Copy the client ID and client secret into `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.