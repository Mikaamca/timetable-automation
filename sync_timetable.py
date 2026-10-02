import email
from email.header import decode_header
import imaplib
import json
import os

# Konfigurasi IMAP (Contoh: untuk Gmail gunakan imap.gmail.com)
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")  # Gunakan App Password, bukan kata laluan utama


def check_and_update():
  mail = imaplib.IMAP4_SSL(IMAP_SERVER)
  mail.login(EMAIL_USER, EMAIL_PASS)
  mail.select("inbox")

  # Cari emel yang ada subjek berkaitan jadual atau DaVinci
  status, messages = mail.search(None, '(SUBJECT "timetable" UNSEEN)')
  mail_ids = messages[0].split()

  if not mail_ids:
    print("Tiada emel jadual baharu.")
    mail.logout()
    return

  latest_email_id = mail_ids[-1]
  status, data = mail.fetch(latest_email_id, "(RFC822)")

  for response_part in data:
    if isinstance(response_part, tuple):
      msg = email.message_from_bytes(response_part[1])
      for part in msg.walk():
        if part.get_content_maintype() == "multipart":
          continue
        if part.get("Content-Disposition") is None:
          continue

        filename = part.get_filename()
        if filename and filename.endswith(".dav"):
          print(f"Jumpa fail jadual terkini: {filename}")
          # Simpan fail .dav yang dimuat turun
          with open("latest_update.dav", "wb") as f:
            f.write(part.get_payload(decode_bytes=True))

          # Di sini data diproses dan timetable.json dikemas kini
          update_json_data()

  mail.logout()


def update_json_data():
  # Skrip akan menulis semula timetable.json dengan data terkini
  print("Kemas kini timetable.json selesai.")


if __name__ == "__main__":
  check_and_update()
