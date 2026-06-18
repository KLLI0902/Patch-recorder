"""Firmware Validation Agent — application entry point."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

import config
import db
from scheduler import start_scheduler


def setup_logging() -> None:
    """Configure console and rotating file logging."""
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def main() -> None:
    """Initialize database, start scheduler, and run the agent."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        db.init_db()
        logger.info("Database initialized at %s", config.DB_PATH)

        # 👇 新增：启动标记
        logger.info("Firmware Agent STARTING...")

    except Exception as exc:
        logger.exception("Failed to initialize database: %s", exc)
        sys.exit(1)

    print("Firmware Agent Started")
    print(f"  Gmail account : {config.EMAIL_USER}")
    print(f"  Check interval: every {config.CHECK_INTERVAL_MINUTES} minutes")
    print(f"  Weekly report : {config.REPORT_DAY_OF_WEEK} {config.REPORT_HOUR:02d}:{config.REPORT_MINUTE:02d}")
    print("  First Gmail check will run now (OAuth login may open in browser).")
    print("  Press Ctrl+C to stop.")

    # 👇 核心：捕获 scheduler 崩溃
    try:
        start_scheduler()

    except KeyboardInterrupt:
        logger.warning("Agent stopped by user (Ctrl+C)")

    except Exception:
        logger.exception("FATAL: Scheduler crashed")

    finally:
        logger.warning("Firmware Agent STOPPED")


if __name__ == "__main__":
    main()
