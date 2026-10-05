"""Radiology STANDARDIZE V0: additive, offline representation of accepted facts.

Only EXTRACT canonical facts and UNDERSTAND structured study context enter here.
The source objects are never modified and terminology cannot change clinical meaning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from backend.app.modules.medical_document_intelligence.understanding.reference_model.models import ConceptFamily
from backend.app.modules.medical_document_intelligence.understanding.reference_model.normalization import normalize_reference_term
from backend.app.modules.medical_document_intelligence.understanding.reference_model.runtime import build_active_reference_registry


PROFILE = "radiology-standardize-v0"
RADLEX = "RADLEX_CURRENT"
PLAYBOOK = "LOINC_RSNA_2_82"
SNOMED = "SNOMED_INT_20260701"
EXACT_TYPES = {"EXACT_LABEL", "EXACT_SYNONYM"}
_MEASURE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z]+)?\s*$")


@dataclass(frozen=True)
class TerminologyCandidate:
    code: str
    preferred_label: str
    match_type: str
    mapping_method: str = "LOCAL_REFERENCE_EXACT"


class TerminologyProvider(Protocol):
    system: str
    version: str | None
    available: bool

    def get_candidates(self, text: str) -> tuple[TerminologyCandidate, ...]: ...


class ReferenceTerminologyProvider:
    """Expose only active, source-backed equivalent codes from the existing registry."""

    def __init__(self, system: str, families: set[ConceptFamily], registry=None):
        self.system = system
        self._registry = registry or build_active_reference_registry()
        self.version = self._registry.active_configuration.get(system)
        self._index: dict[str, list[TerminologyCandidate]] = {}
        if self.version:
            for concept in self._registry.concepts:
                if concept.status != "ACTIVE" or concept.concept_family not in families or system not in concept.provenance:
                    continue
                mappings = [item for item in concept.external_mappings
                            if item.source_id == system and item.mapping_type.casefold() == "equivalent" and item.external_id]
                for mapping in mappings:
                    for term in concept.preferred_terms:
                        self._add(term, TerminologyCandidate(mapping.external_id, mapping.display or concept.canonical_name, "EXACT_LABEL"))
                    for term in concept.synonyms:
                        self._add(term, TerminologyCandidate(mapping.external_id, mapping.display or concept.canonical_name, "EXACT_SYNONYM"))
        self.available = bool(self.version and self._index)

    def _add(self, term: str, candidate: TerminologyCandidate) -> None:
        key = normalize_reference_term(term)
        if key:
            self._index.setdefault(key, []).append(candidate)

    def get_candidates(self, text: str) -> tuple[TerminologyCandidate, ...]:
        return tuple(self._index.get(normalize_reference_term(text), ()))


class OptionalSnomedProvider:
    """Interface placeholder; no licensed content or runtime dependency is bundled."""

    system = SNOMED
    version = None
    available = False

    def get_candidates(self, text: str) -> tuple[TerminologyCandidate, ...]:
        return ()


def _mapping(text: str | None, source_fact_id: str | None, provider: TerminologyProvider) -> dict:
    source = text or ""
    candidates = provider.get_candidates(source) if provider.available and source.strip() else ()
    # A preferred-term hit takes precedence over a synonym hit. Ambiguity
    # within the selected tier still requires review.
    preferred = tuple(item for item in candidates if item.match_type == "EXACT_LABEL")
    if preferred:
        candidates = preferred
    # A duplicated code is one target, but competing codes remain ambiguous.
    by_code = {}
    for candidate in sorted(candidates, key=lambda item: (item.code, item.match_type != "EXACT_LABEL")):
        by_code.setdefault(candidate.code, candidate)
    exact = {code: item for code, item in by_code.items() if item.match_type in EXACT_TYPES}
    chosen = next(iter(exact.values())) if len(exact) == 1 and len(by_code) == 1 else None
    ambiguous = bool(by_code) and chosen is None
    status = "MATCHED" if chosen else "NEEDS_REVIEW" if ambiguous else "UNMAPPED"
    reason = ("AMBIGUOUS_MAPPING" if ambiguous else
              "PROVIDER_UNAVAILABLE" if not provider.available else
              "REFERENCE_DATA_MISSING" if not source.strip() else "UNMAPPED_CONCEPT")
    result = {
        "terminology_system": provider.system,
        "terminology_version": provider.version if provider.available else None,
        "source_text": source,
        "source_fact_id": source_fact_id,
        "code": chosen.code if chosen else None,
        "preferred_label": chosen.preferred_label if chosen else None,
        "mapping_status": status,
        "match_type": chosen.match_type if chosen else "AMBIGUOUS" if ambiguous else "NONE",
        "mapping_method": chosen.mapping_method if chosen else "LOCAL_REFERENCE_CANDIDATES" if ambiguous else "NO_MAPPING",
        "confidence": "1.0" if chosen else None,
        "review_required": ambiguous,
        "review_reason": reason if not chosen else None,
    }
    if ambiguous:
        result["candidate_mappings"] = [
            {"code": item.code, "preferred_label": item.preferred_label, "match_type": item.match_type}
            for item in sorted(by_code.values(), key=lambda value: value.code)
        ]
    return result


def _canonical_terms(fact: dict) -> tuple[str, ...]:
    """Use accepted concept identifiers, never evidence or display-label token stripping.

    Open concepts encode an unordered set of accepted tokens. They can yield
    reviewable component hits, but cannot identify a clinical head or prove
    that any hit is equivalent to the complete fact.
    """
    key = fact.get("canonical_concept")
    if not isinstance(key, str) or not key:
        return ()
    if key.startswith("general:"):
        parts = key.split(":")
        if len(parts) < 2 or parts[1] == "functional_absence":
            return ()
        if parts[1] == "open":
            return tuple(sorted(set(parts[2:])))
        if parts[1] == "condition":
            return (" ".join(parts[2:]),) if len(parts) > 2 else ()
        return (parts[1].replace("_", " "),)
    full = key.replace("_", " ")
    if "_" not in key:
        return (full,)
    # Named identifiers are ordered concept names: only their terminal noun
    # can be proposed as a reviewable base component. In particular, "mass"
    # from "mass_effect" and "lesion" from "lesion_complex" are not heads.
    return (full, key.rsplit("_", 1)[-1])


def _concept_mapping(fact: dict, provider: TerminologyProvider) -> tuple[dict, list[dict]]:
    fact_id = fact["fact_id"]
    display = fact.get("display_label")
    whole = _mapping(display, fact_id, provider)
    whole["lookup_scope"] = "WHOLE_LABEL"
    if whole["mapping_status"] != "UNMAPPED":
        return whole, []

    components = []
    seen_codes = set()
    for term in _canonical_terms(fact):
        mapping = _mapping(term, fact_id, provider)
        if mapping["mapping_status"] != "MATCHED" or mapping["code"] in seen_codes:
            continue
        seen_codes.add(mapping["code"])
        mapping["lookup_scope"] = "CANONICAL_COMPONENT"
        mapping["relationship_to_fact"] = "BROADER"
        components.append(mapping)
    if not components:
        return whole, []

    # Negation belongs to the unchanged source assertion. Only when removing
    # its explicit display prefix leaves exactly the canonical concept can
    # that underlying concept be represented as equivalent.
    label_without_assertion = display or ""
    if fact.get("assertion_state") == "ABSENT_NEGATED":
        label_without_assertion = re.sub(r"^No\s+", "", label_without_assertion, flags=re.I)
    equivalent = (len(components) == 1 and
                  normalize_reference_term(label_without_assertion) ==
                  normalize_reference_term(components[0]["source_text"]))
    if equivalent:
        components[0]["relationship_to_fact"] = "EXACT_CONCEPT_ASSERTION_SEPARATE"
        concept = {**components[0], "source_text": display or "",
                   "lookup_text": components[0]["source_text"],
                   "mapping_method": "STRUCTURED_CANONICAL_CONCEPT",
                   "lookup_scope": "CANONICAL_CONCEPT",
                   "relationship_to_fact": "EXACT_CONCEPT_ASSERTION_SEPARATE"}
        return concept, components

    whole.update(mapping_status="NEEDS_REVIEW", match_type="BROADER",
                 mapping_method="STRUCTURED_COMPONENTS", review_required=True,
                 review_reason="COMPONENT_NOT_WHOLE_EQUIVALENCE",
                 candidate_mappings=[{"code": item["code"],
                                      "preferred_label": item["preferred_label"],
                                      "match_type": item["match_type"]}
                                     for item in components])
    return whole, components


def _decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


def normalize_measurement(text: str, source_measurement_id: str) -> dict:
    """Keep the exact source string and normalize only known length dimensions."""
    match = _MEASURE.fullmatch(text) if isinstance(text, str) else None
    original_value = match.group("value") if match else None
    original_unit = match.group("unit") if match else None
    result = {"source_measurement_id": source_measurement_id, "original_text": text,
              "original_value": original_value, "original_unit": original_unit,
              "ucum_code": None, "normalized_value": None, "normalized_unit": None,
              "conversion_applied": False, "conversion_method": None,
              "mapping_status": "NEEDS_REVIEW", "review_required": True,
              "review_reason": "INVALID_MEASUREMENT"}
    if not match or not original_unit:
        return result
    unit = original_unit.casefold()
    if unit not in {"mm", "cm"}:
        result.update(mapping_status="UNMAPPED", review_required=False,
                      review_reason="UNMAPPED_UNIT")
        return result
    try:
        value = Decimal(original_value)
    except InvalidOperation:
        return result
    normalized = value * (Decimal("10") if unit == "cm" else Decimal("1"))
    result.update(ucum_code=unit, normalized_value=_decimal(normalized),
                  normalized_unit="mm", conversion_applied=unit == "cm",
                  conversion_method="UCUM_LENGTH_CM_TO_MM" if unit == "cm" else "UCUM_LENGTH_IDENTITY",
                  mapping_status="MATCHED", review_required=False, review_reason=None)
    return result


def _value(value):
    return value.value if hasattr(value, "value") else value


def _study(context, provider: TerminologyProvider) -> dict:
    clinical = context.clinical_context
    domain = clinical.domain_extension
    modality_context = domain.modality_context if domain else None
    laterality = _value(getattr(modality_context, "laterality", None))
    examination = clinical.examination or (domain.examination if domain else None)
    procedure = _mapping(examination, None, provider)
    if procedure["mapping_status"] == "UNMAPPED" and isinstance(examination, str) and \
            isinstance(clinical.modality, str) and clinical.modality.upper() == "MRI":
        # Playbook's exact modality spelling is MR. Do not infer anatomy,
        # protocol, contrast, or laterality from the examination label.
        alias = re.sub(r"^MRI\b", "MR", examination, flags=re.I)
        if alias != examination:
            alternative = _mapping(alias, None, provider)
            if alternative["mapping_status"] != "UNMAPPED":
                alternative["source_text"] = examination
                alternative["lookup_text"] = alias
                alternative["mapping_method"] = "EXACT_MODALITY_ALIAS"
                procedure = alternative
    return {"original_exam_name": examination,
            "normalized_modality": clinical.modality,
            "normalized_body_region": clinical.body_region,
            "normalized_laterality": laterality,
            "procedure_mapping": procedure}


class ClinicalStandardizationService:
    def __init__(self, *, concept_provider: TerminologyProvider | None = None,
                 anatomy_provider: TerminologyProvider | None = None,
                 procedure_provider: TerminologyProvider | None = None, registry=None):
        # Reuse the already activated offline reference model. The providers
        # intentionally exclude compatibility/curated concepts without a code.
        if concept_provider is None or anatomy_provider is None or procedure_provider is None:
            registry = registry or build_active_reference_registry()
        self.concept_provider = concept_provider or ReferenceTerminologyProvider(
            RADLEX, {ConceptFamily.CLINICAL_FINDING, ConceptFamily.IMAGING_OBSERVATION}, registry)
        self.anatomy_provider = anatomy_provider or ReferenceTerminologyProvider(
            RADLEX, {ConceptFamily.BODY_REGION, ConceptFamily.IMAGING_FOCUS}, registry)
        self.procedure_provider = procedure_provider or ReferenceTerminologyProvider(
            PLAYBOOK, {ConceptFamily.IMAGING_PROCEDURE}, registry)

    def standardize(self, extract_result: dict, context) -> dict:
        if not isinstance(extract_result, dict) or not isinstance(extract_result.get("clinical_synthesis"), dict):
            raise ValueError("STANDARDIZE requires a completed EXTRACT clinical synthesis.")
        facts = extract_result["clinical_synthesis"].get("canonical_facts")
        if not isinstance(facts, list):
            raise ValueError("STANDARDIZE requires canonical clinical facts.")
        if context is None or context.identity.healthcare_domain != "RADIOLOGY":
            raise ValueError("STANDARDIZE V0 requires accepted Radiology study context.")
        ids = [fact.get("fact_id") for fact in facts]
        if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("Canonical fact IDs must be present and unique.")
        standardized = []
        for fact in facts:
            fact_id = fact["fact_id"]
            concept, components = _concept_mapping(fact, self.concept_provider)
            anatomy = [_mapping(value, fact_id, self.anatomy_provider)
                       for value in fact.get("anatomy", [])]
            measurements = []
            for observation_index, observation in enumerate(fact.get("observations", [])):
                for measurement_index, source in enumerate(observation.get("measurements", [])):
                    measurement = normalize_measurement(source, f"{fact_id}:o{observation_index}:m{measurement_index}")
                    measurement["source_observation_index"] = observation_index
                    measurements.append(measurement)
            review_reasons = sorted({item["review_reason"] for item in [concept, *components, *anatomy, *measurements]
                                     if item["review_required"] and item["review_reason"]})
            standardized.append({"source_fact_id": fact_id,
                "source_assertion_state": fact.get("assertion_state"),
                "concept_mappings": [concept], "component_mappings": components,
                "anatomy_mappings": anatomy,
                "standardized_measurements": measurements,
                "standardization_status": "NEEDS_REVIEW" if review_reasons else "COMPLETE",
                "standardization_review_required": bool(review_reasons),
                "standardization_review_reasons": review_reasons,
                "standardization_provenance": {"profile": PROFILE,
                    "source_report_id": extract_result.get("report_id"),
                    "source_fact_id": fact_id,
                    "provider_versions": self._versions()}})
        study = _study(context, self.procedure_provider)
        concepts = [item["concept_mappings"][0] for item in standardized]
        components = [mapping for item in standardized for mapping in item["component_mappings"]]
        anatomy = [mapping for item in standardized for mapping in item["anatomy_mappings"]]
        measurements = [measurement for item in standardized for measurement in item["standardized_measurements"]]
        counts = lambda values: {status.lower(): sum(item["mapping_status"] == status for item in values)
                                 for status in ("MATCHED", "NEEDS_REVIEW", "UNMAPPED")}
        review = any(item["standardization_review_required"] for item in standardized)
        review = review or study["procedure_mapping"]["review_required"]
        result = {"profile": PROFILE, "report_id": extract_result.get("report_id"),
            "source_extract_state": extract_result.get("state"),
            "state": "NEEDS_REVIEW" if review else "COMPLETE",
            "standardized_facts": standardized,
            "standardized_study_context": study,
            "summary": {"facts_received": len(facts), "facts_processed": len(standardized),
                "clinical_concepts": {"total": len(concepts), **counts(concepts)},
                "whole_fact_exact_mappings": sum(item["mapping_status"] == "MATCHED" and
                    item["lookup_scope"] == "WHOLE_LABEL" for item in concepts),
                "component_exact_mappings": len(components),
                "facts_with_component_standardization": sum(bool(item["component_mappings"])
                    for item in standardized),
                "facts_needing_review": sum(item["standardization_review_required"] for item in standardized),
                "facts_fully_unmapped": sum(item["concept_mappings"][0]["mapping_status"] == "UNMAPPED" and
                    not item["component_mappings"] and
                    not any(mapping["mapping_status"] == "MATCHED" for mapping in item["anatomy_mappings"])
                    for item in standardized),
                "anatomy": {"total": len(anatomy), **counts(anatomy)},
                "measurements": {"total": len(measurements), "normalized": sum(item["mapping_status"] == "MATCHED" for item in measurements),
                                 "needs_review": sum(item["review_required"] for item in measurements),
                                 "unmapped": sum(item["mapping_status"] == "UNMAPPED" for item in measurements)},
                "study_identity": study["procedure_mapping"]["mapping_status"]},
            "technical_diagnostics": {"provider_versions": self._versions(),
                "provider_unavailable": [provider.system for provider in
                    (self.concept_provider, self.anatomy_provider, self.procedure_provider) if not provider.available],
                "codes": sorted({item["review_reason"] for item in [*concepts, *components, *anatomy, *measurements,
                       study["procedure_mapping"]] if item.get("review_reason")})}}
        return result

    def _versions(self) -> dict[str, str | None]:
        return {provider.system: provider.version if provider.available else None for provider in
                (self.concept_provider, self.anatomy_provider, self.procedure_provider)}
