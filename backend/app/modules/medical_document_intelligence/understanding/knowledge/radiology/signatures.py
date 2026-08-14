from ...models import DocumentDomain, DocumentType
from ..models import RecognitionConceptCategory as Category, RecognitionSignal, RecognitionSignature


RADIOLOGY_REPORT_SIGNATURE = RecognitionSignature(
    "RAD_SIGNATURE_REPORT_V1", DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT,
    strong_identity_concepts=("RAD_DOC_REPORT", "RAD_SERVICE_CONTEXT"),
    structural_concepts=("RAD_SECTION_EXAMINATION", "RAD_SECTION_TECHNIQUE", "RAD_SECTION_FINDINGS", "RAD_SECTION_IMPRESSION"),
    supporting_concepts=("RAD_AUTHOR_RADIOLOGIST", "RAD_MODALITY_CT", "RAD_MODALITY_MRI", "RAD_MODALITY_XRAY",
                         "RAD_MODALITY_ULTRASOUND", "RAD_MODALITY_MAMMOGRAPHY", "RAD_MODALITY_NUCLEAR_MEDICINE"),
    conflict_document_types=(DocumentType.EMERGENCY_REPORT, DocumentType.DISCHARGE_SUMMARY, DocumentType.ADMISSION_NOTE),
)

_CATEGORY_MAP = {
    Category.DOCUMENT_IDENTITY: "title", Category.SERVICE_CONTEXT: "context",
    Category.SECTION: "section", Category.MODALITY: "modality",
    Category.PROCEDURE: "procedure", Category.AUTHOR_ROLE: "role",
    Category.STRUCTURAL_SIGNAL: "structure",
}


def radiology_signals(concepts) -> tuple[RecognitionSignal, ...]:
    return tuple(
        RecognitionSignal(alias, concept.evidence_strength, _CATEGORY_MAP[concept.category],
                          concept.concept_id, concept.external_references)
        for concept in concepts for alias in concept.aliases
    )
