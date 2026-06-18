"""Gmail API integration for reading and sending emails."""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
import db
from parser import parse_firmware_email

logger = logging.getLogger(__name__)


def _get_credentials() -> Credentials:
    """
    Load or refresh OAuth credentials for Gmail API.

    On first run, opens a browser for OAuth consent and saves token.json.
    """
    creds: Optional[Credentials] = None

    if config.TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(config.TOKEN_PATH),
            config.GMAIL_SCOPES,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Missing {config.CREDENTIALS_PATH}. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.CREDENTIALS_PATH),
                config.GMAIL_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        config.TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_gmail_service() -> Any:
    """Build and return an authenticated Gmail API service client."""
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict[str, Any]) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    body_text = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    body_text += base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
            elif "parts" in part:
                body_text += _decode_body(part)
    else:
        data = payload.get("body", {}).get("data")
        if data:
            body_text = base64.urlsafe_b64decode(data).decode(
                "utf-8", errors="replace"
            )

    return body_text


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Return a header value by name (case-insensitive)."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def fetch_validation_emails(service: Any) -> list[dict[str, str]]:
    """
    Fetch inbox messages whose subject contains the validation keyword.

    Returns a list of dicts with keys: id, subject, body.
    """
    query = f"subject:({config.KEYWORD} OR {config.EOL_KEYWORD})"
    results: list[dict[str, str]] = []

    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=50)
            .execute()
        )
        messages = response.get("messages", [])

        for msg_ref in messages:
            msg_id = msg_ref["id"]
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            subject = _get_header(headers, "Subject")
            body = _decode_body(msg.get("payload", {}))

            results.append({"id": msg_id, "subject": subject, "body": body})

    except HttpError as exc:
        logger.error("Gmail API error while fetching messages: %s", exc)
        raise
    logger.info("Fetched %d emails from Gmail query", len(results))
    return results


def process_inbox() -> int:
    """
    Check Gmail inbox, parse validation emails, and update the database.

    Returns the number of newly processed emails.
    """
    logger.info("Gmail check started")
    processed_count = 0

    try:
        service = get_gmail_service()
        emails = fetch_validation_emails(service)

        # Mark stale devices inactive before processing new data
        stale_count = db.update_device_status_by_age()
        if stale_count:
            logger.info("Marked %d device(s) as inactive (90-day rule)", stale_count)

        for email in emails:
            msg_id = email["id"]

            if db.is_email_processed(msg_id):
                continue

            subject = email["subject"]
            body = email["body"]

            # =========================
            # ⭐ EOL 处理（新增）
            # =========================
            subject_upper = subject.upper()

            if "EOL CONFIRMED" in subject_upper:
                logger.info("EOL email detected: %s", subject)

                device_name = subject.split("]")[0].replace("[", "").replace("[", "").strip()

                db.mark_device_eol(device_name)

                # ⭐ 这里加 event 记录（重点）
                db.insert_event(
                    device=device_name,
                    version="EOL",
                    raw_text=body,
                )

                db.mark_email_processed(msg_id)
                continue

            # =========================
            # SW Validation 才继续走旧逻辑
            # =========================
            if config.KEYWORD not in subject:
                continue

            firmware = parse_firmware_email(subject, body)
            if firmware is None:
                logger.warning(
                    "Could not parse email id=%s subject=%r", msg_id, subject
                )
                # Still mark as processed to avoid re-parsing failures
                db.mark_email_processed(msg_id)
                continue

            was_update = db.upsert_device(
                device=firmware.device,
                device_type=firmware.type,
                version=firmware.version,
                patch=firmware.patch,
                md5=firmware.md5,
                status=firmware.status,
            )

            db.insert_event(
                device=firmware.device,
                version=firmware.version,
                raw_text=body,
            )
            db.mark_email_processed(msg_id)
            processed_count += 1

            action = "updated" if was_update else "inserted"
            logger.info(
                "Email processed: id=%s device=%s (%s)",
                msg_id,
                firmware.device,
                action,
            )
            logger.info(
                "Device %s: version=%s patch=%s md5=%s",
                firmware.device,
                firmware.version,
                firmware.patch,
                firmware.md5,
            )

        logger.info(
            "Gmail check finished: %d new email(s) processed", processed_count
        )

    except Exception as exc:
        logger.exception("Error during Gmail check: %s", exc)

    return processed_count


def send_email(
    subject: str,
    html_body: str,
    to_email: str | list[str] | None = None,
    cc_email: str | list[str] | None = None,
) -> bool:
    """
    Send an HTML email via Gmail API.
    """

    try:
        service = get_gmail_service()

        # =========================
        # Normalize recipients
        # =========================
        if to_email is None:
            recipients = config.TO_EMAILS
        elif isinstance(to_email, str):
            recipients = [to_email]
        else:
            recipients = to_email

        if cc_email is None:
            cc_list = []
        elif isinstance(cc_email, str):
            cc_list = [cc_email]
        else:
            cc_list = cc_email

            
        recipients = [
            r.strip()
            for r in recipients
            if r and r.strip() and "@" in r
        ]

        if not recipients:
            raise ValueError("No valid recipients found")

        # =========================
        # Build message
        # =========================
        message = MIMEMultipart("alternative")

        message["To"] = ", ".join(recipients)
        if config.CC_EMAILS:
            message["Cc"] = ", ".join(config.CC_EMAILS)

        message["From"] = config.EMAIL_USER
        message["Subject"] = subject

        message.attach(MIMEText(html_body, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        # =========================
        # Send
        # =========================
        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()

        logger.info("Report sent to %s", ", ".join(recipients))
        return True

    except HttpError as exc:
        logger.error("Gmail API error while sending email: %s", exc)
        return False

    except Exception as exc:
        logger.exception("Error sending email: %s", exc)
        return False
        
if __name__ == "__main__":
    """Run a one-shot Gmail inbox check (for testing). Use main.py for full agent."""
    import sys

    from logging.handlers import RotatingFileHandler

    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=config.LOG_MAX_BYTES,
                backupCount=config.LOG_BACKUP_COUNT,
                encoding="utf-8",
            ),
        ],
    )

    print("Running one-shot Gmail check...")
    print(f"Account: {config.EMAIL_USER}")
    print(f"Keyword: {config.KEYWORD}")
    print("Tip: First run requires browser OAuth — complete login when prompted.")
    print("-" * 50)

    db.init_db()
    count = process_inbox()
    print("-" * 50)
    print(f"Done. New emails processed: {count}")
