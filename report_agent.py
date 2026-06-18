"""Weekly HTML firmware report generation and delivery."""

from __future__ import annotations

import logging
from datetime import datetime
from html import escape
from typing import Any

import config
import db
from gmail_agent import send_email

logger = logging.getLogger(__name__)

REPORT_TITLE = "Weekly Software Report"

# Display order for device type groups
_TYPE_ORDER = ["Tablet", "Phone", "Others"]


def _group_devices_by_type(
    devices: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group active devices by type, normalising unknown types to Others."""
    groups: dict[str, list[dict[str, Any]]] = {
        "Tablet": [],
        "Phone": [],
        "Others": [],
    }

    for device in devices:
        device_type = device.get("type", "Others")
        if device_type not in groups:
            device_type = "Others"
        groups[device_type].append(device)

    return groups


def _format_last_update(value: str | None) -> str:
    """Format an ISO datetime string for display."""
    if not value:
        return "N/A"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return escape(str(value))


def generate_html_report() -> str:
    """
    Build an HTML report containing only active devices grouped by type.

    Groups: Tablet, Phone, Others.
    Columns: Device, Version, Status, Last Update.
    """
    devices = db.get_active_devices()
    groups = _group_devices_by_type(devices)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections: list[str] = []

    for group_name in _TYPE_ORDER:
        group_devices = groups.get(group_name, [])
        if not group_devices:
            continue

        rows: list[str] = []
        for dev in group_devices:

            status = dev["status"]

            if status == "updated":
                status_html = f'<span style="color:green;font-weight:bold;">updated</span>'
            elif status == "wait_for_updated":
                status_html = f'<span style="color:red;font-weight:bold;">wait_for_updated</span>'
            else:
                status_html = f'<span style="color:gray;">{status}</span>'
            
            rows.append(
                "<tr>"
                f"<td>{escape(dev['device'])}</td>"
                f"<td>{escape(dev['version'])}</td>"
                f"<td>{escape(dev.get('patch', ''))}</td>"
                f"<td>{status_html}</td>" 
                f"<td>{_format_last_update(dev.get('last_update'))}</td>"
                "</tr>"
            )

        sections.append(
            f"""
            <h2>{escape(group_name)}</h2>
            <table border="1" cellpadding="8" cellspacing="0"
                   style="border-collapse:collapse;width:100%;margin-bottom:24px;">
              <thead>
                <tr style="background-color:#f0f0f0;">
                  <th>Device</th>
                  <th>Version</th>
                  <th>Patch</th>
                  <th>Status</th>
                  <th>Last Update</th>
                </tr>
              </thead>
              <tbody>
                {''.join(rows)}
              </tbody>
            </table>
            """
        )

    if not sections:
        body_content = "<p>No active devices found.</p>"
    else:
        body_content = "".join(sections)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(REPORT_TITLE)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #333; }}
    h1 {{ color: #1a5276; }}
    h2 {{ color: #2874a6; margin-top: 32px; }}
    table {{ font-size: 14px; }}
    th {{ text-align: left; }}
  </style>
</head>
<body>
  <h1>{escape(REPORT_TITLE)}</h1>
  <p>Generated: {escape(generated_at)}</p>
  {body_content}
</body>
</html>"""

    return html


def send_weekly_report() -> bool:
    """
    Generate and email the weekly firmware report.

    Returns True if the report was sent successfully.
    """
    logger.info("Weekly report generation started")

    try:
        # Refresh inactive status before reporting
        stale_count = db.mark_stale_devices_inactive()
        if stale_count:
            logger.info(
                "Marked %d device(s) inactive before report", stale_count
            )

        html = generate_html_report()
        success = send_email(
            subject=REPORT_TITLE,
            html_body=html,
            to_email=config.TO_EMAIL,
        )

        if success:
            logger.info("Weekly report sent successfully")
        else:
            logger.error("Failed to send weekly report")

        return success

    except Exception as exc:
        logger.exception("Error generating or sending weekly report: %s", exc)
        return False


if __name__ == "__main__":
    """Generate (and optionally send) the weekly report for testing."""
    import argparse
    import sys
    from logging.handlers import RotatingFileHandler
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Firmware weekly report tool")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send report email via Gmail API (default: preview only)",
    )
    args = parser.parse_args()

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

    print("Weekly Report Tool")
    print(f"  Recipient: {config.TO_EMAIL}")
    print("-" * 50)

    db.init_db()
    devices = db.get_active_devices()
    groups = _group_devices_by_type(devices)

    print(f"Active devices: {len(devices)}")
    for group_name in _TYPE_ORDER:
        count = len(groups.get(group_name, []))
        if count:
            print(f"  {group_name}: {count}")

    html = generate_html_report()
    report_dir = config.BASE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "latest_report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"HTML saved: {report_path}")

    if args.send:
        print("Sending report email...")
        success = send_weekly_report()
        print("-" * 50)
        print("Sent successfully." if success else "Failed to send report.")
    else:
        print("-" * 50)
        print("Preview only. To send email, run: python report_agent.py --send")
