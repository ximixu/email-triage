import email
import email.header
from dataclasses import dataclass

import imaplib

from .config import Account
from .oauth import get_access_token
from .retry import with_retries

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

    def _connect() -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(account.host)
        try:
            conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
        except Exception:
            # Don't leak the open socket when auth fails before we return.
            try:
                conn.shutdown()
            except Exception:
                pass
            raise
        return conn

    # Retry only transient failures (dropped sockets, TLS hiccups, server aborts).
    # imaplib.IMAP4.error (auth rejection) is not retried, so a bad token fails fast.
    return with_retries(
        _connect,
        attempts=max_retries,
        retry_on=(OSError, imaplib.IMAP4.abort),
    )


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


def _decode_header(value) -> str:
    """Decode an RFC 2047 encoded-word header (e.g. =?UTF-8?Q?...?=) to text."""
    if value is None:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(str(value))))
    except Exception:
        return str(value)


def _parse_email(uid: bytes, raw: bytes) -> Email | None:
    msg = email.message_from_bytes(raw)
    message_id = str(msg.get("Message-ID", ""))
    from_ = _decode_header(msg.get("From"))
    subject = _decode_header(msg.get("Subject"))
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
