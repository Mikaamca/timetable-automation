#!/usr/bin/env python3
"""
Fetch the newest GMI timetable (.dav) from the mailbox and rebuild timetable.json.

Environment variables (set them as GitHub Actions secrets, never in code):
    EMAIL_USER, EMAIL_PASS   mailbox login (use an App Password)
    IMAP_SERVER              default imap.gmail.com
Optional:
    LOOKBACK_DAYS            how far back to look for mail (default 21)
    SENDER_FILTER            only mail whose From contains this text (e.g. "gmi.edu.my")
    CLASS_NAME               default "SEM 5 - DCBS 5"

Exit codes: 0 = OK / nothing new, 1 = mailbox problem, otherwise convert_dav.py's code
(2 = unknown .dav format, 3 = class not found). On any failure timetable.json is untouched.
"""
import datetime
import email
import imaplib
import json
import os
import subprocess
import sys
from email.header import decode_header, make_header
from pathlib import Path

IMAP_SERVER = os.environ.get("IMAP_SERVER") or "imap.gmail.com"   # secrets may be set but empty
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS") or 21)
SENDER_FILTER = os.environ.get("SENDER_FILTER") or ""
CLASS_NAME = os.environ.get("CLASS_NAME") or "SEM 5 - DCBS 5"

DAV_PATH = Path("latest_schedule.dav")      # working copy only, listed in .gitignore
JSON_PATH = Path("timetable.json")
META_PATH = Path("timetable_meta.json")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def imap_date(d):
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year}"


def attachment_name(part):
    name = part.get_filename()
    if not name:
        return None
    try:
        return str(make_header(decode_header(name)))
    except Exception:
        return name


def dav_attachments(msg):
    """All (filename, bytes) pairs ending in .dav, with or without Content-Disposition."""
    found = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        name = attachment_name(part)
        if name and name.lower().endswith(".dav"):
            payload = part.get_payload(decode=True)      # NB: the keyword is decode, not decode_bytes
            if payload:
                found.append((name, payload))
    return found


def fetch_newest_dav(mail):
    """Newest mail (within LOOKBACK_DAYS) that carries a .dav. Read-only: flags are never changed."""
    mail.select("INBOX", readonly=True)
    since = imap_date(datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS))
    criteria = ["SINCE", since]
    if SENDER_FILTER:
        criteria += ["FROM", f'"{SENDER_FILTER}"']
    status, data = mail.search(None, *criteria)
    if status != "OK":
        raise RuntimeError("IMAP search failed")
    ids = data[0].split()
    for mid in reversed(ids):                             # newest first
        status, st = mail.fetch(mid, "(BODYSTRUCTURE)")
        if status != "OK":
            continue
        blob = b" ".join(x if isinstance(x, bytes) else b"".join(x) for x in st if x)
        if b".dav" not in blob.lower():
            continue
        status, msgdata = mail.fetch(mid, "(BODY.PEEK[])")
        for part in msgdata:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                files = sorted(dav_attachments(msg))
                if files:
                    subject = str(make_header(decode_header(msg.get("Subject", ""))))
                    name, payload = files[-1]
                    return name, payload, subject
    return None


def main():
    if not EMAIL_USER or not EMAIL_PASS:
        print("ERROR: EMAIL_USER / EMAIL_PASS not set.", file=sys.stderr)
        return 1
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:                                 # never print the password
        print(f"ERROR: cannot log in to {IMAP_SERVER}: {type(e).__name__}", file=sys.stderr)
        return 1
    try:
        result = fetch_newest_dav(mail)
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    if result is None:
        print(f"Tiada emel dengan fail .dav dalam {LOOKBACK_DAYS} hari lepas.")
        return 0
    name, payload, subject = result
    print(f"Fail terkini: {name} (subjek: {subject!r}, {len(payload)} bait)")

    import hashlib
    sha = hashlib.sha256(payload).hexdigest()
    if META_PATH.exists() and JSON_PATH.exists():
        try:
            if json.loads(META_PATH.read_text(encoding="utf-8")).get("source_sha256") == sha:
                print("Fail sama dengan yang sedia ada. Tiada perubahan.")
                return 0
        except Exception:
            pass

    DAV_PATH.write_bytes(payload)
    rc = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("convert_dav.py")),
         str(DAV_PATH), str(JSON_PATH), "--class", CLASS_NAME, "--source-name", name]
    ).returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
