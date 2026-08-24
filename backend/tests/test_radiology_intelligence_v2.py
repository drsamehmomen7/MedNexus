from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.understanding.document_classifier import DocumentClassifier
from backend.app.modules.medical_document_intelligence.understanding.context_models import (
    MRIClinicalContext, UltrasoundClinicalContext, XRayClinicalContext,
)
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology import (
    RadiologyEvidenceFrameBuilder, RadiologyReasoner,
)
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology.semantic_roles import (
    RadiologySemanticRole,
)
import pytest

from backend.app.modules.medical_document_intelligence.understanding.models import (
    ConfidenceBand, DocumentDomain, DocumentNature, DocumentSubtype, DocumentType,
)
from backend.app.modules.medical_document_intelligence.understanding.section_detector import SectionDetector
from backend.app.modules.medical_document_intelligence.understanding.service import DocumentUnderstandingService


MRI_VALIDATION_R001 = """MRI ABDOMEN AND PELVIS
Procedure Information: Enhanced abdominal and pelvis female MRI
Technique: Examination performed on a 3 Tesla scanner. Axial, sagittal and coronal T1-weighted and T2-weighted sequences with fat saturation and diffusion-weighted imaging. Images obtained before and after contrast.
Clinical Information: Ovarian cancer staging.
Comparison: No prior study.
Findings: Abdominal and pelvic findings described.
Impression: MRI findings for staging.
"""

FAILED_BLIND_FLATTENED_REPORT = """Procedure Information Sag. T2 frFSE, Sag. T1 FSE, Sag. STIR, Axial 3D Merge, Axial T1 FSE and Sag. T2 oblique. Clinical Information Exam Date: Exam Type: MRI Cervical Spine Name of Patient: Date of Birth: Comparison Findings Bone marrow signal intensity is normal. No evidence for fracture. Vertebral bodies are normally aligned. Vertebral body heights are preserved. Normal cord signal without evidence of syringomyelia. The cranio-vertebral junction appears normal. Visualized soft tissues of the cervical neck appear normal. Level-by-level degenerative findings as follows: C2-C3: No significant spinal canal stenosis or neural foraminal narrowing. [Mild / Mod / Severe] Disc desiccation with diffuse [Disc / Annular] bulge and focal [Anterior / Posterior (Central / Paracentral / Foraminal /Extraforaminal)] disc [Protrusion / Extrusion]. Associated end-plate changes include [Modic I, II, III changes / End-plate irregularity / Spondylosis (osteophytes) / Degenerative instability (vertebral body height loss / Listhesis (Type I (above or below degen level) / Type II (at degen level)]. These findings result in [Mild / Mod / Severe] spinal canal stenosis and [Mild / Mod / Severe] [Right/Left] neural foraminal narrowing. C3-C4: No significant spinal canal stenosis or neural foraminal narrowing. C4-C5: No significant spinal canal stenosis or neural foraminal narrowing. C5-C6: No significant spinal canal stenosis or neural foraminal narrowing. C6-C7: No significant spinal canal stenosis or neural foraminal narrowing. C7-T1: No significant spinal canal stenosis or neural foraminal narrowing. Impression"""


def test_r001_builds_compositional_mri_context():
    service = DocumentUnderstandingService()
    result = service.analyze_text(MRI_VALIDATION_R001)
    context = service.build_context(DocumentContent(
        MRI_VALIDATION_R001, "R-001.txt", "text/plain", ".txt",
        len(MRI_VALIDATION_R001.encode()),
    ), result)
    clinical = context.clinical_context
    assert (result.domain, result.document_type, result.document_subtype) == (
        DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, DocumentSubtype.MRI,
    )
    assert result.confidence_band is ConfidenceBand.HIGH
    assert clinical.examination == "MRI Abdomen & Pelvis"
    assert clinical.body_regions == ("ABDOMEN", "PELVIS")
    assert clinical.contrast == "PRE_AND_POST_CONTRAST"
    assert clinical.clinical_purpose == "Oncologic Staging"
    assert clinical.techniques == (
        "T1-weighted imaging", "T2-weighted imaging", "Diffusion-weighted imaging",
        "Fat-suppressed imaging", "Multiplanar imaging",
    )
    radiology = clinical.domain_extension
    assert isinstance(radiology.modality_context, MRIClinicalContext)
    assert radiology.modality_context.sequence_families == clinical.techniques[:-1]
    assert radiology.modality_context.multiplanar_acquisition_present is True


def test_evidence_frame_retains_family_offsets_and_provenance():
    sections = SectionDetector.detect(MRI_VALIDATION_R001)
    frame = RadiologyEvidenceFrameBuilder.build(MRI_VALIDATION_R001, sections)
    signal = next(item for item in frame.technique_signals if item.concept_id == "RAD_TECH_DWI")
    assert MRI_VALIDATION_R001[signal.start:signal.end] == signal.matched_text
    assert signal.concept_family == "IMAGING_TECHNIQUE"
    assert signal.context.startswith("Technique:")
    assert signal.provenance
    assert len({item.concept_family for item in frame.all_signals}) >= 6


def test_domain_and_report_decisions_are_separate():
    text = "MRI examination using T1, T2, DWI and a 3 Tesla scanner for the pelvis."
    assessment = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    assert assessment.domain_satisfied is True
    assert assessment.report_satisfied is False
    assert assessment.modality is DocumentSubtype.MRI
    assert DocumentClassifier.classify(text).document_type is DocumentType.UNKNOWN


def test_unlabeled_findings_body_can_form_a_report_from_strong_composition():
    text = """DIAGNOSTIC IMAGING STUDY
MODALITY: MRI
HISTORY: Headache.
SEQUENCES: Sagittal FLAIR and coronal T2-weighted images supplemented by axial T1 and T2 images.
The ventricles and brainstem are unremarkable. No focal lesion is identified.
IMPRESSION: No acute intracranial abnormality.
Electronically signed by: RADIOLOGIST"""
    result = DocumentUnderstandingService().analyze_text(text)
    assert (result.domain, result.document_type, result.document_subtype) == (
        DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, DocumentSubtype.MRI,
    )
    assert result.confidence_band is ConfidenceBand.HIGH
    context = DocumentUnderstandingService().build_context(
        DocumentUnderstandingService().text_document(text), result
    )
    assert context.clinical_context.domain_extension.finding_bearing is True


def test_modality_neutral_narrative_body_supports_completed_ultrasound_report():
    text = """VASCULAR ULTRASOUND STUDY
CLINICAL INFORMATION: Limb discomfort.
OBSERVATIONS:
Duplex Doppler sonography of both lower limbs was completed. Survey images were obtained throughout the examined regions. Multiple segments were assessed in longitudinal and transverse planes. Dynamic maneuvers were applied during the study. Representative appearances were documented for clinical correlation.
IMPRESSION: Completed vascular ultrasound examination.
RADIOLOGIST: Electronically authenticated."""
    sections = SectionDetector.detect(text)
    assessment = RadiologyReasoner.assess(text, sections)
    result = DocumentUnderstandingService().analyze_text(text)
    assert assessment.narrative_body_present is True
    assert not assessment.frame.technique_signals
    assert not assessment.frame.acquisition_signals
    assert assessment.report_satisfied is True
    assert (result.domain, result.document_type, result.document_subtype) == (
        DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, DocumentSubtype.DOPPLER,
    )
    assert result.document_nature is DocumentNature.PARTIAL_REPORT


def test_related_ultrasound_doppler_evidence_is_one_document_nature_family():
    text = "RADIOLOGY REPORT\nTECHNIQUE: Doppler ultrasound lower limb\nFINDINGS: Normal survey\nIMPRESSION: Completed study"
    result = DocumentUnderstandingService().analyze_text(text)
    assert result.document_subtype is DocumentSubtype.DOPPLER
    assert result.document_nature is DocumentNature.COMPLETED_REPORT


def test_genuine_multimodality_report_remains_structurally_distinguishable():
    text = "RADIOLOGY REPORT\nTECHNIQUE: CT chest and MRI abdomen with T1 and T2 sequences\nFINDINGS: Combined review\nIMPRESSION: Multimodality assessment"
    result = DocumentUnderstandingService().analyze_text(text)
    assert result.document_nature is DocumentNature.STRUCTURED_TEMPLATE


def test_authoritative_anatomy_rejects_modifier_class_and_prefers_supported_region():
    text = "RADIOLOGY REPORT\nTECHNIQUE: Doppler ultrasound of the lower extremity\nFINDINGS: Deep structures were assessed throughout the lower extremity.\nIMPRESSION: Completed study"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result)
    assert context.clinical_context.body_region == "EXTREMITY"
    assert context.clinical_context.domain_extension.authoritative_anatomy == "lower extremity"


def test_observation_evidence_does_not_become_clinical_purpose():
    text = "RADIOLOGY REPORT\nTECHNIQUE: CT chest\nFINDINGS: Calcification is present.\nIMPRESSION: Completed study"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    context = service.build_context(service.text_document(text), result)
    assert any(item.concept_family == "CLINICAL_FINDING" for item in assessment.frame.observation_signals)
    assert not assessment.frame.clinical_purpose_signals
    assert context.clinical_context.clinical_purpose is None


def test_genuine_clinical_purpose_remains_typed_context():
    text = "RADIOLOGY REPORT\nCLINICAL INFORMATION: Diagnostic evaluation\nTECHNIQUE: CT chest\nFINDINGS: Completed survey\nIMPRESSION: Completed study"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result)
    assert context.clinical_context.clinical_purpose == "Diagnostic Evaluation"


@pytest.mark.parametrize(("current_study", "referenced_study", "expected"), (
    ("Chest X-ray", "CT chest", DocumentSubtype.X_RAY),
    ("CT chest", "MRI chest", DocumentSubtype.CT),
))
def test_current_modality_outranks_future_recommended_modality(
    current_study, referenced_study, expected
):
    text = f"""RADIOLOGY REPORT
EXAMINATION: {current_study}
TECHNIQUE: Current study images were obtained.
FINDINGS: Chest appearances are described in the report body.
IMPRESSION: Completed current examination. Recommend {referenced_study} for further assessment.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    assert result.document_subtype is expected
    future = assessment.role_resolution.signals(
        assessment.frame.modality_signals,
        RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY,
    )
    assert future


def test_current_mri_outranks_prior_ct_comparison():
    text = """RADIOLOGY REPORT
EXAMINATION: MRI brain
TECHNIQUE: T1, T2 and FLAIR images were obtained.
COMPARISON: Prior CT head was reviewed.
FINDINGS: Current MRI appearances are described.
IMPRESSION: Completed MRI examination.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    assert result.document_subtype is DocumentSubtype.MRI
    assert assessment.role_resolution.signals(
        assessment.frame.modality_signals, RadiologySemanticRole.COMPARISON_STUDY
    )


def test_findings_anatomy_does_not_inflate_primary_study_anatomy():
    text = """RADIOLOGY REPORT
EXAMINATION: Chest X-ray
TECHNIQUE: Current chest images were obtained.
FINDINGS: Thoracic spine alignment is included in the field of view.
IMPRESSION: Completed chest examination.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result).clinical_context
    assert result.document_subtype is DocumentSubtype.X_RAY
    assert context.body_regions == ("CHEST",)
    assert "SPINE" not in context.body_regions


def test_recommendation_purpose_does_not_overwrite_current_indication():
    text = """RADIOLOGY REPORT
EXAMINATION: Chest X-ray
TECHNIQUE: Current chest images were obtained.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination; recommend follow-up with CT.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result).clinical_context
    assert context.clinical_purpose is None


def test_follow_up_in_current_indication_remains_clinical_purpose():
    text = """RADIOLOGY REPORT
CLINICAL INFORMATION: Follow-up assessment.
EXAMINATION: Chest X-ray
TECHNIQUE: Current chest images were obtained.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result).clinical_context
    assert context.clinical_purpose == "Follow-up / Surveillance"


def test_genuine_current_multimodality_evidence_is_not_collapsed():
    text = """RADIOLOGY REPORT
EXAMINATION: Combined CT and MRI study
TECHNIQUE: CT images and T1 T2 MRI images were obtained.
FINDINGS: Combined appearances are documented.
IMPRESSION: Multimodality assessment.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    current = assessment.role_resolution.signals(
        assessment.frame.modality_signals,
        RadiologySemanticRole.PERFORMED_STUDY,
        RadiologySemanticRole.TECHNIQUE_ACQUISITION,
    )
    assert {item.concept_id for item in current} >= {"RAD_MODALITY_CT", "RAD_MODALITY_MRI"}
    assert result.document_nature is DocumentNature.STRUCTURED_TEMPLATE


def test_xray_views_use_governed_loinc_view_evidence():
    text = """RADIOLOGY REPORT
EXAMINATION: Chest X-ray
TECHNIQUE: PA and lateral views were obtained.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result).clinical_context
    assert isinstance(context.domain_extension.modality_context, XRayClinicalContext)
    assert context.domain_extension.modality_context.views == ("PA", "lateral")


@pytest.mark.parametrize("code", ("CR", "DX", "XR"))
def test_governed_short_radiography_codes_require_study_context(code):
    text = f"""RADIOLOGY REPORT
EXAMINATION: {code} KNEE STUDY
TECHNIQUE: Frontal and lateral views were obtained.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed examination.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    assert (result.domain, result.document_type, result.document_subtype) == (
        DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, DocumentSubtype.X_RAY,
    )
    context = DocumentUnderstandingService().build_context(
        DocumentUnderstandingService().text_document(text), result
    ).clinical_context
    assert context.domain_extension.authoritative_anatomy == "Knee"


def test_ambiguous_short_codes_do_not_create_radiography_or_view_evidence():
    text = "Clinical note: CR was recorded and PA reviewed the general documentation."
    frame = RadiologyEvidenceFrameBuilder.build(text, SectionDetector.detect(text))
    assert not frame.modality_signals
    assert not frame.view_signals


def test_directional_lateral_without_view_context_is_not_an_xray_view():
    text = "RADIOLOGY REPORT\nEXAMINATION: CT abdomen\nFINDINGS: A lateral lesion is described.\nIMPRESSION: Completed study"
    frame = RadiologyEvidenceFrameBuilder.build(text, SectionDetector.detect(text))
    assert not frame.view_signals


def test_current_ct_outranks_referenced_radiograph():
    text = """RADIOLOGY REPORT
EXAMINATION: CT chest
TECHNIQUE: Current CT images were obtained.
COMPARISON: Prior chest radiograph was reviewed.
FINDINGS: Current appearances are documented.
IMPRESSION: Completed CT examination.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    assert result.document_subtype is DocumentSubtype.CT
    assert assessment.role_resolution.signals(
        assessment.frame.modality_signals, RadiologySemanticRole.COMPARISON_STUDY
    )


def test_xray_knee_view_count_is_typed_separately_from_named_views():
    text = """RADIOLOGY REPORT
EXAMINATION: CR left knee study, 4 or more views
CLINICAL INFORMATION: Local discomfort.
FINDINGS: Current study narrative is documented.
IMPRESSION: Completed radiographic assessment.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    clinical = service.build_context(service.text_document(text), result).clinical_context
    xray = clinical.domain_extension.modality_context
    assert result.document_subtype is DocumentSubtype.X_RAY
    assert clinical.examination == "X-ray Left Knee"
    assert clinical.body_region == "left knee"
    assert clinical.domain_extension.authoritative_anatomy == "left knee"
    assert xray.views == ()
    assert (xray.view_count, xray.view_count_qualifier) == (4, "OR_MORE")


def test_xray_shoulder_exact_view_count_is_general():
    text = """RADIOLOGY REPORT
EXAMINATION: DX shoulder study, 3 views
FINDINGS: Current study narrative is documented.
IMPRESSION: Completed radiographic assessment.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    xray = service.build_context(
        service.text_document(text), result
    ).clinical_context.domain_extension.modality_context
    assert (xray.view_count, xray.view_count_qualifier) == (3, "EXACT")


def test_prior_view_count_does_not_define_current_xray_context():
    text = """RADIOLOGY REPORT
EXAMINATION: Chest X-ray
COMPARISON: Prior radiograph with 4 views was reviewed.
FINDINGS: Current study narrative is documented.
IMPRESSION: Completed radiographic assessment.
RADIOLOGIST: Electronically authenticated."""
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    assessment = RadiologyReasoner.assess(text, result.sections)
    xray = service.build_context(
        service.text_document(text), result
    ).clinical_context.domain_extension.modality_context
    assert xray.view_count is None
    assert assessment.role_resolution.signals(
        assessment.frame.view_count_signals, RadiologySemanticRole.COMPARISON_STUDY
    )


def test_role_aware_explanations_exclude_future_modality_and_findings_anatomy():
    text = """RADIOLOGY REPORT
EXAMINATION: CR chest study
FINDINGS: Thoracic spine alignment is included in the field. Current appearances are documented.
IMPRESSION: Completed study. Recommend MRI for further assessment.
RADIOLOGIST: Electronically authenticated."""
    result = DocumentUnderstandingService().analyze_text(text)
    messages = tuple(item.message for item in result.recognition_explanations)
    assert "X-ray / radiography modality identified" in messages
    assert "Current study anatomy identified" in messages
    assert not any("MRI" in item for item in messages)
    assert not any("spine" in item.casefold() for item in messages)


def test_role_aware_clinical_purpose_explanation_requires_current_indication():
    service = DocumentUnderstandingService()
    current = service.analyze_text("""RADIOLOGY REPORT
CLINICAL INFORMATION: Diagnostic evaluation.
EXAMINATION: Chest X-ray
FINDINGS: Current appearances are documented.
IMPRESSION: Completed study.
RADIOLOGIST: Electronically authenticated.""")
    recommended = service.analyze_text("""RADIOLOGY REPORT
EXAMINATION: Chest X-ray
FINDINGS: Current appearances are documented.
IMPRESSION: Recommend follow-up MRI.
RADIOLOGIST: Electronically authenticated.""")
    assert any(item.code == "CURRENT_CLINICAL_PURPOSE" for item in current.recognition_explanations)
    assert not any(item.code == "CURRENT_CLINICAL_PURPOSE" for item in recommended.recognition_explanations)


@pytest.mark.parametrize("text", (
    "Clinical note: a prior ultrasound was reviewed during today's visit.",
    "Clinical note with copied imaging text. Ultrasound leg. IMPRESSION: No interval change. The note continues with treatment planning.",
    "DISCHARGE SUMMARY\nHOSPITAL COURSE: Ultrasound leg report described a long imaging narrative with several observations. IMPRESSION: Stable appearance.\nDISCHARGE DIAGNOSIS: Stable\nDISCHARGE MEDICATIONS: Continue\nCONDITION ON DISCHARGE: Stable\nRADIOLOGIST: quoted source",
    "IMAGING ORDER\nCLINICAL INFORMATION: Limb discomfort requiring Doppler ultrasound assessment.\nREQUEST: Please perform the examination.\nRADIOLOGIST: Not yet assigned.",
    "ULTRASOUND STUDY\nCLINICAL INFORMATION: Limb discomfort.\nCOMMENTS:\nPending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending. Pending.\nIMPRESSION:\nRADIOLOGIST: Pending.",
    "ULTRASOUND STUDY\nIMPRESSION: Limited examination.\nRADIOLOGIST: Electronically authenticated.",
    "ULTRASOUND STUDY\nCLINICAL INFORMATION: Limb discomfort.\nOBSERVATIONS: A lengthy narrative describes the imaging examination in several complete sentences. Multiple regions are discussed with sufficient prose to resemble a report body. Additional statements provide a diverse narrative before the conclusion. The examination narrative continues with general imaging observations.\nIMPRESSION: Completed examination.",
))
def test_modality_neutral_narrative_route_rejects_incomplete_or_embedded_reports(text):
    assessment = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    result = DocumentUnderstandingService().analyze_text(text)
    assert assessment.report_satisfied is False or result.domain is not DocumentDomain.RADIOLOGY


def test_impression_without_strong_report_composition_remains_unknown():
    text = "Clinical note: prior MRI brain reviewed. IMPRESSION: Stable symptoms."
    assessment = RadiologyReasoner.assess(text, SectionDetector.detect(text))
    assert assessment.report_satisfied is False
    assert DocumentClassifier.classify(text).document_type is DocumentType.UNKNOWN


def test_normal_explicit_findings_are_finding_bearing_without_implying_abnormality():
    text = "RADIOLOGY REPORT\nTECHNIQUE: CT chest\nFINDINGS: Normal study\nIMPRESSION: Normal study"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result)
    radiology = context.clinical_context.domain_extension
    assert radiology.finding_bearing is True
    assert not hasattr(radiology, "abnormal_finding")


def test_incidental_modality_mention_has_no_radiology_extension():
    text = "General clinical note: a prior CT was reviewed during today's visit."
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result)
    assert result.domain is DocumentDomain.UNKNOWN
    assert context.clinical_context.domain_extension is None


@pytest.mark.parametrize(("study", "legacy_modality", "typed_modality", "context_type", "doppler"), (
    ("chest X-ray radiograph", "X_RAY", "X_RAY", XRayClinicalContext, None),
    ("abdominal ultrasound sonography", "ULTRASOUND", "ULTRASOUND", UltrasoundClinicalContext, False),
    ("Doppler ultrasound of an extremity", "DOPPLER", "ULTRASOUND", UltrasoundClinicalContext, True),
))
def test_wave_one_typed_modality_context_is_conservative(
    study, legacy_modality, typed_modality, context_type, doppler
):
    text = f"RADIOLOGY REPORT\nTECHNIQUE: {study}\nFINDINGS: Normal study\nIMPRESSION: Normal study"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result).clinical_context
    radiology = context.domain_extension
    assert context.modality == legacy_modality
    assert radiology.modality == typed_modality
    assert isinstance(radiology.modality_context, context_type)
    if isinstance(radiology.modality_context, XRayClinicalContext):
        assert radiology.modality_context.views == ()
    else:
        assert radiology.modality_context.doppler_present is doppler
        assert radiology.modality_context.imaging_modes == ()


def test_understand_context_does_not_emit_extract_level_facts():
    text = "RADIOLOGY REPORT\nTECHNIQUE: CT chest\nFINDINGS: A 7 mm nodule\nIMPRESSION: Pulmonary nodule\nRECOMMENDATION: Follow up"
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    radiology = service.build_context(service.text_document(text), result).clinical_context.domain_extension
    serialized_keys = set(radiology.__dataclass_fields__)
    assert not serialized_keys & {
        "findings", "lesions", "measurements", "diagnoses", "recommendations",
        "coded_concepts", "finding_laterality",
    }


def test_section_detector_v2_handles_flattened_inline_template():
    text = "Procedure Information: MRI pelvis Technique: T1 and T2 Comparison: None Findings: Normal Impression: Normal"
    sections = SectionDetector.detect(text)
    assert [item.canonical_name for item in sections] == [
        "procedure_information", "technique", "comparison", "findings", "impression",
    ]
    assert all(text[item.start:item.end].startswith(item.original_heading) for item in sections)


def test_section_detector_recovers_registered_heading_cluster_without_layout_delimiters():
    text = "Procedure Information Study details Clinical Information Symptoms Comparison None Findings Normal Impression Normal"
    assert [item.canonical_name for item in SectionDetector.detect(text)] == [
        "procedure_information", "clinical_information", "comparison", "findings", "impression",
    ]


def test_failed_blind_flattened_report_uses_general_composition_path():
    service = DocumentUnderstandingService()
    result = service.analyze_text(FAILED_BLIND_FLATTENED_REPORT)
    context = service.build_context(service.text_document(FAILED_BLIND_FLATTENED_REPORT), result)
    assert (result.domain, result.document_type, result.document_subtype) == (
        DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, DocumentSubtype.MRI,
    )
    assert result.confidence_band is ConfidenceBand.HIGH
    assert {"procedure_information", "clinical_information", "comparison", "findings", "impression"} <= {
        item.canonical_name for item in result.sections
    }
    assert context.clinical_context.body_region == "SPINE"
    assert context.clinical_context.examination == "MRI Spine"
    assert context.clinical_context.attributes["authoritative_anatomy"] == "Cervical spine"


def test_modality_and_anatomy_compose_without_exact_exam_phrase():
    text = MRI_VALIDATION_R001.replace("MRI ABDOMEN AND PELVIS", "IMAGING STUDY").replace(
        "Enhanced abdominal and pelvis female MRI", "Magnetic resonance study of the abdominal cavity and pelvic organs"
    )
    service = DocumentUnderstandingService()
    result = service.analyze_text(text)
    context = service.build_context(service.text_document(text), result)
    assert context.clinical_context.examination == "MRI Abdomen & Pelvis"


def test_incidental_imaging_does_not_override_stronger_non_radiology_structure():
    cases = (
        ("DISCHARGE SUMMARY\nHOSPITAL COURSE: MRI pelvis demonstrated no acute issue.\nDISCHARGE DIAGNOSIS: Stable\nDISCHARGE MEDICATIONS: None\nFOLLOW-UP: Clinic", DocumentType.DISCHARGE_SUMMARY),
        ("EMERGENCY DEPARTMENT\nTRIAGE: Urgent\nCHIEF COMPLAINT: Headache\nED COURSE: CT head performed.\nDISPOSITION: Home", DocumentType.EMERGENCY_REPORT),
    )
    for text, expected in cases:
        assert DocumentClassifier.classify(text).document_type is expected
    assert DocumentClassifier.classify("Clinical note: prior MRI brain was reviewed.").document_type is DocumentType.UNKNOWN


def test_existing_english_and_arabic_radiology_patterns_remain_supported():
    samples = (
        "RADIOLOGY REPORT\nTECHNIQUE: CT chest\nFINDINGS: Clear\nIMPRESSION: Normal",
        "قسم الأشعة\nالفحص: أشعة مقطعية على الصدر بالصبغة\nالطريقة: فحص مقطعي\nالنتائج: طبيعية\nالانطباع: لا مشكلة\nطبيب الأشعة: د. س",
    )
    assert all(DocumentClassifier.classify(text).document_type is DocumentType.RADIOLOGY_REPORT for text in samples)


@pytest.mark.parametrize(("study", "expected"), (
    ("CT chest with axial reconstructions", DocumentSubtype.CT),
    ("MRI brain using T1 and T2 sequences", DocumentSubtype.MRI),
    ("chest X-ray radiograph", DocumentSubtype.X_RAY),
    ("abdominal ultrasound sonography", DocumentSubtype.ULTRASOUND),
    ("Doppler ultrasound of an extremity", DocumentSubtype.DOPPLER),
    ("breast mammography mammogram", DocumentSubtype.MAMMOGRAPHY),
    ("nuclear medicine PET scan whole body", DocumentSubtype.NUCLEAR_MEDICINE),
))
def test_compact_modality_validation_matrix(study, expected):
    text = f"RADIOLOGY REPORT\nTECHNIQUE: {study}\nFINDINGS: No acute finding\nIMPRESSION: Completed study"
    result = DocumentClassifier.classify(text)
    assert result.document_type is DocumentType.RADIOLOGY_REPORT
    assert result.document_subtype is expected


def test_discharge_context_dominates_even_with_embedded_imaging_excerpt():
    text = (
        "DISCHARGE SUMMARY\nHOSPITAL COURSE: MRI pelvis was reviewed. The imported imaging excerpt said "
        "Findings: stable lesion. Impression: no acute change.\nDISCHARGE DIAGNOSIS: Stable disease\n"
        "DISCHARGE MEDICATIONS: Continue treatment\nCONDITION ON DISCHARGE: Stable"
    )
    assert DocumentClassifier.classify(text).document_type is DocumentType.DISCHARGE_SUMMARY
