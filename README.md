# email-triage

My personal email triage system using an LLM to categorize and summarize emails.

## Configuration

Accounts live in `config.yaml`. Each account's OAuth client ID is read from `.env`, keyed by the account name (uppercased): `ACCOUNT_<NAME>_CLIENT_ID`.

OAuth tokens are persisted in the OS keychain (macOS Keychain / Windows Credential Locker / Linux Secret Service) via the `keyring` library — no plaintext token files. If you previously ran an older version, you can delete `~/.cache/email-triage/token.json`.

## Microsoft (Outlook) setup

Create a public client app in Azure (Personal Microsoft accounts → "consumers" tenant) with the IMAP scope `https://outlook.office.com/IMAP.AccessAsUser.All`. Drop the application (client) ID into `.env`.

## Google (Gmail) setup

1. At [console.cloud.google.com](https://console.cloud.google.com), create or select a project.
2. **APIs & Services → Library** → enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen** → External → add your Gmail address as a test user.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → application type **TVs and Limited Input devices**.
5. Copy the client ID into `.env` as `ACCOUNT_<NAME>_CLIENT_ID`.

On the first Gmail run you'll be prompted with a verification URL and code; enter the code at the URL to authorize. The refresh token is then cached in the keyring and subsequent runs are silent.

## Usage

```sh
python -m scripts.fetch_unread                          # all accounts
python -m scripts.fetch_unread --account personal_gmail # one account
python -m scripts.classify_unread --limit 20
```
