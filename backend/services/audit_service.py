"""
Audit Trail Logging Service for NIRIKSH Prototype
Team CODE RED — Smart India Hackathon 2026
Tagline: Every case traceable. Every deadline visible. Every decision accountable.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def record_audit_event(
    conn: sqlite3.Connection,
    application_id: str,
    actor_name: str,
    actor_role: str,
    action_type: str,
    previous_value: str,
    new_value: str,
    remarks: str,
) -> Dict[str, Any]:
    """Inserts a chronological, immutable audit trail record into the SQLite audit_logs table."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    audit_id = f"AUD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_logs (
            id, application_id, timestamp, actor_name, actor_role,
            action_type, previous_value, new_value, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            application_id,
            now_str,
            actor_name,
            actor_role,
            action_type,
            previous_value or "",
            new_value or "",
            remarks,
        ),
    )

    return {
        "id": audit_id,
        "application_id": application_id,
        "timestamp": now_str,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "action_type": action_type,
        "previous_value": previous_value or "",
        "new_value": new_value or "",
        "remarks": remarks,
    }


def list_audit_logs(conn: sqlite3.Connection, application_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns audit log entries ordered newest-first, optionally filtered by application_id."""
    cursor = conn.cursor()
    if application_id:
        cursor.execute(
            "SELECT * FROM audit_logs WHERE application_id = ? ORDER BY timestamp DESC, rowid DESC",
            (application_id,),
        )
    else:
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC, rowid DESC")

    rows = cursor.fetchall()
    return [dict(r) for r in rows]
