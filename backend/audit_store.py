"""SQLite persistence for audit history and trend charts."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "audits.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                scenario_id TEXT,
                truth_score INTEGER,
                verdict TEXT,
                deception_pct INTEGER,
                final_state_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_audit(
    supplier_id: str,
    supplier_name: str,
    scenario_id: str,
    final_state: Dict[str, Any],
) -> int:
    init_db()
    payload = json.dumps(final_state, default=str)
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO audits (
                created_at, supplier_id, supplier_name, scenario_id,
                truth_score, verdict, deception_pct, final_state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                supplier_id,
                supplier_name,
                scenario_id,
                final_state.get("corporate_truth_score"),
                final_state.get("status_verdict"),
                final_state.get("deception_confidence_pct"),
                payload,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_audits(limit: int = 50, supplier_id: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    query = "SELECT * FROM audits"
    params: tuple = ()
    if supplier_id:
        query += " WHERE supplier_id = ?"
        params = (supplier_id,)
    query += " ORDER BY id DESC LIMIT ?"
    params = params + (limit,)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_audit(audit_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    out["final_state"] = json.loads(out.pop("final_state_json"))
    return out


def supplier_score_history(supplier_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = list_audits(limit=limit, supplier_id=supplier_id)
    return [
        {
            "created_at": r["created_at"],
            "truth_score": r["truth_score"],
            "verdict": r["verdict"],
            "scenario_id": r["scenario_id"],
        }
        for r in reversed(rows)
    ]
