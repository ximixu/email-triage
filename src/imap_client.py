import email
import time
from dataclasses import dataclass

import imaplib

from .config import Account
from .oauth import get_access_token

BODY_TRUNCATE_CHARS = 2000


@dataclass
class Email:
    uid: str
    message_id: str
    from_: str
    subject: str
    date: str
    body: str


def connect_imap(account: Account, max_retries: int = 3) -> imaplib.IMAP4_SSL:
    token = get_access_token(account)
    auth_string = f"user={account.user}\x01auth=Bearer {token}\x01\x01"

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            conn = imaplib.IMAP4_SSL(account.host)
            conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
            return conn
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff

    raise last_exc  # type: ignore[misc]


def fetch_unread(conn: imaplib.IMAP4_SSL, limit: int | None = None) -> list[Email]:
    conn.select("INBOX")
    status, data = conn.uid("SEARCH", None, "UNSEEN")
    if status != "OK":
        return []

    uids = data[0].split()
    if limit is not None:
        uids = uids[:limit]

    emails: list[Email] = []
    for uid in uids:
        status, msg_data = conn.uid("FETCH", uid, "(RFC822)")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        email = _parse_email(uid, raw)
        if email:
            emails.append(email)

    return emails


def _parse_email(uid: bytes, raw: bytes) -> Email | None:
    msg = email.message_from_bytes(raw)
    message_id = str(msg.get("Message-ID", ""))
    from_ = str(msg.get("From", ""))
    subject = str(msg.get("Subject", ""))
    date = str(msg.get("Date", ""))

    body = _extract_body(msg)
    if not body:
        return None

    body = body[:BODY_TRUNCATE_CHARS]

    return Email(
        uid=uid.decode(),
        message_id=message_id,
        from_=from_,
        subject=subject,
        date=date,
        body=body,
    )


def mark_read(conn: imaplib.IMAP4_SSL, uid: str, account: Account) -> None:
    # No-op: fetch_unread's FETCH RFC822 already sets \Seen server-side.
    # Kept in ACTIONS for dispatch symmetry with categories.yaml.
    pass


def mark_unread(conn: imaplib.IMAP4_SSL, uid: str, account: Account) -> None:
    conn.uid("STORE", uid, "-FLAGS", "(\\Seen)")


def move_to_folder(conn: imaplib.IMAP4_SSL, uid: str, folder: str) -> None:
    conn.uid("COPY", uid, folder)
    conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
    conn.expunge()


def move_to_junk(conn: imaplib.IMAP4_SSL, uid: str, account: Account) -> None:
    move_to_folder(conn, uid, account.junk_folder)


def delete(conn: imaplib.IMAP4_SSL, uid: str, account: Account) -> None:
    conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
    conn.expunge()


ACTIONS = {
    "mark_read": mark_read,
    "mark_unread": mark_unread,
    "move_to_junk": move_to_junk,
    "delete": delete,
}


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="replace")
        return ""
