from __future__ import annotations

from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent

from .context_models import (
    ClinicalContext, ContextProvenance, DocumentDescriptor, DocumentIdentityContext,
    MedNexusDocumentContext, PrivacyContext, PrivacyRegion, ProcessingContext, SemanticSection,
)
from .knowledge.radiology import RADIOLOGY_REGISTRY
from .knowledge.radiology import RadiologyReasoner
from .reference_model.runtime import build_active_reference_registry
from .models import DocumentDomain, DocumentSubtype, DocumentUnderstandingResult


SECTION_ROLES = {
    "patient_information": "Patient / Administrative Information",
    "procedure_information": "Procedure Information",
    "radiology_examination": "Examination",
    "clinical_history": "Clinical Indication", "clinical_information": "Clinical Information",
    "technique": "Technique", "findings": "Findings", "impression": "Impression",
    "radiologist_authentication": "Radiologist / Authentication",
}
PRIVACY_ROLES = {
    "patient_information": "likely_identifier_bearing",
    "radiologist_authentication": "provider_authentication",
    "authorization": "provider_authentication",
}
_BODY_REGION_IDS = {
    "RAD_ANAT_HEAD": "HEAD", "RAD_ANAT_BRAIN": "BRAIN", "RAD_ANAT_NECK": "NECK",
    "RAD_ANAT_CHEST": "CHEST", "RAD_ANAT_ABDOMEN": "ABDOMEN", "RAD_ANAT_PELVIS": "PELVIS",
    "RAD_ANAT_SPINE": "SPINE", "RAD_ANAT_BREAST": "BREAST",
    "RAD_ANAT_EXTREMITY": "EXTREMITY", "RAD_ANAT_WHOLE_BODY": "WHOLE_BODY",
}
_TECHNIQUE_NAMES = {
    "RAD_TECH_T1": "T1-weighted imaging", "RAD_TECH_T2": "T2-weighted imaging",
    "RAD_TECH_FLAIR": "FLAIR imaging", "RAD_TECH_STIR": "STIR imaging",
    "RAD_TECH_DWI": "Diffusion-weighted imaging",
    "RAD_TECH_FAT_SUPPRESSION": "Fat-suppressed imaging",
    "RAD_ACQ_MULTIPLANAR": "Multiplanar imaging",
}


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
                                    result.confidence, result.confidence_band.value, result.document_nature.value),
            sections, cls._clinical_context(result, document.text), PrivacyContext(privacy),
            ProcessingContext(result.routing.privacy_profile_candidate, result.routing.extraction_profile,
                              result.routing.terminology_profile, result.routing.processing_capabilities,
                              result.routing.manual_review_required),
            ContextProvenance(cls.KNOWLEDGE_LAYER_VERSION,
                              tuple(dict.fromkeys(item.concept_id for item in result.evidence if item.concept_id)),
                              tuple({"candidate": item.candidate.value, "concept_id": item.concept_id,
                                     "signal": item.signal, "category": item.category, "weight": item.weight,
                                     "matched": item.reference, "reference_systems": list(item.reference_systems)}
                                    | {"external_mappings": [list(value) for value in item.external_mappings],
                                       "relationships": [list(value) for value in item.relationships]}
                                    for item in result.evidence), result.warnings),
        )

    @classmethod
    def _clinical_context(cls, result: DocumentUnderstandingResult, text: str) -> ClinicalContext:
        if result.domain is not DocumentDomain.RADIOLOGY:
            return ClinicalContext()
        assessment = RadiologyReasoner.assess(text, result.sections)
        modality = None if result.document_subtype is DocumentSubtype.UNKNOWN else result.document_subtype.value
        modality_spans = assessment.frame.modality_signals
        broad_anatomy = [item for item in assessment.frame.anatomy_signals if item.concept_id in _BODY_REGION_IDS]
        if modality_spans:
            broad_anatomy.sort(key=lambda item: (
                min(max(modality.start - item.end, item.start - modality.end, 0) for modality in modality_spans),
                item.start,
            ))
        regions = tuple(dict.fromkeys(_BODY_REGION_IDS[item.concept_id] for item in broad_anatomy))
        region = regions[0] if regions else None
        contrast_ids = {item.concept_id for item in assessment.frame.contrast_signals}
        if "RAD_CONTRAST_PRE_POST" in contrast_ids or {
            "RAD_CONTRAST_WITH", "RAD_CONTRAST_WITHOUT"
        } <= contrast_ids:
            contrast = "PRE_AND_POST_CONTRAST"
        elif "RAD_CONTRAST_WITH" in contrast_ids:
            contrast = "WITH_CONTRAST"
        elif "RAD_CONTRAST_WITHOUT" in contrast_ids:
            contrast = "WITHOUT_CONTRAST"
        else:
            contrast = None
        region_label = " & ".join(item.title() for item in regions)
        examination = " ".join(filter(None, (modality, region_label))) or None
        techniques = tuple(dict.fromkeys(
            _TECHNIQUE_NAMES[item.concept_id]
            for item in assessment.frame.technique_signals + assessment.frame.acquisition_signals
            if item.concept_id in _TECHNIQUE_NAMES
        ))
        purpose_ids = {item.concept_id for item in assessment.frame.clinical_purpose_signals}
        purpose = next((label for concept_id, label in (
            ("RAD_PURPOSE_STAGING", "Oncologic Staging"),
            ("RAD_PURPOSE_SCREENING", "Screening"),
            ("RAD_PURPOSE_POST_TREATMENT", "Post-treatment Assessment"),
            ("RAD_PURPOSE_FOLLOWUP", "Follow-up / Surveillance"),
            ("RAD_PURPOSE_DIAGNOSTIC", "Diagnostic Evaluation"),
        ) if concept_id in purpose_ids), None)
        concepts = tuple(dict.fromkeys(
            RADIOLOGY_REGISTRY.get(item.concept_id).canonical_name
            for item in result.evidence if item.concept_id and item.concept_id.startswith("RAD_")
        ))
        return ClinicalContext(modality, examination, region, regions, contrast, techniques, purpose, concepts,
                               {"recognized_sections": [s.canonical_name for s in result.sections],
                                "authoritative_anatomy": cls._authoritative_anatomy(assessment),
                                "evidence_family_count": sum(bool(getattr(assessment.frame, field))
                                                             for field in assessment.frame.__dataclass_fields__)})

    @staticmethod
    def _authoritative_anatomy(assessment) -> str | None:
        """Preserve the nearest fine-grained authoritative anatomy without replacing broad routing regions."""
        if not assessment.frame.modality_signals or not assessment.frame.anatomy_signals:
            return None
        registry = build_active_reference_registry()
        modality = min(assessment.frame.modality_signals, key=lambda item: item.start)
        specific = [item for item in assessment.frame.anatomy_signals if item.concept_id not in _BODY_REGION_IDS]
        if not specific:
            return None
        ranked = sorted(
            specific,
            key=lambda item: (
                max(modality.start - item.end, item.start - modality.end, 0),
                -(item.end - item.start),
                item.start,
            ),
        )
        nearest = ranked[0]
        distance = max(modality.start - nearest.end, nearest.start - modality.end, 0)
        if distance > 120:
            return None
        try:
            return registry.concept(nearest.concept_id).canonical_name
        except KeyError:
            return None
