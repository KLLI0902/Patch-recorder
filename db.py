"""SQLite database layer for device and event tracking."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import config


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with row factory enabled."""
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create all required tables if they do not exist."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY,
                device TEXT UNIQUE,
                type TEXT,
                version TEXT,
                patch TEXT,
                md5 TEXT,
                status TEXT,
                last_update DATETIME
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                device TEXT,
                version TEXT,
                raw_text TEXT,
                event_time DATETIME
            );

            CREATE TABLE IF NOT EXISTS processed_emails (
                id INTEGER PRIMARY KEY,
                gmail_message_id TEXT UNIQUE,
                processed_time DATETIME
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def is_email_processed(gmail_message_id: str, db_path: Path | None = None) -> bool:
    """Return True if the Gmail message has already been processed."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM processed_emails WHERE gmail_message_id = ?",
            (gmail_message_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_email_processed(gmail_message_id: str, db_path: Path | None = None) -> None:
    """Record a Gmail message as processed."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO processed_emails (gmail_message_id, processed_time) VALUES (?, ?)",
            (gmail_message_id, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_device(
    device: str,
    device_type: str,
    version: str,
    patch: str,
    md5: str,
    status: str,
    db_path: Path | None = None,
) -> bool:
    """
    Insert or update a device record.

    Returns True if the device was updated, False if newly inserted.
    """
    now = datetime.now().isoformat()
    conn = get_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM devices WHERE device = ?",
            (device,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE devices
                SET type = ?, version = ?, patch = ?, md5 = ?, status = ?, last_update = ?
                WHERE device = ?
                """,
                (device_type, version, patch, md5, status, now, device),
            )
            conn.commit()
            return True

        conn.execute(
            """
            INSERT INTO devices (device, type, version, patch, md5, status, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (device, device_type, version, patch, md5, status, now),
        )
        conn.commit()
        return False
    finally:
        conn.close()


def insert_event(
    device: str,
    version: str,
    raw_text: str,
    db_path: Path | None = None,
) -> None:
    """Insert a new firmware validation event."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO events (device, version, raw_text, event_time)
            VALUES (?, ?, ?, ?)
            """,
            (device, version, raw_text, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def mark_stale_devices_inactive(
    inactive_days: int | None = None,
    db_path: Path | None = None,
) -> int:
    """
    Set status to inactive for devices not updated within inactive_days.

    Returns the number of devices marked inactive.
    """
    days = inactive_days if inactive_days is not None else config.INACTIVE_DAYS
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            UPDATE devices
            SET status = 'wait_for_updated'
            WHERE status = 'updated'
              AND last_update < ?
            """,
            (cutoff,),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_active_devices(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return all active devices ordered by type and device name."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT device, type, version, patch, md5, status, last_update
            FROM devices
            WHERE status = 'active'
            ORDER BY type, device
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_devices(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return all devices ordered by status, type, and device name."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT device, type, version, patch, md5, status, last_update
            FROM devices
            ORDER BY status, type, device
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_db_stats(db_path: Path | None = None) -> dict[str, int]:
    """Return row counts for each table."""
    conn = get_connection(db_path)
    try:
        return {
            "devices": conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0],
            "active_devices": conn.execute(
                "SELECT COUNT(*) FROM devices WHERE status = 'active'"
            ).fetchone()[0],
            "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "processed_emails": conn.execute(
                "SELECT COUNT(*) FROM processed_emails"
            ).fetchone()[0],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    """Show database summary (for debugging)."""
    print("Database Tool")
    print(f"  DB path: {config.DB_PATH}")
    print("-" * 50)

    init_db()
    stats = get_db_stats()
    print(f"Devices         : {stats['devices']} (active: {stats['active_devices']})")
    print(f"Events          : {stats['events']}")
    print(f"Processed emails: {stats['processed_emails']}")
    print("-" * 50)

    devices = get_all_devices()
    if not devices:
        print("No devices in database.")
    else:
        print(f"{'Device':<25} {'Type':<8} {'Status':<10} {'Version'}")
        print("-" * 50)
        for dev in devices:
            print(
                f"{dev['device']:<25} {dev['type']:<8} {dev['status']:<10} "
                f"{dev['version']}"
            )

    print("-" * 50)
    print("Tip: Run main.py for the full agent.")
