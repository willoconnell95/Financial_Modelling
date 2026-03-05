"""
email_sender.py
---------------
Sends the HTML deal summary via SMTP.

All credentials are read from environment variables (loaded via python-dotenv
in app.py before this module is imported).

Supported providers
-------------------
- Gmail  : SMTP_HOST=smtp.gmail.com  SMTP_PORT=587
- Outlook: SMTP_HOST=smtp.office365.com  SMTP_PORT=587
- Any STARTTLS or SSL/TLS SMTP server
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

RECIPIENT = "will@athletic.vc"


def send_summary_email(html_content: str, subject: str = "Deal Summary — Athletic VC") -> None:
    """
    Send *html_content* as an HTML email to ``RECIPIENT``.

    Environment variables
    ---------------------
    SMTP_HOST      : SMTP server hostname  (required)
    SMTP_PORT      : SMTP port, default 587
    SMTP_USERNAME  : Login username        (required)
    SMTP_PASSWORD  : Login password        (required)
    SMTP_SENDER    : From address; falls back to SMTP_USERNAME

    Raises
    ------
    RuntimeError
        If required SMTP credentials are missing or the send fails.
    """
    host = os.environ.get("SMTP_HOST", "").strip()
    port_str = os.environ.get("SMTP_PORT", "587").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_SENDER", username).strip()

    missing = [
        name
        for name, val in [("SMTP_HOST", host), ("SMTP_USERNAME", username), ("SMTP_PASSWORD", password)]
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing required SMTP environment variable(s): {', '.join(missing)}. "
            "Check your .env file."
        )

    try:
        port = int(port_str)
    except ValueError:
        raise RuntimeError(f"SMTP_PORT must be an integer, got: '{port_str}'")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = RECIPIENT

    # Plain-text fallback (basic strip of HTML tags)
    plain_text = _html_to_plain(html_content)
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    logger.info("Connecting to SMTP %s:%d as %s…", host, port, username)

    try:
        if port == 465:
            # SSL from the start
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(username, password)
                server.sendmail(sender, [RECIPIENT], msg.as_string())
        else:
            # STARTTLS (587 / 25)
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.sendmail(sender, [RECIPIENT], msg.as_string())

        logger.info("Email delivered successfully to %s", RECIPIENT)

    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            f"SMTP authentication failed. Check SMTP_USERNAME / SMTP_PASSWORD. "
            f"(server said: {exc.smtp_error!r})"
        ) from exc
    except smtplib.SMTPException as exc:
        raise RuntimeError(f"SMTP error: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(
            f"Could not connect to SMTP server {host}:{port} — {exc}"
        ) from exc


def _html_to_plain(html: str) -> str:
    """Very simple HTML → plain text for the fallback MIME part."""
    import re

    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</tr>|</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
