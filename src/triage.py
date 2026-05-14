import argparse
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .classifier import ClassificationResult, classify_email
from .config import Account, AppConfig, load_config
from .imap_client import ACTIONS, Email, connect_imap, fetch_unread


def _classify_parallel(
    emails: list[Email], config: AppConfig, workers: int
) -> list[ClassificationResult]:
    results: list[ClassificationResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(classify_email, e, config): e for e in emails}
        for future in as_completed(futures):
            email = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                print(f"  [classify error] {email.subject[:60]}: {exc}")
    return results


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
        conn = connect_imap(account)
        try:
            emails = fetch_unread(conn, limit=args.limit)
            print(f"  {len(emails)} unread, classifying with {args.workers} workers")

            results = _classify_parallel(emails, config, args.workers)
            all_results.extend((account, r) for r in results)

            for r in results:
                category = config.get_category(r.category)
                action_fn = ACTIONS.get(category.action)
                if not args.dry_run and action_fn is not None:
                    try:
                        action_fn(conn, r.email.uid, account)
                    except Exception as exc:
                        print(f"  [action error] {category.action} on uid {r.email.uid}: {exc}")
                        totals["error"] += 1
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
