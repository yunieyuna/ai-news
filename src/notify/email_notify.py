"""Send notification via SMTP (free with Gmail app password)."""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.analyze.summarize import SummarizedDigest


def send_notification(
    digest: SummarizedDigest,
    success: bool,
    detail: str = "",
) -> bool:
    """Send one email summarizing the run. Returns True if sent."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("NOTIFY_EMAIL_TO")

    if not all([host, user, password, to_addr]):
        print("[notify] Email skipped: set SMTP_* and NOTIFY_EMAIL_TO in .env")
        return False

    status = "Success" if success else "Failed"
    body = f"AI News digest run: {status}\n\n"
    if detail:
        body += f"Detail: {detail}\n\n"
    body += "--- Summary ---\n\n"
    body += digest.summary_text or "(No summary)"

    msg = MIMEMultipart()
    msg["Subject"] = f"AI News Digest — {status}"
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
        print("[notify] Email sent to", to_addr)
        return True
    except Exception as e:
        print("[notify] Email failed:", e)
        return False
