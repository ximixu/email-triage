import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.classifier import classify_email
from src.config import load_config
from src.imap_client import connect_imap, fetch_unread


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None, help="Account name (omit to run all)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    config = load_config()
    accounts = (
        [config.get_account(args.account)] if args.account else config.accounts
    )

    jobs = []
    for account in accounts:
        print(f"=== fetching {account.name} ({account.user}) ===")
        conn = connect_imap(account)
        try:
            emails = fetch_unread(conn, limit=args.limit)
        finally:
            conn.logout()
        print(f"  {len(emails)} unread")
        jobs.extend((account, e) for e in emails)

    print(f"\nClassifying {len(jobs)} emails with {args.workers} workers\n")

    by_category: dict[str, list[tuple]] = defaultdict(list)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(classify_email, email, config): (account, email)
            for account, email in jobs
        }
        for future in as_completed(futures):
            account, email = futures[future]
            try:
                r = future.result()
                by_category[r.category].append((account, email, r.summary))
            except Exception as exc:
                by_category["ERROR"].append((account, email, str(exc)))

    category_order = [c.name for c in config.categories] + ["ERROR"]
    for category in category_order:
        items = by_category.get(category)
        if not items:
            continue
        print(f"\n=== {category} ({len(items)}) ===")
        for account, email, summary in items:
            print(f"[{account.name}] {email.subject[:60]} — {summary}")


if __name__ == "__main__":
    main()
