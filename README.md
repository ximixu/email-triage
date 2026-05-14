# email-triage

My personal email triage system using an LLM to categorize and summarize emails.

## Configuration

- `accounts.yaml` (gitignored) — IMAP accounts. Copy `accounts.yaml.example` and fill in your addresses.
- `categories.yaml` (checked in) — triage categories and their actions.
- `.env` (gitignored) — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `MICROSOFT_CLIENT_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

OAuth tokens are persisted in the OS keychain (macOS Keychain / Windows Credential Locker / Linux Secret Service) via the `keyring` library — no plaintext token files. If you previously ran an older version, you can delete `~/.cache/email-triage/token.json`.

## Microsoft (Outlook) setup

Create a public client app in Azure (Personal Microsoft accounts → "consumers" tenant) with the IMAP scope `https://outlook.office.com/IMAP.AccessAsUser.All`. Drop the application (client) ID into `.env` as `MICROSOFT_CLIENT_ID`.

## Google (Gmail) setup

1. At [console.cloud.google.com](https://console.cloud.google.com), create or select a project.
2. **APIs & Services → Library** → enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen** → External → add your Gmail address as a test user.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → application type **Desktop app**.
5. Copy the client ID and client secret into `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

On the first Gmail run a browser opens for the consent screen; the captured refresh token is then cached in the keyring and subsequent runs are silent. For a headless VPS, authorize once locally and copy the refresh token from the keyring (`keyring get email-triage <account-name>`) onto the VPS.

## Usage

```sh
python -m scripts.fetch_unread                          # all accounts
python -m scripts.fetch_unread --account personal_gmail # one account
python -m scripts.classify_unread --limit 20
```
