from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.understanding.context_builder import DocumentContextBuilder
from backend.app.modules.medical_document_intelligence.understanding.service import DocumentUnderstandingService


ARABIC_RADIOLOGY = """قسم الأشعة
الفحص: أشعة مقطعية على الصدر بالصبغة
سبب الفحص: سعال مستمر
الطريقة: فحص مقطعي بعد حقن الصبغة
النتائج: لا توجد بؤر واضحة
الانطباع: لا توجد مشكلة حادة
طبيب الأشعة: د. عبدالله
CONFIDENTIAL MEDICAL DOCUMENT"""


def _context(text=ARABIC_RADIOLOGY):
    service = DocumentUnderstandingService()
    document = DocumentContent(text, "report.txt", "text/plain", ".txt", len(text.encode()))
    return DocumentContextBuilder.build(service.analyze_document(document), document)


def test_document_context_v1_constructs_radiology_semantics():
    context = _context()
    assert context.identity.healthcare_domain == "RADIOLOGY"
    assert context.clinical_context.modality == "CT"
    assert context.clinical_context.examination == "CT Chest"
    assert context.clinical_context.body_region == "CHEST"
    assert context.clinical_context.body_regions == ("CHEST",)
    assert context.clinical_context.contrast == "WITH_CONTRAST"
    assert context.provenance.knowledge_layer_version == "recognition-knowledge-v1"
    assert "RAD_MODALITY_CT" in context.provenance.concept_ids


def test_document_context_sections_have_semantic_roles_and_exact_boundaries():
    context = _context()
    assert [item.semantic_role for item in context.structure] == [
        "Examination", "Clinical Information", "Technique", "Findings", "Impression",
        "Radiologist / Authentication"
    ]
    assert all(item.start < item.end for item in context.structure)


def test_unknown_context_does_not_fabricate_clinical_attributes():
    context = _context("General administrative healthcare memo.")
    assert context.identity.healthcare_domain == "UNKNOWN"
    assert context.identity.document_subtype is None
    assert context.clinical_context.modality is None
    assert context.clinical_context.examination is None
    assert context.clinical_context.body_region is None
    assert context.clinical_context.contrast is None
    assert context.clinical_context.body_regions == ()


def test_understanding_api_serializes_context_and_journey_handoff():
    client = TestClient(app)
    response = client.post("/api/v1/understanding/analyze-text", json={"text": ARABIC_RADIOLOGY})
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_context"]["clinical_context"]["examination"] == "CT Chest"
    journey_id = payload["journey"]["journey_id"]
    retained = client.get(f"/api/v1/understanding/journeys/{journey_id}")
    assert retained.status_code == 200
    assert retained.json()["document_context"]["document"]["document_id"] == journey_id


def test_understand_to_protect_uses_retained_document_without_reupload(monkeypatch):
    client = TestClient(app)
    created = client.post("/api/v1/understanding/analyze-text", json={"text": ARABIC_RADIOLOGY}).json()
    journey_id = created["journey"]["journey_id"]

    class Response:
        def __init__(self):
            self.metadata = {}

    captured = {}
    def fake_process(text, policy):
        captured.update(text=text, policy=policy.value)
        return Response()
    monkeypatch.setattr(
        "backend.app.modules.medical_document_intelligence.api.understanding.privacy_service.process",
        fake_process,
    )
    response = client.post(
        f"/api/v1/understanding/journeys/{journey_id}/protect",
        json={"policy": "mednexus_research"},
    )
    assert response.status_code == 200
    assert captured == {"text": ARABIC_RADIOLOGY, "policy": "mednexus_research"}
    assert response.json()["metadata"]["journey_id"] == journey_id


def test_invalid_or_expired_journey_is_clear():
    client = TestClient(app)
    response = client.get("/api/v1/understanding/journeys/not-present")
    assert response.status_code == 404


def test_file_journey_preserves_original_source_name():
    client = TestClient(app)
    response = client.post(
        "/api/v1/understanding/analyze-file",
        files={"file": ("Radiology_Report_CT_Chest.txt", ARABIC_RADIOLOGY.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_context"]["document"]["source_name"] == "Radiology_Report_CT_Chest.txt"
    retained = client.get(f"/api/v1/understanding/journeys/{payload['journey']['journey_id']}").json()
    assert retained["document_context"]["document"]["source_name"] == "Radiology_Report_CT_Chest.txt"
    assert payload["journey"]["continue_to_protect"].endswith("#workspace")


def test_english_radiology_context_supports_same_journey_contract():
    text = "RADIOLOGY REPORT\nEXAMINATION: Chest imaging\nTECHNIQUE:\nCT chest with contrast, axial images\nFINDINGS:\nClear lungs\nIMPRESSION:\nNormal"
    client = TestClient(app)
    payload = client.post("/api/v1/understanding/analyze-text", json={"text": text}).json()
    assert payload["document_context"]["clinical_context"] == {
        "modality": "CT", "examination": "CT Chest", "body_region": "CHEST", "body_regions": ["CHEST"],
        "contrast": "WITH_CONTRAST", "techniques": ["Multiplanar imaging"], "clinical_purpose": None,
        "domain_concepts": payload["document_context"]["clinical_context"]["domain_concepts"],
        "attributes": payload["document_context"]["clinical_context"]["attributes"],
    }
    assert client.get(f"/api/v1/understanding/journeys/{payload['journey']['journey_id']}").status_code == 200
