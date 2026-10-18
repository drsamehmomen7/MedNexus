"""Synthetic, model-free atomic clinical claim and provenance tests."""
import pytest

from backend.app.modules.medical_document_intelligence.services.medgemma_evidence import (
    project_and_validate,
)
from backend.app.modules.medical_document_intelligence.services.medgemma_comparison import (
    compare_validated,
)


def project(source, statement, heading="Clinically Important Findings"):
    return project_and_validate(f"**{heading}:**\n* {statement}", source)


def native(text, assertion="PRESENT"):
    return {"display_label": text, "assertion_state": assertion, "group": "KEY"}


def test_composite_supported_and_unsupported_components_validate_independently():
    claims, metrics = project("FINDINGS: The renal lesion is present and measures 1.3 cm.",
                              "The renal lesion measures 1.4 cm")
    assert metrics["raw_medgemma_claim_count"] == 1
    assert [(c["atomic_type"], c["validation_status"]) for c in claims] == [
        ("BASE_FINDING", "SUPPORTED"), ("MEASUREMENT", "UNSUPPORTED")]


def test_unsupported_measurement_cannot_invalidate_supported_base_or_be_corrected():
    source = "FINDINGS: The renal lesion is present and measures 1.3 cm."
    claims, _ = project(source, "The renal lesion measures 1.4 cm")
    assert claims[0]["text"] == "The renal lesion measures"
    assert claims[1]["text"] == "The renal lesion measures 1.4 cm"
    assert claims[1]["validation_reason"] == "Measurement mismatch"
    assert "1.3 cm" not in claims[1]["text"]


def test_unsupported_interval_does_not_invalidate_supported_base():
    source = "FINDINGS: The left nodule is present."
    claims, _ = project(source, "The left nodule is new")
    assert [(c["atomic_type"], c["validation_status"]) for c in claims] == [
        ("BASE_FINDING", "SUPPORTED"), ("TEMPORAL", "UNSUPPORTED")]


def test_supported_base_and_interval_both_survive():
    source = "FINDINGS: The left nodule has decreased since prior study."
    claims, _ = project(source, "The left nodule has decreased since prior study")
    assert [(c["atomic_type"], c["validation_status"]) for c in claims] == [
        ("BASE_FINDING", "SUPPORTED"), ("TEMPORAL", "SUPPORTED")]


def test_contrasting_interval_statuses_are_validated_independently():
    source = "FINDINGS: The left nodule has decreased."
    claims, _ = project(source, "The left nodule has decreased but was stable relative to previous imaging")
    temporal = [c for c in claims if c["atomic_type"] == "TEMPORAL"]
    assert len(temporal) == 2
    assert [c["validation_status"] for c in temporal] == ["SUPPORTED", "UNSUPPORTED"]


def test_resolved_finding_is_atomic_without_promoting_current_presence():
    source = "FINDINGS: Areas of left basal atelectasis have resolved."
    claims, _ = project(source, "Areas of left basal atelectasis seen before now resolved")
    assert len(claims) == 1
    assert claims[0]["atomic_type"] == "TEMPORAL"
    assert claims[0]["validation_status"] == "SUPPORTED"
    assert "resolved" in claims[0]["text"]


def test_two_differential_diagnoses_receive_independent_statuses():
    source = "FINDINGS: Differential includes benign vascular neoplasm."
    claims, _ = project(source,
                        "Differential includes benign vascular neoplasm, aggressive renal malignancy",
                        "Diagnostic Considerations")
    assert [(c["atomic_type"], c["validation_status"]) for c in claims] == [
        ("DIAGNOSTIC_CONSIDERATION", "SUPPORTED"),
        ("DIAGNOSTIC_CONSIDERATION", "UNSUPPORTED")]


def test_supported_and_invented_recommendations_validate_separately():
    source = "RECOMMENDATIONS: Repeat ultrasound in six months."
    claims, _ = project(source, "Repeat ultrasound in six months and obtain MRI in six months",
                        "Follow-Up Recommendations")
    assert [(c["atomic_type"], c["validation_status"]) for c in claims] == [
        ("RECOMMENDATION", "SUPPORTED"), ("RECOMMENDATION", "UNSUPPORTED")]


def test_addendum_supersedes_only_the_affected_atomic_qualifier():
    source = ("FINDINGS: The left nodule is new. The right renal cyst is present.\n"
              "ADDENDUM\nThe left nodule is stable and not new.")
    claims, _ = project(source, "New left nodule and the right renal cyst is present")
    assert any(c["atomic_type"] == "TEMPORAL" and c["validation_status"] == "SUPERSEDED"
               for c in claims)
    assert any("right renal cyst" in c["text"] and c["validation_status"] == "SUPPORTED"
               for c in claims)


def test_explicit_negative_remains_one_negated_assertion():
    source = "FINDINGS: No left renal calculus."
    claims, _ = project(source, "No left renal calculus was visualized during this examination",
                        "Pertinent Negatives")
    assert len(claims) == 1
    assert claims[0]["text"].startswith("No left renal calculus")
    assert claims[0]["validation_status"] == "SUPPORTED"


def test_not_mentioned_never_creates_a_supported_negative():
    claims, _ = project("FINDINGS: Left renal cyst.", "No mention of a right renal calculus",
                        "Pertinent Negatives")
    assert len(claims) == 1
    assert claims[0]["validation_status"] == "UNSUPPORTED"


def test_raw_parent_and_occurrence_provenance_are_preserved():
    parent = "The renal lesion measures 1.4 cm"
    claims, metrics = project("FINDINGS: The renal lesion measures 1.3 cm.", parent)
    assert metrics["parents"][0]["text"] == parent
    assert len(claims) == 2
    assert all(c["parent_text"] == parent and c["parent_id"] == "parent-1" for c in claims)
    assert all(c["raw_occurrences"][0]["parent_occurrence"] == 1 for c in claims)
    assert all(c["source_section"] == "clinically important findings" for c in claims)


def test_repeated_parent_claims_deduplicate_children_without_losing_occurrences():
    raw = ("**Clinically Important Findings:**\n"
           "* The left nodule has decreased.\n* The left nodule has decreased.")
    claims, metrics = project_and_validate(raw, "FINDINGS: The left nodule has decreased.")
    assert metrics["raw_medgemma_claim_count"] == 2
    assert metrics["duplicate_claim_count"] == 1
    assert metrics["raw_atomic_claim_count"] == 4
    assert metrics["unique_atomic_claim_count"] == 2
    assert metrics["atomic_duplicate_count"] == 2
    assert all(c["raw_occurrence_count"] == 2 for c in claims)


def test_atomic_comparison_does_not_merge_opposite_laterality():
    source = "FINDINGS: A left renal cyst and a right renal cyst are present."
    claims, _ = project(source, "Right renal cyst")
    result = compare_validated([native("Left renal cyst")], claims, source, {})
    assert result["counts"]["AGREEMENT"] == 0


def test_atomic_comparison_keeps_materially_different_measurements_separate():
    source = "FINDINGS: The renal lesion measures 1.3 cm."
    claims, _ = project(source, "The renal lesion measures 1.4 cm")
    result = compare_validated([native("Renal lesion measures 1.3 cm")], claims, source, {})
    assert result["counts"]["UNSUPPORTED"] == 1
    assert all("1.4 cm" not in str(row) for row in result["groups"]["AGREEMENT"])


def test_unsupported_child_cannot_become_agreement_from_its_supported_parent_sibling():
    source = "FINDINGS: The left nodule is present."
    claims, _ = project(source, "The left nodule is new")
    result = compare_validated([native("Left nodule")], claims, source, {})
    assert result["counts"]["UNSUPPORTED"] == 1
    assert all("new" not in str(row).casefold() for row in result["groups"]["AGREEMENT"])
