from __future__ import annotations

import re
from dataclasses import dataclass

from ...context_models import (
    CTAcquisitionFeature, CTClinicalContext, CTStudyFamily, MRIClinicalContext,
    MRISequenceFamily, MRIStudyFamily, RadiologyModalityContext, StudyLaterality,
    UltrasoundClinicalContext, UltrasoundSpecialization, UltrasoundStudyExtent,
    VascularContext, XRayClinicalContext, XRaySourceType,
)
from ...models import (
    ClassificationEvidence, DetectedSection, DocumentNature, DocumentSubtype,
    DocumentType, RadiologySubdomain, RecognitionExplanation, SemanticRegionRole,
)
from ...reference_model.runtime import build_active_reference_registry
from .concepts import RADIOLOGY_REGISTRY
from .evidence import DocumentEvidenceFrame, RadiologyEvidenceFrameBuilder
from .semantic_roles import (
    RadiologyEvidenceEligibility, RadiologyEvidenceEligibilityResolution,
    RadiologyEvidenceEligibilityResolver, RadiologyRoleResolution,
    RadiologySemanticRole, RadiologySemanticRoleResolver,
    adapt_radiology_semantic_role,
)


_MODALITIES = {
    "RAD_MODALITY_MRI": DocumentSubtype.MRI,
    "RAD_MODALITY_CT": DocumentSubtype.CT,
    "RAD_MODALITY_XRAY": DocumentSubtype.X_RAY,
    "RAD_MODALITY_ULTRASOUND": DocumentSubtype.ULTRASOUND,
    "RAD_MODALITY_DOPPLER": DocumentSubtype.DOPPLER,
    "RAD_MODALITY_MAMMOGRAPHY": DocumentSubtype.MAMMOGRAPHY,
    "RAD_MODALITY_NUCLEAR_MEDICINE": DocumentSubtype.NUCLEAR_MEDICINE,
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
_MRI_SEQUENCE_FAMILIES = {
    "RAD_TECH_T1": MRISequenceFamily.T1_WEIGHTED,
    "RAD_TECH_T2": MRISequenceFamily.T2_WEIGHTED,
    "RAD_TECH_FLAIR": MRISequenceFamily.FLAIR,
    "RAD_TECH_STIR": MRISequenceFamily.STIR,
    "RAD_TECH_DWI": MRISequenceFamily.DIFFUSION_WEIGHTED,
    "RAD_TECH_FAT_SUPPRESSION": MRISequenceFamily.FAT_SUPPRESSED,
}
_VENOUS_TERMS = ("vein", "venous", "vena cava", "ivc")
_ARTERIAL_TERMS = ("artery", "arterial", "aorta")


@dataclass(frozen=True, slots=True)
class RadiologySemanticRegionDecision:
    """Canonical role decision for one detected document region."""

    section_id: str
    original_heading: str
    start: int
    end: int
    confidence: float
    canonical_role: SemanticRegionRole | None
    qualifiers: tuple[str, ...]
    evidence_concept_ids: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RadiologySupportScores:
    """Bounded internal support values; the public contract retains one confidence."""

    domain: float
    report: float
    subdomain: float
    dimension_count: int
    relationship_count: int
    total: float


@dataclass(frozen=True, slots=True)
class RadiologyUnderstandingDecision:
    """Single immutable semantic authority produced by Radiology UNDERSTAND."""

    frame: DocumentEvidenceFrame
    role_resolution: RadiologyRoleResolution
    evidence_eligibility: RadiologyEvidenceEligibilityResolution
    domain_satisfied: bool
    report_satisfied: bool
    finding_bearing: bool
    narrative_body_present: bool
    subdomain: RadiologySubdomain | None
    modality_variant: str | None
    domain_support: float
    report_support: float
    subdomain_support: float
    eligible_support_dimension_count: int
    eligible_relationship_count: int
    score: float
    evidence: tuple[ClassificationEvidence, ...]
    explanations: tuple[RecognitionExplanation, ...]
    document_nature: DocumentNature
    semantic_regions: tuple[RadiologySemanticRegionDecision, ...]
    body_regions: tuple[str, ...]
    authoritative_anatomy: str | None
    contrast: str | None
    clinical_purpose: str | None
    techniques: tuple[str, ...]
    examination: str | None
    modality_context: RadiologyModalityContext | None
    recognized_sections: tuple[str, ...]
    domain_concepts: tuple[str, ...]
    evidence_family_count: int

    @property
    def compatibility_subtype(self) -> DocumentSubtype:
        """Mechanical legacy projection; it never participates in reasoning."""

        if self.subdomain is RadiologySubdomain.ULTRASOUND and self.modality_variant == "DOPPLER":
            return DocumentSubtype.DOPPLER
        return {
            RadiologySubdomain.CT: DocumentSubtype.CT,
            RadiologySubdomain.MRI: DocumentSubtype.MRI,
            RadiologySubdomain.X_RAY: DocumentSubtype.X_RAY,
            RadiologySubdomain.ULTRASOUND: DocumentSubtype.ULTRASOUND,
            RadiologySubdomain.MAMMOGRAPHY: DocumentSubtype.MAMMOGRAPHY,
            RadiologySubdomain.NUCLEAR_MEDICINE: DocumentSubtype.NUCLEAR_MEDICINE,
            RadiologySubdomain.FLUOROSCOPY: DocumentSubtype.UNKNOWN,
            RadiologySubdomain.OTHER: DocumentSubtype.UNKNOWN,
            None: DocumentSubtype.UNKNOWN,
        }[self.subdomain]

    @property
    def modality(self) -> DocumentSubtype:
        """Compatibility alias retained for existing assessment consumers."""

        return self.compatibility_subtype

    @property
    def observation_narrative_present(self) -> bool:
        """Canonical bounded-context name for the legacy finding-bearing flag."""

        return self.finding_bearing


# Compatibility import retained while callers migrate to the authoritative name.
RadiologyAssessment = RadiologyUnderstandingDecision


class RadiologyReasoner:
    """MedNexus-owned compositional Radiology domain and report reasoning."""

    @classmethod
    def assess(cls, text: str, sections: tuple[DetectedSection, ...]) -> RadiologyAssessment:
        registry = build_active_reference_registry()
        frame = RadiologyEvidenceFrameBuilder.build(text, sections)
        roles = RadiologySemanticRoleResolver.resolve(text, sections, frame)
        eligibility = RadiologyEvidenceEligibilityResolver.resolve(frame, roles)
        current_support = RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
        composition_support = RadiologyEvidenceEligibility.DOCUMENT_COMPOSITION_SUPPORT
        current_roles = (
            RadiologySemanticRole.PERFORMED_STUDY,
            RadiologySemanticRole.TECHNIQUE_ACQUISITION,
        )
        current_modalities = eligibility.signals(current_support, "modality_signals")
        current_procedures = eligibility.signals(current_support, "procedure_signals")
        current_techniques = eligibility.signals(current_support, "technique_signals")
        current_acquisitions = eligibility.signals(current_support, "acquisition_signals")
        current_anatomy = eligibility.signals(current_support, "anatomy_signals")
        current_contrast = eligibility.signals(current_support, "contrast_signals")
        composition_structure = eligibility.signals(
            composition_support, "structure_signals"
        )
        composition_professional = eligibility.signals(
            composition_support, "professional_role_signals"
        )
        composition_domain = eligibility.signals(composition_support, "domain_signals")
        modality_ids = {item.concept_id for item in current_modalities}
        technique_ids = {item.concept_id for item in current_techniques}
        acquisition_ids = {item.concept_id for item in current_acquisitions}
        structure_ids = {item.concept_id for item in composition_structure}
        domain_ids = {item.concept_id for item in composition_domain}
        contextual_families = sum(bool(items) for items in (
            current_techniques, current_acquisitions, current_anatomy,
            current_contrast, composition_structure, composition_professional,
        ))
        imaging_coherence = bool(modality_ids) and (
            len(technique_ids | acquisition_ids) >= 2 or contextual_families >= 3
        )
        explicit_context = bool(domain_ids) and contextual_families >= 1
        structural_cluster = len(structure_ids) >= 3 and bool(
            modality_ids or composition_professional
        )
        domain_satisfied = imaging_coherence or explicit_context or structural_cluster
        explicit_findings_report = {
            "RAD_SECTION_FINDINGS", "RAD_SECTION_IMPRESSION"
        } <= structure_ids
        implied_findings_report = (
            "RAD_SECTION_IMPRESSION" in structure_ids
            and bool(composition_professional)
            and bool(modality_ids)
            and len(technique_ids | acquisition_ids) >= 2
        )
        narrative_body_present = cls._narrative_body_present(text, sections, frame)
        composition_families = sum(bool(items) for items in (
            current_modalities or current_procedures,
            frame.domain_signals,
            current_techniques or current_acquisitions,
            current_anatomy,
            current_contrast,
            composition_structure,
            composition_professional,
        ))
        modality_neutral_narrative_report = (
            narrative_body_present
            and bool(current_modalities or current_procedures)
            and "RAD_SECTION_IMPRESSION" in structure_ids
            and any(item.start >= next(
                section.start for section in sections
                if section.canonical_name == "impression"
            ) for item in composition_professional)
            and len(sections) >= 3
            and composition_families >= 4
        )
        report_satisfied = domain_satisfied and (
            explicit_findings_report
            or implied_findings_report
            or modality_neutral_narrative_report
            or "RAD_DOC_REPORT" in domain_ids
        )
        finding_bearing = domain_satisfied and (
            "RAD_SECTION_FINDINGS" in structure_ids
            or implied_findings_report
            or modality_neutral_narrative_report
        )
        procedure_components = cls._procedure_components(current_procedures, registry)
        compatibility_subtype = cls._modality(modality_ids, technique_ids, acquisition_ids)
        if compatibility_subtype is DocumentSubtype.UNKNOWN:
            compatibility_subtype = cls._component_modality(procedure_components)
        subdomain, modality_variant = cls._canonical_modality(
            compatibility_subtype, domain_satisfied
        )
        study_family = cls._study_family(compatibility_subtype, procedure_components)
        score_support = cls._score_support(eligibility)
        evidence = tuple(ClassificationEvidence(
            DocumentType.RADIOLOGY_REPORT, signal.matched_text,
            cls._evidence_category(field), signal.strength, signal.matched_text,
            signal.concept_id, signal.provenance,
            signal.external_mappings, signal.relationships,
        ) for field in frame.__dataclass_fields__ for signal in getattr(frame, field))
        explanations = cls._explanations(frame, roles, report_satisfied)
        semantic_regions = cls._semantic_regions(sections, frame, roles)
        body_regions, authoritative_anatomy = cls._anatomy_context(
            compatibility_subtype, frame, roles, current_roles,
            procedure_components,
        )
        contrast = cls._contrast_context(frame, roles, current_roles)
        techniques = cls._techniques(frame, roles, current_roles)
        clinical_purpose = cls._clinical_purpose(frame, roles)
        modality_context = cls._modality_context(
            compatibility_subtype, study_family, techniques, frame, roles,
            current_roles, procedure_components, registry,
        )
        examination = cls._examination(
            compatibility_subtype, study_family, body_regions, authoritative_anatomy
        )
        curated_ids = {item.concept_id for item in RADIOLOGY_REGISTRY.concepts}
        domain_concepts = tuple(dict.fromkeys(
            RADIOLOGY_REGISTRY.get(item.concept_id).canonical_name
            for item in evidence if item.concept_id in curated_ids
        ))
        return RadiologyUnderstandingDecision(
            frame=frame,
            role_resolution=roles,
            evidence_eligibility=eligibility,
            domain_satisfied=domain_satisfied,
            report_satisfied=report_satisfied,
            finding_bearing=finding_bearing,
            narrative_body_present=narrative_body_present,
            subdomain=subdomain,
            modality_variant=modality_variant,
            domain_support=score_support.domain,
            report_support=score_support.report,
            subdomain_support=score_support.subdomain,
            eligible_support_dimension_count=score_support.dimension_count,
            eligible_relationship_count=score_support.relationship_count,
            score=score_support.total,
            evidence=evidence,
            explanations=explanations,
            document_nature=cls._document_nature(sections, roles, frame, domain_satisfied),
            semantic_regions=semantic_regions,
            body_regions=body_regions,
            authoritative_anatomy=authoritative_anatomy,
            contrast=contrast,
            clinical_purpose=clinical_purpose,
            techniques=techniques,
            examination=examination,
            modality_context=modality_context,
            recognized_sections=tuple(item.canonical_name for item in sections),
            domain_concepts=domain_concepts,
            evidence_family_count=sum(
                bool(getattr(frame, field)) for field in frame.__dataclass_fields__
            ),
        )

    @staticmethod
    def _canonical_modality(
        compatibility_subtype: DocumentSubtype, domain_satisfied: bool
    ) -> tuple[RadiologySubdomain | None, str | None]:
        if not domain_satisfied:
            return None, None
        if compatibility_subtype is DocumentSubtype.DOPPLER:
            return RadiologySubdomain.ULTRASOUND, "DOPPLER"
        return {
            DocumentSubtype.CT: RadiologySubdomain.CT,
            DocumentSubtype.MRI: RadiologySubdomain.MRI,
            DocumentSubtype.X_RAY: RadiologySubdomain.X_RAY,
            DocumentSubtype.ULTRASOUND: RadiologySubdomain.ULTRASOUND,
            DocumentSubtype.MAMMOGRAPHY: RadiologySubdomain.MAMMOGRAPHY,
            DocumentSubtype.NUCLEAR_MEDICINE: RadiologySubdomain.NUCLEAR_MEDICINE,
            DocumentSubtype.UNKNOWN: RadiologySubdomain.OTHER,
        }[compatibility_subtype], None

    @staticmethod
    def _document_nature(
        sections: tuple[DetectedSection, ...],
        roles: RadiologyRoleResolution,
        frame: DocumentEvidenceFrame,
        domain_satisfied: bool,
    ) -> DocumentNature:
        section_ids = {item.canonical_name for item in sections}
        current_modalities = roles.signals(
            frame.modality_signals,
            RadiologySemanticRole.PERFORMED_STUDY,
            RadiologySemanticRole.TECHNIQUE_ACQUISITION,
        )
        modality_families = {
            "ULTRASOUND" if item.concept_id in {
                "RAD_MODALITY_ULTRASOUND", "RAD_MODALITY_DOPPLER"
            } else item.concept_id
            for item in current_modalities
        }
        if len(modality_families) > 1 and len(section_ids) >= 3:
            return DocumentNature.STRUCTURED_TEMPLATE
        if {"findings", "impression"} <= section_ids:
            return DocumentNature.COMPLETED_REPORT
        if domain_satisfied and section_ids:
            return DocumentNature.PARTIAL_REPORT
        return DocumentNature.UNKNOWN

    @staticmethod
    def _semantic_regions(
        sections: tuple[DetectedSection, ...],
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
    ) -> tuple[RadiologySemanticRegionDecision, ...]:
        structure_signal_ids = {id(item) for item in frame.structure_signals}
        decisions = []
        for section in sections:
            related = tuple(
                value for value in roles.evidence
                if value.section_id == section.canonical_name
                and section.start <= value.signal.start < section.end
            )
            ranked = sorted(related, key=lambda value: (
                0 if id(value.signal) in structure_signal_ids
                and value.signal.start == section.start else 1,
                0 if value.signal.start == section.start else 1,
                value.signal.start,
            ))
            adapted = tuple(
                (value, adapt_radiology_semantic_role(value.role)) for value in ranked
            )
            authoritative = next(
                (mapping for _, mapping in adapted if mapping.authoritative), None
            )
            decisions.append(RadiologySemanticRegionDecision(
                section_id=section.canonical_name,
                original_heading=section.original_heading,
                start=section.start,
                end=section.end,
                confidence=section.confidence,
                canonical_role=(authoritative.canonical_role if authoritative else None),
                qualifiers=tuple(dict.fromkeys(
                    mapping.qualifier for _, mapping in adapted if mapping.qualifier
                )),
                evidence_concept_ids=tuple(dict.fromkeys(
                    value.signal.concept_id for value, _ in adapted
                )),
                provenance=tuple(dict.fromkeys(
                    source for value, _ in adapted for source in value.signal.provenance
                )),
            ))
        return tuple(decisions)

    @classmethod
    def _anatomy_context(
        cls,
        modality: DocumentSubtype,
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
        procedure_components,
    ) -> tuple[tuple[str, ...], str | None]:
        modality_spans = roles.signals(frame.modality_signals, *current_roles)
        anatomy_signals = roles.signals(frame.anatomy_signals, *current_roles)
        broad_anatomy = [
            item for item in anatomy_signals if item.concept_id in _BODY_REGION_IDS
        ]
        if modality_spans:
            broad_anatomy.sort(key=lambda item: (
                min(max(span.start - item.end, item.start - span.end, 0)
                    for span in modality_spans),
                item.start,
            ))
        regions = tuple(dict.fromkeys(
            _BODY_REGION_IDS[item.concept_id] for item in broad_anatomy
        ))
        authoritative_anatomy = cls._authoritative_anatomy(
            frame, roles, anatomy_signals
        )
        component_regions = tuple(dict.fromkeys(
            cls._canonical_body_region(item.canonical_name)
            for item in procedure_components
            if dict(item.attributes).get("part_type")
            == "RAD_ANATOMIC_LOCATION_REGION_IMAGED"
            and cls._canonical_body_region(item.canonical_name) is not None
        ))
        # A role-qualified authoritative procedure preserves its governed component
        # order; lower-level lexical anatomy may supplement but never reorder it.
        regions = tuple(dict.fromkeys((*component_regions, *regions)))
        if authoritative_anatomy is None:
            focuses = tuple(dict.fromkeys(
                item.canonical_name for item in procedure_components
                if dict(item.attributes).get("part_type")
                == "RAD_ANATOMIC_LOCATION_IMAGING_FOCUS"
            ))
            if len(focuses) == 1:
                authoritative_anatomy = focuses[0]
            elif len(component_regions) == 1:
                authoritative_anatomy = component_regions[0].replace("_", " ").title()
        if modality is DocumentSubtype.X_RAY and not regions and authoritative_anatomy:
            regions = (authoritative_anatomy,)
        return regions, authoritative_anatomy

    @staticmethod
    def _canonical_body_region(name: str) -> str | None:
        normalized = name.casefold().replace(".", " ").replace("_", " ")
        for canonical in _BODY_REGION_IDS.values():
            label = canonical.casefold().replace("_", " ")
            if normalized == label or normalized.startswith(f"{label} "):
                return canonical
        if normalized in {"head", "brain"}:
            return normalized.upper()
        return None

    @staticmethod
    def _contrast_context(
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
    ) -> str | None:
        contrast_ids = {
            item.concept_id
            for item in roles.signals(frame.contrast_signals, *current_roles)
        }
        if "RAD_CONTRAST_PRE_POST" in contrast_ids or {
            "RAD_CONTRAST_WITH", "RAD_CONTRAST_WITHOUT"
        } <= contrast_ids:
            return "PRE_AND_POST_CONTRAST"
        if "RAD_CONTRAST_WITH" in contrast_ids:
            return "WITH_CONTRAST"
        if "RAD_CONTRAST_WITHOUT" in contrast_ids:
            return "WITHOUT_CONTRAST"
        return None

    @staticmethod
    def _techniques(
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
    ) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            _TECHNIQUE_NAMES[item.concept_id]
            for item in (
                roles.signals(frame.technique_signals, *current_roles)
                + roles.signals(frame.acquisition_signals, *current_roles)
            )
            if item.concept_id in _TECHNIQUE_NAMES
        ))

    @staticmethod
    def _clinical_purpose(
        frame: DocumentEvidenceFrame, roles: RadiologyRoleResolution
    ) -> str | None:
        purpose_ids = {
            item.concept_id for item in roles.signals(
                frame.clinical_purpose_signals,
                RadiologySemanticRole.CLINICAL_INDICATION,
            )
        }
        return next((label for concept_id, label in (
            ("RAD_PURPOSE_STAGING", "Oncologic Staging"),
            ("RAD_PURPOSE_SCREENING", "Screening"),
            ("RAD_PURPOSE_POST_TREATMENT", "Post-treatment Assessment"),
            ("RAD_PURPOSE_FOLLOWUP", "Follow-up / Surveillance"),
            ("RAD_PURPOSE_DIAGNOSTIC", "Diagnostic Evaluation"),
        ) if concept_id in purpose_ids), None)

    @staticmethod
    def _procedure_components(procedures, registry) -> tuple:
        """Resolve only role-qualified current procedures into governed components."""

        components = []
        for procedure in procedures:
            for relationship_type, target_concept_id in procedure.relationships:
                if relationship_type != "CAN_COMPOSE":
                    continue
                try:
                    component = registry.concept(target_concept_id)
                except KeyError:
                    continue
                if component not in components:
                    components.append(component)
        return tuple(components)

    @staticmethod
    def _component_modality(components) -> DocumentSubtype:
        modality_types = {
            item.canonical_name.casefold() for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_TYPE"
        }
        modality_subtypes = {
            item.canonical_name.casefold() for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_SUBTYPE"
        }
        if modality_types == {"ct"}:
            return DocumentSubtype.CT
        if modality_types == {"mr"}:
            return DocumentSubtype.MRI
        if modality_types == {"xr"}:
            return DocumentSubtype.X_RAY
        if modality_types == {"us"}:
            return (
                DocumentSubtype.DOPPLER
                if "doppler" in modality_subtypes else DocumentSubtype.ULTRASOUND
            )
        return DocumentSubtype.UNKNOWN

    @staticmethod
    def _study_family(modality: DocumentSubtype, components):
        names = {item.canonical_name.casefold() for item in components}
        angiographic = "angio" in names
        if modality is DocumentSubtype.CT:
            return CTStudyFamily.CTA if angiographic else CTStudyFamily.CT
        if modality is DocumentSubtype.MRI:
            if not angiographic:
                return MRIStudyFamily.MRI
            vascular_names = {
                item.canonical_name.casefold() for item in components
                if dict(item.attributes).get("part_type")
                == "RAD_ANATOMIC_LOCATION_IMAGING_FOCUS"
            }
            if any(term in name for name in vascular_names for term in _VENOUS_TERMS):
                return MRIStudyFamily.MRV
            return MRIStudyFamily.MRA
        return None

    @staticmethod
    def _examination(
        modality: DocumentSubtype,
        study_family,
        regions: tuple[str, ...],
        authoritative_anatomy: str | None,
    ) -> str | None:
        modality_value = (
            study_family.value if study_family is not None
            else None if modality is DocumentSubtype.UNKNOWN else modality.value
        )
        region_label = " & ".join(item.title() for item in regions)
        study_anatomy = (
            authoritative_anatomy
            if modality is DocumentSubtype.X_RAY and authoritative_anatomy
            else region_label or None
        )
        modality_label = {
            "X_RAY": "X-ray",
            "DOPPLER": "Doppler Ultrasound",
        }.get(modality_value, modality_value)
        return " ".join(filter(None, (
            modality_label, study_anatomy.title() if study_anatomy else None,
        ))) or None

    @staticmethod
    def _modality_context(
        modality: DocumentSubtype,
        study_family,
        techniques: tuple[str, ...],
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
        procedure_components,
        registry,
    ) -> RadiologyModalityContext | None:
        multiplanar = "Multiplanar imaging" in techniques
        if modality is DocumentSubtype.CT:
            family = study_family or CTStudyFamily.CT
            acquisition = tuple(feature for feature, present in (
                (CTAcquisitionFeature.ANGIOGRAPHIC, family is CTStudyFamily.CTA),
                (CTAcquisitionFeature.MULTIPLANAR_RECONSTRUCTION, multiplanar),
            ) if present)
            return CTClinicalContext(
                study_family=family,
                acquisition_summary=acquisition,
                angiographic_context=family is CTStudyFamily.CTA,
                multiplanar_reconstruction_present=multiplanar,
            )
        if modality is DocumentSubtype.MRI:
            technique_ids = {
                item.concept_id for item in roles.signals(
                    frame.technique_signals, *current_roles
                )
            }
            return MRIClinicalContext(
                study_family=study_family or MRIStudyFamily.MRI,
                canonical_sequence_families=tuple(
                    family for concept_id, family in _MRI_SEQUENCE_FAMILIES.items()
                    if concept_id in technique_ids
                ),
                sequence_families=tuple(
                    item for item in techniques if item != "Multiplanar imaging"
                ),
                multiplanar_acquisition_present=multiplanar,
            )
        if modality is DocumentSubtype.X_RAY:
            view_signals = roles.signals(frame.view_signals, *current_roles)
            views = tuple(dict.fromkeys(
                registry.concept(item.concept_id).canonical_name
                for item in sorted(view_signals, key=lambda signal: signal.start)
            ))
            view_count_signals = roles.signals(
                frame.view_count_signals, *current_roles
            )
            counts = tuple(dict.fromkeys(
                (int(dict(item.attributes)["count"]), dict(item.attributes)["qualifier"])
                for item in view_count_signals
            ))
            view_count, qualifier = counts[0] if len(counts) == 1 else (None, None)
            laterality = RadiologyReasoner._laterality_context(
                frame, roles, current_roles, procedure_components, registry
            )
            source_type = RadiologyReasoner._xray_source_type(
                roles.signals(frame.modality_signals, *current_roles), registry
            )
            return XRayClinicalContext(
                laterality=laterality, source_type=source_type,
                views=views, view_count=view_count, view_count_qualifier=qualifier,
            )
        if modality in {DocumentSubtype.ULTRASOUND, DocumentSubtype.DOPPLER}:
            doppler = (
                modality is DocumentSubtype.DOPPLER
                or any(item.canonical_name.casefold() == "doppler"
                       for item in procedure_components)
            )
            return UltrasoundClinicalContext(
                study_extent=RadiologyReasoner._ultrasound_extent(
                    procedure_components,
                    roles.signals(frame.study_extent_signals, *current_roles),
                    registry,
                ),
                specialization=(UltrasoundSpecialization.DOPPLER if doppler
                                else UltrasoundSpecialization.GENERAL),
                vascular_context=(RadiologyReasoner._vascular_context(procedure_components)
                                  if doppler else None),
                measurement_bearing_present=None,
                doppler_present=doppler,
            )
        return None

    @staticmethod
    def _laterality_context(frame, roles, current_roles, components, registry):
        component_names = [
            item.canonical_name.casefold() for item in components
            if dict(item.attributes).get("part_type") == "RAD_ANATOMIC_LOCATION_LATERALITY"
            and item.canonical_name.casefold() != "unspecified"
        ]
        names = component_names
        if not names:
            for signal in roles.signals(frame.laterality_signals, *current_roles):
                try:
                    names.append(registry.concept(signal.concept_id).canonical_name.casefold())
                except KeyError:
                    continue
        values = tuple(dict.fromkeys(
            value for name in names for label, value in (
                ("left", StudyLaterality.LEFT),
                ("right", StudyLaterality.RIGHT),
                ("bilateral", StudyLaterality.BILATERAL),
            ) if name == label
        ))
        return values[0] if len(values) == 1 else None

    @staticmethod
    def _xray_source_type(signals, registry):
        values = []
        for signal in sorted(signals, key=lambda item: item.start):
            token = signal.matched_text.strip().upper()
            if token in XRaySourceType.__members__:
                values.append(XRaySourceType[token])
                continue
            try:
                canonical_name = registry.concept(signal.concept_id).canonical_name.casefold()
            except KeyError:
                continue
            if canonical_name == "computed radiography":
                values.append(XRaySourceType.CR)
            elif canonical_name == "digital radiography":
                values.append(XRaySourceType.DX)
        values = tuple(dict.fromkeys(values))
        specific = tuple(item for item in values if item is not XRaySourceType.XR)
        return specific[0] if len(specific) == 1 else values[0] if len(values) == 1 else None

    @staticmethod
    def _ultrasound_extent(components, extent_signals=(), registry=None):
        values = {
            item.canonical_name.casefold() for item in components
            if dict(item.attributes).get("part_type") == "RAD_VIEW_AGGREGATION"
        }
        if not values and registry is not None:
            for signal in extent_signals:
                try:
                    values.add(registry.concept(signal.concept_id).canonical_name.casefold())
                except KeyError:
                    continue
        if values == {"complete"}:
            return UltrasoundStudyExtent.COMPLETE
        if values == {"limited"}:
            return UltrasoundStudyExtent.LIMITED
        return None

    @staticmethod
    def _vascular_context(components):
        names = {
            item.canonical_name.casefold() for item in components
            if dict(item.attributes).get("part_type")
            == "RAD_ANATOMIC_LOCATION_IMAGING_FOCUS"
        }
        arterial = any(term in name for name in names for term in _ARTERIAL_TERMS)
        venous = any(term in name for name in names for term in _VENOUS_TERMS)
        if arterial and venous:
            return VascularContext.MIXED
        if arterial:
            return VascularContext.ARTERIAL
        if venous:
            return VascularContext.VENOUS
        return None

    @staticmethod
    def _authoritative_anatomy(
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        anatomy_signals,
    ) -> str | None:
        current_modalities = roles.signals(
            frame.modality_signals,
            RadiologySemanticRole.PERFORMED_STUDY,
            RadiologySemanticRole.TECHNIQUE_ACQUISITION,
        )
        if not current_modalities or not anatomy_signals:
            return None
        registry = build_active_reference_registry()
        modality = min(current_modalities, key=lambda item: item.start)
        specific = [
            item for item in anatomy_signals
            if item.concept_id not in _BODY_REGION_IDS
            and RadiologyReasoner._is_authoritative_anatomy_candidate(
                registry, item.concept_id
            )
        ]
        if not specific:
            broad = [item for item in anatomy_signals if item.concept_id in _BODY_REGION_IDS]
            if not broad:
                return None
            nearest = min(broad, key=lambda item: (
                max(modality.start - item.end, item.start - modality.end, 0), item.start,
            ))
            try:
                return registry.concept(nearest.concept_id).canonical_name
            except KeyError:
                return _BODY_REGION_IDS[nearest.concept_id].replace("_", " ").title()
        broad = [item for item in anatomy_signals if item.concept_id in _BODY_REGION_IDS]
        supported = [
            item for item in specific
            if any(item.start < broad_item.end and broad_item.start < item.end
                   for broad_item in broad)
        ]
        if supported:
            supported.sort(key=lambda item: (-(item.end - item.start), item.start))
            try:
                return registry.concept(supported[0].concept_id).canonical_name
            except KeyError:
                pass
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

    @staticmethod
    def _is_authoritative_anatomy_candidate(registry, concept_id: str) -> bool:
        try:
            concept = registry.concept(concept_id)
        except KeyError:
            return False
        for relationship in concept.relationships:
            if relationship.relationship_type.value != "MEMBER_OF":
                continue
            try:
                parent = registry.concept(relationship.target_concept_id)
            except KeyError:
                continue
            if parent.canonical_name.casefold() == "anatomic modifier":
                return False
        return True

    @staticmethod
    def _explanations(frame, roles, report_satisfied) -> tuple[RecognitionExplanation, ...]:
        current = (RadiologySemanticRole.PERFORMED_STUDY,
                   RadiologySemanticRole.TECHNIQUE_ACQUISITION)
        explanations = []
        if frame.domain_signals:
            explanations.append(RecognitionExplanation(
                "RADIOLOGY_CONTEXT", "Radiology report context identified", "context"
            ))
        current_modalities = roles.signals(frame.modality_signals, *current)
        modality_labels = {
            "RAD_MODALITY_XRAY": "X-ray / radiography modality identified",
            "RAD_MODALITY_CT": "CT imaging modality identified",
            "RAD_MODALITY_MRI": "MRI imaging modality identified",
            "RAD_MODALITY_ULTRASOUND": "Ultrasound imaging modality identified",
            "RAD_MODALITY_DOPPLER": "Doppler imaging context identified",
            "RAD_MODALITY_MAMMOGRAPHY": "Mammography modality identified",
            "RAD_MODALITY_NUCLEAR_MEDICINE": "Nuclear medicine modality identified",
        }
        for signal in current_modalities:
            message = modality_labels.get(signal.concept_id)
            if message:
                explanations.append(RecognitionExplanation(
                    f"CURRENT_MODALITY_{signal.concept_id}", message, "modality",
                    signal.concept_id, RadiologySemanticRole.PERFORMED_STUDY.value,
                ))
        if roles.signals(frame.anatomy_signals, *current):
            explanations.append(RecognitionExplanation(
                "CURRENT_STUDY_ANATOMY", "Current study anatomy identified", "anatomy",
                semantic_role=RadiologySemanticRole.PERFORMED_STUDY.value,
            ))
        if any(item.concept_id == "RAD_SECTION_IMPRESSION" for item in frame.structure_signals):
            explanations.append(RecognitionExplanation(
                "IMPRESSION_SECTION", "Impression section identified", "section",
                "RAD_SECTION_IMPRESSION", RadiologySemanticRole.IMPRESSION_CONTEXT.value,
            ))
        if frame.professional_role_signals:
            explanations.append(RecognitionExplanation(
                "RADIOLOGY_ATTRIBUTION", "Radiology professional attribution identified",
                "professional_role",
            ))
        if roles.signals(
            frame.clinical_purpose_signals, RadiologySemanticRole.CLINICAL_INDICATION
        ):
            explanations.append(RecognitionExplanation(
                "CURRENT_CLINICAL_PURPOSE", "Current clinical purpose context identified",
                "clinical_purpose", semantic_role=RadiologySemanticRole.CLINICAL_INDICATION.value,
            ))
        if report_satisfied:
            explanations.append(RecognitionExplanation(
                "RADIOLOGY_COMPOSITION", "Radiology report composition identified", "composition"
            ))
        unique = {}
        for item in explanations:
            unique.setdefault(item.code, item)
        return tuple(unique.values())

    @staticmethod
    def _narrative_body_present(
        text: str, sections: tuple[DetectedSection, ...], frame: DocumentEvidenceFrame
    ) -> bool:
        """Detect substantive pre-Impression report prose without assigning section semantics."""
        impression = next((item for item in sections if item.canonical_name == "impression"), None)
        if impression is None:
            return False
        preceding = [item for item in sections if item.start < impression.start]
        if not preceding:
            return False
        boundary = max(preceding, key=lambda item: item.start)
        body = text[boundary.start + len(boundary.original_heading):impression.start].strip(" \t\r\n:")
        words = re.findall(r"[^\W_]+", body, re.UNICODE)
        if len(body) < 180 or len(words) < 30:
            return False
        normalized_words = {item.casefold() for item in words}
        if len(normalized_words) / len(words) < 0.30:
            return False
        sentence_count = len(re.findall(r"[.!?](?:\s|$)", body))
        return sentence_count >= 2 and bool(frame.modality_signals or frame.procedure_signals)

    @classmethod
    def _score_support(
        cls, eligibility: RadiologyEvidenceEligibilityResolution
    ) -> RadiologySupportScores:
        """Preserve established weights while restricting them to eligible support."""

        current = RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
        composition = RadiologyEvidenceEligibility.DOCUMENT_COMPOSITION_SUPPORT
        domain_groups = (
            eligibility.signals(composition, "domain_signals"),
        )
        report_groups = (
            eligibility.signals(composition, "structure_signals"),
            eligibility.signals(composition, "professional_role_signals"),
        )
        subdomain_groups = tuple(
            eligibility.signals(current, field_name) for field_name in (
                "modality_signals", "technique_signals", "acquisition_signals",
                "anatomy_signals", "contrast_signals", "laterality_signals",
                "view_signals", "view_count_signals",
            )
        )
        domain_support = round(sum(cls._unique_strength(items) for items in domain_groups), 2)
        report_support = round(sum(cls._unique_strength(items) for items in report_groups), 2)
        subdomain_support = round(
            sum(cls._unique_strength(items) for items in subdomain_groups), 2
        )
        support_dimensions = (
            domain_groups[0],
            subdomain_groups[0],
            (*subdomain_groups[1], *subdomain_groups[2]),
            subdomain_groups[3],
            subdomain_groups[4],
            subdomain_groups[5],
            (*subdomain_groups[6], *subdomain_groups[7]),
            report_groups[0],
            report_groups[1],
        )
        diversity = sum(bool(items) for items in support_dimensions)
        scored_signals = tuple(
            item for group in (*domain_groups, *report_groups, *subdomain_groups)
            for item in group
        )
        eligible_concept_ids = {item.concept_id for item in scored_signals}
        relationships = {
            (item.concept_id, target)
            for item in scored_signals
            for _, target in item.relationships
            if target in eligible_concept_ids
        }
        score = round(
            domain_support + report_support + subdomain_support
            + max(0, diversity - 2)
            + min(2.0, len(relationships) * 0.25),
            2,
        )
        return RadiologySupportScores(
            domain=domain_support,
            report=report_support,
            subdomain=subdomain_support,
            dimension_count=diversity,
            relationship_count=len(relationships),
            total=score,
        )

    @staticmethod
    def _unique_strength(signals) -> float:
        strengths = {}
        for signal in signals:
            strengths[signal.concept_id] = max(strengths.get(signal.concept_id, 0), signal.strength)
        return sum(strengths.values())

    @staticmethod
    def _evidence_category(field: str) -> str:
        return field.removesuffix("_signals").replace("domain", "context").replace("structure", "section")

    @staticmethod
    def _modality(modality_ids, technique_ids, acquisition_ids) -> DocumentSubtype:
        explicit = {_MODALITIES[item] for item in modality_ids if item in _MODALITIES}
        if DocumentSubtype.DOPPLER in explicit:
            explicit.discard(DocumentSubtype.ULTRASOUND)
        if len(explicit) == 1:
            return next(iter(explicit))
        if not explicit and len(technique_ids | acquisition_ids) >= 3:
            return DocumentSubtype.MRI
        return DocumentSubtype.UNKNOWN
