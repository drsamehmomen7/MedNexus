"""Durable reviewed-only collection snapshots and immutable AnalysisRuns."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import ReviewedClinicalRecord
from backend.app.modules.medical_document_intelligence.contracts.reviewed_collection import ReviewedCollectionMember
from backend.app.modules.medical_document_intelligence.services.reviewed_record_repository import (
    ReviewedClinicalRecordRepository, SqliteReviewedClinicalRecordRepository, default_reviewed_record_path,
)


class ReviewedCollectionRepository(Protocol):
    def create_collection(self, name: str, refs: list[tuple[str, int]], *,
                          membership_source: str, creation_method: str) -> dict[str, Any]: ...
    def get_collection(self, collection_id: str) -> dict[str, Any]: ...
    def list_collections(self) -> list[dict[str, Any]]: ...
    def get_version(self, collection_id: str, version: int | None = None) -> dict[str, Any]: ...
    def get_members(self, collection_id: str, version: int | None = None) -> list[ReviewedClinicalRecord]: ...
    def add_member(self, collection_id: str, record_id: str, version: int) -> dict[str, Any]: ...
    def remove_member(self, collection_id: str, record_id: str) -> dict[str, Any]: ...
    def create_version(self, collection_id: str, refs: list[tuple[str, int]]) -> dict[str, Any]: ...
    def archive_collection(self, collection_id: str) -> dict[str, Any]: ...
    def save_analysis(self, payload: dict[str, Any]) -> None: ...
    def get_analysis(self, analysis_id: str) -> dict[str, Any]: ...


def default_reviewed_collection_path() -> Path:
    configured = os.environ.get("MRJ_REVIEWED_COLLECTION_DB")
    return Path(configured).expanduser() if configured else default_reviewed_record_path().with_name("reviewed_collections.sqlite3")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class SqliteReviewedCollectionRepository:
    """Membership changes append snapshots; exact reviewed record versions are rechecked on read."""

    def __init__(self, records: ReviewedClinicalRecordRepository | None = None,
                 path: str | Path | None = None) -> None:
        self.records = records or SqliteReviewedClinicalRecordRepository()
        self.path = Path(path) if path is not None else default_reviewed_collection_path()
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()

    def _db(self) -> sqlite3.Connection:
        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                db.execute("""CREATE TABLE IF NOT EXISTS reviewed_collection_heads (
                    collection_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL,
                    name TEXT NOT NULL, state TEXT NOT NULL, current_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    membership_source TEXT NOT NULL, creation_method TEXT NOT NULL)""")
                db.execute("""CREATE TABLE IF NOT EXISTS reviewed_collection_versions (
                    collection_id TEXT NOT NULL, version INTEGER NOT NULL,
                    created_at TEXT NOT NULL, members_json TEXT NOT NULL,
                    members_sha256 TEXT NOT NULL, PRIMARY KEY(collection_id,version),
                    FOREIGN KEY(collection_id) REFERENCES reviewed_collection_heads(collection_id))""")
                db.execute("""CREATE TABLE IF NOT EXISTS reviewed_collection_analyses (
                    analysis_id TEXT PRIMARY KEY, collection_id TEXT NOT NULL,
                    collection_version INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY(collection_id,collection_version)
                        REFERENCES reviewed_collection_versions(collection_id,version))""")
                db.execute("""CREATE TABLE IF NOT EXISTS reviewed_collection_insights (
                    insight_run_id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL,
                    collection_id TEXT NOT NULL, collection_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY(analysis_id) REFERENCES reviewed_collection_analyses(analysis_id),
                    FOREIGN KEY(collection_id,collection_version)
                        REFERENCES reviewed_collection_versions(collection_id,version))""")
            self._connection = db
        return self._connection

    @staticmethod
    def _id(value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
            raise LookupError("Collection was not found.")
        return value

    def _member(self, record_id: str, version: int) -> ReviewedCollectionMember:
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError("An exact reviewed record version is required.")
        record = self.records.get(record_id, version)
        if record is None:
            raise ValueError("A reviewed record version is unavailable.")
        data = ReviewedClinicalRecord.from_json(record.to_json()).to_dict()
        if (data["review_decision"] != "ACCEPTED" or data["durably_reviewed"] is not True
                or data["major_review_required"] and not data["major_review_acknowledged"]):
            raise ValueError("Only durably accepted reviewed records may enter a collection.")
        profile = data.get("profile_provenance") or {}
        return ReviewedCollectionMember(record_id, version, data["document_id"],
                                        data["exam_context"], profile.get("profile_id"),
                                        profile.get("profile_version"))

    def _members(self, refs: list[tuple[str, int]]) -> list[dict[str, Any]]:
        if not isinstance(refs, list) or len(refs) > 500:
            raise ValueError("Choose up to 500 reviewed records.")
        if len({ref[0] for ref in refs}) != len(refs):
            raise ValueError("A reviewed record can occur only once per collection version.")
        return [self._member(record_id, version).to_dict() for record_id, version in sorted(refs)]

    def _head(self, collection_id: str) -> dict[str, Any]:
        row = self._db().execute("SELECT * FROM reviewed_collection_heads WHERE collection_id=?",
                                 (self._id(collection_id),)).fetchone()
        if row is None:
            raise LookupError("Collection was not found.")
        return dict(row)

    def _version(self, collection_id: str, version: int) -> dict[str, Any]:
        row = self._db().execute("SELECT * FROM reviewed_collection_versions WHERE collection_id=? AND version=?",
                                 (self._id(collection_id), version)).fetchone()
        if row is None:
            raise LookupError("Collection version was not found.")
        if hashlib.sha256(row["members_json"].encode()).hexdigest() != row["members_sha256"]:
            raise ValueError("Collection version integrity failed.")
        members = [ReviewedCollectionMember.from_dict(item) for item in json.loads(row["members_json"])]
        for member in members:
            if self._member(member.reviewed_record_id, member.reviewed_record_version) != member:
                raise ValueError("Pinned reviewed record changed or is unavailable.")
        return {"collection_id": collection_id, "collection_version": version,
                "created_at": row["created_at"], "members": [item.to_dict() for item in members]}

    def create_collection(self, name: str, refs: list[tuple[str, int]], *,
                          membership_source: str = "REVIEWED_RECORD_REPOSITORY",
                          creation_method: str = "EXPLICIT_SELECTION") -> dict[str, Any]:
        if not isinstance(name, str) or not re.fullmatch(r"[\w .,:/()\-]{1,120}", name.strip()):
            raise ValueError("Collection name must be a short safe label.")
        if creation_method not in {"EXPLICIT_SELECTION", "REVIEW_SESSION"}:
            raise ValueError("Unsupported collection creation method.")
        members = self._members(refs)
        identifier, now = uuid4().hex, _now()
        payload = _canonical(members)
        with self._lock, self._db():
            db = self._db()
            db.execute("INSERT INTO reviewed_collection_heads VALUES (?,?,?,?,?,?,?,?,?)",
                       (identifier, 1, name.strip(), "READY_FOR_ANALYSIS" if members else "DRAFT", 1, now, now,
                        membership_source, creation_method))
            db.execute("INSERT INTO reviewed_collection_versions VALUES (?,?,?,?,?)",
                       (identifier, 1, now, payload, hashlib.sha256(payload.encode()).hexdigest()))
        return self.get_collection(identifier)

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        with self._lock:
            head = self._head(collection_id)
            version = self._version(collection_id, head["current_version"])
        return {**head, "version": head["current_version"], "member_count": len(version["members"]),
                "profiles": sorted({m["profile_id"] for m in version["members"] if m["profile_id"]}),
                "exam_types": [{"modality": modality, "body_region": region} for modality, region in sorted({
                    (m["exam_context"].get("normalized_modality") or "UNKNOWN",
                     m["exam_context"].get("normalized_body_region") or "UNKNOWN")
                    for m in version["members"]})]}

    def list_collections(self) -> list[dict[str, Any]]:
        with self._lock:
            ids = [row[0] for row in self._db().execute(
                "SELECT collection_id FROM reviewed_collection_heads ORDER BY updated_at DESC,collection_id")]
            result = []
            for identifier in ids:
                try:
                    result.append(self.get_collection(identifier))
                except (ValueError, LookupError):
                    head = self._head(identifier)
                    result.append({**head, "version": head["current_version"],
                                   "member_count": None, "profiles": [], "exam_types": [], "integrity": "FAILED"})
            return result

    def get_version(self, collection_id: str, version: int | None = None) -> dict[str, Any]:
        with self._lock:
            head = self._head(collection_id)
            return self._version(collection_id, head["current_version"] if version is None else version)

    def get_members(self, collection_id: str, version: int | None = None) -> list[ReviewedClinicalRecord]:
        snapshot = self.get_version(collection_id, version)
        return [self.records.get(item["reviewed_record_id"], item["reviewed_record_version"])
                for item in snapshot["members"]]

    def create_version(self, collection_id: str, refs: list[tuple[str, int]]) -> dict[str, Any]:
        members = self._members(refs)
        payload, now = _canonical(members), _now()
        with self._lock, self._db():
            head = self._head(collection_id)
            if head["state"] == "ARCHIVED":
                raise ValueError("Archived collections cannot be edited.")
            next_version = head["current_version"] + 1
            self._db().execute("INSERT INTO reviewed_collection_versions VALUES (?,?,?,?,?)",
                               (collection_id, next_version, now, payload,
                                hashlib.sha256(payload.encode()).hexdigest()))
            self._db().execute("UPDATE reviewed_collection_heads SET current_version=?,state=?,updated_at=? WHERE collection_id=?",
                               (next_version, "READY_FOR_ANALYSIS" if members else "DRAFT", now, collection_id))
        return self.get_collection(collection_id)

    def archive_collection(self, collection_id: str) -> dict[str, Any]:
        with self._lock, self._db():
            self._head(collection_id)
            self._db().execute("UPDATE reviewed_collection_heads SET state='ARCHIVED',updated_at=? WHERE collection_id=?",
                               (_now(), collection_id))
        return self.get_collection(collection_id)

    def add_member(self, collection_id: str, record_id: str, version: int) -> dict[str, Any]:
        current = self.get_version(collection_id)["members"]
        return self.create_version(collection_id, [
            *((item["reviewed_record_id"], item["reviewed_record_version"]) for item in current),
            (record_id, version)])

    def remove_member(self, collection_id: str, record_id: str) -> dict[str, Any]:
        current = self.get_version(collection_id)["members"]
        refs = [(item["reviewed_record_id"], item["reviewed_record_version"])
                for item in current if item["reviewed_record_id"] != record_id]
        if len(refs) == len(current):
            raise LookupError("Collection member was not found.")
        return self.create_version(collection_id, refs)

    def save_analysis(self, payload: dict[str, Any]) -> None:
        value = _canonical(payload)
        digest = hashlib.sha256(value.encode()).hexdigest()
        with self._lock, self._db():
            row = self._db().execute("SELECT payload_sha256 FROM reviewed_collection_analyses WHERE analysis_id=?",
                                     (payload["analysis_run_id"],)).fetchone()
            if row is not None:
                if row[0] != digest:
                    raise ValueError("Historical analysis is immutable.")
                return
            self._db().execute("INSERT INTO reviewed_collection_analyses VALUES (?,?,?,?,?)",
                               (payload["analysis_run_id"], payload["collection_id"],
                                payload["collection_version"], value, digest))

    def get_analysis(self, analysis_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._db().execute("SELECT collection_id,collection_version,payload_json,payload_sha256 FROM reviewed_collection_analyses WHERE analysis_id=?",
                                     (self._id(analysis_id),)).fetchone()
        if row is None:
            raise LookupError("Analysis was not found.")
        if hashlib.sha256(row["payload_json"].encode()).hexdigest() != row["payload_sha256"]:
            raise ValueError("Analysis integrity failed.")
        self.get_version(row["collection_id"], row["collection_version"])
        return json.loads(row["payload_json"])

    def save_insights(self, payload: dict[str, Any]) -> None:
        value = _canonical(payload)
        digest = hashlib.sha256(value.encode()).hexdigest()
        with self._lock, self._db():
            row = self._db().execute(
                "SELECT payload_sha256 FROM reviewed_collection_insights WHERE insight_run_id=?",
                (payload["insight_run_id"],)).fetchone()
            if row is not None:
                if row[0] != digest:
                    raise ValueError("Historical Insight run is immutable.")
                return
            self._db().execute("INSERT INTO reviewed_collection_insights VALUES (?,?,?,?,?,?)",
                               (payload["insight_run_id"], payload["analysis_run_id"],
                                payload["collection_id"], payload["collection_version"], value, digest))

    def get_insights(self, insight_run_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._db().execute(
                "SELECT analysis_id,collection_id,collection_version,payload_json,payload_sha256 "
                "FROM reviewed_collection_insights WHERE insight_run_id=?",
                (self._id(insight_run_id),)).fetchone()
        if row is None:
            raise LookupError("Insight run was not found.")
        if hashlib.sha256(row["payload_json"].encode()).hexdigest() != row["payload_sha256"]:
            raise ValueError("Insight run integrity failed.")
        analysis = self.get_analysis(row["analysis_id"])
        if (analysis["collection_id"] != row["collection_id"]
                or analysis["collection_version"] != row["collection_version"]):
            raise ValueError("Insight run AnalysisRun binding failed.")
        return json.loads(row["payload_json"])

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
