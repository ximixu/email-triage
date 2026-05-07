import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.classifier import classify_email
from src.config import load_config
from src.imap_client import connect_imap, fetch_unread


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    config = load_config()

    conn = connect_imap(config)
    try:
        emails = fetch_unread(conn, limit=args.limit)
    finally:
        conn.logout()

    print(f"{len(emails)} unread fetched, classifying with {args.workers} workers\n")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(classify_email, e, config): e for e in emails}
        for future in as_completed(futures):
            email = futures[future]
            try:
                r = future.result()
                print(f"[{r.category:<10}] {email.subject[:60]} — {r.summary}")
            except Exception as exc:
                print(f"[ERROR     ] {email.subject[:60]} — {exc}")


if __name__ == "__main__":
    main()
