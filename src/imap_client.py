import email
from dataclasses import dataclass

import imaplib

from .config import AppConfig
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


def connect_imap(config: AppConfig) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(config.imap_host)
    if config.use_oauth:
        token = get_access_token(config.oauth_client_id, config.oauth_tenant)
        auth_string = f"user={config.imap_user}\x01auth=Bearer {token}\x01\x01"
        conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
    else:
        conn.login(config.imap_user, config.imap_pass)
    return conn


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
