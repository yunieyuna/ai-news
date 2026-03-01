"""Send notification via SMTP (free with Gmail app password)."""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import get_settings
from src.analyze.summarize import SummarizedDigest
from src.logging_config import get_logger

logger = get_logger("notify")


def send_notification(
    digest: SummarizedDigest,
    success: bool,
    detail: str = "",
) -> bool:
    """Send one email summarizing the run. Respects notify.method (email vs none). Returns True if sent."""
    settings = get_settings()
    notify = settings.get("notify") or {}
    method = (notify.get("method") or "email").lower()
    if method != "email":
        logger.info("Notify method is %s; skipping email", method)
        return False

    if success and not notify.get("send_on_success", True):
        return False
    if not success and not notify.get("send_on_failure", True):
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("NOTIFY_EMAIL_TO")

    if not all([host, user, password, to_addr]):
        logger.warning("Email skipped: set SMTP_* and NOTIFY_EMAIL_TO in .env")
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
        logger.info("Email sent to %s", to_addr)
        return True
    except Exception as e:
        logger.exception("Email failed: %s", e)
        return False
