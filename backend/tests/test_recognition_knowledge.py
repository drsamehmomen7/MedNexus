from backend.app.modules.medical_document_intelligence.understanding.document_classifier import DocumentClassifier
from backend.app.modules.medical_document_intelligence.understanding.knowledge.models import RecognitionConceptCategory
from backend.app.modules.medical_document_intelligence.understanding.knowledge.radiology import (
    RADIOLOGY_CONCEPTS,
    RADIOLOGY_REGISTRY,
    RADIOLOGY_REPORT_SIGNATURE,
)
from backend.app.modules.medical_document_intelligence.understanding.models import (
    DocumentDomain,
    DocumentType,
)


def test_radiology_registry_resolves_english_and_arabic_aliases():
    english = RADIOLOGY_REGISTRY.resolve("Computed Tomography", domain=DocumentDomain.RADIOLOGY)
    arabic = RADIOLOGY_REGISTRY.resolve("التصوير المقطعي", category=RecognitionConceptCategory.MODALITY)

    assert english[0].concept_id == "RAD_MODALITY_CT"
    assert arabic[0].concept_id == "RAD_MODALITY_CT"


def test_radiology_concepts_have_stable_ids_and_reference_families():
    assert len({concept.concept_id for concept in RADIOLOGY_CONCEPTS}) == len(RADIOLOGY_CONCEPTS)
    assert all(concept.external_references for concept in RADIOLOGY_CONCEPTS)
    assert all(not reference.startswith("http") for concept in RADIOLOGY_CONCEPTS for reference in concept.external_references)


def test_radiology_signature_requires_combined_evidence():
    incidental = RADIOLOGY_REPORT_SIGNATURE.assess({"RAD_MODALITY_CT"})
    report = RADIOLOGY_REPORT_SIGNATURE.assess({
        "RAD_SERVICE_CONTEXT", "RAD_SECTION_TECHNIQUE", "RAD_SECTION_FINDINGS", "RAD_MODALITY_CT"
    })

    assert incidental.satisfied is False
    assert report.satisfied is True


def test_classifier_evidence_exposes_mednexus_concept_traceability():
    outcome = DocumentClassifier.classify(
        "RADIOLOGY REPORT\nTECHNIQUE:\nCT chest\nFINDINGS:\nClear lungs\nIMPRESSION:\nNormal study"
    )

    radiology_evidence = [item for item in outcome.evidence if item.candidate is DocumentType.RADIOLOGY_REPORT]
    assert radiology_evidence
    assert all(item.concept_id for item in radiology_evidence)
    assert all(item.reference_systems for item in radiology_evidence)


def test_arabic_radiology_signature_generalizes_beyond_validation_report():
    outcome = DocumentClassifier.classify(
        "قسم الأشعة\nالفحص: التصوير بالرنين المغناطيسي للدماغ\n"
        "التقنية:\nمقاطع متعددة\nالموجودات:\nلا توجد كتلة\nالخلاصة:\nفحص طبيعي\nأخصائي الأشعة: د. س"
    )

    assert outcome.domain is DocumentDomain.RADIOLOGY
    assert outcome.document_type is DocumentType.RADIOLOGY_REPORT


def test_incidental_ct_remains_insufficient_after_knowledge_refactor():
    outcome = DocumentClassifier.classify(
        "GENERAL CLINICAL NOTE\nThe previous CT chest result was reviewed during follow-up."
    )

    assert outcome.document_type is DocumentType.UNKNOWN
