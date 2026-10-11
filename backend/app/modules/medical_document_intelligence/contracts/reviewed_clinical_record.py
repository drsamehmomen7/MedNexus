"""MRJ-owned, exportable and versioned accepted clinical record contract.

Only protected source text and curated outputs may enter this envelope. The
original upload and original Journey document are never inputs to this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5


SCHEMA_VERSION = 1
_NAMESPACE = UUID("a5aab50d-2fbd-45fc-86bf-a6c5a35ee498")
_RECORD_KEYS = {"schema_version", "record_version", "reviewed_record_id", "journey_run_id",
                "document_id", "reviewed_at", "review_decision", "durably_reviewed",
                "major_review_required", "major_review_acknowledged", "review_issues",
                "protected_source", "exam_context", "clinical_summary", "canonical_facts",
                "standardized_facts", "unassigned_measurements", "provenance"}
_SOURCE_KEYS = {"representation", "text", "sha256", "artifact_id", "output_version",
                "selected_policy_id", "selected_policy_version", "protected_pdf_sha256"}
_FACT_KEYS = {"fact_id", "fact_type", "canonical_concept", "display_label", "assertion_state",
              "salience", "group", "anatomy", "laterality", "review_required", "hypothesis_status",
              "review_reason", "evidence_anchors", "observations", "relationships",
              "temporal_status", "temporal_change"}


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def logical_record_id(run_id: str, document_id: str) -> str:
    return uuid5(_NAMESPACE, f"{run_id}:{document_id}").hex


def _pick(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in keys if key in value and isinstance(value[key], (str, int, float, bool, type(None)))}


def _safe_anchor(value: Any, protected_text: str, digest: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    start, end, quote = value.get("start_offset"), value.get("end_offset"), value.get("quote")
    if not (isinstance(start, int) and not isinstance(start, bool) and
            isinstance(end, int) and not isinstance(end, bool) and
            isinstance(quote, str) and 0 <= start < end <= len(protected_text) and
            protected_text[start:end] == quote):
        return None
    if value.get("protected_artifact_sha256") not in (None, digest):
        return None
    result = {**_pick(value, ("evidence_id", "section_role", "source_section", "role")),
              "start_offset": start, "end_offset": end, "quote": quote,
              "protected_artifact_sha256": digest}
    for key in ("engine_evidence_ids", "source_rule_evidence_ids"):
        if isinstance(value.get(key), list):
            result[key] = [item for item in value[key] if isinstance(item, str)]
    if isinstance(value.get("source_context"), str) and value["source_context"] in protected_text:
        result["source_context"] = value["source_context"]
    return result


def _safe_measurement(value: Any, protected_text: str) -> dict[str, Any]:
    data = _pick(value, ("measurement_id", "source_fact_id", "original_text", "normalized_value",
                         "normalized_unit", "dimension", "measurement_type", "mapping_status",
                         "assignment_state", "review_required", "review_reason", "analytically_eligible"))
    if data.get("original_text") and data["original_text"] not in protected_text:
        data.pop("original_text")
    return data


def _category(value: Any) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_-]{0,63}", value) else None


@dataclass(frozen=True, slots=True)
class ReviewedClinicalRecord:
    """Immutable JSON snapshot; SQLite is one possible repository backend."""

    _json: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReviewedClinicalRecord":
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported reviewed record schema.")
        if set(value) != _RECORD_KEYS:
            raise ValueError("Reviewed record contains unexpected or missing fields.")
        for key in ("reviewed_record_id", "journey_run_id", "document_id", "reviewed_at"):
            if not isinstance(value.get(key), str) or not value[key]:
                raise ValueError("Reviewed record identity is incomplete.")
        if (not isinstance(value.get("record_version"), int) or
                isinstance(value["record_version"], bool) or not 1 <= value["record_version"] <= 1_000_000):
            raise ValueError("Reviewed record version is invalid.")
        if value["reviewed_record_id"] != logical_record_id(value["journey_run_id"], value["document_id"]):
            raise ValueError("Reviewed record identity does not match its document.")
        source = value.get("protected_source")
        if not isinstance(source, dict) or not isinstance(source.get("text"), str) or not source["text"].strip():
            raise ValueError("Protected source is required.")
        if not set(source).issubset(_SOURCE_KEYS) or not {"representation", "text", "sha256", "artifact_id"}.issubset(source):
            raise ValueError("Protected source contains unexpected or missing fields.")
        digest = hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
        if source.get("sha256") != digest or source.get("representation") != "protected_canonical_text":
            raise ValueError("Protected source integrity check failed.")
        if value.get("review_decision") != "ACCEPTED" or value.get("durably_reviewed") is not True:
            raise ValueError("Reviewed record must represent an accepted durable decision.")
        if value.get("major_review_required") and not value.get("major_review_acknowledged"):
            raise ValueError("Major review acknowledgement is required.")
        facts = value.get("canonical_facts")
        if not isinstance(facts, list) or not isinstance(value.get("standardized_facts"), list):
            raise ValueError("Clinical facts are malformed.")
        for fact in facts:
            if not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str):
                raise ValueError("Clinical fact identity is malformed.")
            if not set(fact).issubset(_FACT_KEYS):
                raise ValueError("Clinical fact contains unexpected fields.")
            for anchor in fact.get("evidence_anchors", []):
                if _safe_anchor(anchor, source["text"], digest) != anchor:
                    raise ValueError("Protected evidence anchor failed exact verification.")
        return cls(canonical_json(value))

    @classmethod
    def from_json(cls, value: str) -> "ReviewedClinicalRecord":
        return cls.from_dict(json.loads(value))

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)

    def to_json(self) -> str:
        return self._json

    def evidence_context(self, fact_id: str, evidence_id: str | None = None) -> dict[str, Any] | None:
        """Return exact highlight only when the protected digest and quote agree."""
        value = self.to_dict()
        source = value["protected_source"]
        text = source["text"]
        valid_digest = hashlib.sha256(text.encode("utf-8")).hexdigest() == source["sha256"]
        for fact in value["canonical_facts"]:
            if fact["fact_id"] != fact_id:
                continue
            for anchor in fact.get("evidence_anchors", []):
                if evidence_id is not None and anchor.get("evidence_id") != evidence_id:
                    continue
                valid = valid_digest and _safe_anchor(anchor, text, source["sha256"]) == anchor
                return {"protected_text": text, "artifact_sha256": source["sha256"],
                        "anchor": anchor if valid else None, "exact_highlight": bool(valid)}
        return None


def build_reviewed_record(*, run_id: str, document_id: str, reviewed_at: str,
                          protect: dict[str, Any], extract: dict[str, Any],
                          standardized: dict[str, Any],
                          exam_identity: dict[str, Any] | None = None,
                          major_review_acknowledged: bool = False) -> ReviewedClinicalRecord:
    protected = protect.get("protected_document") or {}
    text = protected.get("protected_text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A protected clinical source is required before acceptance.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if protected.get("report_id") != document_id or protected.get("integrity_sha256") != digest:
        raise ValueError("Protected source integrity check failed.")
    synthesis = extract.get("clinical_synthesis") or {}
    facts = []
    reasons = []
    major = (synthesis.get("technical_diagnostics") or {}).get("code") == "SYNTHESIS_COVERAGE_FAILURE"
    for fact in synthesis.get("canonical_facts", []):
        if not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str):
            raise ValueError("Clinical fact identity is malformed.")
        fact_reasons = fact.get("review_reason") or []
        fact_reasons = fact_reasons if isinstance(fact_reasons, list) else [fact_reasons]
        reasons.extend(str(reason) for reason in fact_reasons if reason)
        if fact.get("group") == "KEY" and any(reason in {
            "CONFLICTING_SOURCE_ASSERTION", "INTERNAL_SOURCE_CONFLICT", "INTERNAL_REPORT_CONFLICT"
        } for reason in fact_reasons):
            major = True
        curated = _pick(fact, ("fact_id", "fact_type", "canonical_concept", "display_label",
                               "assertion_state", "salience", "group", "anatomy", "laterality",
                               "review_required", "hypothesis_status"))
        curated["review_reason"] = [str(reason) for reason in fact_reasons if reason]
        curated["evidence_anchors"] = [anchor for raw in fact.get("evidence_anchors", [])
                                        if (anchor := _safe_anchor(raw, text, digest)) is not None]
        curated["anatomy"] = [value for value in fact.get("anatomy", []) if isinstance(value, str)]
        curated["observations"] = []
        for observation in fact.get("observations", []):
            if not isinstance(observation, dict):
                continue
            data = _pick(observation, ("count", "enhancement", "laterality", "extent", "source_assessment",
                                       "temporal_information", "temporal_change"))
            if isinstance(observation.get("measurements"), list):
                data["measurements"] = [m for m in observation["measurements"]
                                        if isinstance(m, str) and m in text]
            if isinstance(observation.get("morphology"), list):
                data["morphology"] = [m for m in observation["morphology"] if isinstance(m, str)]
            if isinstance(observation.get("source_context"), str) and observation["source_context"] in text:
                data["source_context"] = observation["source_context"]
            anchor = _safe_anchor(observation.get("evidence_anchor"), text, digest)
            if anchor is not None:
                data["evidence_anchor"] = anchor
            curated["observations"].append(data)
        curated["relationships"] = [_pick(rel, ("relation_type", "target_fact_id"))
                                    for rel in fact.get("relationships", []) if isinstance(rel, dict)]
        for key in ("temporal_status", "temporal_change"):
            if isinstance(fact.get(key), str):
                curated[key] = fact[key]
        facts.append(curated)
    if major and not major_review_acknowledged:
        raise ValueError("Major Review requires explicit acknowledgement.")
    standardized_facts = []
    for item in standardized.get("standardized_facts", []):
        if not isinstance(item, dict):
            continue
        data = _pick(item, ("source_fact_id", "source_assertion_state", "standardization_status",
                            "standardization_review_required"))
        data["standardization_review_reasons"] = list(item.get("standardization_review_reasons") or [])
        data["standardized_measurements"] = [_safe_measurement(m, text)
                                              for m in item.get("standardized_measurements", [])]
        for mapping_key in ("concept_mappings", "component_mappings", "anatomy_mappings"):
            data[mapping_key] = [_pick(m, ("system", "code", "display", "mapping_status",
                                           "review_required", "review_reason", "lookup_scope"))
                                 for m in item.get(mapping_key, [])]
        standardized_facts.append(data)
    study = standardized.get("standardized_study_context") or {}
    context = {"domain": "RADIOLOGY", **_pick(study, ("normalized_modality", "normalized_body_region",
                                                     "normalized_laterality"))}
    identity = exam_identity or {}
    for source_key, target_key in (("document_subtype", "subtype"),
                                   ("subdomain_or_family", "scope")):
        if category := _category(identity.get(source_key)):
            context[target_key] = category
    procedure = study.get("procedure_mapping") or {}
    context["procedure_mapping"] = _pick(procedure, ("system", "code", "display", "mapping_status",
                                                     "review_required", "review_reason"))
    value = {
        "schema_version": SCHEMA_VERSION, "record_version": 1,
        "reviewed_record_id": logical_record_id(run_id, document_id),
        "journey_run_id": run_id, "document_id": document_id,
        "reviewed_at": reviewed_at, "review_decision": "ACCEPTED", "durably_reviewed": True,
        "major_review_required": major, "major_review_acknowledged": bool(major_review_acknowledged),
        "review_issues": sorted(set(reasons +
            (["SYNTHESIS_COVERAGE_FAILURE"] if (synthesis.get("technical_diagnostics") or {}).get("code") == "SYNTHESIS_COVERAGE_FAILURE" else []) +
            (["PROTECTION_REVIEW_REQUIRED"] if (protect.get("protection_result") or {}).get("review_required") else []) +
            (["STANDARDIZATION_REVIEW_REQUIRED"] if standardized.get("state") == "NEEDS_REVIEW" else []))),
        "protected_source": {"representation": "protected_canonical_text", "text": text,
                             "sha256": digest, "artifact_id": document_id,
                             **_pick(protected, ("output_version", "selected_policy_id", "selected_policy_version"))},
        "exam_context": context,
        "clinical_summary": synthesis.get("clinical_synthesis") if isinstance(synthesis.get("clinical_synthesis"), str) else "",
        "canonical_facts": facts, "standardized_facts": standardized_facts,
        "unassigned_measurements": [_safe_measurement(m, text) for m in standardized.get("unassigned_measurements", [])],
        "provenance": {"extract_report_id": extract.get("report_id"),
                       "standardize_profile": standardized.get("profile")},
    }
    artifact = protected.get("artifact")
    if isinstance(artifact, dict) and isinstance(artifact.get("integrity_sha256"), str):
        value["protected_source"]["protected_pdf_sha256"] = artifact["integrity_sha256"]
    return ReviewedClinicalRecord.from_dict(value)
