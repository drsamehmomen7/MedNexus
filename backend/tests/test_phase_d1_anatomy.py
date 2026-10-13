"""Synthetic, model-independent safety tests for source-grounded anatomy."""

import copy

import pytest

from backend.app.modules.medical_document_intelligence.services.clinical_synthesis import synthesize
from backend.app.modules.medical_document_intelligence.services.clinical_standardization import (
    ClinicalStandardizationService, TerminologyCandidate,
)
from backend.tests.test_clinical_standardization import Provider, context


def section(text, role, start=0):
    return {"section_id": role.lower(), "role": role, "start": start,
            "end": start + len(text), "text": text}


def observation(text, expression, anatomy=()):
    start = text.index(expression)
    anchor = {"start_offset": 0, "end_offset": len(text), "quote": text,
              "role": "DETAIL_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}
    candidates = [{"candidate_id": f"findings:{i}", "candidate_type": "Anatomy",
                   "source_text": part, "source_start": text.index(part),
                   "source_end": text.index(part) + len(part),
                   "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}
                  for i, part in enumerate(anatomy)]
    result = {"radiology_findings": [{"finding_id": "finding-1", "source_expression": expression,
                                     "assertion_state": "PRESENT", "evidence_anchors": [anchor]}],
              "candidate_count": len(candidates) + 1}
    return synthesize(result, text, candidates, [section(text, "FINDINGS_DESCRIPTION")])


@pytest.mark.parametrize("text,anatomy", [
    ("Mild fatty atrophy of the supraspinatus muscle.", ("supraspinatus", "muscle")),
    ("Mild cerebral atrophy.", ("cerebral",)),
    ("Mild renal cortical atrophy.", ("renal cortical",)),
    ("Mild skeletal muscle atrophy of the thigh.", ("skeletal muscle", "thigh")),
])
def test_nominal_atrophy_preserves_exact_source_anatomy(text, anatomy):
    output = observation(text, "atrophy", anatomy)
    fact = next(f for f in output["canonical_facts"] if "atrophy" in f["display_label"].lower())
    assert fact["display_label"] == text[:-1]
    assert fact["assertion_state"] == "PRESENT"
    assert set(anatomy) <= set(fact["anatomy"])
    anchor = fact["evidence_anchors"][0]
    assert text[anchor["start_offset"]:anchor["end_offset"]] == anchor["quote"]
    assert ("cerebral" in fact["display_label"].lower()) == ("cerebral" in text.lower())


def test_measured_abnormal_noun_phrase_is_recovered_from_independent_summary():
    detail = "Findings: A full-thickness supraspinatus tendon tear measures 12 mm with 8 mm retraction."
    summary = "Impression: Full-thickness supraspinatus tear with mild retraction."
    text = detail + "\n" + summary
    modifier_start = text.index("full-thickness")
    result = {"radiology_findings": [{"finding_id": "finding-1", "source_expression": "full-thickness",
              "assertion_state": "PRESENT", "evidence_anchors": [{
                  "start_offset": 0, "end_offset": len(detail), "quote": detail,
                  "role": "DETAIL_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}]}],
              "candidate_count": 1}
    candidates = [{"candidate_id": "findings:1", "candidate_type": "Observation",
                   "source_text": "full-thickness", "source_start": modifier_start,
                   "source_end": modifier_start + len("full-thickness"),
                   "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}]
    output = synthesize(result, text, candidates, [
        section(detail, "FINDINGS_DESCRIPTION"),
        section(summary, "DIAGNOSTIC_SUMMARY", len(detail) + 1)])
    tear = next(f for f in output["canonical_facts"] if "tear" in f["display_label"].lower())
    assert tear["display_label"] == "Full-thickness supraspinatus tear"
    assert tear["group"] == "KEY"
    assert tear["anatomy"] == ["supraspinatus tendon"]
    assert {"12 mm", "8 mm"} <= set(tear["observations"][0]["measurements"])
    assert {a["section_role"] for a in tear["evidence_anchors"]} == {
        "FINDINGS_DESCRIPTION", "DIAGNOSTIC_SUMMARY"}
    assert not any(f["display_label"] == "full-thickness" for f in output["canonical_facts"])


@pytest.mark.parametrize("text,expression,anatomy", [
    ("Mild renal cortical mass.", "mass", ("renal cortical",)),
    ("Mild pleural effusion.", "effusion", ("pleural",)),
    ("Mild marrow edema.", "edema", ("marrow",)),
])
def test_shared_abnormality_terms_do_not_replace_anatomy(text, expression, anatomy):
    output = observation(text, expression, anatomy)
    assert any(anatomy[0] in f["display_label"].lower() for f in output["canonical_facts"])
    assert all("cerebral" not in f["display_label"].lower() for f in output["canonical_facts"])


def test_standardize_enriches_but_cannot_replace_source_anatomy_or_label():
    output = observation("Mild fatty atrophy of the supraspinatus muscle.", "atrophy",
                         ("supraspinatus", "muscle"))
    fact = output["canonical_facts"][0]
    extract = {"report_id": "synthetic", "state": "NEEDS_REVIEW",
               "clinical_synthesis": output}
    before = copy.deepcopy(extract)
    mapped = ClinicalStandardizationService(
        concept_provider=Provider("RADLEX_CURRENT", {"atrophy": [
            TerminologyCandidate("RID5046", "Atrophy", "EXACT_LABEL")]}),
        anatomy_provider=Provider("RADLEX_CURRENT"),
        procedure_provider=Provider("LOINC_RSNA_2_82")).standardize(extract, context())
    assert extract == before
    assert fact["display_label"] == "Mild fatty atrophy of the supraspinatus muscle"
    assert {"supraspinatus", "muscle"} <= set(fact["anatomy"])
    assert mapped["standardized_facts"][0]["concept_mappings"][0]["source_text"] == fact["display_label"]


def test_source_section_heading_is_not_part_of_clinical_fact_label():
    output = observation("Findings: Cerebral atrophy is present.", "atrophy", ("Cerebral",))
    assert output["canonical_facts"][0]["display_label"] == "Cerebral atrophy"
