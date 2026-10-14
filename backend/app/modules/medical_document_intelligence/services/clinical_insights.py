"""Governed, report-level descriptive analysis of pinned reviewed records."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from typing import Any

from backend.app.modules.medical_document_intelligence.contracts.clinical_intelligence import (
    ClinicalInsightDefinition, ClinicalInsightVariable, ClinicalIntelligenceProfileRegistry,
)
from backend.app.modules.medical_document_intelligence.services.clinical_intelligence_profiles import REGISTRY


CONTRACT = "mrj-clinical-insight-run-v0.1"
LIMITATION = ("Descriptive report-level documentation in this Collection only. "
              "Reports are not deduplicated by person. No inferential, population, predictive, or causal claim.")
_PRIOR = {"PRIOR", "HISTORICAL", "SUPERSEDED"}


def _normal(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def _matches(fact: dict[str, Any], variable: ClinicalInsightVariable) -> bool:
    if (fact.get("temporal_status") in _PRIOR or fact.get("hypothesis_status")
            or fact.get("fact_type") in {"DIAGNOSTIC_HYPOTHESIS", "REPORT_ASSESSMENT", "RECOMMENDATION"}
            or fact.get("group") in {"ASSESSMENT", "RECOMMENDATION"}):
        return False
    concept = _normal(fact.get("canonical_concept"))
    label = _normal(fact.get("display_label"))
    if not any(re.search(r"(?<!\w)" + re.escape(_normal(term)) + r"(?!\w)", value)
               for term in variable.reviewed_concept_terms for value in (concept, label)):
        return False
    if variable.anatomy_terms:
        anatomy = _normal(" ".join(str(item) for item in fact.get("anatomy") or []))
        if not any(_normal(term) in anatomy or _normal(term) in concept or _normal(term) in label
                   for term in variable.anatomy_terms):
            return False
    return not variable.require_laterality or fact.get("laterality") in {"LEFT", "RIGHT"}


def _assessment(record: dict[str, Any], variable: ClinicalInsightVariable, *,
                laterality: str | None = None) -> tuple[str, list[str]]:
    matched = [fact for fact in record["canonical_facts"] if _matches(fact, variable)
               and (laterality is None or fact.get("laterality") == laterality)]
    states = {fact.get("assertion_state") for fact in matched}
    if not matched:
        return "NOT_DOCUMENTED", []
    ids = sorted({fact["fact_id"] for fact in matched})
    if states == {variable.present_assertion}:
        return "PRESENT", ids
    if states == {variable.absent_assertion}:
        return "EXPLICITLY_ABSENT_OR_NORMAL", ids
    return "INDETERMINATE", ids


def _ref(record: dict[str, Any], fact_ids: list[str], *, event: bool,
         coverage: str | None = None) -> dict[str, Any]:
    return {"reviewed_record_id": record["reviewed_record_id"],
            "reviewed_record_version": record["record_version"],
            "fact_ids": fact_ids, "event": event, "coverage": coverage}


def _group(group_id: str, label: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = len(members)
    numerator = sum(item["event"] for item in members)
    return {"group_id": group_id, "label": label, "numerator": numerator,
            "denominator": denominator,
            "bar_percent": round(100 * numerator / denominator, 2) if denominator else 0,
            "contributors": members}


def _coverage(record: dict[str, Any], element_id: str) -> str | None:
    for section in record.get("profile_coverage") or []:
        for element in section.get("elements") or []:
            if element.get("element_id") == element_id:
                return element.get("coverage")
    return None


def _evaluate(definition: ClinicalInsightDefinition, records: list[dict[str, Any]]) -> dict[str, Any]:
    if definition.insight_type == "STRATIFIED_DOCUMENTATION":
        raise ValueError("Stratified documentation requires a governed durable stratifier.")
    groups: list[dict[str, Any]]
    excluded = {"SCOPE_OR_PROFILE": 0, "NOT_DOCUMENTED": 0, "INDETERMINATE": 0,
                "NOT_APPLICABLE": 0, "MISSING_COVERAGE": 0}
    eligible = [record for record in records
                if (record.get("profile_provenance") or {}).get("scope") in definition.compatible_scopes]
    excluded["SCOPE_OR_PROFILE"] = len(records) - len(eligible)
    if definition.insight_type == "COVERAGE_QUALITY":
        documented, limited, not_documented = [], [], []
        for record in eligible:
            status = _coverage(record, definition.coverage_element_id or "")
            if status is None:
                excluded["MISSING_COVERAGE"] += 1
            elif status == "NOT_APPLICABLE":
                excluded["NOT_APPLICABLE"] += 1
            else:
                # Profile coverage is an accepted snapshot without fact-level evidence IDs.
                # Do not imply that a pancreas finding proves its visualization status.
                item = _ref(record, [], event=True, coverage=status)
                if status == "DOCUMENTED":
                    documented.append(item)
                elif status == "LIMITED_OR_NOT_VISUALIZED":
                    limited.append(item)
                else:
                    not_documented.append(item)
        applicable = len(documented) + len(limited) + len(not_documented)
        groups = [
            _group("documented", "Documented visualization", documented),
            _group("limited", "Limited or not visualized", limited),
            _group("not_documented", "Not documented", not_documented),
        ]
        for group in groups:
            group["denominator"] = applicable
            group["bar_percent"] = round(100 * group["numerator"] / applicable, 2) if applicable else 0
        event_support = applicable
        enough = applicable >= definition.support.minimum_eligible_n
        if not applicable and excluded["MISSING_COVERAGE"]:
            state = "UNAVAILABLE"
        elif not applicable and excluded["NOT_APPLICABLE"]:
            state = "NOT_APPLICABLE"
        else:
            state = "OBSERVATION_AVAILABLE" if enough else "INSUFFICIENT_DATA"
        summary = (f"In this Collection, pancreas visualization was documented in "
                   f"{len(documented)}/{applicable} applicable eligible reviewed reports, "
                   f"limited or not visualized in {len(limited)}/{applicable}, and not documented "
                   f"in {len(not_documented)}/{applicable}.") if enough else definition.insufficient_wording
    else:
        with_group, without_group = [], []
        for record in eligible:
            exposure = definition.exposure
            outcome = definition.outcome
            assert exposure is not None and outcome is not None
            exposed, exposed_ids = _assessment(record, exposure)
            if exposed == "INDETERMINATE":
                excluded["INDETERMINATE"] += 1
                continue
            if exposed == "NOT_DOCUMENTED":
                excluded["NOT_DOCUMENTED"] += 1
                continue
            if definition.insight_type == "FINDING_CONTEXT" and exposed != "PRESENT":
                excluded["NOT_APPLICABLE"] += 1
                continue
            if definition.same_laterality:
                sides = {fact.get("laterality") for fact in record["canonical_facts"]
                         if fact["fact_id"] in exposed_ids and fact.get("laterality") in {"LEFT", "RIGHT"}}
                assessments = [_assessment(record, outcome, laterality=side) for side in sorted(sides)]
                if any(status == "PRESENT" for status, _ in assessments):
                    observed = "PRESENT"
                elif assessments and all(status == "EXPLICITLY_ABSENT_OR_NORMAL" for status, _ in assessments):
                    observed = "EXPLICITLY_ABSENT_OR_NORMAL"
                elif any(status == "INDETERMINATE" for status, _ in assessments):
                    observed = "INDETERMINATE"
                else:
                    observed = "NOT_DOCUMENTED"
                outcome_ids = sorted({item for _, ids in assessments for item in ids})
            else:
                observed, outcome_ids = _assessment(record, outcome)
            if observed not in {"PRESENT", "EXPLICITLY_ABSENT_OR_NORMAL"}:
                excluded[observed] += 1
                continue
            item = _ref(record, sorted(set(exposed_ids + outcome_ids)), event=observed == "PRESENT")
            if exposed == "PRESENT":
                with_group.append(item)
            elif definition.explicit_absence_comparison:
                without_group.append(item)
        groups = [_group("with", f"With {definition.exposure.concept_id.replace('_', ' ').lower()}", with_group)]
        if definition.insight_type == "CO_DOCUMENTATION":
            groups.append(_group("without", f"Explicitly without {definition.exposure.concept_id.replace('_', ' ').lower()}", without_group))
        applicable = sum(group["denominator"] for group in groups)
        event_support = sum(group["numerator"] for group in groups)
        enough = (applicable >= definition.support.minimum_eligible_n
                  and all(group["denominator"] >= definition.support.minimum_group_n for group in groups)
                  and event_support >= definition.support.minimum_event_support)
        equal = (len(groups) == 2 and all(group["denominator"] for group in groups)
                 and groups[0]["numerator"] * groups[1]["denominator"]
                 == groups[1]["numerator"] * groups[0]["denominator"])
        state = ("INSUFFICIENT_DATA" if not enough else
                 "NO_CLEAR_DESCRIPTIVE_PATTERN" if equal else "OBSERVATION_AVAILABLE")
        if not enough:
            summary = definition.insufficient_wording
        elif equal:
            summary = definition.no_pattern_wording
        elif len(groups) == 2:
            a, b = groups
            summary = (f"In this Collection, {definition.outcome.concept_id.replace('_', ' ').lower()} was documented "
                       f"in {a['numerator']}/{a['denominator']} eligible reviewed reports with "
                       f"{definition.exposure.concept_id.replace('_', ' ').lower()} and "
                       f"{b['numerator']}/{b['denominator']} with its explicit absence.")
        else:
            a = groups[0]
            summary = (f"In this Collection, {definition.outcome.concept_id.replace('_', ' ').lower()} was documented "
                       f"in {a['numerator']}/{a['denominator']} eligible reviewed reports with "
                       f"{definition.exposure.concept_id.replace('_', ' ').lower()}.")
    return {"insight_id": definition.insight_id, "definition_version": definition.version,
            "title": definition.title, "question": definition.question, "insight_type": definition.insight_type,
            "state": state, "analysis_level": "REPORT", "eligible_n": applicable,
            "event_support": event_support, "groups": groups, "exclusions": excluded,
            "support_policy": asdict(definition.support), "eligibility_rule":
            "Exact accepted reviewed-record version, compatible Clinical Extraction Profile and scope, "
            "explicit current assertions for each required variable; unknown and indeterminate excluded.",
            "denominator_rule": ("Applicable profile coverage snapshots; out-of-scope excluded."
                                 if definition.insight_type == "COVERAGE_QUALITY" else
                                 "Reports with explicit exposure and outcome assessment; unknown is not absence."),
            "summary": summary,
            "exam_profile_reference": asdict(definition.exam_profile_reference),
            "clinical_relationship_reference": (asdict(definition.clinical_relationship_reference)
                                                if definition.clinical_relationship_reference else None),
            "relationship_reference_status": definition.relationship_reference_status,
            "rationale": definition.rationale, "limitations": LIMITATION}


class ClinicalInsightEngine:
    def __init__(self, intelligence, registry: ClinicalIntelligenceProfileRegistry = REGISTRY):
        self.intelligence = intelligence
        self.registry = registry

    def analyze(self, collection_id: str, version: int | None = None) -> dict[str, Any]:
        analysis = self.intelligence.analyze(collection_id, version)
        repo = self.intelligence.repository
        records = repo.get_members(collection_id, analysis["collection_version"])
        values = [record.to_dict() for record in records]
        selected = {}
        unsupported = 0
        for value in values:
            provenance = value.get("profile_provenance") or {}
            profile = self.registry.resolve(provenance.get("profile_id"), provenance.get("profile_version"))
            if profile is None:
                unsupported += 1
            else:
                selected.setdefault((profile.intelligence_profile_id, profile.version), (profile, []))[1].append(value)
        configuration = [asdict(profile) for profile, _ in selected.values()]
        config_digest = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
        key = json.dumps([CONTRACT, analysis["analysis_run_id"], config_digest], sort_keys=True)
        run_id = hashlib.sha256(key.encode()).hexdigest()[:32]
        try:
            return repo.get_insights(run_id)
        except LookupError:
            pass
        profile_runs = []
        for _, (profile, subset) in sorted(selected.items()):
            profile_runs.append({
                "intelligence_profile_id": profile.intelligence_profile_id,
                "intelligence_profile_version": profile.version,
                "clinical_profile_id": profile.compatible_clinical_profile_id,
                "clinical_profile_versions": list(profile.compatible_clinical_profile_versions),
                "compatible_reviewed_reports": len(subset),
                "definitions": [_evaluate(definition, subset) for definition in profile.definitions],
            })
        all_results = [result for group in profile_runs for result in group["definitions"]]
        counts = {state: sum(item["state"] == state for item in all_results)
                  for state in ("OBSERVATION_AVAILABLE", "INSUFFICIENT_DATA",
                                "NO_CLEAR_DESCRIPTIVE_PATTERN", "NOT_APPLICABLE", "UNAVAILABLE")}
        payload = {"contract": CONTRACT, "insight_run_id": run_id,
                   "analysis_run_id": analysis["analysis_run_id"],
                   "collection_id": collection_id, "collection_version": analysis["collection_version"],
                   "analysis_level": "REPORT", "configuration_sha256": config_digest,
                   "profiles": profile_runs, "unsupported_profile_records": unsupported,
                   "summary": {"relationships_evaluated": len(all_results), **counts},
                   "limitations": LIMITATION}
        repo.save_insights(payload)
        return payload

    def contributors(self, run_id: str, insight_id: str, group_id: str) -> dict[str, Any]:
        run = self.intelligence.repository.get_insights(run_id)
        result = next((item for group in run["profiles"] for item in group["definitions"]
                       if item["insight_id"] == insight_id), None)
        if result is None:
            raise LookupError("Insight definition was not found.")
        group = next((item for item in result["groups"] if item["group_id"] == group_id), None)
        if group is None:
            raise LookupError("Insight group was not found.")
        records = self.intelligence.repository.get_members(run["collection_id"], run["collection_version"])
        by_ref = {(record.to_dict()["reviewed_record_id"], record.to_dict()["record_version"]): record
                  for record in records}
        rows = []
        for member in group["contributors"]:
            ref = (member["reviewed_record_id"], member["reviewed_record_version"])
            record = by_ref.get(ref)
            if record is None:
                raise ValueError("Pinned reviewed contributor is unavailable.")
            value = record.to_dict()
            facts = {fact["fact_id"]: fact for fact in value["canonical_facts"]}
            evidence_rows = []
            for fact_id in member["fact_ids"]:
                fact = facts.get(fact_id)
                if fact is None or not fact.get("evidence_anchors"):
                    raise ValueError("Reviewed Insight fact is unavailable.")
                anchor = fact["evidence_anchors"][0]
                evidence = record.evidence_context(fact_id, anchor.get("evidence_id"))
                if not evidence or not evidence["exact_highlight"]:
                    raise ValueError("Reviewed Insight evidence is unavailable.")
                evidence_rows.append({"fact_id": fact_id, "fact_label": fact.get("display_label"),
                                      "assertion_state": fact.get("assertion_state"),
                                      "quote": anchor["quote"], "start_offset": anchor["start_offset"],
                                      "end_offset": anchor["end_offset"],
                                      "protected_artifact_sha256": evidence["artifact_sha256"]})
            rows.append({"reviewed_record_id": ref[0], "reviewed_record_version": ref[1],
                         "exam_context": value["exam_context"], "event": member["event"],
                         "coverage": member["coverage"], "facts": evidence_rows})
        return {"insight_run_id": run_id, "insight_id": insight_id, "group_id": group_id,
                "numerator": group["numerator"], "denominator": group["denominator"],
                "contributors": rows}
