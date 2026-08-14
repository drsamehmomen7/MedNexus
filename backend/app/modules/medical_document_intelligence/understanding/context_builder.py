from __future__ import annotations

import re
from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent

from .context_models import (
    ClinicalContext, ContextProvenance, DocumentDescriptor, DocumentIdentityContext,
    MedNexusDocumentContext, PrivacyContext, PrivacyRegion, ProcessingContext, SemanticSection,
)
from .knowledge.radiology import RADIOLOGY_REGISTRY
from .models import DocumentDomain, DocumentSubtype, DocumentUnderstandingResult


SECTION_ROLES = {
    "patient_information": "Patient / Administrative Information",
    "radiology_examination": "Examination",
    "clinical_history": "Clinical Indication",
    "technique": "Technique", "findings": "Findings", "impression": "Impression",
    "radiologist_authentication": "Radiologist / Authentication",
}
PRIVACY_ROLES = {
    "patient_information": "likely_identifier_bearing",
    "radiologist_authentication": "provider_authentication",
    "authorization": "provider_authentication",
}
BODY_REGIONS = (
    ("CHEST", ("chest", "thorax", "الصدر", "صدرية")),
    ("BRAIN", ("brain", "head", "الدماغ", "الرأس")),
    ("ABDOMEN", ("abdomen", "abdominal", "البطن")),
    ("PELVIS", ("pelvis", "الحوض")),
    ("SPINE", ("spine", "العمود الفقري")),
)


class DocumentContextBuilder:
    KNOWLEDGE_LAYER_VERSION = "recognition-knowledge-v1"

    @classmethod
    def build(
        cls, result: DocumentUnderstandingResult, document: DocumentContent, *, document_id: str | None = None
    ) -> MedNexusDocumentContext:
        sections = tuple(SemanticSection(
            item.canonical_name, SECTION_ROLES.get(item.canonical_name, item.canonical_name.replace("_", " ").title()),
            item.original_heading, item.start, item.end, item.confidence,
        ) for item in result.sections)
        privacy = tuple(PrivacyRegion(PRIVACY_ROLES[item.section_id], item.section_id, item.start, item.end)
                        for item in sections if item.section_id in PRIVACY_ROLES)
        return MedNexusDocumentContext(
            DocumentDescriptor(document_id or uuid4().hex, document.extension.lstrip(".") or "text",
                               result.language.value, document.source_name, document.media_type,
                               {"file_size": document.file_size, "page_count": document.page_count,
                                "line_count": document.line_count, **dict(document.metadata)}),
            DocumentIdentityContext(result.domain.value, result.document_type.value,
                                    None if result.document_subtype is DocumentSubtype.UNKNOWN else result.document_subtype.value,
                                    result.confidence, result.confidence_band.value),
            sections, cls._clinical_context(result, document.text), PrivacyContext(privacy),
            ProcessingContext(result.routing.privacy_profile_candidate, result.routing.extraction_profile,
                              result.routing.terminology_profile, result.routing.processing_capabilities,
                              result.routing.manual_review_required),
            ContextProvenance(cls.KNOWLEDGE_LAYER_VERSION,
                              tuple(dict.fromkeys(item.concept_id for item in result.evidence if item.concept_id)),
                              tuple({"candidate": item.candidate.value, "concept_id": item.concept_id,
                                     "signal": item.signal, "category": item.category, "weight": item.weight,
                                     "matched": item.reference, "reference_systems": list(item.reference_systems)}
                                    for item in result.evidence), result.warnings),
        )

    @classmethod
    def _clinical_context(cls, result: DocumentUnderstandingResult, text: str) -> ClinicalContext:
        if result.domain is not DocumentDomain.RADIOLOGY:
            return ClinicalContext()
        modality = None if result.document_subtype is DocumentSubtype.UNKNOWN else result.document_subtype.value
        region = next((name for name, aliases in BODY_REGIONS if any(
            re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE) for alias in aliases)), None)
        contrast = None
        if re.search(r"\bwith(?:out)?\s+(?:iv\s+)?contrast\b|بالصبغة|مع\s+(?:حقن\s+)?الصبغة", text, re.IGNORECASE):
            contrast = "WITH_CONTRAST" if not re.search(r"\bwithout\s+contrast\b|بدون\s+صبغة", text, re.IGNORECASE) else "WITHOUT_CONTRAST"
        examination = f"{modality} {region.title()}" if modality and region else modality
        concepts = tuple(dict.fromkeys(
            RADIOLOGY_REGISTRY.get(item.concept_id).canonical_name
            for item in result.evidence if item.concept_id and item.concept_id.startswith("RAD_")
        ))
        return ClinicalContext(modality, examination, region, contrast, concepts,
                               {"recognized_sections": [s.canonical_name for s in result.sections]})
