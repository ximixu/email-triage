# Email Triage System — Implementation Plan

## Context

A multi-account email triage pipeline (Outlook + Gmail) that fetches unread mail, classifies each message with an LLM, and applies a per-category action (mark read / move to junk / etc.). Config + OAuth (keyring-backed) + IMAP fetch + LLM classifier are already wired and exercised by `scripts/fetch_unread.py` and `scripts/classify_unread.py`. What's left is the **act** half of the pipeline — turning classifications into mailbox actions — and an orchestrator that runs the full fetch→classify→act loop across all accounts.

## Remaining work

### Step E: Email actions (`src/actions.py`)

- `mark_read(conn, uid)` — set `\Seen` via `STORE`.
- `move_to_folder(conn, uid, folder)` — `COPY` to folder, set `\Deleted` on original, `EXPUNGE`.
- `move_to_junk(conn, uid, account)` — calls `move_to_folder` with `account.junk_folder` (Gmail `[Gmail]/Spam` vs Outlook `Junk`).
- `delete(conn, uid)` — set `\Deleted`, `EXPUNGE`.
- Action dispatch table mapping config action names → functions.

### Step F: Orchestrator (`src/triage.py`)

- `argparse`: `--config`, `--dry-run`, `--limit N`, `--verbose`, `--account NAME`.
- Loop:
  ```python
  for account in accounts_to_run:
      conn = connect_imap(account)
      try:
          emails = fetch_unread(conn, limit=args.limit)
          results = classify_in_parallel(emails, config)  # ThreadPoolExecutor pattern from classify_unread.py
          if not args.dry_run:
              for r in results:
                  apply_action(conn, r, account, config)
      finally:
          conn.logout()
  ```
- Print per-account summary + combined total.

## Reused utilities

- `Email` dataclass — `src/imap_client.py`
- `ClassificationResult`, `classify_email` — `src/classifier.py`
- `Account`, `Category`, `AppConfig.get_account()` — `src/config.py`
- `connect_imap(account)`, `fetch_unread(conn)` — `src/imap_client.py`
- ThreadPoolExecutor pattern — `scripts/classify_unread.py` (lift into orchestrator's classify step)

## Verification

```
python -m src.triage --dry-run --verbose   # classify only, no actions
python -m src.triage                        # apply actions
python -m src.triage --account personal_gmail --limit 5
```

## Out of scope (stretch goals)

- Concurrency across accounts (sequential is fine; classification within an account is already parallel).
- Per-account category or model overrides — single shared lists for now.
- `--watch` mode / cron scheduling.
- Email summary report.
- Reply templates.

## Key design decisions

- **Junk folder per account**: encoded in config so custom folder names work without code changes.
- **Dry-run by classification, not by connection**: `--dry-run` still opens IMAP and fetches/classifies, just skips the action step — so we can preview what would happen.
