"""Synthetic profile contract, coverage, mismatch and persistence checks."""

import hashlib
from dataclasses import replace
from types import SimpleNamespace

import pytest

from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord, build_reviewed_record,
)
from backend.app.modules.medical_document_intelligence.services.clinical_profiles import (
    REGISTRY, ClinicalProfileRegistry, MRI_SHOULDER, US_ABDOMEN, evaluate_profile,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_record_repository import (
    SqliteReviewedClinicalRecordRepository,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)
from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)


def context(modality="ULTRASOUND", region="Abdomen", extent="COMPLETE", family=None):
    modality_context = SimpleNamespace(study_extent=extent, study_family=family)
    clinical = SimpleNamespace(domain_extension=SimpleNamespace(
        modality=modality, authoritative_anatomy=region, body_region=region,
        modality_context=modality_context))
    return SimpleNamespace(identity=SimpleNamespace(healthcare_domain="RADIOLOGY",
                                                  subdomain_or_family=modality),
                           clinical_context=clinical)


def evaluation(text, *, ctx=None, facts=None):
    return evaluate_profile(ctx or context(), text,
                            [{"role": "FINDINGS_DESCRIPTION", "text": text}], facts or [])


def section(result, name):
    return next(item for item in result["coverage"] if item["section_id"] == name)


def element(result, section_id, label):
    return next(item for item in section(result, section_id)["elements"] if item["label"] == label)


def linked_measurement(text, subject, value, anatomy, fact_id="measured-1", laterality=None):
    start = text.index(subject)
    value_start = text.index(value, start)
    end = value_start + len(value)
    fact = {"fact_id": fact_id, "fact_type": "MEASURED_OBSERVATION", "display_label": subject,
            "anatomy": [anatomy], "assertion_state": "PRESENT", "laterality": laterality,
            "observations": [{"measurements": [value]}],
            "evidence_anchors": [{"start_offset": start, "end_offset": end,
                                  "quote": text[start:end], "source_section": "FINDINGS_DESCRIPTION"}]}
    governed = {"measurement_id": "source-measurement-1", "source_text": value,
                "source_fact_id": fact_id, "assignment_state": "LINKED_TO_FACT",
                "evidence_span": {"start_offset": value_start, "end_offset": end, "quote": value}}
    standardized = {"source_fact_id": fact_id,
                    "standardized_measurements": [{"original_text": value}]}
    return fact, governed, standardized


def measured_evaluation(text, measurement, *, ctx=None):
    fact, governed, standardized = measurement
    return evaluate_profile(ctx or context(), text,
                            [{"role": "FINDINGS_DESCRIPTION", "text": text}], [fact],
                            governed_measurements=[governed], standardized_facts=[standardized])


def grounded_fact(text, anatomy, fact_id):
    start = text.index(anatomy)
    return {"fact_id": fact_id, "anatomy": [anatomy], "assertion_state": "PRESENT",
            "evidence_anchors": [{"start_offset": start, "end_offset": start + len(anatomy),
                                  "quote": anatomy, "source_section": "FINDINGS_DESCRIPTION"}]}


def test_registry_exact_identity_version_and_unsupported():
    assert REGISTRY.resolve(context())[0] == US_ABDOMEN
    assert REGISTRY.resolve(context("MRI", "Shoulder"))[0] == MRI_SHOULDER
    assert REGISTRY.get("MRJ_RAD_US_ABDOMEN", "0.1") == US_ABDOMEN
    assert REGISTRY.get("MRJ_RAD_US_ABDOMEN", "0.2") is None
    assert REGISTRY.resolve(context("CT", "Abdomen")) is None
    assert REGISTRY.resolve(context("MRI", "Unknown")) is None
    assert REGISTRY.resolve(context("MRI", "Shoulder", family="MRA")) is None
    ambiguous = context()
    ambiguous.identity.subdomain_or_family = "OTHER"
    assert REGISTRY.resolve(ambiguous) is None
    assert ClinicalProfileRegistry(active_versions={}).resolve(context()) is None
    future = replace(US_ABDOMEN, profile_version="0.2")
    registry = ClinicalProfileRegistry((US_ABDOMEN, future), {US_ABDOMEN.profile_id: "0.1"})
    assert registry.resolve(context())[0].profile_version == "0.1"
    assert registry.get(US_ABDOMEN.profile_id, "0.2") == future


def test_complete_us_documented_normal_limited_and_silent_not_negative():
    result = evaluation("Liver is unremarkable. Pancreas obscured by bowel gas. Right kidney has a cyst.")
    assert result["scope"] == "COMPLETE"
    assert section(result, "liver")["coverage"] == "DOCUMENTED"
    assert section(result, "liver")["assertion"] == "EXPLICITLY_ABSENT_OR_NORMAL"
    assert section(result, "pancreas")["coverage"] == "LIMITED_OR_NOT_VISUALIZED"
    assert section(result, "pancreas")["assertion"] == "INDETERMINATE"
    assert section(result, "right_kidney")["coverage"] == "DOCUMENTED"
    assert section(result, "left_kidney")["coverage"] == "NOT_DOCUMENTED"
    assert section(result, "left_kidney")["assertion"] == "INDETERMINATE"
    assert not result["review_alerts"]


def test_limit_on_adjacent_organ_does_not_spread_across_clause():
    result = evaluation("The liver is unremarkable and the pancreas is obscured by bowel gas.")
    assert section(result, "liver")["coverage"] == "DOCUMENTED"
    assert section(result, "liver")["assertion"] == "EXPLICITLY_ABSENT_OR_NORMAL"
    assert section(result, "pancreas")["coverage"] == "LIMITED_OR_NOT_VISUALIZED"


@pytest.mark.parametrize("extent,expected", [("LIMITED", "LIMITED_OR_FOCUSED"),
                                             (None, "UNKNOWN")])
def test_uncertain_or_focused_us_has_no_false_completeness(extent, expected):
    result = evaluation("Right kidney has a cyst.", ctx=context(extent=extent))
    assert result["scope"] == expected
    assert section(result, "right_kidney")["coverage"] == "DOCUMENTED"
    assert section(result, "pancreas")["coverage"] == "NOT_DOCUMENTED"
    assert section(result, "aorta")["coverage"] == "NOT_APPLICABLE"


def test_renal_scope_is_independent_and_out_of_scope_structures_not_applicable():
    result = evaluation("Left kidney is normal.", ctx=context(region="Kidney", extent="LIMITED"))
    assert result["scope"] == "RETROPERITONEAL_OR_URINARY"
    assert section(result, "left_kidney")["assertion"] == "EXPLICITLY_ABSENT_OR_NORMAL"
    assert section(result, "right_kidney")["coverage"] == "NOT_DOCUMENTED"
    assert section(result, "gallbladder")["coverage"] == "NOT_APPLICABLE"


def test_governed_right_kidney_dimensions_document_profile_length():
    text = "RIGHT UPPER QUADRANT\nRight kidney: Measures 11.3 x 4.1 x 4.9 cm."
    result = measured_evaluation(text, linked_measurement(
        text, "Right kidney", "11.3 x 4.1 x 4.9 cm", "Right kidney", laterality="RIGHT"))
    assert result["scope"] == "LIMITED_OR_FOCUSED"
    assert section(result, "right_kidney")["coverage"] == "DOCUMENTED"
    assert element(result, "right_kidney", "Length")["coverage"] == "DOCUMENTED"
    assert element(result, "right_kidney", "Length")["assertion"] == "INDETERMINATE"


def test_governed_measurement_does_not_cross_laterality():
    text = "Right kidney: Measures 11.3 x 4.1 x 4.9 cm."
    measurement = linked_measurement(text, "Right kidney", "11.3 x 4.1 x 4.9 cm",
                                     "Right kidney", laterality="RIGHT")
    result = measured_evaluation(text, measurement)
    assert element(result, "right_kidney", "Length")["coverage"] == "DOCUMENTED"
    assert element(result, "left_kidney", "Length")["coverage"] == "NOT_DOCUMENTED"
    conflicting = ({**measurement[0], "laterality": "LEFT"}, measurement[1], measurement[2])
    assert element(measured_evaluation(text, conflicting), "right_kidney", "Length")[
        "coverage"] == "NOT_DOCUMENTED"


def test_governed_biliary_duct_value_documents_explicit_diameter_element():
    text = "Biliary duct: Measures 4 mm."
    measurement = linked_measurement(text, "Biliary duct", "4 mm", "Biliary duct")
    assert element(evaluation(text), "biliary_tree", "Duct diameter")["coverage"] == "NOT_DOCUMENTED"
    assert element(measured_evaluation(text, measurement), "biliary_tree", "Duct diameter")[
        "coverage"] == "DOCUMENTED"


def test_governed_shoulder_tear_value_documents_tear_dimensions():
    text = "Supraspinatus tear is 2 cm."
    measurement = linked_measurement(text, "Supraspinatus tear", "2 cm", "Supraspinatus")
    result = measured_evaluation(text, measurement, ctx=context("MRI", "Shoulder", None, "MRI"))
    assert element(result, "rotator_cuff", "Tear dimensions")["coverage"] == "DOCUMENTED"
    assert element(result, "rotator_cuff", "Retraction")["coverage"] == "NOT_DOCUMENTED"


def test_unassigned_or_unverified_measurement_does_not_document_element():
    text = "Right kidney: Measures 11.3 x 4.1 x 4.9 cm."
    fact, governed, standardized = linked_measurement(
        text, "Right kidney", "11.3 x 4.1 x 4.9 cm", "Right kidney", laterality="RIGHT")
    for rejected in ({**governed, "assignment_state": "UNASSIGNED"},
                     {**governed, "evidence_span": {**governed["evidence_span"], "quote": "wrong"}}):
        result = evaluate_profile(context(), text, [{"role": "FINDINGS_DESCRIPTION", "text": text}],
                                  [fact], governed_measurements=[rejected],
                                  standardized_facts=[standardized])
        assert element(result, "right_kidney", "Length")["coverage"] == "NOT_DOCUMENTED"


def test_out_of_scope_measurement_cannot_override_not_applicable():
    text = "RIGHT UPPER QUADRANT\nLeft kidney: Measures 10 cm."
    result = measured_evaluation(text, linked_measurement(
        text, "Left kidney", "10 cm", "Left kidney", laterality="LEFT"))
    assert section(result, "left_kidney")["coverage"] == "NOT_APPLICABLE"
    assert element(result, "left_kidney", "Length")["coverage"] == "NOT_APPLICABLE"


def test_profile_length_remains_not_documented_without_support():
    result = evaluation("Right kidney is unremarkable.")
    assert section(result, "right_kidney")["coverage"] == "DOCUMENTED"
    assert element(result, "right_kidney", "Length")["coverage"] == "NOT_DOCUMENTED"


def test_mri_shoulder_unknown_variant_and_major_sections():
    result = evaluation("Supraspinatus tear. Labral tear. Biceps tendon intact. Marrow edema.",
                        ctx=context("MRI", "Shoulder", None, "MRI"))
    assert result["scope"] == "UNKNOWN"
    for name in ("rotator_cuff", "labrum", "biceps", "bone_marrow"):
        assert section(result, name)["coverage"] == "DOCUMENTED"
    assert section(result, "ac_joint")["coverage"] == "NOT_DOCUMENTED"


def test_mismatch_requires_dominant_grounded_structured_anatomy():
    text = "Supraspinatus tear. Labrum tear. Biceps tear."
    facts = [grounded_fact(text, anatomy, str(index)) for index, anatomy in
             enumerate(("Supraspinatus", "Labrum", "Biceps"))]
    result = evaluation(text, facts=facts)
    assert result["compatibility"] == "POSSIBLE_ANATOMY_MISMATCH"
    assert result["review_alerts"][0]["code"] == "PROFILE_ANATOMY_MISMATCH"
    assert evaluation("Biceps tear.", facts=[grounded_fact("Biceps tear.", "Biceps", "1")])[
        "compatibility"] == "INSUFFICIENT_INFORMATION"


def test_compatible_and_incidental_extra_profile_fact():
    text = "Liver lesion. Gallbladder polyp. Biceps tear."
    facts = [grounded_fact(text, anatomy, str(index)) for index, anatomy in
             enumerate(("Liver", "Gallbladder", "Biceps"))]
    result = evaluation(text, facts=facts)
    assert result["compatibility"] == "COMPATIBLE"
    assert not result["review_alerts"]


def test_shoulder_profile_flags_only_dominant_source_grounded_gross_anatomy():
    text = "Cerebral atrophy. Cerebellar edema. Intracranial mass."
    parts = ("Cerebral", "Cerebellar", "Intracranial")
    facts = [grounded_fact(text, part, str(index)) for index, part in enumerate(parts)]
    mismatch = evaluation(text, ctx=context("MRI", "Shoulder"), facts=facts)
    assert mismatch["compatibility"] == "POSSIBLE_ANATOMY_MISMATCH"
    assert mismatch["review_alerts"][0]["message"] == "Extracted anatomy may not match the exam."
    assert [fact["anatomy"] for fact in facts] == [[part] for part in parts]
    # A terminology-only label cannot become source anatomy.
    unsupported = [{**fact, "anatomy": ["Cerebral"]} for fact in facts]
    assert evaluation(text, ctx=context("MRI", "Shoulder"), facts=unsupported)[
        "compatibility"] == "INSUFFICIENT_INFORMATION"


def test_single_incidental_foreign_region_does_not_raise_major_review():
    text = "Supraspinatus tear. Labrum injury. Incidental cerebral atrophy."
    facts = [grounded_fact(text, part, str(index)) for index, part in
             enumerate(("Supraspinatus", "Labrum", "cerebral"))]
    result = evaluation(text, ctx=context("MRI", "Shoulder"), facts=facts)
    assert result["compatibility"] == "COMPATIBLE"
    assert result["review_alerts"] == []


def _record(schema_version, profile):
    text = "Pancreas is unremarkable."
    protect = {"protected_document": {"report_id": "document", "protected_text": text,
                "integrity_sha256": hashlib.sha256(text.encode()).hexdigest()}}
    extract = {"report_id": "document", "clinical_synthesis": {"canonical_facts": []}}
    standardized = {"report_id": "document", "standardized_facts": []}
    return build_reviewed_record(run_id="journey", document_id="document", reviewed_at="2026-10-11T00:00:00Z",
                                 protect=protect, extract=extract, standardized=standardized,
                                 schema_version=schema_version, profile_evaluation=profile)


def test_profile_provenance_is_version_pinned_and_old_record_readable(tmp_path):
    profile = evaluation("Pancreas is unremarkable.")
    old = _record(1, profile)
    new = _record(2, profile)
    assert "profile_provenance" not in old.to_dict()
    assert new.to_dict()["profile_provenance"] == {
        "profile_id": "MRJ_RAD_US_ABDOMEN", "profile_version": "0.1",
        "scope": "COMPLETE", "evaluation_status": "EVALUATED"}
    assert ReviewedClinicalRecord.from_json(old.to_json()).to_json() == old.to_json()
    repo = SqliteReviewedClinicalRecordRepository(tmp_path / "records.sqlite3")
    repo.save(new)
    repo.close()
    reopened = SqliteReviewedClinicalRecordRepository(tmp_path / "records.sqlite3")
    assert reopened.get_current(new.to_dict()["reviewed_record_id"]).to_json() == new.to_json()
    reopened.close()


def test_journey_standardize_accept_saves_resolved_profile(tmp_path):
    text = ("ULTRASOUND ABDOMEN COMPLETE\nFindings: The liver is normal. "
            "The pancreas is obscured by bowel gas.\nImpression: Limited pancreas assessment.")
    service = DocumentUnderstandingService()
    document = service.text_document(text)
    context_value = service.build_context(document, service.analyze_document(document))
    assert REGISTRY.resolve(context_value)[0].profile_id == US_ABDOMEN.profile_id
    repo = SqliteReviewedClinicalRecordRepository(tmp_path / "records.sqlite3")
    store = JourneyStore(batch_root=tmp_path / "batches", reviewed_records=repo)
    run = store.create_run("single")
    item = JourneyDocument(document_id="a" * 32, original_filename="synthetic.txt",
                           order=0, source_type="txt", document=document, context=context_value)
    item.stage_status[JourneyStage.PROTECT] = StageStatus.COMPLETE
    item.stage_status[JourneyStage.EXTRACT] = StageStatus.COMPLETE
    item.stage_results[JourneyStage.PROTECT] = {"protected_document": {
        "report_id": item.document_id, "protected_text": text,
        "integrity_sha256": hashlib.sha256(text.encode()).hexdigest()}}
    item.stage_results[JourneyStage.EXTRACT] = {"report_id": item.document_id,
        "clinical_synthesis": {"canonical_facts": []}}
    run.documents.append(item)

    class Standardizer:
        def standardize(self, extract, context):
            return {"report_id": item.document_id, "state": "COMPLETE", "standardized_facts": []}

    store.standardize_document(run.run_id, item.document_id, Standardizer())
    evaluation_result = item.stage_results[JourneyStage.STANDARDIZE]["profile_evaluation"]
    assert evaluation_result["profile_id"] == US_ABDOMEN.profile_id
    assert section(evaluation_result, "pancreas")["coverage"] == "LIMITED_OR_NOT_VISUALIZED"
    store.accept_clinical_review(run.run_id, item.document_id)
    saved = repo.get_current(item.reviewed_record_id).to_dict()
    assert saved["schema_version"] == 3
    assert saved["profile_coverage"] is not None
    assert saved["profile_provenance"]["profile_version"] == "0.1"
    assert saved["profile_provenance"]["scope"] == "COMPLETE"
    repo.close()
