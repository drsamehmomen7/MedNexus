from __future__ import annotations

from ...models import DocumentDomain
from ..models import RecognitionConcept, RecognitionConceptCategory as Category
from ..references import ReferenceFamily as Ref
from ..registry import RecognitionKnowledgeRegistry


def _refs(*items: Ref) -> tuple[str, ...]:
    return tuple(item.value for item in items)


RADIOLOGY_CONTEXT_CONCEPTS = (
    RecognitionConcept("RAD_DOC_REPORT", "Radiology report", Category.DOCUMENT_IDENTITY, DocumentDomain.RADIOLOGY,
                       "radiology report", "تقرير الأشعة", ("imaging report",), evidence_strength=5,
                       external_references=_refs(Ref.LOINC_DOCUMENT_ONTOLOGY, Ref.DICOM_SR, Ref.RADREPORT)),
    RecognitionConcept("RAD_SERVICE_CONTEXT", "Radiology service", Category.SERVICE_CONTEXT, DocumentDomain.RADIOLOGY,
                       "radiology department", "قسم الأشعة", evidence_strength=4,
                       external_references=_refs(Ref.LOINC_DOCUMENT_ONTOLOGY, Ref.DICOM)),
    RecognitionConcept("RAD_AUTHOR_RADIOLOGIST", "Radiologist", Category.AUTHOR_ROLE, DocumentDomain.RADIOLOGY,
                       "radiologist", "طبيب الأشعة", aliases_ar=("اختصاصي الأشعة", "أخصائي الأشعة"), evidence_strength=2,
                       external_references=_refs(Ref.DICOM_SR, Ref.HL7_CDA, Ref.SNOMED_CT)),
)

# Composed after section/modality definitions are imported by the package.
from .modalities import RADIOLOGY_MODALITY_CONCEPTS  # noqa: E402
from .sections import RADIOLOGY_SECTION_CONCEPTS  # noqa: E402

RADIOLOGY_CONCEPTS = RADIOLOGY_CONTEXT_CONCEPTS + RADIOLOGY_SECTION_CONCEPTS + RADIOLOGY_MODALITY_CONCEPTS
RADIOLOGY_REGISTRY = RecognitionKnowledgeRegistry(RADIOLOGY_CONCEPTS)
