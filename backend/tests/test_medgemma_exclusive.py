"""Model-free primary-category invariants for validated atomic comparisons."""

from backend.app.modules.medical_document_intelligence.services.medgemma_comparison import (
    V2_CATEGORIES, compare_validated,
)
from backend.app.modules.medical_document_intelligence.services.medgemma_evidence import (
    project_and_validate, validate_claim,
)


def native(text, *, assertion="PRESENT", group="KEY"):
    return {"display_label": text, "assertion_state": assertion, "group": group,
            "evidence_anchors": [{"quote": text}]}


def child(text, source, role="FINDING"):
    return validate_claim({"text": text, "role": role}, source)


def categories_for(result, text):
    return [category for category, rows in result["groups"].items()
            if any(row.get("medgemma") == text for row in rows)]


def test_shared_atomic_child_is_agreement_only_not_medgemma_only():
    source = "FINDINGS: Mild soft-tissue swelling."
    result = compare_validated([native("Mild soft tissue swelling")],
                               [child("Mild soft-tissue swelling", source)], source, {})
    assert categories_for(result, "Mild soft-tissue swelling") == ["AGREEMENT"]
    assert result["counts"]["MEDGEMMA_ONLY"] == 0


def test_shared_native_fact_is_not_also_mrj_only():
    source = "FINDINGS: Left renal cyst."
    result = compare_validated([native("Left renal cyst")],
                               [child("Left renal cyst", source)], source, {})
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["MRJ_ONLY"] == 0


def test_shared_base_and_supported_extra_interval_are_separate_children():
    source = "FINDINGS: The left renal cyst is present and has decreased."
    claims = [child("Left renal cyst", source), child("Left renal cyst decreased", source)]
    result = compare_validated([native("Left renal cyst")], claims, source, {})
    assert categories_for(result, "Left renal cyst") == ["AGREEMENT"]
    assert categories_for(result, "Left renal cyst decreased") == ["MEDGEMMA_ONLY"]
    assert result["counts"]["AGREEMENT"] == result["counts"]["MEDGEMMA_ONLY"] == 1


def test_unsupported_child_has_no_positive_primary_category():
    source = "FINDINGS: A left renal cyst measures 1.3 cm."
    rejected = child("Left renal cyst measures 1.4 cm", source, "MEASUREMENT")
    result = compare_validated([native("Left renal cyst")], [rejected], source, {})
    assert rejected["validation_status"] == "UNSUPPORTED"
    assert categories_for(result, rejected["text"]) == ["UNSUPPORTED"]


def test_unresolved_child_has_no_agreement_or_medgemma_only():
    source = "FINDINGS: A left renal cyst."
    uncertain = {"text": "Indeterminate parenchymal change", "role": "FINDING",
                 "validation_status": "UNRESOLVED", "validation_reason": "Source support uncertain"}
    result = compare_validated([native("Left renal cyst")], [uncertain], source, {})
    assert categories_for(result, uncertain["text"]) == ["UNRESOLVED"]


def test_conflict_is_exclusive_and_does_not_create_native_only():
    source = "FINDINGS: Left renal cyst. No left renal cyst."
    opposite = {"text": "No left renal cyst", "role": "PERTINENT_NEGATIVE",
                "validation_status": "SUPPORTED", "validation_reason": "Supported by protected report"}
    result = compare_validated([native("Left renal cyst")], [opposite], source, {})
    assert categories_for(result, opposite["text"]) == ["CONFLICT"]
    assert result["counts"]["MRJ_ONLY"] == 0


def test_duplicate_raw_occurrences_have_one_primary_category_and_keep_provenance():
    source = "FINDINGS: Left renal cyst."
    raw = ("**Findings:**\n* Left renal cyst.\n"
           "**Clinically Important Findings:**\n* Left renal cyst.")
    claims, metrics = project_and_validate(raw, source)
    assert len(claims) == 1 and claims[0]["raw_occurrence_count"] == 2
    before = [dict(occurrence) for occurrence in claims[0]["raw_occurrences"]]
    result = compare_validated([native("Left renal cyst")], claims, source, metrics)
    assert categories_for(result, "Left renal cyst") == ["AGREEMENT"]
    assert result["counts"]["AGREEMENT"] == 1
    assert claims[0]["raw_occurrences"] == before
    assert len({item["parent_id"] for item in before}) == 2


def test_duplicate_supplied_children_do_not_inflate_category_totals():
    source = "FINDINGS: Left renal cyst. Right renal cyst."
    shared = child("Left renal cyst", source)
    result = compare_validated([native("Left renal cyst"), native("Right renal cyst")],
                               [shared, shared], source, {"duplicate_claim_count": 0})
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["MRJ_ONLY"] == 1
    assert result["metrics"]["duplicate_claim_count"] == 1
    med_ids = [row["atomic_claim_id"] for category in V2_CATEGORIES
               for row in result["groups"][category] if row.get("atomic_claim_id")]
    assert len(med_ids) == len(set(med_ids)) == 1
    assert sum(result["counts"].values()) == 2
