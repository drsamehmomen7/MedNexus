"""MRJ reviewed-record persistence boundary and local SQLite implementation."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Protocol

from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord,
)


class ReviewedClinicalRecordRepository(Protocol):
    def save(self, record: ReviewedClinicalRecord) -> ReviewedClinicalRecord: ...
    def get(self, record_id: str, version: int) -> ReviewedClinicalRecord | None: ...
    def get_current(self, record_id: str) -> ReviewedClinicalRecord | None: ...
    def list(self, limit: int = 100, offset: int = 0) -> list[ReviewedClinicalRecord]: ...
    def list_versions(self, record_id: str) -> list[dict[str, object]]: ...
    def close(self) -> None: ...


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


def default_reviewed_record_path() -> Path:
    configured = os.environ.get("MRJ_REVIEWED_RECORD_DB")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "MRJ" / "reviewed_records.sqlite3"


class SqliteReviewedClinicalRecordRepository:
    """Append-only versions with a transactionally updated current pointer."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_reviewed_record_path()
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()

    def _db(self) -> sqlite3.Connection:
        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 30000")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
            version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
            if version > 1:
                connection.close()
                raise RuntimeError("Reviewed record database schema is newer than this application.")
            if version == 0:
                with connection:
                    connection.execute("""CREATE TABLE reviewed_record_versions (
                        record_id TEXT NOT NULL, version INTEGER NOT NULL CHECK (version > 0),
                        journey_run_id TEXT NOT NULL, document_id TEXT NOT NULL,
                        reviewed_at TEXT NOT NULL, envelope_json TEXT NOT NULL,
                        envelope_sha256 TEXT NOT NULL,
                        PRIMARY KEY (record_id, version))""")
                    connection.execute("""CREATE TABLE reviewed_record_heads (
                        record_id TEXT PRIMARY KEY, journey_run_id TEXT NOT NULL,
                        document_id TEXT NOT NULL, current_version INTEGER NOT NULL,
                        reviewed_at TEXT NOT NULL,
                        UNIQUE (journey_run_id, document_id),
                        FOREIGN KEY (record_id, current_version)
                            REFERENCES reviewed_record_versions(record_id, version))""")
                    connection.execute("CREATE INDEX reviewed_records_reviewed_at ON reviewed_record_heads(reviewed_at DESC, record_id)")
                    connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
            self._connection = connection
        return self._connection

    @_locked
    def save(self, record: ReviewedClinicalRecord) -> ReviewedClinicalRecord:
        value = record.to_dict()
        payload = record.to_json()
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT envelope_sha256 FROM reviewed_record_versions WHERE record_id=? AND version=?",
                             (value["reviewed_record_id"], value["record_version"])).fetchone()
            if row is not None:
                if row[0] != digest:
                    raise ValueError("A different reviewed record version already exists.")
                db.commit()
                return record
            head = db.execute("SELECT current_version FROM reviewed_record_heads WHERE record_id=?",
                              (value["reviewed_record_id"],)).fetchone()
            if value["record_version"] != (head[0] + 1 if head else 1):
                raise ValueError("Reviewed record versions must be appended in order.")
            db.execute("""INSERT INTO reviewed_record_versions
                (record_id,version,journey_run_id,document_id,reviewed_at,envelope_json,envelope_sha256)
                VALUES (?,?,?,?,?,?,?)""",
                (value["reviewed_record_id"], value["record_version"], value["journey_run_id"],
                 value["document_id"], value["reviewed_at"], payload, digest))
            db.execute("""INSERT INTO reviewed_record_heads
                (record_id,journey_run_id,document_id,current_version,reviewed_at)
                VALUES (?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET
                current_version=excluded.current_version, reviewed_at=excluded.reviewed_at""",
                (value["reviewed_record_id"], value["journey_run_id"], value["document_id"],
                 value["record_version"], value["reviewed_at"]))
            db.commit()
        except Exception:
            db.rollback()
            raise
        return record

    @_locked
    def get(self, record_id: str, version: int) -> ReviewedClinicalRecord | None:
        row = self._db().execute("SELECT envelope_json,envelope_sha256 FROM reviewed_record_versions WHERE record_id=? AND version=?",
                                 (record_id, version)).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row[0].encode("utf-8")).hexdigest() != row[1]:
            raise ValueError("Reviewed record integrity check failed.")
        return ReviewedClinicalRecord.from_json(row[0])

    @_locked
    def get_current(self, record_id: str) -> ReviewedClinicalRecord | None:
        row = self._db().execute("SELECT current_version FROM reviewed_record_heads WHERE record_id=?",
                                 (record_id,)).fetchone()
        return self.get(record_id, row[0]) if row else None

    @_locked
    def list(self, limit: int = 100, offset: int = 0) -> list[ReviewedClinicalRecord]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid reviewed record page.")
        rows = self._db().execute("SELECT record_id,current_version FROM reviewed_record_heads "
                                  "ORDER BY reviewed_at DESC,record_id LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [record for record_id, version in rows if (record := self.get(record_id, version)) is not None]

    @_locked
    def list_versions(self, record_id: str) -> list[dict[str, object]]:
        rows = self._db().execute("SELECT version,reviewed_at,envelope_sha256 FROM reviewed_record_versions "
                                  "WHERE record_id=? ORDER BY version", (record_id,)).fetchall()
        return [{"record_version": version, "reviewed_at": reviewed_at, "envelope_sha256": digest}
                for version, reviewed_at, digest in rows]

    @_locked
    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
