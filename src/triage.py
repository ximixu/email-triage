import argparse
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ERROR_LOG = Path(__file__).resolve().parent.parent / "errors.log"

from .classifier import ClassificationResult, classify_email
from .config import Account, AppConfig, load_config
from .imap_client import ACTIONS, Email, connect_imap, fetch_unread, mark_unread


def _classify_parallel(
    emails: list[Email], config: AppConfig, workers: int
) -> tuple[list[ClassificationResult], list[Email]]:
    results: list[ClassificationResult] = []
    failed: list[Email] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(classify_email, e, config): e for e in emails}
        for future in as_completed(futures):
            email = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failed.append(email)
                print(f"  [classify error] {email.subject[:60]}: {exc} (see {ERROR_LOG.name})")
                with ERROR_LOG.open("a") as f:
                    f.write(
                        f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} classify ---\n"
                        f"uid={email.uid} from={email.from_!r} subject={email.subject!r}\n"
                        f"{traceback.format_exc()}"
                    )
    return results, failed


def _restore_unread(conn, account: Account, uid: str) -> bool:
    """Mark a message unread so a failed run re-triages it next time. Best-effort."""
    try:
        mark_unread(conn, uid, account)
        return True
    except Exception as exc:
        print(f"  [restore error] uid {uid}: {exc} (see {ERROR_LOG.name})")
        with ERROR_LOG.open("a") as f:
            f.write(
                f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} restore ---\n"
                f"uid={uid} account={account.name}\n"
                f"{traceback.format_exc()}"
            )
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None, help="Account name (omit to run all)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true", help="Classify but skip actions")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-email grouped summary")
    args = parser.parse_args()

    if args.dry_run:
        print("!!! DRY RUN STILL SETS FETCHED MESSAGES TO READ !!!")
        print('!!! "ctrl+c" TO CANCEL... !!!')
        time.sleep(5)

    config = load_config()
    accounts = (
        [config.get_account(args.account)] if args.account else config.accounts
    )

    all_results: list[tuple[Account, ClassificationResult]] = []
    totals: Counter[str] = Counter()

    for account in accounts:
        print(f"\n=== {account.name} ({account.user}) ===")
        try:
            conn = connect_imap(account)
        except Exception as exc:
            print(f"  SKIPPED: {exc}")
            totals["error"] += 1
            continue
        try:
            emails = fetch_unread(conn, limit=args.limit)
            print(f"  {len(emails)} unread, classifying with {args.workers} workers")

            results, failed = _classify_parallel(emails, config, args.workers)
            all_results.extend((account, r) for r in results)

            # A failed classify left the message marked \Seen (set by fetch) but
            # never triaged. Restore it to unread so the next run retries it.
            if not args.dry_run:
                for e in failed:
                    if _restore_unread(conn, account, e.uid):
                        totals["restored"] += 1
                    else:
                        totals["error"] += 1

            for r in results:
                category = config.get_category(r.category)
                action_fn = ACTIONS.get(category.action)
                if not args.dry_run and action_fn is not None:
                    try:
                        action_fn(conn, r.email.uid, account)
                    except Exception as exc:
                        print(f"  [action error] {category.action} on uid {r.email.uid}: {exc} (see {ERROR_LOG.name})")
                        with ERROR_LOG.open("a") as f:
                            f.write(
                                f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} action ---\n"
                                f"action={category.action} uid={r.email.uid} account={account.name}\n"
                                f"{traceback.format_exc()}"
                            )
                        totals["error"] += 1
                        # Restore so a failed action is retried next run rather
                        # than left read-and-untriaged.
                        _restore_unread(conn, account, r.email.uid)
                        continue
                totals[category.action] += 1
        finally:
            conn.logout()

    if not args.quiet:
        by_category: dict[str, list[tuple[Account, ClassificationResult]]] = defaultdict(list)
        for account, r in all_results:
            by_category[r.category].append((account, r))

        for category in config.categories:
            items = by_category.get(category.name)
            if not items:
                continue
            print(f"\n=== {category.name} ({len(items)}) → {category.action} ===")
            for account, r in items:
                print(f"[{account.name}] {r.email.subject[:60]} — {r.summary}")

    print(f"\n=== total: {dict(totals)} ===")


if __name__ == "__main__":
    main()
