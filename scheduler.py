"""APScheduler job definitions for Gmail monitoring and weekly reports."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
from gmail_agent import process_inbox
from report_agent import send_weekly_report

logger = logging.getLogger(__name__)


def create_scheduler() -> BlockingScheduler:
    """
    Create and configure the APScheduler instance with all jobs.

    Job 1: Check Gmail every CHECK_INTERVAL_MINUTES.
    Job 2: Send weekly report every Monday at 10:00.
    """
    scheduler = BlockingScheduler()

    scheduler.add_job(
        process_inbox,
        trigger=IntervalTrigger(minutes=config.CHECK_INTERVAL_MINUTES),
        id="gmail_check",
        name="Gmail Inbox Check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        send_weekly_report,
        trigger=CronTrigger(
            day_of_week=config.REPORT_DAY_OF_WEEK,
            hour=config.REPORT_HOUR,
            minute=config.REPORT_MINUTE,
        ),
        id="weekly_report",
        name="Weekly Firmware Report",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        "Scheduler configured: Gmail every %d min, report %s %02d:%02d",
        config.CHECK_INTERVAL_MINUTES,
        config.REPORT_DAY_OF_WEEK,
        config.REPORT_HOUR,
        config.REPORT_MINUTE,
    )

    return scheduler


def start_scheduler() -> None:
    """Start the blocking scheduler (runs until interrupted)."""
    scheduler = create_scheduler()

    # Run an initial Gmail check on startup
    try:
        process_inbox()
    except Exception as exc:
        logger.exception("Initial Gmail check failed: %s", exc)

    logger.info("Scheduler starting")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    print("Starting scheduler (use Ctrl+C to stop)...")
    print("Tip: For full startup, run: python main.py")
    start_scheduler()
