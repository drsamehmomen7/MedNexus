"""Synthetic, model-free evidence and final-authority contract tests."""
import pytest

from backend.app.modules.medical_document_intelligence.services.medgemma_evidence import (
    project_and_validate, project_clinical_claims, validate_claim,
)
from backend.app.modules.medical_document_intelligence.services.medgemma_comparison import (
    compare_validated, revalidate_payload,
)


def claim(text, role="FINDING"):
    return {"text": text, "role": role}


def fact(text, assertion="PRESENT", group="KEY"):
    return {"display_label": text, "assertion_state": assertion, "group": group}


def test_projector_excludes_reasoning_metadata_and_unmapped_prose():
    raw = ("<unused94>thought\n**Clinically Important Findings:**\n* Invented reasoning item\n"
           "<unused95>Result\n**Clinically Important Findings:**\n* Left pleural effusion.\n"
           "**Note:**\n* This task was completed.\n"
           "**Follow-Up Recommendations:**\n* Repeat ultrasound in six months.\n")
    claims, count = project_clinical_claims(raw)
    assert count == 2
    assert [c["text"] for c in claims] == ["Left pleural effusion", "Repeat ultrasound in six months"]


def test_duplicate_clinical_claims_do_not_inflate_projection():
    raw = "**Pertinent Negatives:**\n* No thrombosis.\n* No thrombosis.\n* Negative for thrombosis."
    claims, count = project_clinical_claims(raw)
    assert count == 3 and len(claims) == 1


def test_equivalent_spacing_matches_without_changing_source_validation():
    source = "FINDINGS: Mild pleural effusion."
    med = validate_claim(claim("Mild  pleural effusion"), source)
    result = compare_validated([fact("Mild pleural effusion")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1


def test_equivalent_hyphenation_matches_without_fuzzy_synonyms():
    source = "FINDINGS: Mild soft-tissue edema."
    med = validate_claim(claim("Mild soft-tissue edema"), source)
    result = compare_validated([fact("Mild soft tissue edema")], [med], source, {})
    assert result["counts"]["AGREEMENT"] == 1


def test_joined_and_split_compound_uses_exact_native_concept():
    source = "FINDINGS: Peri bronchial thickening."
    med = validate_claim(claim("Peri bronchial thickening"), source)
    native = {**fact("Peribronchial"), "canonical_concept": "general:open:peribronchial",
              "evidence_anchors": [{"quote": "Peri bronchial"}]}
    result = compare_validated([native], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1


def test_recommendation_meaning_matches_despite_model_section_label():
    source = ("RECOMMENDATIONS: Further diagnostic testing such as telemetry could be considered. "
              "Telemetry could be provided as clinically indicated.")
    med = validate_claim(claim("Further diagnostic testing such as telemetry could be considered",
                               "DIAGNOSTIC_CONSIDERATION"), source)
    native = {**fact("Telemetry could be provided as clinically indicated", "NOT_APPLICABLE",
                     "RECOMMENDATION"),
              "evidence_anchors": [{"quote": "Telemetry could be provided as clinically indicated"}]}
    result = compare_validated([native], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1


def test_same_base_and_same_qualifiers_is_complete_agreement():
    source = "FINDINGS: A mild left renal cyst is present."
    med = validate_claim(claim("Mild left renal cyst"), source)
    result = compare_validated([fact("Mild left renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["MEDGEMMA_ONLY"] == 0
    assert result["groups"]["AGREEMENT"][0]["match_scope"] == "COMPLETE_CLAIM"


@pytest.mark.parametrize("qualifier", ["stable", "new"])
def test_supported_temporal_status_is_separate_from_the_shared_base(qualifier):
    source = f"FINDINGS: The left renal cyst is present and {qualifier}."
    base = validate_claim(claim("Left renal cyst"), source)
    interval = validate_claim(claim(f"Left renal cyst {qualifier}"), source)
    result = compare_validated([fact("Left renal cyst")], [base, interval], source, {})
    assert base["validation_status"] == interval["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert "interval status" in result["groups"]["MEDGEMMA_ONLY"][0]["reason"]
    assert result["groups"]["AGREEMENT"][0]["medgemma"] == "Left renal cyst"


def test_resolved_status_has_only_one_primary_category():
    source = "FINDINGS: The left renal cyst has resolved."
    med = validate_claim(claim("Left renal cyst resolved"), source)
    result = compare_validated([fact("Left renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert result["counts"]["AGREEMENT"] == 0


def test_specific_location_cannot_be_consumed_by_generic_native_claim():
    source = "FINDINGS: A right renal cyst is present."
    med = validate_claim(claim("Right renal cyst"), source)
    result = compare_validated([fact("Renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 0
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert "laterality: right" in result["groups"]["MEDGEMMA_ONLY"][0]["reason"]


def test_specific_anatomical_subsite_is_preserved_without_a_terminology_lookup():
    source = "FINDINGS: A renal cyst is present in the upper pole."
    med = validate_claim(claim("Renal cyst in the upper pole"), source)
    result = compare_validated([fact("Renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 0
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert "location: upper pole" in result["groups"]["MEDGEMMA_ONLY"][0]["reason"]


def test_different_explicit_location_cannot_share_an_agreement():
    source = "FINDINGS: A left renal cyst and a right renal cyst are present."
    med = validate_claim(claim("Right renal cyst"), source)
    result = compare_validated([fact("Left renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 0
    assert result["counts"]["MEDGEMMA_ONLY"] == 1


def test_native_interval_qualifier_is_not_labeled_complete_agreement():
    source = "FINDINGS: The renal cyst has decreased."
    med = validate_claim(claim("Renal cyst"), source)
    result = compare_validated([fact("Renal cyst decreased")], [med], source, {})
    assert med["validation_status"] == "SUPPORTED"
    assert result["counts"]["AGREEMENT"] == 1
    assert result["groups"]["AGREEMENT"][0]["match_scope"] == "BASE_CONCEPT"
    assert result["counts"]["MRJ_ONLY"] == 0
    assert result["groups"]["AGREEMENT"][0]["native_additional_components"] == ["interval status: decreased"]


def test_repeated_equivalent_supported_claims_do_not_inflate_comparison():
    source = "FINDINGS: Mild left renal cyst."
    med = validate_claim(claim("Mild left renal cyst"), source)
    metrics = {"duplicate_claim_count": 0}
    result = compare_validated([fact("Mild left renal cyst")], [med, med], source, metrics)
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["MEDGEMMA_ONLY"] == 0
    assert result["metrics"]["duplicate_claim_count"] == 1


def test_unsupported_extra_qualifier_does_not_gain_base_agreement():
    source = "FINDINGS: A left renal cyst is present."
    med = validate_claim(claim("New left renal cyst in 2099"), source)
    result = compare_validated([fact("Left renal cyst")], [med], source, {})
    assert med["validation_status"] == "UNSUPPORTED"
    assert result["counts"]["UNSUPPORTED"] == 1
    assert result["counts"]["AGREEMENT"] == 0
    assert result["counts"]["MEDGEMMA_ONLY"] == 0


def test_superseded_qualifier_does_not_gain_base_agreement():
    source = ("FINDINGS: A new left renal cyst is present.\n"
              "ADDENDUM\nThe left renal cyst is stable and not new.")
    med = validate_claim(claim("New left renal cyst"), source)
    result = compare_validated([fact("Left renal cyst")], [med], source, {})
    assert med["validation_status"] == "SUPERSEDED"
    assert result["counts"]["UNSUPPORTED"] == 1
    assert result["counts"]["AGREEMENT"] == 0


def test_cross_section_claim_deduplicates_with_provenance():
    raw = ("**Clinically Important Findings:**\n* No pneumothorax.\n"
           "**Pertinent Negatives:**\n* No pneumothorax.")
    claims, raw_count = project_clinical_claims(raw)
    assert (raw_count, len(claims)) == (2, 1)
    assert claims[0]["raw_occurrence_count"] == 2
    assert claims[0]["source_sections"] == ["clinically important findings", "pertinent negatives"]
    assert len(claims[0]["raw_occurrences"]) == 2


def test_finding_and_measurement_repeat_one_concept_with_both_raw_variants():
    raw = ("**Clinically Important Findings:**\n"
           "* The renal cyst measures 2.4 cm in greatest dimension.\n"
           "**Measurements:**\n* Renal cyst size: 2.4 cm in greatest dimension.")
    claims, raw_count = project_clinical_claims(raw)
    assert (raw_count, len(claims)) == (2, 1)
    assert claims[0]["raw_occurrence_count"] == 2
    assert claims[0]["source_sections"] == ["clinically important findings", "measurements"]
    assert len(claims[0]["raw_text_variants"]) == 2
    assert [item["line_number"] for item in claims[0]["raw_occurrences"]] == [2, 4]


def test_different_measurements_laterality_and_assertion_remain_separate():
    measurements = ("**Findings:**\n* Renal cyst size 2.4 cm.\n* Renal cyst size 2.8 cm.")
    laterality = "**Findings:**\n* Left pleural effusion.\n* Right pleural effusion."
    assertion = "**Findings:**\n* Left pleural effusion.\n* No left pleural effusion."
    for raw in (measurements, laterality, assertion):
        claims, raw_count = project_clinical_claims(raw)
        assert (raw_count, len(claims)) == (2, 2)


def test_normalization_cannot_turn_unsupported_claim_into_agreement():
    source = "FINDINGS: Left-sided pleural effusion."
    med = validate_claim(claim("Right sided pleural effusion"), source)
    result = compare_validated([fact("Left sided pleural effusion")], [med], source, {})
    assert med["validation_status"] == "UNSUPPORTED"
    assert result["counts"]["AGREEMENT"] == 0
    assert result["counts"]["UNSUPPORTED"] == 1


def test_validated_dedup_retains_raw_output_and_all_occurrences():
    raw = ("**Findings:**\n* Left pleural effusion.\n"
           "**Clinically Important Findings:**\n* Left pleural effusion.")
    source = "FINDINGS: Left pleural effusion."
    claims, metrics = project_and_validate(raw, source)
    assert metrics["raw_medgemma_claim_count"] == 2
    assert metrics["unique_projected_medgemma_claim_count"] == 1
    assert metrics["duplicate_claim_count"] == 1
    assert len(claims[0]["raw_occurrences"]) == 2
    assert [item["text"] for item in claims[0]["raw_occurrences"]] == ["Left pleural effusion"] * 2
    assert raw.count("Left pleural effusion") == 2


@pytest.mark.parametrize("text,role,expected", [
    ("Left pleural effusion", "FINDING", "SUPPORTED"),
    ("Right pleural effusion", "FINDING", "UNSUPPORTED"),
    ("1.4 cm left pleural effusion", "MEASUREMENT", "UNSUPPORTED"),
    ("Repeat CT in six months", "RECOMMENDATION", "UNSUPPORTED"),
    ("Lymphoma is possible", "DIAGNOSTIC_CONSIDERATION", "UNSUPPORTED"),
    ("No pneumothorax", "PERTINENT_NEGATIVE", "SUPPORTED"),
    ("No mention of fracture", "PERTINENT_NEGATIVE", "UNSUPPORTED"),
])
def test_evidence_statuses(text, role, expected):
    source = "FINDINGS: Left pleural effusion measures 1.3 cm. No pneumothorax."
    assert validate_claim(claim(text, role), source)["validation_status"] == expected


def test_uncertain_paraphrase_remains_unresolved():
    source = "FINDINGS: Mild opacity near the left base."
    result = validate_claim(claim("Subtle parenchymal change"), source)
    assert result["validation_status"] == "UNRESOLVED"


def test_addendum_overrides_prior_uncertainty_and_comparison_request():
    source = ("FINDINGS: The pulmonary opacity is new and indeterminate.\n"
              "IMPRESSION: Compare with prior films to assess the pulmonary opacity.\n"
              "ADDENDUM\nPrior films are now available. The pulmonary opacity is stable and definitely a scar."
              " No further evaluation is needed.")
    status = validate_claim(claim("The new indeterminate pulmonary opacity requires further evaluation"), source)
    request = validate_claim(claim("Compare with prior films to assess the pulmonary opacity", "RECOMMENDATION"), source)
    assert status["validation_status"] == "SUPERSEDED"
    assert request["validation_status"] == "SUPERSEDED"


def test_final_impression_can_supersede_explicit_opposite_assertion():
    source = "FINDINGS: Left opacity is present.\nIMPRESSION: No left opacity."
    assert validate_claim(claim("Left opacity is present"), source)["validation_status"] == "SUPERSEDED"


def test_supported_medgemma_only_requires_source_support():
    source = "FINDINGS: Right thigh mass measures 3.5 cm.\nIMPRESSION: Repeat ultrasound in six months."
    claims = [validate_claim(claim("Repeat ultrasound in six months", "RECOMMENDATION"), source),
              validate_claim(claim("Obtain brain MRI", "RECOMMENDATION"), source)]
    result = compare_validated([fact("Right thigh mass")], claims, source, {})
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert result["counts"]["UNSUPPORTED"] == 1


def test_agreement_requires_source_support_and_unsupported_is_not_conflict():
    source = "FINDINGS: No pneumothorax."
    supported = validate_claim(claim("No pneumothorax", "PERTINENT_NEGATIVE"), source)
    unsupported = validate_claim(claim("Pneumothorax is present"), source)
    result = compare_validated([fact("No pneumothorax", "ABSENT_NEGATED", "NEGATIVE")],
                               [supported, unsupported], source, {})
    assert result["counts"]["AGREEMENT"] == 1
    assert result["counts"]["UNSUPPORTED"] == 1
    assert result["counts"]["CONFLICT"] == 0


def test_truncated_output_is_invalid_and_raw_is_unchanged():
    raw = "**Clinically Important Findings:**\n* Left pleural effusion"
    payload = {"status": "AVAILABLE", "raw_response": raw, "output_tokens": 2000,
               "native_document": {"stage_results": {"PROTECT": {"protected_document": {
                   "protected_text": "FINDINGS: Left pleural effusion."}},
                   "EXTRACT": {"clinical_synthesis": {"canonical_facts": [fact("Left pleural effusion")]}}}}}
    result = revalidate_payload(payload)
    assert result["comparison"]["status"] == "COMPARISON_NOT_VALID"
    assert result["comparison"]["comparison_valid"] is False
    assert result["comparison"]["counts"]["AGREEMENT"] == 0
    assert result["raw_response"] == raw == payload["raw_response"]


def test_model_content_failure_is_distinct_from_missing_input():
    source = "FINDINGS: Liver normal.\nIMPRESSION: Normal."
    raw = "I cannot extract because the report lacks findings."
    claims, metrics = project_and_validate(raw, source)
    assert claims == [] and metrics["model_content_failure"] is True
    payload = {"status": "AVAILABLE", "raw_response": raw, "output_tokens": 35,
               "native_document": {"stage_results": {"PROTECT": {"protected_document": {
                   "protected_text": source}}, "EXTRACT": {"clinical_synthesis": {"canonical_facts": []}}}}}
    assert revalidate_payload(payload)["comparison"]["status"] == "MODEL_CONTENT_FAILURE"
