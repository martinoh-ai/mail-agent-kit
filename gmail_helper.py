#!/usr/bin/env python3
"""gmail_helper.py — CLI Gmail pour le SOUL mail-triage Hermes.

Commands:
  list [--max N] [--query GMAIL_QUERY]
      Liste les N derniers threads matching query (default: in:inbox newer_than:1d).
      Output: JSON array [{id, subject, from, date, snippet, unread, starred}, ...]

  read <id>
      Récupère le contenu complet d'un thread (ou message). Output: JSON {id, subject, from, to, body_text, headers}.

  archive <id> [--dry-run]
      Archive un thread (retire label INBOX). --dry-run = log only.

  save-draft --to ADDR --subject S --body B [--reply-to MSG_ID]
      Crée un brouillon dans Gmail Drafts. Output: JSON {draft_id}.

  state <id>
      Récupère l'état d'un thread : flags (UNREAD, STARRED, INBOX, TRASH), martin_replied.
      Utile pour le learning loop.

Env required: MAIL_TRIAGE_GMAIL_PASS (App Password Gmail, 16 chars).
"""
import os
import sys
import json
import imaplib
import smtplib
import email
import email.message
import argparse
import re
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime, formatdate, make_msgid

def _load_env():
    import os as _os
    f = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env')
    if _os.path.exists(f):
        for line in open(f):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                _os.environ.setdefault(k.strip(), v.strip().strip(chr(34)).strip(chr(39)))
_load_env()

GMAIL_ACCOUNT = os.environ.get("GMAIL_USER", "")
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

INBOX = "INBOX"
ALL_MAIL = '"[Gmail]/All Mail"'
DRAFTS = '"[Gmail]/Drafts"'
SENT = '"[Gmail]/Sent Mail"'


def get_password() -> str:
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        sys.stderr.write("FATAL: GMAIL_APP_PASSWORD manquant (cf .env)\n")
        sys.exit(2)
    return pw


def _detect_drafts(m):
    try:
        typ, boxes = m.list()
        for b in boxes:
            s = b.decode("utf-8", "replace") if isinstance(b, (bytes, bytearray)) else str(b)
            if "\\Drafts" in s:
                return s.split(' "/" ')[-1].strip().strip('"')
    except Exception:
        pass
    return "[Gmail]/Drafts"


def connect_imap() -> imaplib.IMAP4_SSL:
    m = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    m.login(GMAIL_ACCOUNT, get_password())
    return m


def _decode(s) -> str:
    if isinstance(s, bytes):
        try:
            return s.decode("utf-8", errors="replace")
        except Exception:
            return s.decode("latin-1", errors="replace")
    return str(s) if s is not None else ""


def _parse_envelope(msg_id: str, msg_data: bytes) -> dict:
    msg = email.message_from_bytes(msg_data)
    return {
        "id": msg_id,
        "subject": _decode(msg.get("Subject", "")),
        "from": _decode(msg.get("From", "")),
        "to": _decode(msg.get("To", "")),
        "date": _decode(msg.get("Date", "")),
        "message_id": _decode(msg.get("Message-ID", "")),
    }


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    return part.get_payload(decode=False) or ""
        # Fallback: html → strip tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                    return re.sub(r"<[^>]+>", " ", html)
                except Exception:
                    return part.get_payload(decode=False) or ""
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        try:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            return str(payload)
    return msg.get_payload(decode=False) or ""


def cmd_list(args):
    m = connect_imap()
    try:
        m.select(INBOX, readonly=True)
        query = args.query or "ALL"
        # Use Gmail-specific X-GM-RAW for advanced queries like "newer_than:1d"
        if args.query and any(t in args.query for t in ("newer_than", "older_than", "from:", "to:", "has:", "is:")):
            typ, data = m.search(None, "X-GM-RAW", f'"{args.query}"')
        elif args.query and args.query.lower() != "all":
            # Simple subject/from substring
            typ, data = m.search(None, query)
        else:
            # Default = last 24h via X-GM-RAW (Gmail trick)
            typ, data = m.search(None, "X-GM-RAW", '"newer_than:1d"')
        ids = data[0].split() if data and data[0] else []
        # Sort desc (newest first) and cap
        ids = list(reversed(ids))[: args.max]
        out = []
        for mid in ids:
            mid_s = mid.decode()
            typ, env_data = m.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE MESSAGE-ID)] FLAGS X-GM-THRID)")
            if typ != "OK" or not env_data:
                continue
            # env_data shape: [(b'1 (FLAGS (\\Seen) X-GM-THRID 1234 BODY[...] {N}', b'headers...'), b')']
            flags = []
            gm_thrid = None
            for item in env_data:
                if isinstance(item, tuple):
                    meta = item[0].decode(errors="replace")
                    fmatch = re.search(r"FLAGS \(([^)]*)\)", meta)
                    if fmatch:
                        flags = fmatch.group(1).split()
                    tmatch = re.search(r"X-GM-THRID (\d+)", meta)
                    if tmatch:
                        gm_thrid = tmatch.group(1)
                    env = _parse_envelope(mid_s, item[1])
                    env["unread"] = "\\Seen" not in flags
                    env["starred"] = "\\Flagged" in flags
                    env["thread_id"] = gm_thrid or mid_s
                    out.append(env)
                    break
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        try:
            m.logout()
        except Exception:
            pass


def cmd_read(args):
    m = connect_imap()
    try:
        m.select(INBOX, readonly=True)
        typ, data = m.fetch(args.id.encode(), "(RFC822 FLAGS X-GM-THRID X-GM-LABELS)")
        if typ != "OK" or not data:
            print(json.dumps({"error": "not found", "id": args.id}))
            sys.exit(1)
        msg = None
        flags = []
        labels = []
        for item in data:
            if isinstance(item, tuple):
                meta = item[0].decode(errors="replace")
                fmatch = re.search(r"FLAGS \(([^)]*)\)", meta)
                if fmatch:
                    flags = fmatch.group(1).split()
                lmatch = re.search(r"X-GM-LABELS \(([^)]*)\)", meta)
                if lmatch:
                    labels = lmatch.group(1).split()
                msg = email.message_from_bytes(item[1])
        if msg is None:
            print(json.dumps({"error": "parse failed", "id": args.id}))
            sys.exit(1)
        out = {
            "id": args.id,
            "subject": _decode(msg.get("Subject", "")),
            "from": _decode(msg.get("From", "")),
            "to": _decode(msg.get("To", "")),
            "date": _decode(msg.get("Date", "")),
            "message_id": _decode(msg.get("Message-ID", "")),
            "in_reply_to": _decode(msg.get("In-Reply-To", "")),
            "references": _decode(msg.get("References", "")),
            "body_text": _extract_body(msg)[: args.max_body_chars],
            "unread": "\\Seen" not in flags,
            "starred": "\\Flagged" in flags,
            "labels": labels,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        try:
            m.logout()
        except Exception:
            pass


def cmd_archive(args):
    if args.dry_run:
        print(json.dumps({"id": args.id, "action": "would_archive", "dry_run": True}))
        return
    m = connect_imap()
    try:
        m.select(INBOX)
        # Gmail archive = remove from INBOX (move to All Mail). Standard IMAP: STORE -X-GM-LABELS.
        typ, _ = m.store(args.id.encode(), "-X-GM-LABELS", "\\Inbox")
        if typ != "OK":
            print(json.dumps({"error": "archive failed", "id": args.id}))
            sys.exit(1)
        print(json.dumps({"id": args.id, "action": "archived"}))
    finally:
        try:
            m.logout()
        except Exception:
            pass


def cmd_state(args):
    """Get current state of a message (for learning loop)."""
    m = connect_imap()
    try:
        # Use INBOX as a stable starting point, then search by X-GM-MSGID across all accessible mailboxes
        m.select(INBOX, readonly=True)
        typ, data = m.search(None, "X-GM-MSGID", args.id)
        
        if typ != "OK" or not data or not data[0]:
            # Try a UID-based fetch if we have the id as UID
            try:
                typ, data = m.fetch(args.id, "(FLAGS X-GM-LABELS)")
            except:
                # Give up
                print(json.dumps({"error": "not found", "id": args.id}))
                sys.exit(1)
        else:
            uid = data[0].split()[0]
            typ, data = m.fetch(uid, "(FLAGS X-GM-LABELS)")
        
        if typ != "OK" or not data or not data[0]:
            print(json.dumps({"error": "not found", "id": args.id}))
            sys.exit(1)
        
        flags = []
        labels = []
        for item in data:
            s = item.decode(errors="replace") if isinstance(item, bytes) else (item[0].decode() if isinstance(item, tuple) else "")
            fmatch = re.search(r"FLAGS \(([^)]*)\)", s)
            if fmatch:
                flags = fmatch.group(1).split()
            lmatch = re.search(r"X-GM-LABELS \(([^)]*)\)", s)
            if lmatch:
                labels = lmatch.group(1).split()
        
        out = {
            "id": args.id,
            "unread": "\\Seen" not in flags,
            "starred": "\\Flagged" in flags,
            "in_inbox": "\\\\Inbox" in labels,
            "in_trash": "\\\\Trash" in labels,
            "in_spam": "\\\\Spam" in labels,
            "labels": labels,
        }
        print(json.dumps(out, ensure_ascii=False))
    finally:
        try:
            m.logout()
        except Exception:
            pass


def cmd_save_draft(args):
    msg = email.message.EmailMessage()
    msg["From"] = GMAIL_ACCOUNT
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if args.reply_to:
        msg["In-Reply-To"] = args.reply_to
        msg["References"] = args.reply_to
    msg.set_content(args.body)
    m = connect_imap()
    try:
        # APPEND to Drafts folder with \Draft flag
        m.append(_detect_drafts(m), "\\Draft", imaplib.Time2Internaldate(datetime.now(timezone.utc)), msg.as_bytes())
        print(json.dumps({"action": "draft_saved", "to": args.to, "subject": args.subject}))
    finally:
        try:
            m.logout()
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser(description="Gmail helper for mail-triage SOUL")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List inbox threads")
    p_list.add_argument("--max", type=int, default=80)
    p_list.add_argument("--query", type=str, default=None, help="Gmail X-GM-RAW query (e.g. 'newer_than:1d')")
    p_list.set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="Read a thread/message")
    p_read.add_argument("id")
    p_read.add_argument("--max-body-chars", type=int, default=4000)
    p_read.set_defaults(func=cmd_read)

    p_arch = sub.add_parser("archive", help="Archive (remove from INBOX)")
    p_arch.add_argument("id")
    p_arch.add_argument("--dry-run", action="store_true")
    p_arch.set_defaults(func=cmd_archive)

    p_state = sub.add_parser("state", help="Get current state (for learning)")
    p_state.add_argument("id")
    p_state.set_defaults(func=cmd_state)

    p_draft = sub.add_parser("save-draft", help="Save a draft reply")
    p_draft.add_argument("--to", required=True)
    p_draft.add_argument("--subject", required=True)
    p_draft.add_argument("--body", required=True)
    p_draft.add_argument("--reply-to", default=None, help="Message-ID to thread on")
    p_draft.set_defaults(func=cmd_save_draft)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
