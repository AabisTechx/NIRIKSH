"""
SQLite Database Layer for NIRIKSH Prototype
Team CODE RED — Smart India Hackathon 2026
Provides zero-configuration SQLite persistence with full JSON serialization for structured workflow entities.
Supports NIRIKSH_DB_PATH environment variable for isolated automated testing.
"""

import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR_DB = os.path.join(BASE_DIR, "niriksh_demo.db")
_DB_LOCK = threading.RLock()
_CACHED_DEFAULT_PATH: Optional[str] = None


def _is_valid_sqlite_file(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    try:
        conn = sqlite3.connect(path)
        res = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return bool(res and res[0] == "ok")
    except sqlite3.Error:
        return False


def _resolve_db_path() -> str:
    global _CACHED_DEFAULT_PATH
    env_override = os.environ.get("NIRIKSH_DB_PATH")
    if env_override:
        return env_override
    if _CACHED_DEFAULT_PATH:
        return _CACHED_DEFAULT_PATH

    # If running inside a 9p/virtiofs mount (/working_dir), use /tmp for safe POSIX locking
    if BASE_DIR.startswith("/working_dir"):
        tmp_db = "/tmp/niriksh_demo.db"
        if not _is_valid_sqlite_file(tmp_db):
            if os.path.exists(tmp_db):
                try:
                    os.remove(tmp_db)
                except OSError:
                    pass
            if _is_valid_sqlite_file(LOCAL_DIR_DB):
                try:
                    shutil.copyfile(LOCAL_DIR_DB, tmp_db)
                except OSError:
                    pass
        _CACHED_DEFAULT_PATH = tmp_db
        return tmp_db

    try:
        conn = sqlite3.connect(LOCAL_DIR_DB)
        conn.execute("CREATE TABLE IF NOT EXISTS _lock_probe (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        _CACHED_DEFAULT_PATH = LOCAL_DIR_DB
        return LOCAL_DIR_DB
    except sqlite3.Error:
        tmp_db = "/tmp/niriksh_demo.db"
        if _is_valid_sqlite_file(LOCAL_DIR_DB) and not _is_valid_sqlite_file(tmp_db):
            try:
                shutil.copyfile(LOCAL_DIR_DB, tmp_db)
            except OSError:
                pass
        _CACHED_DEFAULT_PATH = tmp_db
        return tmp_db


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a thread-safe SQLite connection with row factory enabled."""
    with _DB_LOCK:
        active_path = _resolve_db_path()
        conn = sqlite3.connect(active_path, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if active_path != LOCAL_DIR_DB and not os.environ.get("NIRIKSH_DB_PATH"):
            try:
                shutil.copyfile(active_path, LOCAL_DIR_DB)
            except OSError:
                pass


def _table_has_column(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [r["name"] for r in cursor.fetchall()]
    return column_name in cols


def init_db_schema(force_recreate: bool = False) -> None:
    """Create tables if they do not exist, without dropping existing valid user data unless force_recreate is True."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if force_recreate:
            cursor.execute("DROP TABLE IF EXISTS cases")
            cursor.execute("DROP TABLE IF EXISTS audit_logs")
            cursor.execute("DROP TABLE IF EXISTS alerts")
        else:
            # Only drop if an obsolete legacy schema lacking application_id exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cases'")
            if cursor.fetchone() and not _table_has_column(cursor, "cases", "application_id"):
                cursor.execute("DROP TABLE IF EXISTS cases")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
            if cursor.fetchone() and not _table_has_column(cursor, "audit_logs", "application_id"):
                cursor.execute("DROP TABLE IF EXISTS audit_logs")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
            if cursor.fetchone() and not _table_has_column(cursor, "alerts", "application_id"):
                cursor.execute("DROP TABLE IF EXISTS alerts")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                application_id TEXT PRIMARY KEY,
                institution_name TEXT NOT NULL,
                state TEXT NOT NULL,
                city TEXT NOT NULL,
                application_type TEXT NOT NULL,
                programme TEXT NOT NULL,
                proposed_intake INTEGER NOT NULL,
                submission_date TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                compliance_status TEXT NOT NULL,
                assigned_officer TEXT NOT NULL,
                assigned_role TEXT NOT NULL,
                sla_deadline TEXT NOT NULL,
                evc_required INTEGER NOT NULL DEFAULT 1,
                evc_due INTEGER NOT NULL DEFAULT 1,
                extracted_fields_json TEXT NOT NULL,
                documents_json TEXT NOT NULL,
                compliance_results_json TEXT NOT NULL,
                evc_inspection_json TEXT NOT NULL,
                decisions_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action_type TEXT NOT NULL,
                previous_value TEXT,
                new_value TEXT,
                remarks TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                institution_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                due_date TEXT NOT NULL,
                escalation_status TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
