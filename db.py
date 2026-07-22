"""
SQLite-backed governance layer. Replaces the flat audit_log.jsonl file with
a real relational database -- structured columns for querying (applicant_id,
timestamp, score, tier, PD, fairness group) plus JSON columns for the
nested objects (extracted document data, full risk assessment, routing
decision), so you get both queryability and full record fidelity.

Default location: risk_engine.db in the working directory. Override with
the RISK_ENGINE_DB_PATH environment variable.

Note on Streamlit Community Cloud: the filesystem there is ephemeral --
the SQLite file resets whenever the app redeploys or the container
restarts. Fine for a demo/prototype; for a persistent production database,
swap this module for a hosted Postgres connection (e.g. Supabase, Neon) by
changing only the connection string below -- schemas.py and workflow.py
don't need to change.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

from schemas import AuditRecord, ExtractedDocumentData, RiskAssessment, RoutingDecision

DB_PATH = os.environ.get("RISK_ENGINE_DB_PATH", "risk_engine.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    computed_pd REAL NOT NULL,
    pd_decile INTEGER NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_tier TEXT NOT NULL,
    requires_human_review INTEGER NOT NULL,
    applicant_group TEXT,
    human_override TEXT,
    extracted_data_json TEXT NOT NULL,
    risk_assessment_json TEXT NOT NULL,
    routing_decision_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_applicant_id ON audit_records(applicant_id);
CREATE INDEX IF NOT EXISTS idx_applicant_group ON audit_records(applicant_group);
"""


@contextmanager
def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _get_connection() as conn:
        conn.executescript(_SCHEMA)


def insert_audit_record(record: AuditRecord) -> None:
    init_db()
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_records (
                applicant_id, timestamp, computed_pd, pd_decile, risk_score,
                risk_tier, requires_human_review, applicant_group, human_override,
                extracted_data_json, risk_assessment_json, routing_decision_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.applicant_id,
                record.timestamp,
                record.computed_pd,
                record.pd_decile,
                record.risk_assessment.risk_score,
                record.routing_decision.risk_tier,
                int(record.routing_decision.requires_human_review),
                record.applicant_group,
                record.human_override,
                record.extracted_data.model_dump_json(),
                record.risk_assessment.model_dump_json(),
                record.routing_decision.model_dump_json(),
            ),
        )


def _row_to_audit_record(row: sqlite3.Row) -> AuditRecord:
    return AuditRecord(
        applicant_id=row["applicant_id"],
        timestamp=row["timestamp"],
        computed_pd=row["computed_pd"],
        pd_decile=row["pd_decile"],
        extracted_data=ExtractedDocumentData(**json.loads(row["extracted_data_json"])),
        risk_assessment=RiskAssessment(**json.loads(row["risk_assessment_json"])),
        routing_decision=RoutingDecision(**json.loads(row["routing_decision_json"])),
        applicant_group=row["applicant_group"],
        human_override=row["human_override"],
    )


def fetch_all_audit_records() -> List[AuditRecord]:
    init_db()
    with _get_connection() as conn:
        rows = conn.execute("SELECT * FROM audit_records ORDER BY id ASC").fetchall()
    return [_row_to_audit_record(r) for r in rows]


def fetch_by_applicant_id(applicant_id: str) -> Optional[AuditRecord]:
    init_db()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM audit_records WHERE applicant_id = ? ORDER BY id DESC LIMIT 1",
            (applicant_id,),
        ).fetchone()
    return _row_to_audit_record(row) if row else None


def record_human_override(applicant_id: str, override_note: str) -> None:
    """Lets an underwriter log a human override decision against an existing record."""
    init_db()
    with _get_connection() as conn:
        conn.execute(
            "UPDATE audit_records SET human_override = ? WHERE applicant_id = ?",
            (override_note, applicant_id),
        )
