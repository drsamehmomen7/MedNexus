from __future__ import annotations

from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent

from .context_models import (
    CTRadiologyLightContext, CTClinicalContext, CanonicalLightContext,
    CanonicalSemanticRegion, ClinicalContext, ContextProvenance, DocumentDescriptor,
    DocumentIdentityContext, FluoroscopyClinicalContext,
    FluoroscopyRadiologyLightContext, MammographyClinicalContext,
    MammographyRadiologyLightContext, MedNexusDocumentContext,
    MRIRadiologyLightContext, MRIClinicalContext, NuclearMedicineClinicalContext,
    NuclearMedicineRadiologyLightContext, OtherRadiologyClinicalContext,
    OtherRadiologyLightContext, PrivacyContext, PrivacyRegion, ProcessingContext,
    RadiologyClinicalContext, SemanticSection, UltrasoundClinicalContext,
    UltrasoundRadiologyLightContext, XRayClinicalContext, XRayRadiologyLightContext,
)
from .knowledge.radiology import RadiologyUnderstandingDecision
from .models import (
    DocumentDomain, DocumentSubtype, DocumentUnderstandingResult, RadiologySubdomain,
)


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
        review_required = result.routing.manual_review_required
        capabilities = result.routing.processing_capabilities
        return MedNexusDocumentContext(
            document=DocumentDescriptor(
                document_id or uuid4().hex,
                document.extension.lstrip(".") or "text",
                result.language.value,
                document.source_name,
                document.media_type,
                {"file_size": document.file_size, "page_count": document.page_count,
                 "line_count": document.line_count, **dict(document.metadata)},
            ),
            identity=DocumentIdentityContext(
                healthcare_domain=result.domain.value,
                document_type=result.document_type.value,
                document_subtype=(
                    None
                    if result.document_subtype is DocumentSubtype.UNKNOWN
                    else result.document_subtype.value
                ),
                confidence=result.confidence,
                confidence_band=result.confidence_band.value,
                document_nature=result.document_nature.value,
                subdomain_or_family=(canonical_subdomain.value if canonical_subdomain else None),
                document_review_required=review_required,
                domain=result.domain.value,
                language=result.language.value,
            ),
            structure=sections,
            clinical_context=cls._clinical_context(result, radiology_decision),
            privacy_context=PrivacyContext(privacy),
            processing_context=ProcessingContext(
                result.routing.privacy_profile_candidate,
                result.routing.extraction_profile,
                result.routing.terminology_profile,
                capabilities,
                review_required,
                protect_ready="PROTECT" in capabilities and not review_required,
                extract_ready="EXTRACT" in capabilities and not review_required,
                document_review_required=review_required,
            ),
            provenance=ContextProvenance(
                cls.KNOWLEDGE_LAYER_VERSION,
                tuple(dict.fromkeys(
                    item.concept_id for item in result.evidence if item.concept_id
                )),
                tuple(
                    {"candidate": item.candidate.value, "concept_id": item.concept_id,
                     "signal": item.signal, "category": item.category, "weight": item.weight,
                     "matched": item.reference, "reference_systems": list(item.reference_systems)}
                    | {"external_mappings": [list(value) for value in item.external_mappings],
                       "relationships": [list(value) for value in item.relationships]}
                    for item in result.evidence
                ),
                result.warnings,
            ),
            light_context=cls._light_context(radiology_decision),
            semantic_regions=tuple(
                CanonicalSemanticRegion(
                    region_id=item.section_id,
                    role=item.canonical_role,
                    start=item.start,
                    end=item.end,
                    confidence=item.confidence,
                    provenance=item.provenance,
                    qualifiers=item.qualifiers,
                )
                for item in sections
            ),
        )

    @staticmethod
    def _light_context(
        decision: RadiologyUnderstandingDecision | None,
    ) -> CanonicalLightContext:
        if decision is None or decision.subdomain is None:
            return CanonicalLightContext()
        context = decision.modality_context
        body_region = decision.authoritative_anatomy or (
            " & ".join(decision.body_regions) if decision.body_regions else None
        )
        subdomain = decision.subdomain.value
        if isinstance(context, CTClinicalContext):
            family_context = CTRadiologyLightContext(
                subdomain, body_region, decision.contrast, context.study_family,
                context.acquisition_summary,
            )
        elif isinstance(context, MRIClinicalContext):
            family_context = MRIRadiologyLightContext(
                subdomain, body_region, decision.contrast, context.study_family,
                context.canonical_sequence_families,
            )
        elif isinstance(context, XRayClinicalContext):
            family_context = XRayRadiologyLightContext(
                subdomain, body_region, context.laterality, context.views,
                context.view_count, context.view_count_qualifier, context.source_type,
            )
        elif isinstance(context, UltrasoundClinicalContext):
            family_context = UltrasoundRadiologyLightContext(
                subdomain, body_region, context.study_extent, context.vascular_context,
                context.specialization, context.measurement_bearing_present,
            )
        elif isinstance(context, MammographyClinicalContext):
            family_context = MammographyRadiologyLightContext(
                subdomain, context.study_purpose, context.laterality,
                context.acquisition_context, context.birads_assessment_present,
            )
        elif isinstance(context, NuclearMedicineClinicalContext):
            family_context = NuclearMedicineRadiologyLightContext(
                subdomain, context.study_family, body_region,
                context.radiopharmaceutical_context_present,
                context.quantitative_uptake_context_present,
            )
        elif isinstance(context, FluoroscopyClinicalContext):
            family_context = FluoroscopyRadiologyLightContext(
                subdomain, context.study_family, context.body_system,
                context.contrast_study_present, context.dynamic_functional_present,
            )
        elif isinstance(context, OtherRadiologyClinicalContext):
            family_context = OtherRadiologyLightContext(
                subdomain, context.resolution_reason,
            )
        else:
            raise ValueError(
                "A selected Radiology subdomain requires its governed light context."
            )
        return CanonicalLightContext("RADIOLOGY", family_context)

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
            if decision.subdomain in {None, RadiologySubdomain.OTHER}
            else decision.subdomain.value
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
                "radiology_other_reason": (
                    decision.other_reason.value if decision.other_reason else None
                ),
            },
            modality=legacy_modality,
            examination=decision.examination,
            body_region=body_region,
            body_regions=decision.body_regions,
            contrast=decision.contrast,
            techniques=decision.techniques,
        )
