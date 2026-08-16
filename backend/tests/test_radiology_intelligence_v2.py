from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.understanding.document_classifier import DocumentClassifier
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology import (
    RadiologyEvidenceFrameBuilder, RadiologyReasoner,
)
import pytest

from backend.app.modules.medical_document_intelligence.understanding.models import (
    ConfidenceBand, DocumentDomain, DocumentSubtype, DocumentType,
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
    assert context.clinical_context.examination == "MRI Spine & Neck"
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
