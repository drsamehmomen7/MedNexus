"""MRJ-owned, version-pinned membership contract for reviewed collections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_ID = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True, slots=True)
class ReviewedCollectionMember:
    reviewed_record_id: str
    reviewed_record_version: int
    document_id: str
    exam_context: dict[str, Any]
    profile_id: str | None
    profile_version: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReviewedCollectionMember":
        if (not isinstance(value, dict) or set(value) != {
                "reviewed_record_id", "reviewed_record_version", "document_id",
                "exam_context", "profile_id", "profile_version"}):
            raise ValueError("Collection membership is malformed.")
        if (not isinstance(value["reviewed_record_id"], str)
                or not _ID.fullmatch(value["reviewed_record_id"])
                or not isinstance(value["reviewed_record_version"], int)
                or isinstance(value["reviewed_record_version"], bool)
                or value["reviewed_record_version"] < 1
                or not isinstance(value["document_id"], str) or not value["document_id"]
                or not isinstance(value["exam_context"], dict)
                or any(value[key] is not None and not isinstance(value[key], str)
                       for key in ("profile_id", "profile_version"))):
            raise ValueError("Collection membership identity is invalid.")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.__dataclass_fields__}
