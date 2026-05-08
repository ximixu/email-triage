import argparse

from src.config import load_config
from src.imap_client import connect_imap, fetch_unread


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None, help="Account name (omit to run all)")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    accounts = (
        [config.get_account(args.account)] if args.account else config.accounts
    )

    for account in accounts:
        print(f"=== {account.name} ({account.user}) ===")
        conn = connect_imap(account)
        try:
            emails = fetch_unread(conn, limit=args.limit)
            print(f"{len(emails)} unread\n")
            for e in emails:
                print(f"[{e.uid}] {e.date}")
                print(f"  From:    {e.from_}")
                print(f"  Subject: {e.subject}")
                preview = e.body.replace("\n", " ").strip()[:1000]
                print(f"  Preview: {preview}")
                print()
        finally:
            conn.logout()


if __name__ == "__main__":
    main()
