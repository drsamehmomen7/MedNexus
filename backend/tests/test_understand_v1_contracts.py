import json
from dataclasses import asdict, replace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology.semantic_roles import (
    RadiologyEvidenceEligibility,
    RadiologySemanticRole,
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
    MRIClinicalContext,
    MRISequenceFamily,
    MRIStudyFamily,
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
    DocumentSubtype,
    RadiologySubdomain,
    SemanticRegionRole,
    canonical_radiology_subdomain_from_legacy,
)
from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
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


def test_ct_contrast_is_a_bounded_state_and_does_not_expose_exact_protocol_facts():
    decision = _radiology_decision(
        "CT chest", "CT images obtained with contrast (100 mL iodinated agent via IV)."
    )

    assert decision.contrast == "WITH_CONTRAST"
    assert isinstance(decision.modality_context, CTClinicalContext)
    assert "dose" not in asdict(decision.modality_context)
    assert "agent" not in asdict(decision.modality_context)
    assert "route" not in asdict(decision.modality_context)


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
