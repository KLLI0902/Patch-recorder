"""Application configuration for Firmware Validation Agent."""

from __future__ import annotations

import os
from pathlib import Path

# Base paths (defined first so .env path can be resolved)
BASE_DIR: Path = Path(__file__).resolve().parent

# Load .env if present (optional dependency)
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

LOGS_DIR: Path = BASE_DIR / "logs"
DB_PATH: Path = BASE_DIR / "firmware.db"
CREDENTIALS_PATH: Path = BASE_DIR / "credentials.json"
TOKEN_PATH: Path = BASE_DIR / "token.json"

# Gmail monitoring
KEYWORD: str = os.environ.get("KEYWORD", "SW Validation")
CHECK_INTERVAL_MINUTES: int = int(os.environ.get("CHECK_INTERVAL_MINUTES", "10"))

# Email accounts — load from environment; never hardcode secrets in source.
EMAIL_USER: str = os.environ.get("EMAIL_USER", "logicom.smqd@gmail.com")
EMAIL_PASS: str = os.environ.get("EMAIL_PASS", "")
TO_EMAIL: str = os.environ.get("TO_EMAIL", "k.li@logicom-europe.com")

# Device lifecycle
INACTIVE_DAYS: int = int(os.environ.get("INACTIVE_DAYS", "90"))

# Scheduler — weekly report every Monday at 10:00
REPORT_DAY_OF_WEEK: str = os.environ.get("REPORT_DAY_OF_WEEK", "mon")
REPORT_HOUR: int = int(os.environ.get("REPORT_HOUR", "10"))
REPORT_MINUTE: int = int(os.environ.get("REPORT_MINUTE", "0"))

# Gmail API scopes
GMAIL_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Logging
LOG_FILE: Path = LOGS_DIR / "firmware_agent.log"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 5


if __name__ == "__main__":
    """Print current configuration (secrets masked)."""
    print("Configuration")
    print("-" * 50)
    print(f"  KEYWORD               : {KEYWORD}")
    print(f"  CHECK_INTERVAL_MINUTES: {CHECK_INTERVAL_MINUTES}")
    print(f"  EMAIL_USER            : {EMAIL_USER}")
    print(f"  EMAIL_PASS            : {'*' * 8 if EMAIL_PASS else '(not set)'}")
    print(f"  TO_EMAIL              : {TO_EMAIL}")
    print(f"  INACTIVE_DAYS         : {INACTIVE_DAYS}")
    print(f"  REPORT schedule       : {REPORT_DAY_OF_WEEK} {REPORT_HOUR:02d}:{REPORT_MINUTE:02d}")
    print(f"  DB_PATH               : {DB_PATH}")
    print(f"  CREDENTIALS_PATH      : {CREDENTIALS_PATH} ({'exists' if CREDENTIALS_PATH.exists() else 'missing'})")
    print(f"  TOKEN_PATH            : {TOKEN_PATH} ({'exists' if TOKEN_PATH.exists() else 'missing'})")
    print("-" * 50)
    print("Tip: Run main.py for the full agent.")
