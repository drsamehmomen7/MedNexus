import json
from dataclasses import asdict, replace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology.semantic_roles import (
    RadiologyEvidenceEligibility,
    RadiologySemanticRole,
    RadiologySemanticRoleResolver,
    adapt_radiology_semantic_role,
)
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology import (
    RadiologyReasoner,
    RadiologyUnderstandingDecision,
)
from backend.app.modules.medical_document_intelligence.understanding.context_models import (
    CTAcquisitionFeature,
    CTClinicalContext,
    CTStudyFamily,
    FluoroscopyClinicalContext,
    FluoroscopyStudyFamily,
    MammographyAcquisitionContext,
    MammographyClinicalContext,
    MammographyStudyPurpose,
    MRIClinicalContext,
    MRISequenceFamily,
    MRIStudyFamily,
    NuclearMedicineClinicalContext,
    NuclearMedicineStudyFamily,
    OtherRadiologyClinicalContext,
    RadiologyOtherReason,
    StudyLaterality,
    UltrasoundClinicalContext,
    UltrasoundSpecialization,
    UltrasoundStudyExtent,
    VascularContext,
    XRayClinicalContext,
    XRaySourceType,
)
from backend.app.modules.medical_document_intelligence.understanding.models import (
    DocumentDomain,
    DocumentNature,
    DocumentSubtype,
    RadiologySubdomain,
    SemanticRegionRole,
    canonical_radiology_subdomain_from_legacy,
)
from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)
from backend.app.modules.medical_document_intelligence.understanding.section_detector import (
    SectionDetector,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model.runtime import (
    build_active_reference_registry,
)


RADIOLOGY_REPORT = """RADIOLOGY REPORT
EXAMINATION: CT chest
TECHNIQUE: Current CT images were obtained with contrast.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RADIOLOGIST: Electronically authenticated.
"""


def test_frozen_radiology_subdomains_are_exact_and_exclude_doppler():
    assert tuple(item.value for item in RadiologySubdomain) == (
        "CT", "MRI", "X_RAY", "ULTRASOUND", "MAMMOGRAPHY",
        "NUCLEAR_MEDICINE", "FLUOROSCOPY", "OTHER",
    )
    assert "DOPPLER" not in RadiologySubdomain.__members__


@pytest.mark.parametrize(("legacy", "canonical"), (
    (DocumentSubtype.CT, RadiologySubdomain.CT),
    (DocumentSubtype.MRI, RadiologySubdomain.MRI),
    (DocumentSubtype.X_RAY, RadiologySubdomain.X_RAY),
    (DocumentSubtype.ULTRASOUND, RadiologySubdomain.ULTRASOUND),
    (DocumentSubtype.DOPPLER, RadiologySubdomain.ULTRASOUND),
    (DocumentSubtype.MAMMOGRAPHY, RadiologySubdomain.MAMMOGRAPHY),
    (DocumentSubtype.NUCLEAR_MEDICINE, RadiologySubdomain.NUCLEAR_MEDICINE),
))
def test_legacy_radiology_subtypes_map_explicitly(legacy, canonical):
    assert canonical_radiology_subdomain_from_legacy(
        DocumentDomain.RADIOLOGY, legacy
    ) is canonical


def test_radiology_other_is_distinct_from_unknown_domain():
    assert canonical_radiology_subdomain_from_legacy(
        DocumentDomain.RADIOLOGY, DocumentSubtype.UNKNOWN
    ) is RadiologySubdomain.OTHER
    assert canonical_radiology_subdomain_from_legacy(
        DocumentDomain.UNKNOWN, DocumentSubtype.UNKNOWN
    ) is None


def test_frozen_semantic_region_roles_are_exact():
    assert tuple(item.value for item in SemanticRegionRole) == (
        "STUDY_OR_EVENT_IDENTITY",
        "CLINICAL_OR_REPORTING_INDICATION",
        "TECHNIQUE_OR_ACQUISITION",
        "OBSERVATION_NARRATIVE",
        "CONCLUSION_OR_STATUS",
        "COMPARISON_OR_PRIOR_CONTEXT",
        "RECOMMENDATION_OR_FUTURE_ACTION",
        "PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION",
    )


@pytest.mark.parametrize(("legacy", "canonical"), (
    (RadiologySemanticRole.PERFORMED_STUDY, SemanticRegionRole.STUDY_OR_EVENT_IDENTITY),
    (RadiologySemanticRole.CLINICAL_INDICATION, SemanticRegionRole.CLINICAL_OR_REPORTING_INDICATION),
    (RadiologySemanticRole.TECHNIQUE_ACQUISITION, SemanticRegionRole.TECHNIQUE_OR_ACQUISITION),
    (RadiologySemanticRole.FINDINGS_CONTEXT, SemanticRegionRole.OBSERVATION_NARRATIVE),
    (RadiologySemanticRole.IMPRESSION_CONTEXT, SemanticRegionRole.CONCLUSION_OR_STATUS),
    (RadiologySemanticRole.COMPARISON_STUDY, SemanticRegionRole.COMPARISON_OR_PRIOR_CONTEXT),
    (RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY, SemanticRegionRole.RECOMMENDATION_OR_FUTURE_ACTION),
    (RadiologySemanticRole.PROFESSIONAL_ATTRIBUTION, SemanticRegionRole.PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION),
))
def test_existing_authoritative_radiology_roles_map_once(legacy, canonical):
    adaptation = adapt_radiology_semantic_role(legacy)
    assert adaptation.canonical_role is canonical
    assert adaptation.authoritative is True


def test_historical_and_unresolved_role_adaptation_preserves_semantics():
    historical = adapt_radiology_semantic_role(RadiologySemanticRole.HISTORICAL_STUDY)
    unresolved = adapt_radiology_semantic_role(RadiologySemanticRole.UNKNOWN_OR_UNRESOLVED)
    assert historical.canonical_role is SemanticRegionRole.COMPARISON_OR_PRIOR_CONTEXT
    assert historical.qualifier == "HISTORICAL"
    assert unresolved.canonical_role is None
    assert unresolved.authoritative is False
    assert unresolved.qualifier == "UNRESOLVED"


def test_canonical_region_serialization_preserves_offsets_and_compatibility():
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    payload = json.loads(json.dumps(service.build_context(document, result).to_dict()))
    findings = next(item for item in payload["structure"] if item["section_id"] == "findings")

    assert findings["canonical_role"] == "OBSERVATION_NARRATIVE"
    assert RADIOLOGY_REPORT[findings["start"]:findings["end"]].startswith("FINDINGS:")
    assert findings["evidence_concept_ids"]
    assert findings["provenance"]
    assert findings["semantic_role"] == "Findings"
    assert payload["identity"]["document_subtype"] == "CT"
    assert payload["identity"]["subdomain_or_family"] == "CT"
    assert payload["identity"]["document_review_required"] is False
    assert payload["clinical_context"]["modality"] == "CT"


def test_service_projects_other_and_review_without_changing_legacy_results():
    service = DocumentUnderstandingService()
    radiology = """RADIOLOGY REPORT
TECHNIQUE: CT and MRI images were obtained.
FINDINGS: Combined appearances are documented.
IMPRESSION: Multimodality assessment.
"""
    radiology_result = service.analyze_text(radiology)
    radiology_context = service.build_context(
        service.text_document(radiology), radiology_result
    )
    unknown_document = service.text_document("General administrative healthcare memo.")
    unknown_result = service.analyze_document(unknown_document)
    unknown_context = service.build_context(unknown_document, unknown_result)

    assert radiology_result.domain is DocumentDomain.RADIOLOGY
    assert radiology_result.document_subtype is DocumentSubtype.UNKNOWN
    assert radiology_context.identity.document_subtype is None
    assert radiology_context.identity.subdomain_or_family == "OTHER"
    assert unknown_result.domain is DocumentDomain.UNKNOWN
    assert unknown_context.identity.subdomain_or_family is None
    assert unknown_context.identity.document_review_required is True


def test_understanding_api_retains_legacy_fields_with_additive_canonical_contract():
    payload = TestClient(app).post(
        "/api/v1/understanding/analyze-text", json={"text": RADIOLOGY_REPORT}
    ).json()
    assert payload["domain"] == "RADIOLOGY"
    assert payload["document_subtype"] == "CT"
    assert payload["document_context"]["clinical_context"]["modality"] == "CT"
    assert payload["document_context"]["identity"]["subdomain_or_family"] == "CT"
    assert payload["document_context"]["identity"]["document_review_required"] is False
    assert "radiology_decision" not in payload


def test_understanding_api_serializes_frozen_canonical_product_contract():
    payload = TestClient(app).post(
        "/api/v1/understanding/analyze-text", json={"text": RADIOLOGY_REPORT}
    ).json()
    context = payload["document_context"]

    assert {
        "domain": "RADIOLOGY",
        "subdomain_or_family": "CT",
        "document_type": "RADIOLOGY_REPORT",
        "language": "ENGLISH",
        "document_review_required": False,
    }.items() <= context["identity"].items()
    assert context["light_context"] == {
        "domain_type": "RADIOLOGY",
        "family_context": {
            "subdomain": "CT",
            "body_region": "Chest",
            "contrast": "WITH_CONTRAST",
            "study_family": "CT",
            "acquisition_summary": [],
        },
    }
    assert context["semantic_regions"]
    assert all({"role", "start", "end", "confidence", "provenance"} <= item.keys()
               for item in context["semantic_regions"])
    assert context["semantic_relationships"] == []
    assert {
        "protect_ready": True,
        "extract_ready": True,
        "document_review_required": False,
    }.items() <= context["processing_context"].items()
    assert payload["recognition_explanations"]
    assert "radiology_decision" not in payload


def test_canonical_other_and_unknown_api_contexts_remain_distinct():
    client = TestClient(app)
    other = client.post(
        "/api/v1/understanding/analyze-text",
        json={"text": """RADIOLOGY REPORT
TECHNIQUE: CT and MRI images were obtained.
FINDINGS: Combined appearances are documented.
IMPRESSION: Multimodality assessment.
"""},
    ).json()["document_context"]
    unknown = client.post(
        "/api/v1/understanding/analyze-text",
        json={"text": "General administrative healthcare memo."},
    ).json()["document_context"]

    assert other["identity"]["domain"] == "RADIOLOGY"
    assert other["identity"]["subdomain_or_family"] == "OTHER"
    assert other["light_context"]["family_context"]["subdomain"] == "OTHER"
    assert other["processing_context"]["document_review_required"] is True
    assert other["processing_context"]["protect_ready"] is True
    assert other["processing_context"]["extract_ready"] is False
    assert unknown["identity"]["domain"] == "UNKNOWN"
    assert unknown["identity"]["subdomain_or_family"] is None
    assert unknown["light_context"]["family_context"] is None
    assert unknown["processing_context"]["protect_ready"] is True
    assert unknown["processing_context"]["extract_ready"] is False


def test_canonical_doppler_api_context_is_ultrasound_with_legacy_alias_only():
    payload = TestClient(app).post(
        "/api/v1/understanding/analyze-text",
        json={"text": """RADIOLOGY REPORT
TECHNIQUE: Doppler ultrasound of the lower extremity
FINDINGS: Normal vascular survey.
IMPRESSION: Completed examination.
"""},
    ).json()

    assert payload["document_subtype"] == "DOPPLER"
    assert payload["document_context"]["clinical_context"]["modality"] == "DOPPLER"
    family = payload["document_context"]["light_context"]["family_context"]
    assert family["subdomain"] == "ULTRASOUND"
    assert family["specialization"] == "DOPPLER"


def test_canonical_light_context_does_not_publish_extract_level_fields():
    decisions = (
        _radiology_decision(
            "FFD mammogram Breast - bilateral Screening", "Current images obtained."
        ),
        _radiology_decision("PET+CT Whole body Views", "Current images obtained."),
        _radiology_decision(
            "RF Gastrointestinal tract upper Views W barium contrast PO",
            "Current images obtained.",
        ),
    )
    service = DocumentUnderstandingService()
    forbidden = {
        "birads_category", "density_category", "lesion_diagnosis", "tracer_name",
        "tracer_dose", "suv", "uptake_value", "diagnosis", "measurements",
        "recommendation_text", "exact_values",
    }

    def serialized_keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(serialized_keys(item) for item in value.values()))
        if isinstance(value, (list, tuple)):
            return set().union(*(serialized_keys(item) for item in value), set())
        return set()

    for decision in decisions:
        light = asdict(service.build_context(
            service.text_document(RADIOLOGY_REPORT),
            replace(
                service.analyze_text(RADIOLOGY_REPORT),
                document_subtype=decision.compatibility_subtype,
                radiology_decision=decision,
            ),
        ).light_context)
        assert forbidden.isdisjoint(serialized_keys(light))


def test_complete_radiology_understand_operation_executes_reasoner_once(monkeypatch):
    original = RadiologyReasoner.assess.__func__
    calls = []

    def counted(cls, text, sections):
        calls.append((text, sections))
        return original(cls, text, sections)

    monkeypatch.setattr(RadiologyReasoner, "assess", classmethod(counted))
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    context = service.build_context(document, result)

    assert len(calls) == 1
    assert isinstance(result.radiology_decision, RadiologyUnderstandingDecision)
    assert context.identity.subdomain_or_family == "CT"


def test_context_builder_serializes_supplied_decision_without_reasoning(monkeypatch):
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    assert decision is not None

    def forbidden(*args, **kwargs):
        raise AssertionError("ContextBuilder must not invoke RadiologyReasoner.")

    monkeypatch.setattr(RadiologyReasoner, "assess", forbidden)
    context = service.build_context(document, result)

    assert context.identity.subdomain_or_family == decision.subdomain.value
    assert context.clinical_context.examination == decision.examination
    assert context.clinical_context.domain_extension.modality_context is decision.modality_context


def test_context_semantics_cannot_change_from_post_decision_raw_input_changes():
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    original = service.build_context(document, result)
    altered_raw_inputs = replace(result, sections=(), evidence=())
    rebuilt = service.build_context(document, altered_raw_inputs)

    assert rebuilt.structure == original.structure
    assert rebuilt.clinical_context == original.clinical_context


def test_canonical_and_legacy_subtypes_share_one_transported_decision():
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    context = service.build_context(document, result)

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.compatibility_subtype is DocumentSubtype.CT
    assert result.document_subtype is decision.compatibility_subtype
    assert context.identity.subdomain_or_family == decision.subdomain.value
    assert result.recognition_explanations is decision.explanations


def test_doppler_is_one_ultrasound_decision_with_legacy_projection():
    text = """RADIOLOGY REPORT
TECHNIQUE: Doppler ultrasound of the lower extremity
FINDINGS: Normal vascular survey.
IMPRESSION: Completed examination.
"""
    service = DocumentUnderstandingService()
    document = service.text_document(text)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    context = service.build_context(document, result)

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.ULTRASOUND
    assert decision.modality_variant == "DOPPLER"
    assert decision.compatibility_subtype is DocumentSubtype.DOPPLER
    assert result.document_subtype is DocumentSubtype.DOPPLER
    assert context.identity.subdomain_or_family == "ULTRASOUND"
    assert context.clinical_context.modality == "DOPPLER"
    assert context.clinical_context.domain_extension.modality == "ULTRASOUND"


def test_authoritative_semantic_region_trace_survives_complete_pipeline():
    service = DocumentUnderstandingService()
    document = service.text_document(RADIOLOGY_REPORT)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    context = service.build_context(document, result)
    assert decision is not None

    decided = next(item for item in decision.semantic_regions if item.section_id == "findings")
    serialized = next(item for item in context.structure if item.section_id == "findings")
    assert (serialized.start, serialized.end) == (decided.start, decided.end)
    assert serialized.canonical_role is decided.canonical_role
    assert serialized.evidence_concept_ids == decided.evidence_concept_ids
    assert serialized.provenance == decided.provenance


def _radiology_decision(examination: str, technique: str, findings: str = "Current appearances."):
    text = f"""RADIOLOGY REPORT
EXAMINATION: {examination}
TECHNIQUE: {technique}
FINDINGS: {findings}
IMPRESSION: No acute process.
RADIOLOGIST: Electronically authenticated.
"""
    result = DocumentUnderstandingService().analyze_text(text)
    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.radiology_decision is not None
    return result.radiology_decision


def test_cta_family_and_acquisition_are_governed_by_current_procedure_composition():
    decision = _radiology_decision(
        "CTA Chest vessels W contrast IV",
        "Current CT images obtained with multiplanar reconstruction.",
    )

    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.body_regions == ("CHEST",)
    assert isinstance(decision.modality_context, CTClinicalContext)
    assert decision.modality_context.study_family is CTStudyFamily.CTA
    assert decision.modality_context.acquisition_summary == (
        CTAcquisitionFeature.ANGIOGRAPHIC,
        CTAcquisitionFeature.MULTIPLANAR_RECONSTRUCTION,
    )
    assert decision.examination == "CTA Chest"


def test_reference_derived_cta_token_preserves_offsets_and_bounded_current_context():
    text = """RADIOLOGY REPORT
EXAMINATION: CTA abdomen and pelvis
TECHNIQUE: Current images were obtained after contrast administration.
FINDINGS: Current appearances are documented.
IMPRESSION: No acute process.
RADIOLOGIST: Electronically authenticated.
"""
    service = DocumentUnderstandingService()
    document = service.text_document(text)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    context = service.build_context(document, result)

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.body_regions == ("ABDOMEN", "PELVIS")
    assert decision.authoritative_anatomy == "Abdomen and Pelvis"
    assert decision.contrast == "WITH_CONTRAST"
    assert isinstance(decision.modality_context, CTClinicalContext)
    assert decision.modality_context.study_family is CTStudyFamily.CTA
    assert decision.modality_context.acquisition_summary == (
        CTAcquisitionFeature.ANGIOGRAPHIC,
    )
    cta_signals = [
        item for item in decision.frame.modality_signals
        if item.matched_text == "CTA"
    ]
    assert len(cta_signals) == 2
    assert {dict(item.attributes).get("part_type") for item in cta_signals} == {
        "RAD_MODALITY_MODALITY_TYPE", "RAD_MODALITY_MODALITY_SUBTYPE",
    }
    assert all(text[item.start:item.end] == "CTA" for item in cta_signals)
    assert context.light_context.family_context.body_region == "Abdomen and Pelvis"


def test_performed_study_title_anatomy_excludes_acquisition_coverage_anatomy():
    text = """RADIOLOGY REPORT
EXAMINATION: CTA abdomen and pelvis
TECHNIQUE: Current acquisition extended through the chest for scan coverage.
FINDINGS: Current appearances are documented.
IMPRESSION: No acute process.
RADIOLOGIST: Electronically authenticated.
"""
    service = DocumentUnderstandingService()
    document = service.text_document(text)
    result = service.analyze_document(document)
    decision = result.radiology_decision
    context = service.build_context(document, result)

    assert decision is not None
    assert decision.body_regions == ("ABDOMEN", "PELVIS")
    assert "CHEST" not in decision.body_regions
    assert decision.authoritative_anatomy == "Abdomen and Pelvis"
    assert context.light_context.family_context.body_region == "Abdomen and Pelvis"
    coverage = [
        item for item in decision.evidence_eligibility.evidence
        if item.field_name == "anatomy_signals"
        and item.signal.matched_text.casefold() == "chest"
    ]
    assert coverage
    assert all(
        item.semantic_role is RadiologySemanticRole.TECHNIQUE_ACQUISITION
        and item.eligibility is RadiologyEvidenceEligibility.CONTEXT_ONLY
        for item in coverage
    )


_TITLE_LED_OBSERVATION = (
    "The current examination provides a complete diagnostic imaging survey of the "
    "stated region. Image quality is adequate for document-level review, and "
    "observations are recorded throughout the study. Several anatomic structures "
    "are evaluated in sequence without introducing another performed modality. "
    "The narrative concludes with an overall statement about the current examination."
)


def test_compact_title_led_ct_report_uses_structural_identity_and_narrative():
    title = "CT STUDY OF THE HEAD"
    text = f"{title}\n\n{_TITLE_LED_OBSERVATION}"
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.CT
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert decision is not None and decision.report_satisfied is True
    assert decision.body_regions == ("HEAD",)
    title_signal = next(
        item for item in decision.frame.structure_signals
        if item.concept_id == "RAD_STRUCTURE_STUDY_TITLE"
    )
    assert (title_signal.start, title_signal.end) == (0, len(title))
    assert text[title_signal.start:title_signal.end] == title


def test_context_preamble_does_not_swallow_a_later_governed_ct_study_label():
    title = "CT STUDY OF THE CERVICAL SPINE"
    text = f"""Indication: Persistent neck discomfort.
Scanner metadata: routine quality-control record.

{title}

Protocol: Current spiral acquisition without contrast followed by multiplanar reconstruction.
Results:
{_TITLE_LED_OBSERVATION}
Conclusion:
Current imaging assessment is complete.
"""
    sections = SectionDetector.detect(text)
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    indication = next(
        item for item in sections if item.canonical_name == "clinical_information"
    )
    assert indication.end < text.index(title)
    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.CT
    assert decision is not None and decision.report_satisfied is True
    assert decision.contrast == "WITHOUT_CONTRAST"
    negative_contrast = next(
        item for item in decision.evidence_eligibility.evidence
        if item.signal.concept_id == "RAD_CONTRAST_WITHOUT"
    )
    assert negative_contrast.semantic_role in {
        RadiologySemanticRole.PERFORMED_STUDY,
        RadiologySemanticRole.TECHNIQUE_ACQUISITION,
    }
    assert (
        negative_contrast.eligibility
        is RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
    )
    title_signal = next(
        item for item in decision.frame.structure_signals
        if item.concept_id == "RAD_STRUCTURE_STUDY_TITLE"
    )
    assert text[title_signal.start:title_signal.end] == title


def test_compact_single_line_mri_uses_bounded_identity_and_inferred_narrative():
    identity = (
        "The current shoulder MRI examination was performed using T1-weighted, "
        "T2-weighted, and diffusion-weighted acquisitions."
    )
    recommendation = "A later ultrasound examination is recommended."
    text = f"{identity} {_TITLE_LED_OBSERVATION} {recommendation}"
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.MRI
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert decision is not None and decision.report_satisfied is True
    region = next(
        item for item in decision.semantic_regions
        if item.section_id == "unheaded_observation"
    )
    assert region.start == len(identity) + 1
    assert region.end <= text.index(recommendation)
    assert region.canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE
    assert region.qualifiers == ("INFERRED_UNHEADED",)
    assert "MEDNEXUS_STRUCTURAL_REASONING" in region.provenance
    future = next(
        item for item in decision.evidence_eligibility.evidence
        if item.signal.matched_text.casefold() == "ultrasound"
    )
    assert future.semantic_role is RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY
    assert future.eligibility is RadiologyEvidenceEligibility.CONTEXT_ONLY


@pytest.mark.parametrize(("title", "expected_subtype"), (
    ("X-RAY STUDY OF THE LEFT WRIST", DocumentSubtype.X_RAY),
    ("ULTRASOUND STUDY OF THE RIGHT SHOULDER", DocumentSubtype.ULTRASOUND),
))
def test_title_led_radiology_families_emit_inferred_observation_regions(
    title, expected_subtype
):
    text = f"{title}\n\n{_TITLE_LED_OBSERVATION}"
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.document_subtype is expected_subtype
    assert decision is not None
    region = next(
        item for item in decision.semantic_regions
        if item.section_id == "unheaded_observation"
    )
    assert text[region.start:region.end] == _TITLE_LED_OBSERVATION
    assert region.canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE
    assert region.qualifiers == ("INFERRED_UNHEADED",)
    assert "MEDNEXUS_STRUCTURAL_REASONING" in region.provenance


@pytest.mark.parametrize(("heading", "canonical"), (
    ("IMPRESSION", "impression"),
    ("RECOMMENDATION", "recommendation"),
    ("RADIOLOGIST", "radiologist_authentication"),
))
def test_inferred_observation_stops_before_later_governed_region(heading, canonical):
    text = f"""ULTRASOUND STUDY OF THE ABDOMEN

{_TITLE_LED_OBSERVATION}
{heading}:
Completed document-level statement.
"""
    sections = SectionDetector.detect(text)
    decision = RadiologyReasoner.assess(text, sections)
    inferred = next(
        item for item in decision.semantic_regions
        if item.section_id == "unheaded_observation"
    )
    governed = next(item for item in sections if item.canonical_name == canonical)

    assert inferred.end <= governed.start


def test_title_led_mri_with_technique_and_findings_is_a_partial_report():
    text = f"""MRI STUDY OF THE SHOULDER
TECHNIQUE: Current magnetic resonance images were obtained with T1-weighted acquisition.
FINDINGS:
{_TITLE_LED_OBSERVATION}
"""
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.MRI
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert decision is not None and decision.report_satisfied is True
    assert decision.examination == "MRI Shoulder"


@pytest.mark.parametrize("title", (
    "RECOMMENDED CT STUDY OF THE HEAD",
    "PRIOR MRI STUDY OF THE SHOULDER",
))
def test_contextual_title_modality_does_not_form_current_study_identity(title):
    result = DocumentUnderstandingService().analyze_text(
        f"{title}\n\n{_TITLE_LED_OBSERVATION}"
    )

    assert result.domain is DocumentDomain.UNKNOWN
    assert result.radiology_decision is None


@pytest.mark.parametrize("text", (
    "Scanner inventory CT head",
    "Scheduling record for MRI shoulder",
    "Equipment note: X-ray wrist detector",
    "Administrative ultrasound abdomen request",
))
def test_short_administrative_imaging_text_does_not_form_a_report(text):
    result = DocumentUnderstandingService().analyze_text(text)

    assert result.domain is DocumentDomain.UNKNOWN
    assert result.radiology_decision is None


def test_findings_only_modality_and_anatomy_do_not_replace_title_identity():
    text = f"""CT STUDY OF THE HEAD
FINDINGS:
{_TITLE_LED_OBSERVATION} MRI pelvis appears only in this observation narrative.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.body_regions == ("HEAD",)
    current = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
    )
    assert not any(item.signal.matched_text.casefold() == "mri" for item in current)
    assert not any(item.signal.matched_text.casefold() == "pelvis" for item in current)


def test_title_led_other_and_domain_unknown_remain_distinct():
    service = DocumentUnderstandingService()
    other_document = service.text_document(
        f"CT AND MRI STUDY OF THE CHEST\n\n{_TITLE_LED_OBSERVATION}"
    )
    other_result = service.analyze_document(other_document)
    other_context = service.build_context(other_document, other_result)
    unknown_result = service.analyze_text(_TITLE_LED_OBSERVATION)

    assert other_result.domain is DocumentDomain.RADIOLOGY
    assert other_context.identity.subdomain_or_family == "OTHER"
    assert unknown_result.domain is DocumentDomain.UNKNOWN
    assert unknown_result.radiology_decision is None


def test_governed_document_report_identity_is_source_agnostic():
    text = f"MRI REPORT\n\n{_TITLE_LED_OBSERVATION}"
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.MRI
    assert decision.report_satisfied is True
    assert decision.finding_bearing is True
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert any(
        item.concept_family == "DOCUMENT_REPORT"
        for item in decision.frame.domain_signals
    )


def test_governed_mri_sequences_support_an_unheaded_partial_report():
    text = f"""Sequences were acquired using T1-weighted, T2-weighted, and FLAIR imaging in axial and sagittal planes.

{_TITLE_LED_OBSERVATION}

IMPRESSION:
The imaging assessment is complete.
"""
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.MRI
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert decision is not None and decision.report_satisfied is True
    assert not any(
        item.concept_id == "RAD_MODALITY_MRI"
        for item in decision.frame.modality_signals
    )


def test_existing_results_region_adapts_to_observation_narrative():
    text = """X-RAY STUDY OF THE LEFT HAND
RESULTS:
Alignment is preserved. No additional document-level qualification is required.
"""
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_subtype is DocumentSubtype.X_RAY
    assert result.document_nature is DocumentNature.PARTIAL_REPORT
    assert decision is not None and decision.report_satisfied is True
    result_signal = next(
        item for item in decision.evidence_eligibility.evidence
        if item.signal.concept_id == "RAD_SECTION_FINDINGS"
    )
    assert result_signal.semantic_role is RadiologySemanticRole.FINDINGS_CONTEXT
    assert (
        result_signal.eligibility
        is RadiologyEvidenceEligibility.DOCUMENT_COMPOSITION_SUPPORT
    )


@pytest.mark.parametrize("context_heading", ("RECOMMENDATION", "COMPARISON"))
def test_contextual_mri_sequences_cannot_establish_current_identity(context_heading):
    text = f"""{context_heading}:
MRI may use T1-weighted, T2-weighted, and FLAIR sequences in a future or prior study.

IMPRESSION:
The current non-imaging document remains unresolved.
"""
    result = DocumentUnderstandingService().analyze_text(text)

    assert result.domain is DocumentDomain.UNKNOWN
    assert result.radiology_decision is None


def test_ct_contrast_is_a_bounded_state_and_does_not_expose_exact_protocol_facts():
    decision = _radiology_decision(
        "CT chest", "CT images obtained with contrast (100 mL iodinated agent via IV)."
    )

    assert decision.contrast == "WITH_CONTRAST"
    assert isinstance(decision.modality_context, CTClinicalContext)
    assert "dose" not in asdict(decision.modality_context)
    assert "agent" not in asdict(decision.modality_context)
    assert "route" not in asdict(decision.modality_context)


def test_current_ct_positive_contrast_resolves_with_contrast():
    decision = _radiology_decision(
        "CT abdomen", "Current CT images were acquired with intravenous contrast."
    )

    assert decision.contrast == "WITH_CONTRAST"


def test_current_ct_negative_contrast_resolves_without_contrast():
    decision = _radiology_decision(
        "CT abdomen", "Current CT images were acquired without oral contrast."
    )

    assert decision.contrast == "WITHOUT_CONTRAST"


def test_coordinated_current_ct_contrast_resolves_pre_and_post():
    decision = _radiology_decision(
        "CT abdomen",
        "Current series were acquired both with delayed and without intravenous contrast.",
    )

    assert decision.contrast == "PRE_AND_POST_CONTRAST"


def test_unqualified_current_contrast_mention_does_not_imply_administration():
    decision = _radiology_decision(
        "CT abdomen", "Current acquisition documents contrast timing metadata."
    )

    assert decision.contrast is None


def test_recommended_future_contrast_does_not_change_current_ct_contrast():
    text = """RADIOLOGY REPORT
EXAMINATION: CT abdomen
TECHNIQUE: Current CT images were acquired without contrast.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RECOMMENDATION: Consider future CT chest with contrast.
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision

    assert decision is not None
    assert decision.contrast == "WITHOUT_CONTRAST"


def test_prior_contrast_ct_does_not_change_current_ct_contrast():
    text = """RADIOLOGY REPORT
EXAMINATION: CT abdomen
COMPARISON: Prior CT chest with contrast.
TECHNIQUE: Current CT images were acquired without contrast.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision

    assert decision is not None
    assert decision.contrast == "WITHOUT_CONTRAST"


def test_negated_current_contrast_cannot_resolve_as_positive():
    decision = _radiology_decision(
        "CT pelvis", "No intravenous contrast was administered for the current study."
    )

    assert decision.contrast == "WITHOUT_CONTRAST"


def test_findings_only_contrast_does_not_define_current_ct_context():
    decision = _radiology_decision(
        "CT head",
        "Current CT images were acquired.",
        "No acute change. Historical contrast enhancement was previously described.",
    )

    assert decision.contrast is None


def test_conflicting_current_contrast_evidence_resolves_conservatively():
    decision = _radiology_decision(
        "CT chest",
        "One current series was acquired with contrast; another was acquired without contrast.",
    )

    assert decision.contrast is None


def _comparison_boundary_report(*, tail: str) -> str:
    return f"""ULTRASOUND STUDY OF THE ABDOMEN
Comparison: Prior imaging was reviewed.

{tail}
"""


def test_inline_comparison_is_bounded_before_unheaded_current_narrative():
    text = _comparison_boundary_report(tail=_TITLE_LED_OBSERVATION)
    sections = SectionDetector.detect(text)
    comparison = next(item for item in sections if item.canonical_name == "comparison")
    decision = RadiologyReasoner.assess(text, sections)
    observation = next(
        item for item in decision.semantic_regions
        if item.section_id == "unheaded_observation"
    )

    assert "\n" not in text[comparison.start:comparison.end]
    assert comparison.end < observation.start < observation.end
    assert observation.canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE


def test_explicit_comparison_section_ends_at_findings_heading():
    text = """ULTRASOUND STUDY OF THE ABDOMEN
COMPARISON:
Prior imaging was reviewed.
FINDINGS:
Current appearances are documented.
IMPRESSION:
Completed examination.
"""
    sections = SectionDetector.detect(text)
    comparison = next(item for item in sections if item.canonical_name == "comparison")
    findings = next(item for item in sections if item.canonical_name == "findings")

    assert comparison.end == findings.start


def test_inline_comparison_unheaded_observation_and_impression_are_separate():
    text = _comparison_boundary_report(
        tail=f"{_TITLE_LED_OBSERVATION}\nIMPRESSION:\nCompleted examination."
    )
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    by_id = {item.section_id: item for item in decision.semantic_regions}

    assert by_id["comparison"].canonical_role is SemanticRegionRole.COMPARISON_OR_PRIOR_CONTEXT
    assert by_id["unheaded_observation"].canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE
    assert by_id["impression"].canonical_role is SemanticRegionRole.CONCLUSION_OR_STATUS
    assert by_id["comparison"].end < by_id["unheaded_observation"].start
    assert by_id["unheaded_observation"].end <= by_id["impression"].start


def test_comparison_language_inside_findings_remains_findings_context():
    text = """ULTRASOUND STUDY OF THE ABDOMEN
FINDINGS:
Current appearances are stable in comparison with prior imaging.
IMPRESSION:
Completed examination.
"""
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))

    assert not any(item.section_id == "comparison" for item in decision.semantic_regions)
    findings = next(item for item in decision.semantic_regions if item.section_id == "findings")
    assert findings.canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE


def test_prior_study_reference_without_heading_remains_context_only():
    text = """ULTRASOUND STUDY OF THE ABDOMEN
FINDINGS:
Prior CT imaging was reviewed. Current ultrasound appearances are documented.
IMPRESSION:
Completed examination.
"""
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    prior_ct = next(
        item for item in decision.evidence_eligibility.evidence
        if item.field_name == "modality_signals"
        and item.signal.matched_text.casefold() == "ct"
    )

    assert prior_ct.semantic_role is RadiologySemanticRole.HISTORICAL_STUDY
    assert prior_ct.eligibility is RadiologyEvidenceEligibility.CONTEXT_ONLY


def test_current_narrative_after_inline_comparison_does_not_inherit_comparison_role():
    text = _comparison_boundary_report(
        tail="The liver and pancreas are evaluated in the current ultrasound study."
    )
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    liver = next(
        item for item in decision.role_resolution.evidence
        if item.signal.matched_text.casefold() == "liver"
    )

    assert liver.section_id == "unheaded_observation"
    assert liver.role is RadiologySemanticRole.FINDINGS_CONTEXT


def test_recommendation_after_inline_comparison_remains_future_action():
    text = _comparison_boundary_report(
        tail=f"{_TITLE_LED_OBSERVATION}\nRECOMMENDATION:\nConsider future MRI of the pelvis."
    )
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    recommendation = next(
        item for item in decision.role_resolution.evidence
        if item.signal.matched_text.casefold() == "mri"
    )
    by_id = {item.section_id: item for item in decision.semantic_regions}

    assert recommendation.role is RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY
    assert by_id["unheaded_observation"].end <= by_id["recommendation"].start
    assert by_id["recommendation"].canonical_role is SemanticRegionRole.RECOMMENDATION_OR_FUTURE_ACTION


@pytest.mark.parametrize(("examination", "expected"), (
    ("MRA Head vessels", MRIStudyFamily.MRA),
    ("MRA Head veins", MRIStudyFamily.MRV),
))
def test_mr_angiographic_family_uses_authoritative_composition(examination, expected):
    decision = _radiology_decision(
        examination, "MR images obtained with T1 and T2 weighted sequences."
    )

    assert decision.subdomain is RadiologySubdomain.MRI
    assert isinstance(decision.modality_context, MRIClinicalContext)
    assert decision.modality_context.study_family is expected
    assert decision.modality_context.canonical_sequence_families == (
        MRISequenceFamily.T1_WEIGHTED,
        MRISequenceFamily.T2_WEIGHTED,
    )
    assert decision.examination.startswith(expected.value)


def test_vascular_narrative_does_not_promote_base_ct_or_mri_family():
    ct = _radiology_decision(
        "CT chest", "Current CT images obtained.", "Vascular structures are normal."
    )
    mri = _radiology_decision(
        "MR brain", "Current MR images obtained.", "The intracranial veins are unremarkable."
    )

    assert isinstance(ct.modality_context, CTClinicalContext)
    assert ct.modality_context.study_family is CTStudyFamily.CT
    assert isinstance(mri.modality_context, MRIClinicalContext)
    assert mri.modality_context.study_family is MRIStudyFamily.MRI


def test_recommended_procedure_and_findings_anatomy_do_not_override_current_study():
    text = """RADIOLOGY REPORT
EXAMINATION: CT chest
TECHNIQUE: Current CT images were obtained.
FINDINGS: Degenerative change is present in the thoracic spine.
IMPRESSION: No acute chest process.
RECOMMENDATION: Consider CTA Abdomen vessels W contrast IV.
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.body_regions == ("CHEST",)
    assert isinstance(decision.modality_context, CTClinicalContext)
    assert decision.modality_context.study_family is CTStudyFamily.CT
    assert decision.examination == "CT Chest"


def test_recommended_family_or_source_metadata_is_ineligible_for_current_context():
    cases = (
        ("CT chest", "CT images obtained.", "CTA Abdomen vessels W contrast IV"),
        ("MR brain", "MR images obtained.", "MRA Head veins"),
        ("X-ray chest", "X-ray images obtained.", "CR chest"),
        ("US abdomen", "Ultrasound images obtained.",
         "US.doppler Lower extremity veins - bilateral"),
    )
    decisions = []
    for examination, technique, recommendation in cases:
        text = f"""RADIOLOGY REPORT
EXAMINATION: {examination}
TECHNIQUE: {technique}
FINDINGS: Current appearances.
IMPRESSION: No acute process.
RECOMMENDATION: Consider {recommendation}.
RADIOLOGIST: Electronically authenticated.
"""
        decisions.append(DocumentUnderstandingService().analyze_text(text).radiology_decision)

    ct, mri, xray, ultrasound = decisions
    assert isinstance(ct.modality_context, CTClinicalContext)
    assert ct.modality_context.study_family is CTStudyFamily.CT
    assert isinstance(mri.modality_context, MRIClinicalContext)
    assert mri.modality_context.study_family is MRIStudyFamily.MRI
    assert isinstance(xray.modality_context, XRayClinicalContext)
    assert xray.modality_context.source_type is None
    assert isinstance(ultrasound.modality_context, UltrasoundClinicalContext)
    assert ultrasound.modality_context.specialization is UltrasoundSpecialization.GENERAL


@pytest.mark.parametrize(("examination", "technique", "current_region"), (
    ("CT chest", "CT images obtained.", "CHEST"),
    ("MR brain", "MR images obtained.", "BRAIN"),
    ("XR chest", "X-ray images obtained.", "CHEST"),
    ("US abdomen", "Ultrasound images obtained.", "ABDOMEN"),
))
def test_findings_only_anatomy_cannot_replace_performed_study_anatomy(
    examination, technique, current_region
):
    decision = _radiology_decision(
        examination, technique, "An incidental finding is described in the pelvis."
    )

    assert current_region in decision.body_regions
    assert "PELVIS" not in decision.body_regions


@pytest.mark.parametrize(("source", "expected"), (
    ("CR", XRaySourceType.CR),
    ("DX", XRaySourceType.DX),
    ("XR", XRaySourceType.XR),
))
def test_xray_source_and_view_summary_are_bounded_and_governed(source, expected):
    decision = _radiology_decision(
        f"{source} chest 2 views", "PA and lateral views obtained."
    )

    assert isinstance(decision.modality_context, XRayClinicalContext)
    assert decision.modality_context.source_type is expected
    assert decision.modality_context.views == ("PA", "lateral")
    assert decision.modality_context.view_count == 2
    assert decision.modality_context.view_count_qualifier == "EXACT"


def test_xray_study_laterality_is_distinct_from_directional_view_language():
    directional = _radiology_decision("XR Chest Left lateral", "Images obtained.")
    study_laterality = _radiology_decision(
        "XR Knee - left AP and Lateral and Right oblique and Left oblique",
        "Images obtained.",
    )

    assert isinstance(directional.modality_context, XRayClinicalContext)
    assert directional.modality_context.laterality is None
    assert isinstance(study_laterality.modality_context, XRayClinicalContext)
    assert study_laterality.modality_context.laterality is StudyLaterality.LEFT

    ordinary_direction = _radiology_decision(
        "XR chest 2 views", "Images obtained.",
        "There is soft-tissue swelling along the lateral chest wall.",
    )
    assert isinstance(ordinary_direction.modality_context, XRayClinicalContext)
    assert ordinary_direction.modality_context.views == ()
    assert ordinary_direction.modality_context.view_count == 2


def test_ultrasound_context_uses_governed_extent_and_doppler_territory():
    decision = _radiology_decision(
        "US.doppler Thoracic and abdominal aorta limited",
        "Doppler ultrasound performed.",
    )

    assert decision.subdomain is RadiologySubdomain.ULTRASOUND
    assert decision.body_regions == ("CHEST", "ABDOMEN")
    assert isinstance(decision.modality_context, UltrasoundClinicalContext)
    assert decision.modality_context.study_extent is UltrasoundStudyExtent.LIMITED
    assert decision.modality_context.specialization is UltrasoundSpecialization.DOPPLER
    assert decision.modality_context.vascular_context is VascularContext.ARTERIAL
    assert decision.modality_context.measurement_bearing_present is None

    complete = _radiology_decision(
        "Complete ultrasound of abdomen", "Ultrasound images obtained."
    )
    assert isinstance(complete.modality_context, UltrasoundClinicalContext)
    assert complete.modality_context.study_extent is UltrasoundStudyExtent.COMPLETE
    assert complete.modality_context.specialization is UltrasoundSpecialization.GENERAL

    venous = _radiology_decision(
        "US.doppler Lower extremity veins - bilateral",
        "Doppler ultrasound performed.",
        "The vein caliber measures 4.2 mm.",
    )
    assert isinstance(venous.modality_context, UltrasoundClinicalContext)
    assert venous.modality_context.vascular_context is VascularContext.VENOUS
    assert venous.modality_context.measurement_bearing_present is None
    assert "measurement_value" not in asdict(venous.modality_context)


def test_family_context_contract_stays_bounded_and_contains_no_extract_facts():
    decisions = (
        _radiology_decision("CT chest", "Current CT images obtained."),
        _radiology_decision("MR brain", "T1 weighted images obtained."),
        _radiology_decision("XR chest 2 views", "PA and lateral views obtained."),
        _radiology_decision("US abdomen", "Ultrasound images obtained."),
    )
    forbidden = {
        "diagnosis", "measurements", "measurement_value", "finding_text",
        "recommendation_text", "patient", "medication",
    }

    for decision in decisions:
        modality_context = asdict(decision.modality_context)
        assert forbidden.isdisjoint(modality_context)
        assert len(modality_context) <= 6


def test_current_mri_evidence_is_eligible_for_current_identity_support():
    decision = _radiology_decision(
        "MRI brain", "Current MRI images obtained with T1 weighted sequences."
    )
    current = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
    )

    assert any(
        item.field_name == "modality_signals"
        and item.signal.matched_text.casefold() in {"mr", "mri"}
        for item in current
    )
    assert decision.subdomain_support > 0
    assert decision.subdomain is RadiologySubdomain.MRI


@pytest.mark.parametrize(("current_exam", "current_technique", "context_sentence", "excluded"), (
    (
        "CR chest 2 views",
        "PA and lateral views obtained.",
        "Recommend MRI brain with contrast.",
        "RAD_MODALITY_MRI",
    ),
    (
        "CT chest",
        "Current CT images obtained.",
        "Prior MRI brain was reviewed.",
        "RAD_MODALITY_MRI",
    ),
    (
        "US abdomen",
        "Current ultrasound images obtained.",
        "Recommend a future nuclear medicine study.",
        "RAD_MODALITY_NUCLEAR_MEDICINE",
    ),
))
def test_context_only_modalities_are_preserved_but_ineligible_for_current_identity(
    current_exam, current_technique, context_sentence, excluded
):
    text = f"""RADIOLOGY REPORT
EXAMINATION: {current_exam}
TECHNIQUE: {current_technique}
FINDINGS: Current appearances.
IMPRESSION: No acute process. {context_sentence}
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision
    assert decision is not None
    context_only = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CONTEXT_ONLY
    )
    current = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
    )

    assert any(item.signal.concept_id == excluded for item in context_only)
    assert not any(item.signal.concept_id == excluded for item in current)
    assert any(item.concept_id == excluded for item in decision.frame.modality_signals)


def test_governed_short_ultrasound_code_is_current_while_future_nuclear_study_is_context_only():
    text = """RADIOLOGY REPORT
EXAMINATION: US abdomen complete
TECHNIQUE: Current sonographic images were obtained.
FINDINGS: Current appearances are documented.
IMPRESSION: No acute process.
RECOMMENDATION: Consider a future nuclear medicine study.
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.ULTRASOUND
    assert decision.body_regions == ("ABDOMEN",)
    assert isinstance(decision.modality_context, UltrasoundClinicalContext)
    assert decision.modality_context.study_extent is UltrasoundStudyExtent.COMPLETE
    current = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
    )
    contextual = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.CONTEXT_ONLY
    )
    assert any(
        item.field_name == "modality_signals"
        and item.signal.matched_text == "US"
        and text[item.signal.start:item.signal.end] == "US"
        for item in current
    )
    assert any(
        item.signal.concept_id == "RAD_MODALITY_NUCLEAR_MEDICINE"
        and item.semantic_role is RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY
        for item in contextual
    )


def test_future_and_historical_context_cannot_inflate_current_identity_or_confidence():
    current_only = """RADIOLOGY REPORT
EXAMINATION: CR chest 2 views
TECHNIQUE: PA and lateral views obtained.
FINDINGS: Current appearances.
IMPRESSION: No acute process.
RADIOLOGIST: Electronically authenticated.
"""
    contextual = current_only.replace(
        "No acute process.",
        "No acute process. Recommend MRI brain with contrast. "
        "Prior CT abdomen was reviewed.",
    )
    service = DocumentUnderstandingService()
    base_result = service.analyze_text(current_only)
    contextual_result = service.analyze_text(contextual)
    base = base_result.radiology_decision
    enriched = contextual_result.radiology_decision
    assert base is not None and enriched is not None

    assert enriched.subdomain is base.subdomain is RadiologySubdomain.X_RAY
    assert enriched.modality_context == base.modality_context
    assert enriched.body_regions == base.body_regions
    assert enriched.contrast == base.contrast
    assert enriched.subdomain_support == base.subdomain_support
    assert enriched.eligible_support_dimension_count == base.eligible_support_dimension_count
    assert enriched.eligible_relationship_count == base.eligible_relationship_count
    assert enriched.score == base.score
    assert contextual_result.confidence == base_result.confidence
    assert len(enriched.frame.all_signals) > len(base.frame.all_signals)
    assert {
        item.signal.concept_id for item in enriched.evidence_eligibility.decisions_for(
            RadiologyEvidenceEligibility.CONTEXT_ONLY
        )
    } >= {"RAD_MODALITY_MRI", "RAD_MODALITY_CT"}


def test_findings_only_anatomy_does_not_increase_identity_support_or_score():
    base = _radiology_decision(
        "CT chest", "Current CT images obtained.", "Current chest appearances."
    )
    secondary = _radiology_decision(
        "CT chest",
        "Current CT images obtained.",
        "Current chest appearances. An incidental pelvis observation is noted.",
    )

    assert secondary.body_regions == base.body_regions == ("CHEST",)
    assert secondary.subdomain_support == base.subdomain_support
    assert secondary.eligible_support_dimension_count == base.eligible_support_dimension_count
    assert secondary.score == base.score
    assert len(secondary.frame.anatomy_signals) > len(base.frame.anatomy_signals)
    assert any(
        item.field_name == "anatomy_signals"
        and item.signal.matched_text.casefold() == "chest"
        for item in base.evidence_eligibility.decisions_for(
            RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
        )
    )


def test_report_structure_and_authentication_support_composition_not_modality():
    decision = _radiology_decision(
        "CT chest", "Current CT images obtained.", "Current appearances."
    )
    composition = decision.evidence_eligibility.decisions_for(
        RadiologyEvidenceEligibility.DOCUMENT_COMPOSITION_SUPPORT
    )

    assert decision.domain_support > 0
    assert decision.report_support > 0
    assert any(item.field_name == "structure_signals" for item in composition)
    assert any(item.field_name == "professional_role_signals" for item in composition)
    assert all(
        item.field_name != "modality_signals" for item in composition
        if item.semantic_role is RadiologySemanticRole.PROFESSIONAL_ATTRIBUTION
    )


def test_recommendation_only_modality_does_not_create_current_modality_support():
    text = """RADIOLOGY REPORT
FINDINGS: No current study modality is stated.
IMPRESSION: Recommend MRI brain with contrast.
RADIOLOGIST: Electronically authenticated.
"""
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision
    assert decision is not None

    assert decision.subdomain is RadiologySubdomain.OTHER
    assert decision.compatibility_subtype is DocumentSubtype.UNKNOWN
    assert decision.subdomain_support == 0
    assert any(
        item.signal.concept_id == "RAD_MODALITY_MRI"
        for item in decision.evidence_eligibility.decisions_for(
            RadiologyEvidenceEligibility.CONTEXT_ONLY
        )
    )


def test_true_current_multimodality_evidence_remains_identity_eligible():
    text = """RADIOLOGY REPORT
TECHNIQUE: Current CT and MRI images were obtained using multiplanar imaging.
FINDINGS: Combined current-study appearances.
IMPRESSION: Multimodality assessment.
RADIOLOGIST: Electronically authenticated.
"""
    decision = DocumentUnderstandingService().analyze_text(text).radiology_decision
    assert decision is not None
    current_modality_ids = {
        item.signal.concept_id
        for item in decision.evidence_eligibility.decisions_for(
            RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
        )
        if item.field_name == "modality_signals"
    }

    assert current_modality_ids >= {"RAD_MODALITY_CT", "RAD_MODALITY_MRI"}
    assert decision.subdomain is RadiologySubdomain.OTHER
    assert decision.compatibility_subtype is DocumentSubtype.UNKNOWN


@pytest.mark.parametrize(("examination", "purpose"), (
    ("FFD mammogram Breast - bilateral Screening", MammographyStudyPurpose.SCREENING),
    ("FFD mammogram Breast - left Diagnostic", MammographyStudyPurpose.DIAGNOSTIC),
))
def test_mammography_current_procedure_governs_purpose_and_laterality(
    examination, purpose
):
    decision = _radiology_decision(examination, "Current mammography images obtained.")

    assert decision.subdomain is RadiologySubdomain.MAMMOGRAPHY
    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.study_purpose is purpose
    assert decision.modality_context.laterality is (
        StudyLaterality.BILATERAL
        if purpose is MammographyStudyPurpose.SCREENING
        else StudyLaterality.LEFT
    )
    assert decision.modality_context.acquisition_context == (
        MammographyAcquisitionContext.STANDARD_VIEWS,
    )


def test_mammography_findings_laterality_and_history_do_not_redefine_current_study():
    decision = _radiology_decision(
        "FFD mammogram Breast - bilateral Screening",
        "Current mammography images obtained.",
        "A left breast observation is described.",
    )
    historical = _radiology_decision(
        "CT chest",
        "Current CT images obtained. Prior mammogram of the left breast was reviewed.",
    )

    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.laterality is StudyLaterality.BILATERAL
    assert historical.subdomain is RadiologySubdomain.CT


def test_mammography_tomosynthesis_and_birads_contract_remain_bounded():
    decision = _radiology_decision(
        "DBT Breast - bilateral screening",
        "Current breast tomosynthesis images obtained.",
        "Current BI-RADS category 2 is documented.",
    )

    assert decision.subdomain is RadiologySubdomain.MAMMOGRAPHY
    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.acquisition_context == (
        MammographyAcquisitionContext.TOMOSYNTHESIS,
    )
    assert decision.modality_context.birads_assessment_present is True
    assert any(
        item.code == "CURRENT_GOVERNED_PROCEDURE"
        and "Mammography" in item.message
        for item in decision.explanations
    )
    serialized = asdict(decision.modality_context)
    assert "birads_category" not in serialized
    assert "density_category" not in serialized
    assert "lesion_diagnosis" not in serialized


def test_fully_headed_mri_knee_comparator_remains_stable():
    decision = _radiology_decision(
        "MRI right knee",
        "Current acquisition was performed without contrast.",
        "Meniscal morphology and joint structures are described.",
    )

    assert decision.subdomain is RadiologySubdomain.MRI
    assert decision.document_nature is DocumentNature.COMPLETED_REPORT
    assert decision.authoritative_anatomy.casefold() == "right knee"
    assert decision.contrast == "WITHOUT_CONTRAST"


def test_compact_unheaded_current_ultrasound_keeps_unperformed_mri_context_only():
    text = (
        "Current ultrasound examination of the shoulder was performed. "
        "Dynamic assessment demonstrates tendon discontinuity with surrounding "
        "bursal distention and associated motion abnormality. The remaining "
        "evaluated soft tissues retain expected continuity without a focal "
        "collection, and the current imaging observations support a completed "
        "diagnostic report. MRI is contraindicated."
    )
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.ULTRASOUND
    assert decision.authoritative_anatomy == "Shoulder"
    assert any(
        item.section_id == "unheaded_observation"
        and item.canonical_role is SemanticRegionRole.OBSERVATION_NARRATIVE
        for item in decision.semantic_regions
    )
    mri = next(
        item for item in decision.evidence_eligibility.evidence
        if item.field_name == "modality_signals"
        and item.signal.matched_text.casefold() == "mri"
    )
    assert mri.eligibility is RadiologyEvidenceEligibility.CONTEXT_ONLY


def test_governed_spot_view_composition_recovers_diagnostic_mammography():
    text = (
        "Clinical information: Evaluation of a newly identified concern. "
        "Spot views demonstrate a rounded opacity in the right breast with stable "
        "margins and no suspicious calcification. Supplemental ultrasound documents "
        "a benign fluid collection and is included only as complementary imaging. "
        "Impression: BI-RADS Category 2."
    )
    result = DocumentUnderstandingService().analyze_text(text)
    decision = result.radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.MAMMOGRAPHY
    assert decision.authoritative_anatomy == "Breast"
    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.study_purpose is MammographyStudyPurpose.DIAGNOSTIC
    assert decision.modality_context.laterality is StudyLaterality.RIGHT
    assert decision.modality_context.birads_assessment_present is True
    assert any(
        item.section_id == "unheaded_observation"
        for item in decision.semantic_regions
    )
    complementary_us = next(
        item for item in decision.evidence_eligibility.evidence
        if item.field_name == "modality_signals"
        and item.signal.matched_text.casefold() == "ultrasound"
    )
    assert complementary_us.eligibility is RadiologyEvidenceEligibility.CONTEXT_ONLY


def test_underspecified_mammography_procedure_does_not_inherit_reference_specificity():
    decision = _radiology_decision(
        "MG breast views",
        "Standard projections were obtained.",
    )

    assert decision.subdomain is RadiologySubdomain.MAMMOGRAPHY
    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.study_purpose is None
    assert decision.modality_context.laterality is None
    assert decision.contrast is None


def test_composed_procedure_projects_only_observed_attributes_and_base_modality():
    text = (
        "Clinical information: Evaluation of a newly identified concern. "
        "Spot views demonstrate a rounded opacity in the right breast with stable "
        "margins and no suspicious calcification. Supplemental ultrasound documents "
        "a benign fluid collection and is included only as complementary imaging. "
        "Impression: BI-RADS Category 2."
    )
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))

    assert decision.subdomain is RadiologySubdomain.MAMMOGRAPHY
    assert isinstance(decision.modality_context, MammographyClinicalContext)
    assert decision.modality_context.study_purpose is MammographyStudyPurpose.DIAGNOSTIC
    assert decision.modality_context.laterality is StudyLaterality.RIGHT
    composed = next(
        item for item in decision.frame.procedure_signals
        if dict(item.attributes).get("inference_basis")
        == "REFERENCE_COMPONENT_COMPOSITION"
    )
    projected = {
        target for relationship, target in composed.relationships
        if relationship == "CAN_COMPOSE"
    }
    assert projected
    registry = build_active_reference_registry()
    assert all(
        dict(item.attributes).get("part_type") not in {
            "RAD_REASON_FOR_EXAM", "RAD_PHARMACEUTICAL_SUBSTANCE_GIVEN",
            "RAD_GUIDANCE_FOR_OBJECT",
        }
        for item in (registry.concept(target) for target in projected)
    )
    without_eligibility = replace(
        decision.evidence_eligibility,
        evidence=tuple(
            item for item in decision.evidence_eligibility.evidence
            if item.signal is not composed
        ),
    )
    without_support = RadiologyReasoner._score_support(without_eligibility)
    assert composed.strength <= 1.0
    assert decision.subdomain_support == without_support.subdomain + composed.strength
    assert decision.score - without_support.total <= composed.strength + 1.0


def test_unobserved_contrast_is_not_inherited_by_governed_ct_context():
    decision = _radiology_decision(
        "CT abdomen views",
        "Current CT abdomen views were obtained.",
    )

    assert decision.subdomain is RadiologySubdomain.CT
    assert decision.contrast is None


def test_multisentence_inline_context_does_not_manufacture_observation_region():
    text = (
        "Clinical information: Persistent pain. Fracture and effusion were documented "
        "on AP views. Impression: No current conclusion."
    )
    sections = SectionDetector.detect(text)
    frame = RadiologyReasoner.assess(text, sections).frame
    regions = RadiologySemanticRoleResolver.unheaded_observation_regions(
        text, sections, frame
    )

    assert regions == ()


def test_composed_partial_report_requires_semantic_report_roles_not_section_count():
    text = (
        "Clinical information: Current concern under evaluation. "
        "Spot views of the right breast were obtained. The document continues with "
        "general descriptive prose about image review and presentation without a "
        "clinical observation label. It provides sufficient neutral narrative length "
        "for structural assessment while deliberately avoiding extracted clinical facts. "
        "A second neutral sentence describes orderly documentation and review workflow. "
        "Recommendation: Continue according to the established care pathway."
    )
    decision = RadiologyReasoner.assess(text, SectionDetector.detect(text))

    assert any(
        dict(item.attributes).get("inference_basis")
        == "REFERENCE_COMPONENT_COMPOSITION"
        for item in decision.frame.procedure_signals
    )
    assert decision.report_satisfied is False


def test_acquisition_and_msk_findings_without_current_modality_remain_unknown():
    text = (
        "Joint discomfort is documented. Dynamic assessment describes a tendon "
        "abnormality. MRI cannot be performed."
    )

    result = DocumentUnderstandingService().analyze_text(text)

    assert result.domain is DocumentDomain.UNKNOWN
    assert result.radiology_decision is None


@pytest.mark.parametrize("context", ("prior", "recommended"))
def test_mammography_and_ultrasound_context_alone_do_not_replace_current_ct(context):
    contextual_clause = (
        "Prior mammography and ultrasound were reviewed."
        if context == "prior"
        else "Recommend mammography and ultrasound for future assessment."
    )
    decision = _radiology_decision(
        "CT abdomen",
        f"Current CT images were obtained. {contextual_clause}",
    )

    assert decision.subdomain is RadiologySubdomain.CT


@pytest.mark.parametrize(("examination", "family"), (
    ("NM Bone Views", NuclearMedicineStudyFamily.PLANAR),
    ("SPECT Brain", NuclearMedicineStudyFamily.SPECT),
    ("PT Brain", NuclearMedicineStudyFamily.PET),
    ("SPECT+CT Whole body", NuclearMedicineStudyFamily.SPECT_CT),
    ("PET+CT Whole body Views", NuclearMedicineStudyFamily.PET_CT),
))
def test_nuclear_medicine_current_procedure_governs_family(examination, family):
    decision = _radiology_decision(examination, "Current study images obtained.")

    assert decision.subdomain is RadiologySubdomain.NUCLEAR_MEDICINE
    assert isinstance(decision.modality_context, NuclearMedicineClinicalContext)
    assert decision.modality_context.study_family is family
    assert decision.modality_context.radiopharmaceutical_context_present is True


def test_nuclear_hybrid_requires_one_governed_current_composition():
    pet = _radiology_decision(
        "PT Brain",
        "Current PET images obtained. Prior CT head was reviewed.",
    )
    spect = _radiology_decision(
        "SPECT Brain",
        "Current SPECT images obtained. Recommend CT head for follow-up.",
    )

    assert isinstance(pet.modality_context, NuclearMedicineClinicalContext)
    assert pet.modality_context.study_family is NuclearMedicineStudyFamily.PET
    assert isinstance(spect.modality_context, NuclearMedicineClinicalContext)
    assert spect.modality_context.study_family is NuclearMedicineStudyFamily.SPECT


def test_nuclear_presence_fields_do_not_emit_exact_extract_facts():
    decision = _radiology_decision(
        "NM Thyroid gland Uptake",
        "Current nuclear medicine study performed with radionuclide administration.",
        "The uptake value and administered activity are documented in the source.",
    )

    assert isinstance(decision.modality_context, NuclearMedicineClinicalContext)
    assert decision.modality_context.study_family is NuclearMedicineStudyFamily.PLANAR
    assert decision.modality_context.radiopharmaceutical_context_present is True
    assert decision.modality_context.quantitative_uptake_context_present is True
    assert {
        "tracer_name", "tracer_dose", "suv", "uptake_value", "diagnosis"
    }.isdisjoint(asdict(decision.modality_context))


def test_diagnostic_fluoroscopy_has_bounded_contrast_context():
    decision = _radiology_decision(
        "RF Gastrointestinal tract upper Views W barium contrast PO",
        "Current diagnostic fluoroscopic images obtained.",
    )

    assert decision.subdomain is RadiologySubdomain.FLUOROSCOPY
    assert isinstance(decision.modality_context, FluoroscopyClinicalContext)
    assert decision.modality_context.study_family is FluoroscopyStudyFamily.CONTRAST_STUDY
    assert decision.modality_context.body_system == "ABDOMEN"
    assert decision.modality_context.contrast_study_present is True
    assert decision.modality_context.dynamic_functional_present is None


def test_dynamic_fluoroscopy_context_uses_governed_current_procedure():
    decision = _radiology_decision(
        "RF Rectum Views for rectal dysfunction W barium contrast PR",
        "Current diagnostic fluoroscopic images obtained.",
    )

    assert isinstance(decision.modality_context, FluoroscopyClinicalContext)
    assert (
        decision.modality_context.study_family
        is FluoroscopyStudyFamily.DYNAMIC_FUNCTIONAL_STUDY
    )
    assert decision.modality_context.dynamic_functional_present is True


def test_fluoroscopic_guidance_is_other_not_diagnostic_fluoroscopy():
    decision = _radiology_decision(
        "RF Guidance for biopsy of Lung",
        "Current image-guided intervention was performed.",
    )

    assert decision.subdomain is RadiologySubdomain.OTHER
    assert decision.other_reason is RadiologyOtherReason.INTERVENTIONAL_PROCEDURE
    assert isinstance(decision.modality_context, OtherRadiologyClinicalContext)
    assert decision.modality_context.family_specific_context_available is False


def test_historical_or_recommended_fluoroscopy_does_not_define_current_family():
    decision = _radiology_decision(
        "CT chest",
        "Current CT images obtained. Prior fluoroscopy was reviewed. "
        "Recommend RF Gastrointestinal tract upper Views W barium contrast PO.",
    )

    assert decision.subdomain is RadiologySubdomain.CT
    assert isinstance(decision.modality_context, CTClinicalContext)


@pytest.mark.parametrize(("examination", "reason"), (
    ("Thermography chest", RadiologyOtherReason.UNSUPPORTED_FAMILY),
    ("CT chest and MRI brain", RadiologyOtherReason.CONFLICTING_CURRENT_FAMILY),
))
def test_known_radiology_unsafe_family_resolves_other(examination, reason):
    service = DocumentUnderstandingService()
    text = f"""RADIOLOGY REPORT
EXAMINATION: {examination}
TECHNIQUE: Current study images were obtained.
FINDINGS: Current appearances.
IMPRESSION: Completed study.
RADIOLOGIST: Electronically authenticated.
"""
    document = service.text_document(text)
    result = service.analyze_document(document)
    context = service.build_context(document, result)
    decision = result.radiology_decision

    assert result.domain is DocumentDomain.RADIOLOGY
    assert decision is not None and decision.subdomain is RadiologySubdomain.OTHER
    assert decision.other_reason is reason
    assert context.identity.subdomain_or_family == "OTHER"
    assert context.identity.document_review_required is True
    assert context.clinical_context.domain_extension.modality is None
    assert isinstance(decision.modality_context, OtherRadiologyClinicalContext)
    assert context.provenance.evidence


def test_other_remains_distinct_from_unknown_and_incidental_imaging():
    service = DocumentUnderstandingService()
    unknown = service.analyze_text("General administrative healthcare memo.")
    discharge = service.analyze_text(
        "DISCHARGE SUMMARY\nHOSPITAL COURSE: Thermography was mentioned in a prior note.\n"
        "DISCHARGE DIAGNOSIS: Stable\nDISCHARGE MEDICATIONS: None\n"
        "CONDITION ON DISCHARGE: Stable"
    )

    assert unknown.domain is DocumentDomain.UNKNOWN
    assert unknown.radiology_decision is None
    assert discharge.document_type.value == "DISCHARGE_SUMMARY"
    assert discharge.radiology_decision is None


def test_new_family_contexts_preserve_understand_extract_firewall():
    contexts = (
        _radiology_decision(
            "FFD mammogram Breast - bilateral Screening", "Current images obtained."
        ).modality_context,
        _radiology_decision("PET+CT Whole body Views", "Current images obtained.").modality_context,
        _radiology_decision(
            "RF Gastrointestinal tract upper Views W barium contrast PO",
            "Current images obtained.",
        ).modality_context,
        _radiology_decision("Thermography chest", "Current images obtained.").modality_context,
    )
    forbidden = {
        "birads_category", "density_category", "lesion_diagnosis",
        "tracer_name", "tracer_dose", "suv", "uptake_value", "diagnosis",
        "procedure_findings", "contrast_amount", "device_details",
        "treatment_outcome", "guessed_modality",
    }

    for context in contexts:
        assert context is not None
        assert forbidden.isdisjoint(asdict(context))


def test_new_family_context_evidence_is_role_qualified_and_score_stable():
    base = _radiology_decision("SPECT Brain", "Current SPECT images obtained.")
    contextual = _radiology_decision(
        "SPECT Brain",
        "Current SPECT images obtained. Prior MRI brain was reviewed. "
        "Recommend PET+CT Whole body Views.",
    )

    assert isinstance(contextual.modality_context, NuclearMedicineClinicalContext)
    assert contextual.modality_context.study_family is NuclearMedicineStudyFamily.SPECT
    assert contextual.subdomain_support == base.subdomain_support
    assert contextual.eligible_support_dimension_count == base.eligible_support_dimension_count
    assert contextual.eligible_relationship_count == base.eligible_relationship_count
    assert contextual.score == base.score
    context_only_text = {
        item.signal.matched_text.casefold()
        for item in contextual.evidence_eligibility.decisions_for(
            RadiologyEvidenceEligibility.CONTEXT_ONLY
        )
    }
    assert any("mri" in item for item in context_only_text)
    assert any("pet" in item for item in context_only_text)
