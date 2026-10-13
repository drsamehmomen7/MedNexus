"""Cross-domain, invented clauses for Phase D.2 evidence boundaries."""
import hashlib
from types import SimpleNamespace

from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord, build_reviewed_record,
)
from backend.app.modules.medical_document_intelligence.services.clinical_profiles import evaluate_profile
from backend.app.modules.medical_document_intelligence.services.clinical_synthesis import (
    _addendum_authority, _governed_measurement_ledger, _source_fact,
    _source_measured_observations, _source_nonfinding_statements, classify_clause,
    synthesize,
)


def section(text, role, start=0):
    return {"role": role, "start": start, "end": start + len(text), "text": text}


def source_fact(text, phrase, label):
    start = text.index(phrase)
    fact = _source_fact(text, start, start + len(phrase), label, "FINDING", "KEY")
    fact["fact_id"] = "canonical-1"
    return fact


def test_resolving_addendum_preserves_prior_evidence_and_updates_current_status():
    earlier = "The left femoral component may have shifted."
    later = "ADDENDUM\nPrior films show the left femoral component appears stable and unchanged."
    text = earlier + "\n" + later
    old = source_fact(text, earlier, "Left femoral component may have shifted")
    facts = [old]
    _addendum_authority(text, [section(text, "DIAGNOSTIC_SUMMARY")], facts)
    assert old["temporal_status"] == "SUPERSEDED"
    assert old["group"] == "HISTORICAL"
    assert old["evidence_anchors"][0]["quote"] == earlier
    assert facts[-1]["temporal_status"] == "CURRENT"
    assert "stable and unchanged" in facts[-1]["display_label"]
    assert facts[-1]["evidence_anchors"][0]["quote"] in text


def test_unresolved_addendum_conflict_requires_review_without_supersession():
    earlier = "The left renal lesion is a simple cyst."
    text = earlier + "\nADDENDUM\nThe left renal lesion may represent another structure."
    old = source_fact(text, earlier, "Left renal lesion is a simple cyst")
    facts = [old]
    _addendum_authority(text, [section(text, "DIAGNOSTIC_SUMMARY")], facts)
    assert len(facts) == 1
    assert old.get("temporal_status") is None
    assert "ADDENDUM_UNRESOLVED_CONFLICT" in old["review_reason"]


def test_ordinary_later_sentence_has_no_addendum_authority():
    text = "The left femoral component may have shifted.\nPrior films show the component appears stable and unchanged."
    old = source_fact(text, text.splitlines()[0], "Left femoral component may have shifted")
    facts = [old]
    _addendum_authority(text, [section(text, "DIAGNOSTIC_SUMMARY")], facts)
    assert facts == [old]
    assert old.get("temporal_status") is None


def test_explicit_primary_negative_and_incidental_positive_coexist():
    first = "This examination is negative for venous thrombosis."
    second = "A superficial calf nodule is present."
    text = first + "\n" + second
    findings = []
    for index, (sentence, expression, assertion) in enumerate(((first, "thrombosis", "ABSENT_NEGATED"),
                                                                  (second, "nodule", "PRESENT")), 1):
        start = text.index(sentence)
        findings.append({"finding_id": f"finding-{index}", "source_expression": expression,
                         "assertion_state": assertion,
                         "evidence_anchors": [{"start_offset": start, "end_offset": start + len(sentence),
                                               "quote": sentence, "role": "SUMMARY_ASSERTION",
                                               "source_section": "DIAGNOSTIC_SUMMARY"}]})
    output = synthesize({"radiology_findings": findings, "candidate_count": 2}, text, [],
                        [section(text, "DIAGNOSTIC_SUMMARY")])
    negative = next(f for f in output["canonical_facts"] if f["group"] == "NEGATIVE")
    assert negative["display_label"] == "No venous thrombosis"
    assert negative["salience"] == "PRIMARY"
    assert output["clinical_synthesis"].startswith("No venous thrombosis.")
    assert any(f["assertion_state"] == "PRESENT" for f in output["canonical_facts"])


def test_secondary_negative_is_not_automatically_primary():
    text = "No pleural effusion is seen."
    fact = source_fact(text, text, "No pleural effusion")
    fact["group"] = "NEGATIVE"
    assert "negative for" not in fact["evidence_anchors"][0]["quote"].lower()


def test_acquisition_action_is_not_patient_finding_but_adjacent_observation_is():
    text = "A view of a posterior shadow was performed; a pulmonary nodule is present."
    first = {"start_offset": 0, "end_offset": text.index(";"), "quote": text[:text.index(";")]}
    second_start = text.index("a pulmonary")
    second = {"start_offset": second_start, "end_offset": len(text), "quote": text[second_start:]}
    assert classify_clause("shadow", first, "FINDINGS_DESCRIPTION", text)[0] == "TECHNIQUE_OR_PROCEDURE"
    assert classify_clause("nodule", second, "FINDINGS_DESCRIPTION", text)[0] == "PATIENT_FINDING"


def test_final_assessment_and_recommendation_keep_distinct_non_disease_roles():
    text = "IMPRESSION: CLASS CATEGORY 3, benign assessment.\nConsultation should be considered."
    facts = []
    _source_nonfinding_statements(text, [section(text, "DIAGNOSTIC_SUMMARY")], facts)
    assert {f["group"] for f in facts} == {"ASSESSMENT", "RECOMMENDATION"}
    assert all(f["assertion_state"] == "NOT_APPLICABLE" for f in facts)
    assert all(f["evidence_anchors"][0]["quote"] in text for f in facts)


def test_headed_duct_and_sided_organ_dimensions_get_exact_owners():
    text = "Common duct: Measures 4 mm. Normal.\nRight renal unit: Measures 11.3 x 4.1 x 4.9 cm. Normal."
    facts = []
    _source_measured_observations(text, [section(text, "FINDINGS_DESCRIPTION")], facts)
    assert len(facts) == 2
    assert facts[1]["laterality"] == "RIGHT"
    ledger = _governed_measurement_ledger(text, [section(text, "FINDINGS_DESCRIPTION")], facts)
    assert [m["assignment_state"] for m in ledger] == ["LINKED_TO_FACT", "LINKED_TO_FACT"]


def test_same_clause_lesion_size_has_neutral_evidence_owner():
    text = "There is a 1.3 cm diameter round area of low attenuation in the lower right lobe."
    facts = []
    _source_measured_observations(text, [section(text, "FINDINGS_DESCRIPTION")], facts)
    assert len(facts) == 1
    assert facts[0]["fact_type"] == "MEASURED_OBSERVATION"
    assert facts[0]["group"] == "MEASUREMENT"
    assert facts[0]["observations"][0]["measurements"] == ["1.3 cm"]


def test_ambiguous_measurement_remains_unassigned():
    text = "Two structures measure 4 mm and 5 mm respectively."
    facts = []
    _source_measured_observations(text, [section(text, "FINDINGS_DESCRIPTION")], facts)
    assert facts == []
    ledger = _governed_measurement_ledger(text, [section(text, "FINDINGS_DESCRIPTION")], facts)
    assert all(m["assignment_state"] == "UNASSIGNED_REVIEW" for m in ledger)


def _profile_context(extent="UNKNOWN", region="Abdomen"):
    domain = SimpleNamespace(modality="ULTRASOUND", authoritative_anatomy=region,
                             body_region=region, modality_context=SimpleNamespace(
                                 study_extent=extent, study_family=None))
    return SimpleNamespace(identity=SimpleNamespace(healthcare_domain="RADIOLOGY",
                                                  subdomain_or_family="ULTRASOUND"),
                           clinical_context=SimpleNamespace(domain_extension=domain))


def test_explicit_ruq_scope_excludes_spleen_and_left_kidney():
    text = "ULTRASOUND RIGHT UPPER QUADRANT\nFINDINGS: Liver and right kidney are normal."
    result = evaluate_profile(_profile_context(), text, [section(text, "FINDINGS_DESCRIPTION")], [])
    by_id = {item["section_id"]: item["coverage"] for item in result["coverage"]}
    assert result["scope"] == "LIMITED_OR_FOCUSED"
    assert by_id["spleen"] == by_id["left_kidney"] == "NOT_APPLICABLE"
    assert by_id["right_kidney"] == "DOCUMENTED"


def test_complete_renal_and_unknown_scopes_stay_distinct():
    text = "Liver is normal."
    complete = evaluate_profile(_profile_context("COMPLETE"), text,
                                [section(text, "FINDINGS_DESCRIPTION")], [])
    renal = evaluate_profile(_profile_context("LIMITED", "Kidney"), text,
                             [section(text, "FINDINGS_DESCRIPTION")], [])
    unknown = evaluate_profile(_profile_context(), text,
                               [section(text, "FINDINGS_DESCRIPTION")], [])
    assert complete["scope"] == "COMPLETE"
    assert renal["scope"] == "RETROPERITONEAL_OR_URINARY"
    assert unknown["scope"] == "UNKNOWN"


def test_historical_and_current_source_provenance_survive_record_v1_and_v2():
    text = "Earlier lesion may be complex.\nADDENDUM\nThis lesion is definitely a simple cyst."
    earlier = source_fact(text, "Earlier lesion may be complex.", "Earlier lesion may be complex")
    earlier["temporal_status"] = "SUPERSEDED"
    earlier["group"] = "HISTORICAL"
    current = source_fact(text, "This lesion is definitely a simple cyst.",
                          "This lesion is definitely a simple cyst")
    current["fact_id"] = "canonical-2"
    current["temporal_status"] = "CURRENT"
    protect = {"protected_document": {"report_id": "document", "protected_text": text,
               "integrity_sha256": hashlib.sha256(text.encode()).hexdigest()}}
    extract = {"report_id": "document", "clinical_synthesis": {
        "canonical_facts": [earlier, current], "clinical_synthesis": current["display_label"]}}
    standardized = {"report_id": "document", "standardized_facts": []}
    for version in (1, 2):
        record = build_reviewed_record(run_id="journey", document_id="document",
                                       reviewed_at="2026-10-13T00:00:00Z", protect=protect,
                                       extract=extract, standardized=standardized,
                                       schema_version=version)
        reopened = ReviewedClinicalRecord.from_json(record.to_json()).to_dict()
        assert [f["temporal_status"] for f in reopened["canonical_facts"]] == ["SUPERSEDED", "CURRENT"]
        assert reopened["canonical_facts"][0]["evidence_anchors"][0]["quote"] in text
