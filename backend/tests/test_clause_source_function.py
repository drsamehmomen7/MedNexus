"""Synthetic clause-role checks for the R2.0C protected evidence pipeline."""

import pytest

from backend.app.modules.medical_document_intelligence.services.clinical_synthesis import (
    classify_clause,
    synthesize,
)


def output(text, mentions, sections=()):
    findings = []
    for index, (expression, sentence, section, assertion) in enumerate(mentions):
        start = text.index(sentence)
        findings.append({
            "finding_id": f"synthetic-{index}",
            "source_expression": expression,
            "assertion_state": assertion,
            "evidence_anchors": [{"start_offset": start, "end_offset": start + len(sentence),
                                  "quote": sentence, "role": "SUMMARY_ASSERTION" if section == "DIAGNOSTIC_SUMMARY" else "DETAIL_SUPPORT",
                                  "source_section": section}],
        })
    return synthesize({"radiology_findings": findings, "candidate_count": len(findings)},
                      text, [], sections)


@pytest.mark.parametrize("sentence,expression,section,expected", [
    ("Do you have a prior operation?", "operation", "DIAGNOSTIC_SUMMARY", "QUESTIONNAIRE_OR_PROMPT"),
    ("Cystoscopy is recommended.", "Cystoscopy", "DIAGNOSTIC_SUMMARY", "RECOMMENDATION"),
    ("Contrast was instilled through a catheter.", "Contrast", "FINDINGS_DESCRIPTION", "TECHNIQUE_OR_PROCEDURE"),
    ("Dense tissue may reduce screening sensitivity.", "tissue", "DIAGNOSTIC_SUMMARY", "REFERENCE_OR_EDUCATIONAL_TEXT"),
    ("Shape and showing diffusely", "Shape", "FINDINGS_DESCRIPTION", "FRAGMENT_OR_LOW_INFORMATION"),
    ("Peak systolic velocities", "velocities", "FINDINGS_DESCRIPTION", "MEASUREMENT_OR_TECHNICAL_ATTRIBUTE"),
    ("The old fracture was seen previously.", "fracture", "COMPARISON", "COMPARISON_PRIOR_ONLY"),
    ("The fracture has increased in distraction since prior.", "fracture", "COMPARISON", "COMPARISON_CURRENT_FINDING"),
])
def test_local_function_overrides_broad_section(sentence, expression, section, expected):
    anchor = {"start_offset": 0, "end_offset": len(sentence), "quote": sentence}
    assert classify_clause(expression, anchor, section, sentence)[0] == expected


def test_rejected_clause_stays_in_decision_provenance():
    sentence = "Cystoscopy is recommended."
    result = output(sentence, [("Cystoscopy", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert not result["canonical_facts"]
    decision = result["technical_diagnostics"]["candidate_decisions"][0]
    assert decision["source_function"] == "RECOMMENDATION"
    assert decision["rejection_reason"] == "RECOMMENDATION_NOT_FINDING"


def test_short_grounded_abnormality_survives_fragment_gate():
    sentence = "Edema is present."
    result = output(sentence, [("Edema", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert any("edema" in fact["display_label"].casefold() for fact in result["canonical_facts"])


def test_suggestive_of_is_a_hypothesis_and_not_a_present_finding():
    sentence = "Features are suggestive of chronic inflammatory lesions."
    result = output(sentence, [("lesions", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert any(fact["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and fact["assertion_state"] == "UNCERTAIN"
               and fact["hypothesis_status"] == "POSSIBLE" for fact in result["canonical_facts"])


def test_current_comparison_survives_and_prior_only_does_not():
    current = "The left fracture has increased in displacement since prior."
    previous = "The right fracture was present on the prior examination."
    result = output(current + "\n" + previous, [("fracture", current, "COMPARISON", "PRESENT"),
                                                   ("fracture", previous, "COMPARISON", "PRESENT")])
    assert any("left fracture" in fact["display_label"].casefold() for fact in result["canonical_facts"])
    assert not any("right fracture" in fact["display_label"].casefold() for fact in result["canonical_facts"])


def test_measurement_attaches_only_to_its_positive_clause():
    sentence = "No hydronephrosis is seen. A cortical cyst measures 20 x 20 mm."
    result = output(sentence, [("hydronephrosis", sentence, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED"),
                               ("cyst", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    negatives = [fact for fact in result["canonical_facts"] if fact["group"] == "NEGATIVE"]
    positives = [fact for fact in result["canonical_facts"] if fact["group"] != "NEGATIVE"]
    assert negatives and positives
    assert not any(obs.get("measurements") for fact in negatives for obs in fact["observations"])
    assert any(obs.get("measurements") for fact in positives for obs in fact["observations"])


def test_patient_assessment_before_same_line_advice_remains_eligible():
    sentence = "Benign screening study. Routine follow-up is recommended."
    sections = [{"role": "DIAGNOSTIC_SUMMARY", "start": 0, "text": sentence}]
    result = output(sentence, [], sections)
    assert any("benign screening study" in fact["display_label"].casefold()
               for fact in result["canonical_facts"])
    assert not any("follow-up" in fact["display_label"].casefold()
                   for fact in result["canonical_facts"])


def test_generic_numbered_reference_entries_are_not_patient_facts():
    text = "1. Normal\n2. Benign\n3. Suspicious\n4. Malignant"
    sentence = "2. Benign"
    result = output(text, [("Benign", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert not result["canonical_facts"]


def test_numbered_patient_summary_is_not_mistaken_for_reference_list():
    text = "1. Focal stricture involving the left duct.\n2. No leak is seen.\n3. Mild upstream dilatation."
    sentence = "1. Focal stricture involving the left duct."
    result = output(text, [("stricture", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert any("stricture" in fact["display_label"].casefold() and fact["group"] == "KEY"
               for fact in result["canonical_facts"])


def test_lowercase_pdf_continuation_keeps_completing_modifier():
    sentence = "The tissue pattern is\nsymmetric bilaterally."
    result = output(sentence, [("tissue pattern", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert any("symmetric" in fact["display_label"].casefold() for fact in result["canonical_facts"])


def test_broken_noun_and_gerund_clause_does_not_become_a_finding():
    sentence = "Shape and showing diffusely increased echogenicity."
    result = output(sentence, [("echogenicity", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert result["canonical_facts"] == []
    assert result["technical_diagnostics"]["candidate_decisions"][0]["rejection_reason"] == "INCOMPLETE_CLAUSE_FRAGMENT"


def test_opposing_source_assertions_remain_reviewable():
    present = "Vasogenic edema is present."
    absent = "Vasogenic edema is absent."
    result = output(present + "\n" + absent, [("edema", present, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                                               ("edema", absent, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(result["canonical_facts"]) == 2
    assert all("CONFLICTING_SOURCE_ASSERTION" in fact["review_reason"] for fact in result["canonical_facts"])


def test_zero_fact_coverage_gate_still_reports_failure():
    sentence = "The rotator cuff is normal."
    result = output(sentence, [("rotator cuff", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert result["canonical_facts"] == []
    assert result["technical_diagnostics"]["code"] == "SYNTHESIS_COVERAGE_FAILURE"


def test_headed_patient_state_keeps_its_volume_attribute():
    sentence = "Prostate: It is enlarged in size (38cc vol), shape and echotexture."
    result = output(sentence, [], [{"role": "FINDINGS_DESCRIPTION", "start": 0, "text": sentence}])
    fact = result["canonical_facts"][0]
    assert fact["display_label"] == "Enlarged Prostate"
    assert "38cc" in fact["observations"][0]["measurements"]


def test_comparison_change_is_an_attribute_of_current_finding():
    sentence = "This fracture has increased in displacement since the prior study."
    result = output(sentence, [("fracture", sentence, "COMPARISON", "PRESENT")])
    assert result["canonical_facts"][0]["temporal_change"] == "INCREASED"


def test_interval_change_across_pdf_line_wrap_keeps_temporal_attribute():
    sentence = "The fracture has increased displacement from its donor\nsite since 2020."
    result = output(sentence, [("fracture", sentence, "COMPARISON", "PRESENT")])
    assert result["canonical_facts"][0]["temporal_change"] == "INCREASED"


def test_conflicting_patient_specific_types_are_both_reviewable():
    first = "Both structures show Type C composition."
    second = "Type D composition is present."
    result = output(first + "\n" + second,
                    [("composition", first, "FINDINGS_DESCRIPTION", "PRESENT"),
                     ("composition", second, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert len(result["canonical_facts"]) == 2
    assert all("INTERNAL_SOURCE_CONFLICT" in fact["review_reason"] for fact in result["canonical_facts"])


def test_source_recovered_state_merges_measurement_into_matching_summary_fact():
    detail = "Liver: It is enlarged in size measuring 17.5 cm."
    summary = "Hepatomegaly with fatty liver."
    text = detail + "\n" + summary
    sections = [{"role": "FINDINGS_DESCRIPTION", "start": 0, "text": detail},
                {"role": "DIAGNOSTIC_SUMMARY", "start": len(detail) + 1, "text": summary}]
    result = output(text, [("Hepatomegaly", summary, "DIAGNOSTIC_SUMMARY", "PRESENT")], sections)
    assert len(result["canonical_facts"]) == 1
    assert any("17.5 cm" in obs.get("measurements", []) for obs in result["canonical_facts"][0]["observations"])


def test_patient_specific_impression_promotes_validated_secondary_finding():
    detail = "Irregular narrowing/stricture is noted in the left duct."
    summary = "1. Duct stricture disease involving the left segment."
    text = detail + "\n" + summary
    sections = [{"role": "FINDINGS_DESCRIPTION", "start": 0, "text": detail},
                {"role": "DIAGNOSTIC_SUMMARY", "start": len(detail) + 1, "text": summary}]
    result = output(text, [("stricture", detail, "FINDINGS_DESCRIPTION", "PRESENT")], sections)
    assert result["canonical_facts"][0]["group"] == "KEY"
    assert any(a["section_role"] == "DIAGNOSTIC_SUMMARY" for a in result["canonical_facts"][0]["evidence_anchors"])
