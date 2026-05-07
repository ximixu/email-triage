from src.config import load_config
from src.imap_client import connect_imap, fetch_unread


def main() -> None:
    conn = connect_imap(load_config())
    try:
        emails = fetch_unread(conn)
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
