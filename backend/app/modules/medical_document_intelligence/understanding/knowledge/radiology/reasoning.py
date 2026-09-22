from __future__ import annotations

import re
from dataclasses import dataclass, replace

from ...context_models import (
    CTAcquisitionFeature, CTClinicalContext, CTStudyFamily, MRIClinicalContext,
    FluoroscopyClinicalContext, FluoroscopyStudyFamily,
    MammographyAcquisitionContext, MammographyClinicalContext,
    MammographyStudyPurpose, MRISequenceFamily, MRIStudyFamily,
    NuclearMedicineClinicalContext, NuclearMedicineStudyFamily,
    OtherRadiologyClinicalContext, RadiologyModalityContext,
    RadiologyOtherReason, StudyLaterality, UltrasoundClinicalContext,
    UltrasoundSpecialization, UltrasoundStudyExtent, VascularContext,
    XRayClinicalContext, XRaySourceType,
)
from ...models import (
    ClassificationEvidence, DetectedSection, DocumentNature, DocumentSubtype,
    DocumentType, RadiologySubdomain, RecognitionExplanation, SemanticRegionRole,
)
from ...reference_model.runtime import build_active_reference_registry
from .concepts import RADIOLOGY_REGISTRY
from .evidence import DocumentEvidenceFrame, EvidenceSignal, RadiologyEvidenceFrameBuilder
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
    other_reason: RadiologyOtherReason | None
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
        frame = cls._with_governed_composite_procedure(
            text, sections, frame, registry
        )
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
        procedure_components = cls._procedure_components(current_procedures, registry)
        compatibility_subtype = cls._modality(modality_ids, technique_ids, acquisition_ids)
        if compatibility_subtype is DocumentSubtype.UNKNOWN:
            compatibility_subtype = cls._component_modality(procedure_components)
        current_family_identified = (
            compatibility_subtype is not DocumentSubtype.UNKNOWN
            or bool(current_modalities or current_procedures)
        )
        narrative_body_present = (
            current_family_identified
            and cls._narrative_body_present(text, sections, frame)
        )
        observation_region_present = cls._observation_region_present(text, sections)
        title_led_partial_report = (
            "RAD_STRUCTURE_STUDY_TITLE" in structure_ids
            and (narrative_body_present or observation_region_present)
        )
        inferred_mri_impression_report = (
            compatibility_subtype is DocumentSubtype.MRI
            and narrative_body_present
            and "RAD_SECTION_IMPRESSION" in structure_ids
        )
        governed_report_identity = any(
            item.concept_id == "RAD_DOC_REPORT"
            or (
                item.concept_family == "DOCUMENT_REPORT"
                and any(
                    item.start <= modality.start
                    and modality.end <= item.end
                    for modality in current_modalities
                )
            )
            for item in composition_domain
        )
        governed_report_narrative = (
            governed_report_identity and narrative_body_present
        )
        composition_roles = {
            item.semantic_role
            for item in eligibility.decisions_for(composition_support)
        }
        meaningful_report_composition = bool(
            {
                RadiologySemanticRole.FINDINGS_CONTEXT,
                RadiologySemanticRole.IMPRESSION_CONTEXT,
            }
            & composition_roles
        )
        reference_composed_partial_report = (
            narrative_body_present
            and any(
                dict(item.attributes).get("inference_basis")
                == "REFERENCE_COMPONENT_COMPOSITION"
                for item in current_procedures
            )
            and meaningful_report_composition
        )
        contextual_families = sum(bool(items) for items in (
            current_techniques, current_acquisitions, current_anatomy,
            current_contrast, composition_structure, composition_professional,
        ))
        imaging_coherence = bool(current_modalities or current_procedures) and (
            len(technique_ids | acquisition_ids) >= 2 or contextual_families >= 3
        )
        explicit_context = bool(domain_ids) and contextual_families >= 1
        structural_cluster = len(structure_ids) >= 3 and bool(
            modality_ids or current_procedures or composition_professional
        )
        domain_satisfied = (
            imaging_coherence or explicit_context or structural_cluster
            or title_led_partial_report or inferred_mri_impression_report
            or reference_composed_partial_report
        )
        explicit_findings_report = {
            "RAD_SECTION_FINDINGS", "RAD_SECTION_IMPRESSION"
        } <= structure_ids
        implied_findings_report = (
            "RAD_SECTION_IMPRESSION" in structure_ids
            and bool(composition_professional)
            and bool(modality_ids)
            and len(technique_ids | acquisition_ids) >= 2
        )
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
            or title_led_partial_report
            or inferred_mri_impression_report
            or governed_report_identity
            or reference_composed_partial_report
        )
        finding_bearing = domain_satisfied and (
            "RAD_SECTION_FINDINGS" in structure_ids
            or implied_findings_report
            or modality_neutral_narrative_report
            or title_led_partial_report
            or inferred_mri_impression_report
            or governed_report_narrative
            or reference_composed_partial_report
        )
        subdomain, modality_variant, other_reason = cls._canonical_modality(
            compatibility_subtype,
            domain_satisfied,
            current_modalities,
            procedure_components,
            registry,
        )
        study_family = cls._study_family(
            subdomain, procedure_components, current_modalities, registry
        )
        score_support = cls._score_support(eligibility)
        evidence = tuple(ClassificationEvidence(
            DocumentType.RADIOLOGY_REPORT, signal.matched_text,
            cls._evidence_category(field), signal.strength, signal.matched_text,
            signal.concept_id, signal.provenance,
            signal.external_mappings, signal.relationships,
        ) for field in frame.__dataclass_fields__ for signal in getattr(frame, field))
        explanations = cls._explanations(
            frame, roles, report_satisfied, subdomain
        )
        semantic_regions = cls._semantic_regions(text, sections, frame, roles)
        body_regions, authoritative_anatomy = cls._anatomy_context(
            subdomain, frame, roles, current_roles,
            procedure_components,
        )
        contrast = cls._contrast_context(frame, roles, current_roles)
        techniques = cls._techniques(frame, roles, current_roles)
        clinical_purpose = cls._clinical_purpose(frame, roles)
        modality_context = cls._modality_context(
            subdomain, modality_variant, other_reason, study_family, techniques,
            body_regions, frame, roles, current_roles, procedure_components, registry,
        )
        examination = cls._examination(
            subdomain, modality_variant, study_family, modality_context,
            body_regions, authoritative_anatomy,
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
            other_reason=other_reason,
            domain_support=score_support.domain,
            report_support=score_support.report,
            subdomain_support=score_support.subdomain,
            eligible_support_dimension_count=score_support.dimension_count,
            eligible_relationship_count=score_support.relationship_count,
            score=score_support.total,
            evidence=evidence,
            explanations=explanations,
            document_nature=cls._document_nature(
                sections,
                roles,
                frame,
                domain_satisfied,
                (
                    title_led_partial_report
                    or inferred_mri_impression_report
                    or governed_report_narrative
                    or reference_composed_partial_report
                ),
            ),
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

    @classmethod
    def _with_governed_composite_procedure(
        cls,
        text: str,
        sections: tuple[DetectedSection, ...],
        frame: DocumentEvidenceFrame,
        registry,
    ) -> DocumentEvidenceFrame:
        """Recover a procedure only from a unique governed component composition.

        The source must contain co-clausal current-study components. Reference
        terminology supplies the possible procedure; it does not supply semantic
        role, so contextual sections and future/history clauses are excluded here.
        """

        excluded_sections = {
            "clinical_information", "clinical_history", "follow_up", "comparison",
            "findings", "results", "impression", "recommendation",
        }
        source_fields = (
            "modality_signals", "technique_signals", "acquisition_signals",
            "anatomy_signals", "contrast_signals", "laterality_signals",
            "study_extent_signals", "view_signals",
        )
        signals = tuple(
            item for field_name in source_fields for item in getattr(frame, field_name)
        )
        if not signals:
            return frame

        candidates = []
        for clause_start, clause_end in cls._signal_clause_ranges(text, signals):
            clause = text[clause_start:clause_end]
            if (
                RadiologySemanticRoleResolver._RECOMMENDATION.search(clause)
                or RadiologySemanticRoleResolver._HISTORICAL.search(clause)
            ):
                continue
            section = next(
                (item for item in sections if item.start <= clause_start < item.end),
                None,
            )
            if section is not None and section.canonical_name in excluded_sections:
                continue
            clause_signals = tuple(
                item for item in signals
                if clause_start <= item.start and item.end <= clause_end
            )
            if len({(item.start, item.end) for item in clause_signals}) < 2:
                continue
            component_ids = {
                concept_id
                for signal in clause_signals
                for concept_id in registry.equivalent_concept_ids(
                    signal.concept_id, signal.composition_equivalent_mappings
                )
            }
            procedures = registry.composing_procedures(component_ids)
            for procedure in procedures:
                components = []
                matched_signals = []
                categories = set()
                eligible_component_ids = set()
                for relationship in procedure.relationships:
                    if relationship.relationship_type.value != "CAN_COMPOSE":
                        continue
                    try:
                        component = registry.concept(relationship.target_concept_id)
                    except KeyError:
                        continue
                    category = cls._composition_category(component)
                    if category is None:
                        continue
                    eligible_component_ids.add(component.mednexus_concept_id)
                    matched = next(
                        (signal for signal in clause_signals
                         if cls._signal_matches_component(signal, component, registry)),
                        None,
                    )
                    if matched is None:
                        continue
                    components.append(component)
                    matched_signals.append(matched)
                    categories.add(category)
                distinct_components = {
                    item.mednexus_concept_id for item in components
                }
                if (
                    len(distinct_components) < 3
                    or not {"ANATOMY", "ACQUISITION"} <= categories
                ):
                    continue
                modalities = set()
                for relationship in procedure.relationships:
                    if relationship.relationship_type.value != "CAN_COMPOSE":
                        continue
                    try:
                        component = registry.concept(relationship.target_concept_id)
                    except KeyError:
                        continue
                    if dict(component.attributes).get("part_type") \
                            == "RAD_MODALITY_MODALITY_TYPE":
                        modalities.add(component.canonical_name.casefold())
                if len(modalities) != 1:
                    continue
                candidates.append((
                    len(distinct_components), len(categories),
                    -(len(eligible_component_ids) - len(distinct_components)),
                    clause_start, clause_end, procedure,
                    tuple(dict.fromkeys(matched_signals)),
                    frozenset(distinct_components), next(iter(modalities)),
                ))

        if not candidates:
            return frame
        best_score = max((item[0], item[1], item[2]) for item in candidates)
        best = [
            item for item in candidates
            if (item[0], item[1], item[2]) == best_score
        ]
        if len({item[8] for item in best}) != 1:
            return frame
        if len({item[5].mednexus_concept_id for item in best}) != 1:
            return frame
        selected = sorted(best, key=lambda item: (
            item[3], item[4]
        ))[0]
        (
            _, _, _, clause_start, clause_end, procedure, matched,
            observed_component_ids, _,
        ) = selected
        projected_component_ids = set(observed_component_ids)
        for relationship in procedure.relationships:
            if relationship.relationship_type.value != "CAN_COMPOSE":
                continue
            try:
                component = registry.concept(relationship.target_concept_id)
            except KeyError:
                continue
            if dict(component.attributes).get("part_type") \
                    == "RAD_MODALITY_MODALITY_TYPE":
                projected_component_ids.add(component.mednexus_concept_id)
        start = min(item.start for item in matched)
        end = max(item.end for item in matched)
        composed_strength = round(min(
            1.0,
            max(item.strength for item in {id(value): value for value in matched}.values()),
        ), 2)
        signal = EvidenceSignal(
            procedure.mednexus_concept_id,
            procedure.concept_family.value,
            text[start:end],
            start,
            end,
            composed_strength,
            procedure.provenance,
            text[clause_start:clause_end].strip(),
            tuple((item.source_id, item.external_id) for item in procedure.external_mappings),
            tuple((item.relationship_type.value, item.target_concept_id)
                  for item in procedure.relationships
                  if item.relationship_type.value == "CAN_COMPOSE"
                  and item.target_concept_id in projected_component_ids),
            (("inference_basis", "REFERENCE_COMPONENT_COMPOSITION"),),
        )
        if any(
            item.concept_id == signal.concept_id
            and item.start == signal.start and item.end == signal.end
            for item in frame.procedure_signals
        ):
            return frame
        return replace(frame, procedure_signals=(*frame.procedure_signals, signal))

    @staticmethod
    def _signal_clause_ranges(text: str, signals) -> tuple[tuple[int, int], ...]:
        ranges = []
        for signal in signals:
            left = max(
                text.rfind(mark, 0, signal.start)
                for mark in ("\n", ".", ";", "?", "!")
            ) + 1
            right_candidates = [
                position + 1 for mark in ("\n", ".", ";", "?", "!")
                if (position := text.find(mark, signal.end)) >= 0
            ]
            right = min(right_candidates) if right_candidates else len(text)
            ranges.append((left, right))
        return tuple(dict.fromkeys(ranges))

    @staticmethod
    def _composition_category(component) -> str | None:
        part_type = dict(component.attributes).get("part_type")
        if part_type in {
            "RAD_ANATOMIC_LOCATION_REGION_IMAGED",
            "RAD_ANATOMIC_LOCATION_IMAGING_FOCUS",
        }:
            return "ANATOMY"
        if part_type == "RAD_ANATOMIC_LOCATION_LATERALITY":
            return "LATERALITY"
        if part_type in {"RAD_VIEW_VIEW_TYPE", "RAD_VIEW_AGGREGATION"}:
            return "ACQUISITION"
        if part_type in {
            "RAD_MODALITY_MODALITY_TYPE", "RAD_MODALITY_MODALITY_SUBTYPE",
        }:
            return "MODALITY"
        if part_type in {
            "RAD_GUIDANCE_FOR_OBJECT", "RAD_PHARMACEUTICAL_SUBSTANCE_GIVEN",
        }:
            return "CONTRAST"
        return None

    @staticmethod
    def _signal_matches_component(signal: EvidenceSignal, component, registry) -> bool:
        if signal.concept_id == component.mednexus_concept_id:
            return True
        return component.mednexus_concept_id in registry.equivalent_concept_ids(
            signal.concept_id, signal.composition_equivalent_mappings
        )

    @staticmethod
    def _canonical_modality(
        compatibility_subtype: DocumentSubtype,
        domain_satisfied: bool,
        current_modalities,
        procedure_components,
        registry,
    ) -> tuple[RadiologySubdomain | None, str | None, RadiologyOtherReason | None]:
        if not domain_satisfied:
            return None, None, None
        if RadiologyReasoner._interventional_procedure(procedure_components):
            return (
                RadiologySubdomain.OTHER,
                None,
                RadiologyOtherReason.INTERVENTIONAL_PROCEDURE,
            )
        hybrid_family = RadiologyReasoner._nuclear_hybrid_family(procedure_components)
        if hybrid_family is not None:
            return RadiologySubdomain.NUCLEAR_MEDICINE, None, None
        subdomains = {
            item for item in (
                RadiologyReasoner._signal_subdomain(signal, registry)
                for signal in current_modalities
            ) if item is not None
        }
        subdomains.update(RadiologyReasoner._component_subdomains(procedure_components))
        if (
            RadiologySubdomain.FLUOROSCOPY in subdomains
            and RadiologySubdomain.X_RAY in subdomains
        ):
            # Fluoroscopy is a governed, more-specific dynamic X-ray family.
            # Generic projection-radiography evidence must not turn that
            # compatible parent/specialization pair into a false conflict.
            subdomains.discard(RadiologySubdomain.X_RAY)
        if compatibility_subtype is DocumentSubtype.DOPPLER:
            subdomains.add(RadiologySubdomain.ULTRASOUND)
        elif compatibility_subtype is not DocumentSubtype.UNKNOWN:
            subdomains.add({
                DocumentSubtype.CT: RadiologySubdomain.CT,
                DocumentSubtype.MRI: RadiologySubdomain.MRI,
                DocumentSubtype.X_RAY: RadiologySubdomain.X_RAY,
                DocumentSubtype.ULTRASOUND: RadiologySubdomain.ULTRASOUND,
                DocumentSubtype.MAMMOGRAPHY: RadiologySubdomain.MAMMOGRAPHY,
                DocumentSubtype.NUCLEAR_MEDICINE: RadiologySubdomain.NUCLEAR_MEDICINE,
            }[compatibility_subtype])
        if len(subdomains) == 1:
            selected = next(iter(subdomains))
            variant = (
                "DOPPLER"
                if selected is RadiologySubdomain.ULTRASOUND
                and compatibility_subtype is DocumentSubtype.DOPPLER
                else None
            )
            return selected, variant, None
        if len(subdomains) > 1:
            return (
                RadiologySubdomain.OTHER,
                None,
                RadiologyOtherReason.CONFLICTING_CURRENT_FAMILY,
            )
        reason = (
            RadiologyOtherReason.UNSUPPORTED_FAMILY
            if current_modalities or procedure_components
            else RadiologyOtherReason.INSUFFICIENT_FAMILY_EVIDENCE
        )
        return RadiologySubdomain.OTHER, None, reason

    @staticmethod
    def _document_nature(
        sections: tuple[DetectedSection, ...],
        roles: RadiologyRoleResolution,
        frame: DocumentEvidenceFrame,
        domain_satisfied: bool,
        title_led_partial_report: bool = False,
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
        if title_led_partial_report:
            return DocumentNature.PARTIAL_REPORT
        if domain_satisfied and section_ids:
            return DocumentNature.PARTIAL_REPORT
        return DocumentNature.UNKNOWN

    @staticmethod
    def _semantic_regions(
        text: str,
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
        for start, end in RadiologySemanticRoleResolver.unheaded_observation_regions(
            text, sections, frame
        ):
            related = tuple(
                value for value in roles.evidence
                if value.section_id
                == RadiologySemanticRoleResolver._UNHEADED_OBSERVATION_SECTION
                and start <= value.signal.start < end
            )
            decisions.append(RadiologySemanticRegionDecision(
                section_id=RadiologySemanticRoleResolver._UNHEADED_OBSERVATION_SECTION,
                original_heading="",
                start=start,
                end=end,
                confidence=0.75,
                canonical_role=SemanticRegionRole.OBSERVATION_NARRATIVE,
                qualifiers=("INFERRED_UNHEADED",),
                evidence_concept_ids=tuple(dict.fromkeys(
                    value.signal.concept_id for value in related
                )),
                provenance=tuple(dict.fromkeys((
                    "MEDNEXUS_STRUCTURAL_REASONING",
                    *(source for value in related for source in value.signal.provenance),
                ))),
            ))
        return tuple(sorted(decisions, key=lambda item: (item.start, item.end)))

    @classmethod
    def _anatomy_context(
        cls,
        subdomain: RadiologySubdomain | None,
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
        identity_anatomy = cls._performed_study_anatomy_signals(
            broad_anatomy, roles
        )
        if modality_spans:
            broad_anatomy.sort(key=lambda item: (
                min(max(span.start - item.end, item.start - span.end, 0)
                    for span in modality_spans),
                item.start,
            ))
        component_regions = tuple(dict.fromkeys(
            cls._canonical_body_region(item.canonical_name)
            for item in procedure_components
            if dict(item.attributes).get("part_type")
            == "RAD_ANATOMIC_LOCATION_REGION_IMAGED"
            and cls._canonical_body_region(item.canonical_name) is not None
        ))
        # A role-qualified procedure or performed-study title is authoritative.
        # Technique scan coverage and lower-level narrative anatomy remain evidence,
        # but cannot broaden or replace the performed-study anatomy set.
        selected_broad = identity_anatomy or broad_anatomy
        lexical_regions = tuple(dict.fromkeys(
            _BODY_REGION_IDS[item.concept_id] for item in selected_broad
        ))
        regions = tuple(dict.fromkeys((*component_regions, *lexical_regions)))
        authoritative_anatomy = cls._authoritative_anatomy(
            frame, roles, anatomy_signals
        )
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
        if subdomain is RadiologySubdomain.X_RAY and not regions and authoritative_anatomy:
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
    def _performed_study_anatomy_signals(anatomy_signals, roles):
        qualified = {id(item.signal): item for item in roles.evidence}
        return [
            signal for signal in anatomy_signals
            if (
                (item := qualified.get(id(signal))) is not None
                and (
                    item.section_id in {
                        "document_title", "radiology_examination", "procedure_information",
                    }
                    or (
                        item.role is RadiologySemanticRole.PERFORMED_STUDY
                        and RadiologySemanticRoleResolver._title_like(signal.context)
                    )
                )
            )
        ]

    @staticmethod
    def _contrast_context(
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
    ) -> str | None:
        current_contrast = roles.signals(frame.contrast_signals, *current_roles)
        contrast_ids = {item.concept_id for item in current_contrast}
        polarities = {
            dict(item.attributes).get("contrast_polarity")
            for item in current_contrast
        } - {None}
        if "RAD_CONTRAST_PRE_POST" in contrast_ids or "PRE_AND_POST" in polarities:
            return "PRE_AND_POST_CONTRAST"
        if {"WITH", "WITHOUT"} <= polarities or {
            "RAD_CONTRAST_WITH", "RAD_CONTRAST_WITHOUT"
        } <= contrast_ids:
            return None
        if "RAD_CONTRAST_WITH" in contrast_ids or "WITH" in polarities:
            return "WITH_CONTRAST"
        if "RAD_CONTRAST_WITHOUT" in contrast_ids or "WITHOUT" in polarities:
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
        if modality_types == {"mg"}:
            return DocumentSubtype.MAMMOGRAPHY
        if modality_types in ({"nm"}, {"pt"}, {"nm.spect+ct"}, {"pt+ct"}):
            return DocumentSubtype.NUCLEAR_MEDICINE
        return DocumentSubtype.UNKNOWN

    @staticmethod
    def _component_subdomains(components) -> set[RadiologySubdomain]:
        names = {
            item.canonical_name.casefold()
            for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_TYPE"
        }
        result = set()
        for name in names:
            if name == "ct":
                result.add(RadiologySubdomain.CT)
            elif name == "mr":
                result.add(RadiologySubdomain.MRI)
            elif name in {"xr", "cr", "dx"}:
                result.add(RadiologySubdomain.X_RAY)
            elif name == "us":
                result.add(RadiologySubdomain.ULTRASOUND)
            elif name == "mg":
                result.add(RadiologySubdomain.MAMMOGRAPHY)
            elif name in {"nm", "pt", "nm.spect+ct", "pt+ct"}:
                result.add(RadiologySubdomain.NUCLEAR_MEDICINE)
            elif name == "rf":
                result.add(RadiologySubdomain.FLUOROSCOPY)
        return result

    @staticmethod
    def _signal_subdomain(signal, registry) -> RadiologySubdomain | None:
        curated = {
            "RAD_MODALITY_CT": RadiologySubdomain.CT,
            "RAD_MODALITY_MRI": RadiologySubdomain.MRI,
            "RAD_MODALITY_XRAY": RadiologySubdomain.X_RAY,
            "RAD_MODALITY_ULTRASOUND": RadiologySubdomain.ULTRASOUND,
            "RAD_MODALITY_DOPPLER": RadiologySubdomain.ULTRASOUND,
            "RAD_MODALITY_MAMMOGRAPHY": RadiologySubdomain.MAMMOGRAPHY,
            "RAD_MODALITY_NUCLEAR_MEDICINE": RadiologySubdomain.NUCLEAR_MEDICINE,
        }
        if signal.concept_id in curated:
            return curated[signal.concept_id]
        try:
            concept = registry.concept(signal.concept_id)
        except KeyError:
            return None
        if dict(concept.attributes).get("part_type") == "RAD_MODALITY_MODALITY_TYPE":
            component_subdomains = RadiologyReasoner._component_subdomains((concept,))
            return next(iter(component_subdomains), None)
        if dict(concept.attributes).get("part_type") == "RAD_MODALITY_MODALITY_SUBTYPE":
            governed = RadiologyReasoner._governed_subtype_subdomain(concept, registry)
            if governed is not None:
                return governed
        dicom_codes = {
            mapping.external_id.upper()
            for mapping in concept.external_mappings
            if mapping.source_id in {"DICOM_2026_CURRENT", "DICOM_DCMR_2026C"}
        }
        for codes, subdomain in (
            ({"CT"}, RadiologySubdomain.CT),
            ({"MR"}, RadiologySubdomain.MRI),
            ({"CR", "DX", "XR"}, RadiologySubdomain.X_RAY),
            ({"US"}, RadiologySubdomain.ULTRASOUND),
            ({"MG"}, RadiologySubdomain.MAMMOGRAPHY),
            ({"NM", "PT"}, RadiologySubdomain.NUCLEAR_MEDICINE),
            ({"RF"}, RadiologySubdomain.FLUOROSCOPY),
        ):
            if dicom_codes & codes:
                return subdomain
        name = concept.canonical_name.casefold()
        return {
            "computed tomography": RadiologySubdomain.CT,
            "magnetic resonance imaging": RadiologySubdomain.MRI,
            "radiography": RadiologySubdomain.X_RAY,
            "projection radiography": RadiologySubdomain.X_RAY,
            "computed radiography": RadiologySubdomain.X_RAY,
            "digital radiography": RadiologySubdomain.X_RAY,
            "ultrasound": RadiologySubdomain.ULTRASOUND,
            "doppler ultrasound": RadiologySubdomain.ULTRASOUND,
            "mammography": RadiologySubdomain.MAMMOGRAPHY,
            "nuclear medicine": RadiologySubdomain.NUCLEAR_MEDICINE,
            "scintigraphy": RadiologySubdomain.NUCLEAR_MEDICINE,
            "positron emission tomography": RadiologySubdomain.NUCLEAR_MEDICINE,
            "single photon emission computed tomography": RadiologySubdomain.NUCLEAR_MEDICINE,
            "fluoroscopy": RadiologySubdomain.FLUOROSCOPY,
        }.get(name)

    @staticmethod
    def _governed_subtype_subdomain(concept, registry) -> RadiologySubdomain | None:
        """Infer one family only when every governed composing procedure agrees."""

        supported: set[RadiologySubdomain] = set()
        procedures = registry.composing_procedures((concept.mednexus_concept_id,))
        if not procedures:
            return None
        for procedure in procedures:
            components = []
            for relationship in procedure.relationships:
                if relationship.relationship_type.value != "CAN_COMPOSE":
                    continue
                try:
                    components.append(
                        registry.concept(relationship.target_concept_id)
                    )
                except KeyError:
                    continue
            procedure_subdomains = RadiologyReasoner._component_subdomains(components)
            if len(procedure_subdomains) != 1:
                return None
            supported.update(procedure_subdomains)
            if len(supported) > 1:
                return None
        return next(iter(supported), None)

    @staticmethod
    def _nuclear_hybrid_family(components) -> NuclearMedicineStudyFamily | None:
        modality_types = {
            item.canonical_name.casefold()
            for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_TYPE"
        }
        if "pt+ct" in modality_types:
            return NuclearMedicineStudyFamily.PET_CT
        if "nm.spect+ct" in modality_types:
            return NuclearMedicineStudyFamily.SPECT_CT
        return None

    @staticmethod
    def _nuclear_study_family(
        components, current_modalities, registry
    ) -> NuclearMedicineStudyFamily:
        hybrid = RadiologyReasoner._nuclear_hybrid_family(components)
        if hybrid is not None:
            return hybrid
        modality_types = {
            item.canonical_name.casefold()
            for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_TYPE"
        }
        modality_subtypes = {
            item.canonical_name.casefold()
            for item in components
            if dict(item.attributes).get("part_type") == "RAD_MODALITY_MODALITY_SUBTYPE"
        }
        if "pt" in modality_types:
            return NuclearMedicineStudyFamily.PET
        if "nm" in modality_types and "spect" in modality_subtypes:
            return NuclearMedicineStudyFamily.SPECT
        if "nm" in modality_types:
            return NuclearMedicineStudyFamily.PLANAR
        names = set()
        for signal in current_modalities:
            try:
                names.add(registry.concept(signal.concept_id).canonical_name.casefold())
            except KeyError:
                if signal.concept_id == "RAD_MODALITY_NUCLEAR_MEDICINE":
                    names.add("nuclear medicine")
        if "positron emission tomography" in names:
            return NuclearMedicineStudyFamily.PET
        if "single photon emission computed tomography" in names:
            return NuclearMedicineStudyFamily.SPECT
        return NuclearMedicineStudyFamily.OTHER

    @staticmethod
    def _interventional_procedure(components) -> bool:
        interventional_parts = {
            "RAD_GUIDANCE_FOR_ACTION",
            "RAD_GUIDANCE_FOR_APPROACH",
            "RAD_GUIDANCE_FOR_PRESENCE",
        }
        return any(
            dict(item.attributes).get("part_type") in interventional_parts
            for item in components
        )

    @staticmethod
    def _study_family(subdomain, components, current_modalities, registry):
        names = {item.canonical_name.casefold() for item in components}
        for signal in current_modalities:
            try:
                concept = registry.concept(signal.concept_id)
            except KeyError:
                continue
            if dict(concept.attributes).get("part_type") == "RAD_MODALITY_MODALITY_SUBTYPE":
                names.add(concept.canonical_name.casefold())
        angiographic = "angio" in names
        if subdomain is RadiologySubdomain.CT:
            return CTStudyFamily.CTA if angiographic else CTStudyFamily.CT
        if subdomain is RadiologySubdomain.MRI:
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
        subdomain: RadiologySubdomain | None,
        modality_variant: str | None,
        study_family,
        modality_context: RadiologyModalityContext | None,
        regions: tuple[str, ...],
        authoritative_anatomy: str | None,
    ) -> str | None:
        if subdomain in {None, RadiologySubdomain.OTHER}:
            return None
        modality_value = study_family.value if study_family is not None else subdomain.value
        if isinstance(modality_context, NuclearMedicineClinicalContext):
            modality_value = {
                NuclearMedicineStudyFamily.PLANAR: "Nuclear Medicine",
                NuclearMedicineStudyFamily.SPECT: "SPECT",
                NuclearMedicineStudyFamily.PET: "PET",
                NuclearMedicineStudyFamily.SPECT_CT: "SPECT/CT",
                NuclearMedicineStudyFamily.PET_CT: "PET/CT",
                NuclearMedicineStudyFamily.OTHER: "Nuclear Medicine",
            }[modality_context.study_family]
        elif subdomain is RadiologySubdomain.FLUOROSCOPY:
            modality_value = "Fluoroscopy"
        elif subdomain is RadiologySubdomain.MAMMOGRAPHY:
            modality_value = "Mammography"
        elif subdomain is RadiologySubdomain.ULTRASOUND and modality_variant == "DOPPLER":
            modality_value = "Doppler Ultrasound"
        region_label = " & ".join(item.title() for item in regions)
        study_anatomy = (
            authoritative_anatomy
            if authoritative_anatomy and (
                subdomain is RadiologySubdomain.X_RAY or not region_label
            )
            else region_label or None
        )
        modality_label = {
            "X_RAY": "X-ray",
        }.get(modality_value, modality_value)
        return " ".join(filter(None, (
            modality_label, study_anatomy.title() if study_anatomy else None,
        ))) or None

    @staticmethod
    def _modality_context(
        subdomain: RadiologySubdomain | None,
        modality_variant: str | None,
        other_reason: RadiologyOtherReason | None,
        study_family,
        techniques: tuple[str, ...],
        body_regions: tuple[str, ...],
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
        current_roles: tuple[RadiologySemanticRole, ...],
        procedure_components,
        registry,
    ) -> RadiologyModalityContext | None:
        multiplanar = "Multiplanar imaging" in techniques
        if subdomain is RadiologySubdomain.CT:
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
        if subdomain is RadiologySubdomain.MRI:
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
        if subdomain is RadiologySubdomain.X_RAY:
            view_signals = tuple(
                item for item in roles.signals(frame.view_signals, *current_roles)
                if dict(item.attributes).get("part_type") == "RAD_VIEW_VIEW_TYPE"
                or item.concept_family != "PROCEDURE_ATTRIBUTE"
            )
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
        if subdomain is RadiologySubdomain.ULTRASOUND:
            doppler = (
                modality_variant == "DOPPLER"
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
        if subdomain is RadiologySubdomain.MAMMOGRAPHY:
            purpose_names = {
                item.canonical_name.casefold()
                for item in procedure_components
                if dict(item.attributes).get("part_type") == "RAD_REASON_FOR_EXAM"
            }
            purposes = tuple(
                value for name, value in (
                    ("screening", MammographyStudyPurpose.SCREENING),
                    ("diagnostic", MammographyStudyPurpose.DIAGNOSTIC),
                ) if name in purpose_names
            )
            if not purposes and any(
                dict(item.attributes).get("part_type") == "RAD_VIEW_VIEW_TYPE"
                and item.canonical_name.casefold() == "spot"
                for item in procedure_components
            ):
                purposes = (MammographyStudyPurpose.DIAGNOSTIC,)
            acquisition = tuple(value for value, present in (
                (
                    MammographyAcquisitionContext.STANDARD_VIEWS,
                    any(
                        dict(item.attributes).get("part_type") == "RAD_VIEW_AGGREGATION"
                        and item.canonical_name.casefold() in {"view", "views"}
                        for item in procedure_components
                    ),
                ),
                (
                    MammographyAcquisitionContext.TOMOSYNTHESIS,
                    any(
                        dict(item.attributes).get("part_type")
                        == "RAD_MODALITY_MODALITY_SUBTYPE"
                        and item.canonical_name.casefold() == "tomosynthesis"
                        for item in procedure_components
                    ),
                ),
            ) if present)
            return MammographyClinicalContext(
                study_purpose=purposes[0] if len(purposes) == 1 else None,
                laterality=RadiologyReasoner._laterality_context(
                    frame, roles, current_roles, procedure_components, registry
                ),
                acquisition_context=acquisition,
                birads_assessment_present=RadiologyReasoner._birads_assessment_presence(
                    frame, roles, registry
                ),
            )
        if subdomain is RadiologySubdomain.NUCLEAR_MEDICINE:
            family = RadiologyReasoner._nuclear_study_family(
                procedure_components,
                roles.signals(frame.modality_signals, *current_roles),
                registry,
            )
            radiopharmaceutical = any(
                dict(item.attributes).get("part_type")
                == "RAD_PHARMACEUTICAL_SUBSTANCE_GIVEN"
                for item in procedure_components
            )
            quantitative_uptake = any(
                dict(item.attributes).get("part_type") == "RAD_VIEW_AGGREGATION"
                and item.canonical_name.casefold() == "uptake"
                for item in procedure_components
            )
            return NuclearMedicineClinicalContext(
                study_family=family,
                radiopharmaceutical_context_present=(
                    True if radiopharmaceutical else None
                ),
                quantitative_uptake_context_present=(
                    True if quantitative_uptake else None
                ),
            )
        if subdomain is RadiologySubdomain.FLUOROSCOPY:
            contrast = any(
                dict(item.attributes).get("part_type")
                in {"RAD_PHARMACEUTICAL_SUBSTANCE_GIVEN", "RAD_GUIDANCE_FOR_OBJECT"}
                and "contrast" in item.canonical_name.casefold()
                for item in procedure_components
            )
            dynamic = any(
                (
                    dict(item.attributes).get("part_type") == "RAD_VIEW_AGGREGATION"
                    and item.canonical_name.casefold() == "dynamic"
                )
                or (
                    dict(item.attributes).get("part_type")
                    == "RAD_MODALITY_MODALITY_SUBTYPE"
                    and item.canonical_name.casefold() == "functional"
                )
                or (
                    dict(item.attributes).get("part_type") == "RAD_REASON_FOR_EXAM"
                    and item.canonical_name.casefold().endswith("function")
                )
                for item in procedure_components
            )
            family = (
                FluoroscopyStudyFamily.DYNAMIC_FUNCTIONAL_STUDY if dynamic
                else FluoroscopyStudyFamily.CONTRAST_STUDY if contrast
                else FluoroscopyStudyFamily.GENERAL_DIAGNOSTIC
            )
            return FluoroscopyClinicalContext(
                study_family=family,
                body_system=body_regions[0] if body_regions else None,
                contrast_study_present=True if contrast else None,
                dynamic_functional_present=True if dynamic else None,
            )
        if subdomain is RadiologySubdomain.OTHER:
            return OtherRadiologyClinicalContext(
                resolution_reason=(
                    other_reason or RadiologyOtherReason.INSUFFICIENT_FAMILY_EVIDENCE
                )
            )
        return None

    @staticmethod
    def _birads_assessment_presence(frame, roles, registry) -> bool | None:
        assessment_signals = roles.signals(
            frame.observation_signals,
            RadiologySemanticRole.FINDINGS_CONTEXT,
            RadiologySemanticRole.IMPRESSION_CONTEXT,
            RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY,
        )
        for signal in assessment_signals:
            try:
                concept = registry.concept(signal.concept_id)
            except KeyError:
                continue
            attributes = dict(concept.attributes)
            if (
                concept.concept_family.value == "IMAGING_OBSERVATION"
                and concept.canonical_name.casefold().startswith("bi-rads category")
                and attributes.get("relationship.Source", "").casefold().startswith(
                    "bi-rads"
                )
            ):
                return True
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
        identity_anatomy = RadiologyReasoner._performed_study_anatomy_signals(
            anatomy_signals, roles
        )
        if identity_anatomy:
            anatomy_signals = identity_anatomy
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
            if identity_anatomy and len({item.concept_id for item in broad}) > 1:
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
    def _explanations(
        frame,
        roles,
        report_satisfied,
        subdomain: RadiologySubdomain | None,
    ) -> tuple[RecognitionExplanation, ...]:
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
        current_procedures = roles.signals(frame.procedure_signals, *current)
        if current_procedures:
            family = (
                subdomain.value.replace("_", " ").title()
                if subdomain not in {None, RadiologySubdomain.OTHER}
                else "Imaging"
            )
            explanations.append(RecognitionExplanation(
                "CURRENT_GOVERNED_PROCEDURE",
                f"Current {family} procedure composition identified",
                "procedure",
                current_procedures[0].concept_id,
                RadiologySemanticRole.PERFORMED_STUDY.value,
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
        text: str,
        sections: tuple[DetectedSection, ...],
        frame: DocumentEvidenceFrame,
    ) -> bool:
        """Detect substantive report prose without assigning EXTRACT semantics."""
        inferred = RadiologySemanticRoleResolver.unheaded_observation_regions(
            text, sections, frame
        )
        if any(
            RadiologySemanticRoleResolver.substantive_narrative(text[start:end])
            for start, end in inferred
        ):
            return True
        if inferred:
            return True
        impression = next((item for item in sections if item.canonical_name == "impression"), None)
        if impression is not None:
            preceding = [item for item in sections if item.start < impression.start]
            if preceding:
                boundary = max(preceding, key=lambda item: item.start)
                body = text[
                    boundary.start + len(boundary.original_heading):impression.start
                ].strip(" \t\r\n:")
            else:
                body = text[:impression.start].strip(" \t\r\n:")
        else:
            findings = next(
                (item for item in sections if item.canonical_name == "findings"), None
            )
            if findings is not None:
                body = text[
                    findings.start + len(findings.original_heading):
                ].strip(" \t\r\n:")
            else:
                title = RadiologyEvidenceFrameBuilder._first_nonempty_line(text)
                if title is None:
                    return False
                body = text[title[2]:].strip(" \t\r\n:")
        return RadiologySemanticRoleResolver.substantive_narrative(body)

    @staticmethod
    def _observation_region_present(
        text: str, sections: tuple[DetectedSection, ...]
    ) -> bool:
        """Accept a non-empty governed observation region without prose heuristics."""

        for section in sections:
            if section.canonical_name not in {"findings", "results"}:
                continue
            body = text[
                section.start + len(section.original_heading):section.end
            ].strip(" \t\r\n:")
            if re.search(r"[^\W_]", body, re.UNICODE):
                return True
        return False

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
            eligibility.signals(composition, "observation_signals"),
        )
        subdomain_groups = tuple(
            eligibility.signals(current, field_name) for field_name in (
                "modality_signals", "procedure_signals",
                "technique_signals", "acquisition_signals",
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
            subdomain_groups[1],
            (*subdomain_groups[2], *subdomain_groups[3]),
            subdomain_groups[4],
            subdomain_groups[5],
            subdomain_groups[6],
            (*subdomain_groups[7], *subdomain_groups[8]),
            report_groups[0],
            report_groups[1],
            report_groups[2],
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
