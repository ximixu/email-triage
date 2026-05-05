# Email Triage System — Implementation Plan

## Architecture

```
email-triage/
├── config.yaml          # Categories, actions, IMAP/LLM settings
├── .env                 # Secrets (password, API key)
├── src/
│   ├── __init__.py
│   ├── config.py        # Loads config.yaml + .env
│   ├── imap_client.py   # Fetch unread emails, parse headers/body
│   ├── classifier.py    # Send email content to OpenRouter LLM
│   ├── actions.py       # Mark read, move to folder, delete
│   └── triage.py        # Orchestrator + CLI entry point
├── requirements.txt
└── README.md
```

## Step-by-step Plan

### Step 1: Project scaffolding

- Create `src/` directory structure and placeholder files
- Create `requirements.txt` with dependencies:
  - `pyyaml` — parse config.yaml
  - `python-dotenv` — load .env secrets
  - `openai` — OpenRouter uses OpenAI-compatible API
- Create `.env.example` as a template:
  ```
  IMAP_HOST=imap.example.com
  IMAP_USER=user@example.com
  IMAP_PASS=your-password
  OPENROUTER_API_KEY=sk-or-...
  ```
- Create `config.yaml` to define categories and their actions:
  ```yaml
  categories:
    - name: important
      description: "Personal emails, work-related, bills, legal documents"
      action: mark_read
    - name: marketing
      description: "Promotions, newsletters, sales offers, marketing"
      action: mark_read
    - name: junk
      description: "Spam, phishing, unsolicited bulk mail"
      action: move_to_junk
    - name: other
      description: "Anything that doesn't clearly fit the above"
      action: mark_read
  ```

### Step 2: Config loader (`src/config.py`)

- Load `.env` via `dotenv`
- Parse `config.yaml` via `pyyaml`
- Validate required fields (categories, IMAP host, user, OpenRouter key)
- Return a typed `AppConfig` object (dataclass) with:
  - `imap_host`, `imap_user`, `imap_pass`
  - `openrouter_api_key`, `openrouter_model` (default `"openai/gpt-4o-mini"`)
  - `categories` list of category dataclasses

### Step 3: Email fetch (`src/imap_client.py`)

- Connect via IMAP SSL (`imaplib.IMAP4_SSL`)
- Login with credentials
- Select `INBOX`
- Search for `UNSEEN` messages (returns UIDs)
- For each UID, fetch `RFC822` (full raw message)
- Parse with `email.message_from_bytes`
- Extract plain text body from multipart/alternative messages
- Return a list of `Email` dataclasses:
  ```python
  @dataclass
  class Email:
      uid: str
      message_id: str
      from_: str
      subject: str
      date: str
      body: str  # plain text, truncated
  ```
- Logout/close connection

### Step 4: LLM harness (`src/classifier.py`)

- Use `openai.OpenAI` pointed at `https://openrouter.ai/api/v1`
- Build a prompt listing the category names + descriptions from config
- For each email, send subject + body (truncated to ~2000 chars to stay under token limits)
- Prompt instructs the LLM to return JSON like:
  ```json
  {"category": "important", "reason": "Brief explanation"}
  ```
- Parse response, validate category matches a known category
- Use `other` as fallback if parsing fails or LLM returns unknown category
- Handle retries on API errors with exponential backoff
- Return a `ClassificationResult` with category, reason, and the email

### Step 5: Email actions (`src/actions.py`)

- Functions that take an IMAP connection and Email UID:
  - `mark_read(conn, uid)` — set `\Seen` flag via `STORE`
  - `move_to_junk(conn, uid)` — `COPY` to `[Gmail]/Spam` or `Junk` folder, then `STORE +FLAGS (\Deleted)` and `EXPUNGE` the original
  - `delete(conn, uid)` — mark deleted and expunge
  - `move_to_folder(conn, uid, folder)` — copy to folder, delete original
- Action mapping: map config action names to these functions

### Step 6: Orchestrator (`src/triage.py`)

- Main entry point with `argparse`:
  - `--config` / `-c` — path to config.yaml (default: `config.yaml`)
  - `--dry-run` — classify but don't apply actions
  - `--limit N` — max number of emails to process (for testing)
  - `--verbose` / `-v` — print per-email classification details
- `triage()` function:
  1. Load config via `load_config()`
  2. Connect IMAP via `connect_imap()`
  3. Fetch unread emails via `fetch_unread()`
  4. For each email, classify via `classify_email()`
  5. If not dry-run, apply action via `apply_action()`
  6. Print summary: `X emails processed: N important, M marketing, K junk`
  7. Disconnect IMAP
- Example CLI usage:
  ```
  python -m src.triage --dry-run --verbose --limit 5
  python -m src.triage
  ```

### Step 7: Future enhancements (stretch goals)

- **`--watch` mode**: Poll IMAP every N minutes, run triage loop
- **Email summary report**: Send a summary email of actions taken
- **Multiple IMAP accounts**: Support multiple inboxes in config
- **Reply templates**: Auto-reply for specific categories
- **Systemd service / crontab**: Deploy to VPS for unattended runs

## Key Design Decisions

- **IMAP UIDs**: Track emails by UID rather than sequence number (UID remains stable across sessions)
- **Dry-run mode**: `--dry-run` flag to test classification without mutating mailbox
- **Idempotency**: Only process `UNSEEN` emails; don't reprocess already-triaged emails
- **Secrets**: Credentials in `.env`, not in `config.yaml` (so config can be committed)
- **OpenAI-compatible API**: OpenRouter exposes an OpenAI-compatible endpoint, so we use the `openai` Python client directly
- **Truncation**: Email bodies truncated to ~2000 chars before sending to LLM to stay under token limits and reduce cost
