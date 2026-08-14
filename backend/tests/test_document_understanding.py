from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.understanding.document_classifier import DocumentClassifier
from backend.app.modules.medical_document_intelligence.understanding.language_detector import LanguageDetector
from backend.app.modules.medical_document_intelligence.understanding.models import (
    ConfidenceBand,
    DocumentDomain,
    DocumentLanguage,
    DocumentSubtype,
    DocumentType,
)
from backend.app.modules.medical_document_intelligence.understanding.section_detector import SectionDetector
from backend.app.modules.medical_document_intelligence.understanding.service import DocumentUnderstandingService


SAMPLES = {
    DocumentType.RADIOLOGY_REPORT: "RADIOLOGY REPORT\nTECHNIQUE:\nCT chest\nFINDINGS:\nClear lungs\nIMPRESSION:\nNormal study",
    DocumentType.PATHOLOGY_REPORT: "PATHOLOGY REPORT\nSPECIMEN:\nColon biopsy\nGROSS DESCRIPTION:\nFragment\nMICROSCOPIC DESCRIPTION:\nBenign\nFINAL DIAGNOSIS:\nNo malignancy",
    DocumentType.LABORATORY_REPORT: "LABORATORY REPORT\nTEST RESULT UNITS REFERENCE RANGE\nHemoglobin 13 g/dL 12-16\nCollected and validated",
    DocumentType.EMERGENCY_REPORT: "EMERGENCY DEPARTMENT\nCHIEF COMPLAINT:\nPain\nTRIAGE:\nStable\nVITAL SIGNS:\nNormal\nED COURSE:\nObserved\nDISPOSITION:\nHome",
    DocumentType.ADMISSION_NOTE: "ADMISSION NOTE\nREASON FOR ADMISSION:\nFever\nADMITTING DIAGNOSIS:\nPneumonia\nASSESSMENT AND PLAN:\nAntibiotics",
    DocumentType.DISCHARGE_SUMMARY: "DISCHARGE SUMMARY\nHOSPITAL COURSE:\nImproved\nDISCHARGE DIAGNOSIS:\nPneumonia\nDISCHARGE MEDICATIONS:\nNone\nCONDITION ON DISCHARGE:\nStable",
    DocumentType.PUBLIC_HEALTH_DOCUMENT: "PUBLIC HEALTH NOTIFICATION\nCASE NOTIFICATION:\nConfirmed case\nEPIDEMIOLOGICAL INVESTIGATION:\nContact tracing",
}


@pytest.mark.parametrize(("text", "expected"), [
    ("Clinical report findings and impression", DocumentLanguage.ENGLISH),
    ("تقرير طبي ونتائج الفحص", DocumentLanguage.ARABIC),
    ("Clinical report نتائج الفحص", DocumentLanguage.MIXED),
    ("123", DocumentLanguage.UNKNOWN),
])
def test_language_detection(text, expected):
    assert LanguageDetector.detect(text) is expected


def test_section_detection_preserves_heading_offsets_and_aliases():
    text = "Header\nHPI:\nPain for two days\nFINDINGS: Normal"
    sections = SectionDetector.detect(text)
    assert [section.canonical_name for section in sections] == [
        "history_of_present_illness", "findings"
    ]
    assert sections[0].original_heading == "HPI"
    assert text[sections[0].start:sections[0].end].startswith("HPI:")
    assert sections[0].end == sections[1].start
    assert sections[1].end == len(text)


def test_section_detection_handles_crlf_repeats_and_ignores_prose():
    text = "The findings remain stable.\r\nFINDINGS:\r\nFirst\r\nFINDINGS: Second"
    sections = SectionDetector.detect(text)
    assert [section.canonical_name for section in sections] == ["findings", "findings"]
    assert sections[0].end == sections[1].start
    assert sections[1].end == len(text)


@pytest.mark.parametrize("expected_type", tuple(SAMPLES))
def test_classifier_recognizes_initial_document_types(expected_type):
    result = DocumentClassifier.classify(SAMPLES[expected_type])
    assert result.document_type is expected_type
    assert result.domain is not DocumentDomain.UNKNOWN
    assert result.confidence_band in {ConfidenceBand.MEDIUM, ConfidenceBand.HIGH}
    assert result.evidence


def test_radiology_subtype_requires_unambiguous_modality():
    ct = DocumentClassifier.classify(SAMPLES[DocumentType.RADIOLOGY_REPORT])
    conflict = DocumentClassifier.classify(
        SAMPLES[DocumentType.RADIOLOGY_REPORT].replace("CT chest", "CT and MRI chest")
    )
    assert ct.document_subtype is DocumentSubtype.CT
    assert conflict.document_subtype is DocumentSubtype.UNKNOWN


def test_radiology_subtype_ignores_incidental_modality_history():
    text = "RADIOLOGY REPORT\nFINDINGS:\nNormal chest radiograph. Prior MRI was reviewed.\nIMPRESSION:\nNo acute disease"
    result = DocumentClassifier.classify(text)
    assert result.document_subtype is DocumentSubtype.UNKNOWN


@pytest.mark.parametrize("text", [
    "Patient reviewed today. Continue hydration.",
    "Findings",
    "RADIOLOGY REPORT\nIMPRESSION:\nNormal\nPATHOLOGY REPORT\nFINAL DIAGNOSIS:\nBenign",
])
def test_weak_or_conflicting_evidence_returns_unknown(text):
    result = DocumentClassifier.classify(text)
    assert result.document_type is DocumentType.UNKNOWN
    assert result.confidence_band in {ConfidenceBand.LOW, ConfidenceBand.UNKNOWN}


@pytest.mark.parametrize("text", [
    "The patient has tuberculosis and remains on treatment.",
    "Routine clinic notification was sent after surveillance follow-up.",
    "Surveillance",
])
def test_public_health_is_not_inferred_from_isolated_context(text):
    assert DocumentClassifier.classify(text).document_type is DocumentType.UNKNOWN


def test_section_terms_in_prose_are_not_structural_evidence():
    text = "The findings and impression were discussed during a routine visit."
    result = DocumentClassifier.classify(text)
    assert result.document_type is DocumentType.UNKNOWN
    assert not result.evidence


def test_heading_alias_contributes_structural_evidence():
    text = "EMERGENCY DEPARTMENT\nHPI:\nAcute chest pain\nTRIAGE:\nUrgent"
    result = DocumentClassifier.classify(text)
    assert any(item.signal == "history of present illness" for item in result.evidence)


def test_confidence_distinguishes_strong_moderate_and_isolated_evidence():
    strong = DocumentClassifier.classify(SAMPLES[DocumentType.RADIOLOGY_REPORT])
    moderate = DocumentClassifier.classify("RADIOLOGY REPORT\nIMPRESSION:\nNormal")
    isolated = DocumentClassifier.classify("RADIOLOGY REPORT")
    assert strong.confidence_band is ConfidenceBand.HIGH
    assert moderate.confidence_band is ConfidenceBand.MEDIUM
    assert isolated.document_type is DocumentType.UNKNOWN
    assert isolated.confidence_band is ConfidenceBand.LOW


def test_language_detector_ignores_tiny_incidental_other_script_fragment():
    english = "This is a complete English clinical report with detailed findings. نعم"
    arabic = "هذا تقرير سريري عربي كامل يحتوي على نتائج الفحص بالتفصيل. CT"
    assert LanguageDetector.detect(english) is DocumentLanguage.ENGLISH
    assert LanguageDetector.detect(arabic) is DocumentLanguage.ARABIC


def test_primary_arabic_language_ignores_short_english_technical_footer():
    text = (
        "قسم الأشعة\nالفحص: أشعة مقطعية على الصدر\nالطريقة: بعد حقن الصبغة\n"
        "النتائج: لا توجد مشكلة حادة\nالانطباع: فحص طبيعي\n"
        "CONFIDENTIAL MEDICAL DOCUMENT\nGenerated by Hospital System"
    )
    assert LanguageDetector.detect(text) is DocumentLanguage.ARABIC


def test_substantial_bilingual_content_remains_mixed():
    text = "Clinical history and examination findings. التاريخ السريري ونتائج الفحص الطبي."
    assert LanguageDetector.detect(text) is DocumentLanguage.MIXED


def test_representative_arabic_ct_radiology_report_is_recognized():
    text = (
        "قسم الأشعة\nالفحص: أشعة مقطعية على الصدر بالصبغة\n"
        "سبب الفحص: سعال مستمر\nالطريقة: فحص مقطعي بعد حقن الصبغة.\n"
        "النتائج:\nلا توجد بؤر التهاب.\nالانطباع:\nلا توجد مشكلة حادة.\n"
        "طبيب الأشعة: د. عبدالله الفهد\nCONFIDENTIAL MEDICAL DOCUMENT"
    )
    result = DocumentUnderstandingService().analyze_text(text)
    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_type is DocumentType.RADIOLOGY_REPORT
    assert result.document_subtype is DocumentSubtype.CT
    assert result.language is DocumentLanguage.ARABIC
    assert result.confidence_band is ConfidenceBand.HIGH
    assert {"technique", "findings", "impression"} <= {
        section.canonical_name for section in result.sections
    }


def test_real_arabic_radiology_validation_report():
    path = (
        Path(__file__).resolve().parents[2]
        / "Validation/MedNexus_Validation_Dataset_v2.0_240_reports/01_TXT"
        / "MNX-01-03_Radiology_Arabic.txt"
    )
    result = DocumentUnderstandingService().analyze_file(path)
    assert result.domain is DocumentDomain.RADIOLOGY
    assert result.document_type is DocumentType.RADIOLOGY_REPORT
    assert result.document_subtype is DocumentSubtype.CT
    assert result.language is DocumentLanguage.ARABIC
    assert result.confidence_band is ConfidenceBand.HIGH


@pytest.mark.parametrize("text", [
    "The patient was seen in clinic. Prior CT chest was reviewed. Continue treatment.",
    "تمت مراجعة نتائج الأشعة المقطعية السابقة خلال الزيارة واستمر العلاج.",
])
def test_incidental_ct_mention_does_not_create_radiology_report(text):
    assert DocumentClassifier.classify(text).document_type is DocumentType.UNKNOWN


def test_emergency_structure_outweighs_incidental_arabic_ct_mention():
    text = (
        "قسم الطوارئ\nالشكوى الرئيسية: ألم في الصدر\nالفرز: عاجل\n"
        "HISTORY OF PRESENT ILLNESS:\nتمت مراجعة أشعة مقطعية سابقة\n"
        "VITAL SIGNS:\nStable\nED COURSE:\nObserved\nDISPOSITION:\nHome"
    )
    assert DocumentClassifier.classify(text).document_type is DocumentType.EMERGENCY_REPORT


def test_service_returns_sections_routing_and_serializable_contract():
    result = DocumentUnderstandingService().analyze_text(SAMPLES[DocumentType.RADIOLOGY_REPORT])
    payload = result.to_dict()
    assert payload["domain"] == "RADIOLOGY"
    assert payload["routing"]["extraction_profile"] == "radiology_extraction"
    assert payload["routing"]["manual_review_required"] is False
    assert "impression" in [section["canonical_name"] for section in payload["sections"]]


def test_unknown_routes_to_manual_review():
    result = DocumentUnderstandingService().analyze_text("General clinical note")
    assert result.routing.manual_review_required is True
    assert result.routing.processing_capabilities == ("PROTECT",)


def test_document_content_metadata_and_warnings_survive():
    document = DocumentContent(
        text=SAMPLES[DocumentType.LABORATORY_REPORT], source_name="lab.txt",
        media_type="text/plain", extension=".txt", file_size=100,
        metadata={"extractor": "txt"}, warnings=("source warning",),
    )
    result = DocumentUnderstandingService().analyze_document(document)
    assert result.metadata["source_name"] == "lab.txt"
    assert result.metadata["extraction_metadata"] == {"extractor": "txt"}
    assert result.warnings == ("source warning",)


def test_existing_txt_extractor_integrates_with_understanding(tmp_path: Path):
    path = tmp_path / "report.txt"
    path.write_text(SAMPLES[DocumentType.DISCHARGE_SUMMARY], encoding="utf-8")
    result = DocumentUnderstandingService().analyze_file(path)
    assert result.document_type is DocumentType.DISCHARGE_SUMMARY
    assert result.metadata["extension"] == ".txt"


client = TestClient(app)


def test_understanding_text_api_returns_structured_result():
    response = client.post(
        "/api/v1/understanding/analyze-text",
        json={"text": SAMPLES[DocumentType.EMERGENCY_REPORT]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_type"] == "EMERGENCY_REPORT"
    assert payload["routing"]["manual_review_required"] is False


def test_understanding_text_api_returns_unknown_as_success():
    response = client.post(
        "/api/v1/understanding/analyze-text",
        json={"text": "General clinical note with no document-specific structure."},
    )
    assert response.status_code == 200
    assert response.json()["document_type"] == "UNKNOWN"


def test_understanding_text_api_rejects_empty_text():
    response = client.post(
        "/api/v1/understanding/analyze-text",
        json={"text": ""},
    )
    assert response.status_code == 422


def test_understanding_file_api_uses_existing_extraction():
    content = SAMPLES[DocumentType.PATHOLOGY_REPORT].encode()
    response = client.post(
        "/api/v1/understanding/analyze-file",
        files={"file": ("pathology.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_type"] == "PATHOLOGY_REPORT"
    assert payload["metadata"]["source_name"] == "pathology.txt"


@pytest.mark.parametrize(("filename", "content"), [("report.csv", b"data"), ("empty.txt", b"")])
def test_understanding_file_api_rejects_unsupported_or_empty_files(filename, content):
    response = client.post(
        "/api/v1/understanding/analyze-file",
        files={"file": (filename, content, "application/octet-stream")},
    )
    assert response.status_code == 400


def test_understanding_frontend_route_and_assets_are_available():
    page = client.get("/understanding")
    styles = client.get("/understanding-styles.css")
    script = client.get("/understanding.js")
    assert page.status_code == styles.status_code == script.status_code == 200
    assert "Document Understanding Workspace — MedNexus" in page.text
    assert "Medical Document" in page.text
    assert "Understanding Workspace." in page.text
    assert "/api/v1/understanding/analyze-text" in script.text
    assert "/api/v1/understanding/analyze-file" in script.text
    assert "Recognized sections" in page.text
    assert "CLINICAL CONTEXT IDENTIFIED" in page.text
    assert "READY FOR MEDNEXUS" in page.text
    assert "Continue to Privacy Protection" in page.text
    assert "Technical details" in page.text
    assert "<details class=\"technical-details\">" in page.text
    assert "Radiology Report" in script.text
    assert "result-primary" in page.text
    assert "MEDNEXUS DOCUMENT CONTEXT" in page.text


def test_progressive_result_reveal_is_frontend_only_and_preserves_authoritative_output():
    privacy = client.get("/privacy")
    helper = client.get("/progressive-result.js")
    assert privacy.status_code == helper.status_code == 200
    assert 'src="/progressive-result.js"' in privacy.text
    assert "MedNexusProgressiveResult.reveal" in privacy.text
    assert "Show full result" in privacy.text
    assert "last=n.protectedText" in privacy.text
    assert "navigator.clipboard.writeText(last)" in privacy.text
    assert "prefers-reduced-motion" in helper.text
    assert "target.textContent=fullText" in helper.text
    assert "target.textContent=current" in helper.text
    assert "current=chunks[index++]" in helper.text
    assert "lineChunks" in helper.text
    assert "token" not in helper.text.lower()


def test_progressive_reveal_keeps_placeholders_as_complete_line_chunks():
    helper = client.get("/progressive-result.js").text
    assert "match(/[^\\n]*\\n|[^\\n]+$/g)" in helper
    assert "current+=chunks[index++]" in helper
    assert "target.textContent=current" in helper


def test_privacy_handoff_status_and_lifecycle_are_visible_without_breaking_standalone():
    page = client.get("/privacy").text
    assert "DOCUMENT RECEIVED" in page
    assert "MedNexus Document Context available" in page
    assert "No re-upload required" in page
    assert "UNDERSTAND" in page and "PRIVACY PROTECTION" in page
    assert "loadJourney" in page
    assert "scrollIntoView({block:'start'})" in page
    assert "Protecting document…" in page
    assert "toFixed(2)" in page
    assert "forceRevealMotion" in page
    assert "activeJourneyId=null" in page
    assert "if(activeJourneyId)loadJourney()" in page
    assert ".input-panel.journey-active>#manualInputTabs" in page
    assert ".input-panel.journey-active>#textInput" in page
    assert ".input-panel.journey-active>#uploadBox" in page
    assert ".input-panel.journey-active>.input-step{display:none}" in page
    assert "#handoffStatus:not([hidden])~#manualInputTabs" in page
    assert "#handoffStatus:not([hidden])~#textInput" in page
    assert "#handoffStatus:not([hidden])~#uploadBox" in page
    assert "classList.remove('journey-active')" in page


def test_homepage_lists_live_capabilities_in_canonical_order():
    page = client.get("/app")
    recognition = page.text.index("Document Recognition")
    privacy = page.text.index("Clinical Privacy Policy Engine", recognition)
    extraction = page.text.index("Clinical Extraction", privacy)
    public_health = page.text.index("Public Health Intelligence", extraction)
    assert recognition < privacy < extraction < public_health
    assert 'href="/understanding"' in page.text
