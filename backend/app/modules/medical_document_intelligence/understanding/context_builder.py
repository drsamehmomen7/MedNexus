from __future__ import annotations

from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent

from .context_models import (
    ClinicalContext, ContextProvenance, DocumentDescriptor, DocumentIdentityContext,
    MedNexusDocumentContext, PrivacyContext, PrivacyRegion, ProcessingContext,
    RadiologyClinicalContext, SemanticSection,
)
from .knowledge.radiology import RadiologyUnderstandingDecision
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
class DocumentContextBuilder:
    KNOWLEDGE_LAYER_VERSION = "recognition-knowledge-v1"

    @classmethod
    def build(
        cls, result: DocumentUnderstandingResult, document: DocumentContent, *, document_id: str | None = None
    ) -> MedNexusDocumentContext:
        radiology_decision = cls._selected_radiology_decision(result)
        sections = cls._semantic_sections(result, radiology_decision)
        privacy = tuple(PrivacyRegion(PRIVACY_ROLES[item.section_id], item.section_id, item.start, item.end)
                        for item in sections if item.section_id in PRIVACY_ROLES)
        canonical_subdomain = (
            radiology_decision.subdomain if radiology_decision is not None else None
        )
        return MedNexusDocumentContext(
            DocumentDescriptor(document_id or uuid4().hex, document.extension.lstrip(".") or "text",
                               result.language.value, document.source_name, document.media_type,
                               {"file_size": document.file_size, "page_count": document.page_count,
                                "line_count": document.line_count, **dict(document.metadata)}),
            DocumentIdentityContext(
                result.domain.value,
                result.document_type.value,
                None if result.document_subtype is DocumentSubtype.UNKNOWN else result.document_subtype.value,
                result.confidence,
                result.confidence_band.value,
                result.document_nature.value,
                subdomain_or_family=(canonical_subdomain.value if canonical_subdomain else None),
                document_review_required=result.routing.manual_review_required,
            ),
            sections, cls._clinical_context(result, radiology_decision), PrivacyContext(privacy),
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

    @staticmethod
    def _selected_radiology_decision(
        result: DocumentUnderstandingResult,
    ) -> RadiologyUnderstandingDecision | None:
        if result.domain is not DocumentDomain.RADIOLOGY:
            return None
        if result.radiology_decision is None:
            raise ValueError(
                "A selected Radiology result requires its authoritative "
                "RadiologyUnderstandingDecision."
            )
        return result.radiology_decision

    @staticmethod
    def _semantic_sections(
        result: DocumentUnderstandingResult,
        decision: RadiologyUnderstandingDecision | None,
    ) -> tuple[SemanticSection, ...]:
        if decision is None:
            return tuple(SemanticSection(
                item.canonical_name,
                SECTION_ROLES.get(
                    item.canonical_name, item.canonical_name.replace("_", " ").title()
                ),
                item.original_heading,
                item.start,
                item.end,
                item.confidence,
            ) for item in result.sections)
        return tuple(SemanticSection(
            item.section_id,
            SECTION_ROLES.get(
                item.section_id, item.section_id.replace("_", " ").title()
            ),
            item.original_heading,
            item.start,
            item.end,
            item.confidence,
            canonical_role=item.canonical_role,
            qualifiers=item.qualifiers,
            evidence_concept_ids=item.evidence_concept_ids,
            provenance=item.provenance,
        ) for item in decision.semantic_regions)

    @staticmethod
    def _clinical_context(
        result: DocumentUnderstandingResult,
        decision: RadiologyUnderstandingDecision | None,
    ) -> ClinicalContext:
        if result.domain is not DocumentDomain.RADIOLOGY:
            return ClinicalContext()
        if decision is None:  # guarded by _selected_radiology_decision
            raise ValueError("Radiology context serialization requires a decision.")

        compatibility_subtype = decision.compatibility_subtype
        legacy_modality = (
            None
            if compatibility_subtype is DocumentSubtype.UNKNOWN
            else compatibility_subtype.value
        )
        typed_modality = (
            None
            if compatibility_subtype is DocumentSubtype.UNKNOWN
            else decision.subdomain.value if decision.subdomain is not None else None
        )
        body_region = decision.body_regions[0] if decision.body_regions else None
        radiology = RadiologyClinicalContext(
            modality=typed_modality,
            examination=decision.examination,
            body_region=body_region,
            body_regions=decision.body_regions,
            contrast=decision.contrast,
            techniques=decision.techniques,
            recognized_sections=decision.recognized_sections,
            authoritative_anatomy=decision.authoritative_anatomy,
            observation_narrative_present=decision.observation_narrative_present,
            finding_bearing=decision.finding_bearing,
            modality_context=decision.modality_context,
        )
        # Existing flat fields are mechanical compatibility projections only.
        return ClinicalContext(
            clinical_purpose=decision.clinical_purpose,
            domain_concepts=decision.domain_concepts,
            domain_extension=radiology,
            attributes={
                "recognized_sections": list(decision.recognized_sections),
                "authoritative_anatomy": decision.authoritative_anatomy,
                "evidence_family_count": decision.evidence_family_count,
            },
            modality=legacy_modality,
            examination=decision.examination,
            body_region=body_region,
            body_regions=decision.body_regions,
            contrast=decision.contrast,
            techniques=decision.techniques,
        )
