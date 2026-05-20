# email-triage

My personal email triage system using an LLM to categorize and summarize emails. I run it as a cron job and pipe the output to discord to keep my inboxes clean. 

## Configuration

- `accounts.yaml` (gitignored) — IMAP accounts. Copy `accounts.yaml.example` and fill in your addresses.
- `categories.yaml` (checked in) — triage categories and their actions.
- `.env` (gitignored) — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `MICROSOFT_CLIENT_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

## Microsoft (Outlook) setup

1. At [portal.azure.com](https://portal.azure.com), go to **Microsoft Entra ID → App registrations → New registration**.
2. Name the app, choose **Accounts in any organizational directory and personal Microsoft accounts**, and register.
3. **Manage → API permissions → Add a permission → APIs my organization uses** → search **Office 365 Exchange Online** → **Delegated permissions** → enable `IMAP.AccessAsUser.All`.
4. **Manage → Authentication** → enable **Allow public client flows**.
5. Copy the **Application (client) ID** into `.env` as `MICROSOFT_CLIENT_ID`.

## Google (Gmail) setup

1. At [console.cloud.google.com](https://console.cloud.google.com), create or select a project.
2. **APIs & Services → Library** → enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen** → External → add your Gmail address as a test user.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → application type **Desktop app**.
5. Copy the client ID and client secret into `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.