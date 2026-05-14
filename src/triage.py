import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .classifier import ClassificationResult, classify_email
from .config import AppConfig, load_config
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
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    config = load_config()
    accounts = (
        [config.get_account(args.account)] if args.account else config.accounts
    )

    grand_total: Counter[str] = Counter()

    for account in accounts:
        print(f"\n=== {account.name} ({account.user}) ===")
        conn = connect_imap(account)
        try:
            emails = fetch_unread(conn, limit=args.limit)
            print(f"  {len(emails)} unread, classifying with {args.workers} workers")

            results = _classify_parallel(emails, config, args.workers)

            per_account: Counter[str] = Counter()
            grouped: dict[str, list[ClassificationResult]] = defaultdict(list)
            for r in results:
                grouped[r.category].append(r)

            for category_name, items in grouped.items():
                try:
                    category = config.get_category(category_name)
                except KeyError:
                    print(f"  [unknown category {category_name!r}] skipping {len(items)} emails")
                    per_account["unknown"] += len(items)
                    continue

                action_name = category.action
                action_fn = ACTIONS.get(action_name)

                for r in items:
                    if args.verbose or args.dry_run:
                        print(
                            f"  {action_name} <- {category_name}: "
                            f"[{r.email.from_[:30]}] {r.email.subject[:60]} — {r.summary}"
                        )
                    if not args.dry_run and action_fn is not None:
                        try:
                            action_fn(conn, r.email.uid, account)
                        except Exception as exc:
                            print(f"  [action error] {action_name} on uid {r.email.uid}: {exc}")
                            per_account["error"] += 1
                            continue
                    per_account[action_name] += 1

            print(f"  summary: {dict(per_account)}")
            grand_total.update(per_account)
        finally:
            conn.logout()

    print(f"\n=== total: {dict(grand_total)} ===")


if __name__ == "__main__":
    main()
