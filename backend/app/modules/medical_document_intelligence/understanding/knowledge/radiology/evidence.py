from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from ...models import DetectedSection
from ..models import RecognitionConcept, RecognitionConceptCategory
from .concepts import RADIOLOGY_CONCEPTS
from ...reference_model.runtime import build_active_reference_registry
from ...reference_model.models import ConceptFamily


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    concept_id: str
    concept_family: str
    matched_text: str
    start: int
    end: int
    strength: float
    provenance: tuple[str, ...]
    context: str
    external_mappings: tuple[tuple[str, str], ...] = ()
    relationships: tuple[tuple[str, str], ...] = ()
    attributes: tuple[tuple[str, str], ...] = ()
    composition_equivalent_mappings: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentEvidenceFrame:
    domain_signals: tuple[EvidenceSignal, ...] = ()
    modality_signals: tuple[EvidenceSignal, ...] = ()
    technique_signals: tuple[EvidenceSignal, ...] = ()
    acquisition_signals: tuple[EvidenceSignal, ...] = ()
    anatomy_signals: tuple[EvidenceSignal, ...] = ()
    procedure_signals: tuple[EvidenceSignal, ...] = ()
    contrast_signals: tuple[EvidenceSignal, ...] = ()
    structure_signals: tuple[EvidenceSignal, ...] = ()
    clinical_purpose_signals: tuple[EvidenceSignal, ...] = ()
    observation_signals: tuple[EvidenceSignal, ...] = ()
    laterality_signals: tuple[EvidenceSignal, ...] = ()
    study_extent_signals: tuple[EvidenceSignal, ...] = ()
    view_signals: tuple[EvidenceSignal, ...] = ()
    view_count_signals: tuple[EvidenceSignal, ...] = ()
    professional_role_signals: tuple[EvidenceSignal, ...] = ()
    conflicting_signals: tuple[EvidenceSignal, ...] = ()

    @property
    def all_signals(self) -> tuple[EvidenceSignal, ...]:
        return tuple(
            signal for field_name in self.__dataclass_fields__
            for signal in getattr(self, field_name)
        )


_FAMILY_FIELD = {
    RecognitionConceptCategory.DOCUMENT_IDENTITY: "domain_signals",
    RecognitionConceptCategory.SERVICE_CONTEXT: "domain_signals",
    RecognitionConceptCategory.MODALITY: "modality_signals",
    RecognitionConceptCategory.IMAGING_TECHNIQUE: "technique_signals",
    RecognitionConceptCategory.ACQUISITION: "acquisition_signals",
    RecognitionConceptCategory.ANATOMY: "anatomy_signals",
    RecognitionConceptCategory.PROCEDURE: "procedure_signals",
    RecognitionConceptCategory.CONTRAST: "contrast_signals",
    RecognitionConceptCategory.SECTION: "structure_signals",
    RecognitionConceptCategory.CLINICAL_PURPOSE: "clinical_purpose_signals",
    RecognitionConceptCategory.AUTHOR_ROLE: "professional_role_signals",
}

_REFERENCE_FAMILY_FIELD = {
    ConceptFamily.DOCUMENT_REPORT: "domain_signals",
    ConceptFamily.IMAGING_MODALITY: "modality_signals",
    ConceptFamily.MODALITY_SUBTYPE: "modality_signals",
    ConceptFamily.IMAGING_TECHNIQUE: "technique_signals",
    ConceptFamily.ACQUISITION: "acquisition_signals",
    ConceptFamily.BODY_REGION: "anatomy_signals",
    ConceptFamily.IMAGING_FOCUS: "anatomy_signals",
    ConceptFamily.IMAGING_PROCEDURE: "procedure_signals",
    ConceptFamily.CONTRAST: "contrast_signals",
    ConceptFamily.PHARMACEUTICAL: "contrast_signals",
    ConceptFamily.CLINICAL_PURPOSE: "clinical_purpose_signals",
    ConceptFamily.REASON_FOR_EXAM: "clinical_purpose_signals",
    ConceptFamily.PROFESSIONAL_ROLE: "professional_role_signals",
    ConceptFamily.IMAGING_OBSERVATION: "observation_signals",
    ConceptFamily.CLINICAL_FINDING: "observation_signals",
    ConceptFamily.LATERALITY: "laterality_signals",
}


class RadiologyEvidenceFrameBuilder:
    """Normalize Radiology concepts into exact, traceable source-coordinate signals."""

    _SHORT_RADIOGRAPHY_CODE = re.compile(r"(?<!\w)(CR|DX|XR)(?!\w)", re.IGNORECASE)
    _SHORT_VIEW_CODE = re.compile(r"(?<!\w)(PA|AP)(?!\w)", re.IGNORECASE)
    _STUDY_CONTEXT = re.compile(
        r"\b(?:exam(?:ination)?|modality|procedure|radiograph(?:y|ic)?|x[- ]?ray|study|views?)\b",
        re.IGNORECASE,
    )
    _IDENTIFIER_FIELD_LABEL = re.compile(
        r"(?:patient|visit|accession|document|report)\s+(?:id|number|no)"
        r"|medical\s+record\s+number|mrn|identifier",
        re.IGNORECASE,
    )
    _CURRENT_STUDY_STATEMENT = re.compile(
        r"\b(?:performed|obtained|acquired|completed|exam(?:ination)?|study)\b",
        re.IGNORECASE,
    )
    _VIEW_CONTEXT = re.compile(r"\b(?:view|views|projection|projections)\b", re.IGNORECASE)
    _VIEW_COUNT = re.compile(
        r"(?<!\w)(?P<count>\d{1,2})\s+(?P<qualifier>or\s+more\s+)?views?\b",
        re.IGNORECASE,
    )
    _CONTRAST_NEGATION_BEFORE = re.compile(
        r"\b(?:without|no|non[- ]?|w\s*/?\s*o)\b(?:[\s-]+[^\W_]+){0,4}[\s-]*$",
        re.IGNORECASE,
    )
    _CONTRAST_NEGATION_AFTER = re.compile(
        r"^\s*(?:[^\W_]+\s+){0,4}(?:not\s+(?:administered|given|used)|"
        r"(?:was\s+)?omitted|absent)\b",
        re.IGNORECASE,
    )
    _CONTRAST_POSITIVE_BEFORE = re.compile(
        r"\b(?:with|after|post|administered|given|enhanced|w)\b"
        r"(?:[\s-]+[^\W_]+){0,4}[\s-]*$",
        re.IGNORECASE,
    )
    _CONTRAST_POSITIVE_AFTER = re.compile(
        r"^\s*(?:[^\W_]+\s+){0,4}(?:was\s+)?(?:administered|given|used)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _equivalent_mapping_pairs(concept) -> tuple[tuple[str, str], ...]:
        return tuple(
            (item.source_id, item.external_id)
            for item in concept.external_mappings
            if item.mapping_type.casefold() == "equivalent"
        )

    @classmethod
    def build(cls, text: str, sections: tuple[DetectedSection, ...]) -> DocumentEvidenceFrame:
        reference_model = build_active_reference_registry()
        buckets: dict[str, list[EvidenceSignal]] = {
            name: [] for name in DocumentEvidenceFrame.__dataclass_fields__
        }
        section_by_concept = cls._section_concepts(sections)
        seen: set[tuple[str, int, int]] = set()
        for concept in RADIOLOGY_CONCEPTS:
            if concept.category is RecognitionConceptCategory.SECTION:
                matches = section_by_concept.get(concept.concept_id, ())
            else:
                matches = cls._matches(text, concept)
            for matched, start, end in matches:
                if (
                    concept.category is RecognitionConceptCategory.MODALITY
                    and cls._ambiguous_short_modality(matched)
                    and not cls._governed_short_modality_context(text, start, end)
                ):
                    continue
                key = (concept.concept_id, start, end)
                if key in seen:
                    continue
                seen.add(key)
                resolved = next((item for item in reference_model.resolve(matched)
                                 if item.concept.mednexus_concept_id == concept.concept_id), None)
                canonical = resolved.concept if resolved else None
                signal = EvidenceSignal(
                    concept.concept_id,
                    canonical.concept_family.value if canonical else concept.category.value,
                    matched, start, end, concept.evidence_strength,
                    canonical.provenance if canonical else concept.external_references,
                    cls._context(text, start, end),
                    tuple((item.source_id, item.external_id) for item in canonical.external_mappings) if canonical else (),
                    tuple((item.relationship_type.value, item.target_concept_id)
                          for item in canonical.relationships) if canonical else (),
                    canonical.attributes if canonical else (),
                    cls._equivalent_mapping_pairs(canonical) if canonical else (),
                )
                field_name = _FAMILY_FIELD.get(concept.category)
                if field_name:
                    buckets[field_name].append(signal)
        cls._add_governed_radiography_codes(text, reference_model, buckets, seen)
        # Authoritative imported terms add candidates to the same Evidence Frame. Lexical
        # ambiguity is retained; downstream coherence, structure and relationships decide meaning.
        for span in reference_model.resolve_text(text):
            for canonical in span.concepts[:8]:
                field_name = cls._reference_field(canonical)
                if not field_name or canonical.provenance == ("MNX_RAD_REF_V1",):
                    continue
                if len(span.normalized_term) < 3 and not (
                    field_name == "modality_signals"
                    and cls._governed_short_modality_context(text, span.start, span.end)
                ):
                    continue
                if field_name == "view_signals" and not cls._governed_view_context(text, span.start, span.end):
                    continue
                if field_name == "laterality_signals" \
                        and cls._directional_view_laterality(text, span.start, span.end):
                    continue
                key = (canonical.mednexus_concept_id, span.start, span.end)
                if key in seen:
                    continue
                seen.add(key)
                existing_index = next((index for index, signal in enumerate(buckets[field_name])
                                       if signal.start == span.start and signal.end == span.end
                                       and not (
                                           signal.concept_family == "PROCEDURE_ATTRIBUTE"
                                           and canonical.concept_family
                                           is ConceptFamily.PROCEDURE_ATTRIBUTE
                                           and signal.concept_id
                                           != canonical.mednexus_concept_id
                                       )), None)
                if existing_index is not None:
                    existing = buckets[field_name][existing_index]
                    buckets[field_name][existing_index] = replace(
                        existing,
                        provenance=tuple(dict.fromkeys((*existing.provenance, *canonical.provenance))),
                        external_mappings=tuple(dict.fromkeys((*existing.external_mappings,
                            *((item.source_id, item.external_id) for item in canonical.external_mappings)))),
                        relationships=tuple(dict.fromkeys((*existing.relationships,
                            *((item.relationship_type.value, item.target_concept_id) for item in canonical.relationships)))),
                        attributes=tuple(dict.fromkeys((*existing.attributes, *canonical.attributes))),
                        composition_equivalent_mappings=tuple(dict.fromkeys((
                            *existing.composition_equivalent_mappings,
                            *cls._equivalent_mapping_pairs(canonical),
                        ))),
                    )
                    continue
                buckets[field_name].append(EvidenceSignal(
                    canonical.mednexus_concept_id, canonical.concept_family.value,
                    span.source_text, span.start, span.end, 0.75, canonical.provenance,
                    cls._context(text, span.start, span.end),
                    tuple((item.source_id, item.external_id) for item in canonical.external_mappings),
                    tuple((item.relationship_type.value, item.target_concept_id) for item in canonical.relationships),
                    canonical.attributes,
                    cls._equivalent_mapping_pairs(canonical),
                ))
        cls._add_governed_short_views(text, reference_model, buckets, seen)
        cls._add_governed_view_counts(text, buckets, seen)
        cls._add_governed_study_title_structure(text, sections, buckets, seen)
        cls._qualify_contrast_polarity(text, buckets)
        return DocumentEvidenceFrame(**{key: tuple(value) for key, value in buckets.items()})

    @classmethod
    def _qualify_contrast_polarity(cls, text: str, buckets) -> None:
        """Attach bounded polarity to governed contrast evidence in its clause."""

        qualified = []
        for signal in buckets["contrast_signals"]:
            polarity = cls._contrast_polarity(text, signal)
            attributes = tuple(
                item for item in signal.attributes if item[0] != "contrast_polarity"
            )
            if polarity is not None:
                attributes = (*attributes, ("contrast_polarity", polarity))
            qualified.append(replace(signal, attributes=attributes))
        buckets["contrast_signals"] = qualified

    @classmethod
    def _contrast_polarity(cls, text: str, signal: EvidenceSignal) -> str | None:
        clause = cls._contrast_clause(text, signal.start, signal.end)
        relative_start = signal.start - clause[0]
        relative_end = signal.end - clause[0]
        through_signal = clause[1][:relative_end]
        tokens = {item.casefold() for item in re.findall(r"[^\W_]+", through_signal)}
        if (
            "both" in tokens
            and tokens & {"with", "after", "post"}
            and tokens & {"without", "no"}
        ):
            return "PRE_AND_POST"
        if signal.concept_id == "RAD_CONTRAST_PRE_POST":
            return "PRE_AND_POST"
        if signal.concept_id == "RAD_CONTRAST_WITHOUT":
            return "WITHOUT"
        if signal.concept_id == "RAD_CONTRAST_WITH":
            return "WITH"

        before = clause[1][:relative_start]
        after = clause[1][relative_end:]
        if (
            cls._CONTRAST_NEGATION_BEFORE.search(before)
            or cls._CONTRAST_NEGATION_AFTER.search(after)
        ):
            return "WITHOUT"
        if (
            cls._CONTRAST_POSITIVE_BEFORE.search(before)
            or cls._CONTRAST_POSITIVE_AFTER.search(after)
        ):
            return "WITH"
        return None

    @staticmethod
    def _contrast_clause(text: str, start: int, end: int) -> tuple[int, str]:
        left = max(text.rfind(mark, 0, start) for mark in ("\n", ".", ";", "?", "!")) + 1
        right_candidates = [
            position
            for mark in ("\n", ".", ";", "?", "!")
            if (position := text.find(mark, end)) >= 0
        ]
        right = min(right_candidates) if right_candidates else len(text)
        return left, text[left:right]

    @classmethod
    def _add_governed_study_title_structure(
        cls, text, sections, buckets, seen
    ) -> None:
        excluded_sections = {
            "clinical_information", "clinical_history", "follow_up",
            "comparison", "findings", "results", "impression", "recommendation",
        }
        first = cls._first_nonempty_line(text)
        first_start = first[1] if first is not None else None
        for matched_text, start, end in cls._study_identity_candidates(text):
            section = next(
                (item for item in sections if item.start <= start < item.end), None
            )
            if section is not None and section.canonical_name in excluded_sections:
                continue
            modality_signals = tuple(
                item for item in buckets["modality_signals"]
                if start <= item.start and item.end <= end
            )
            has_modality = bool(modality_signals)
            has_anatomy = any(
                start <= item.start and item.end <= end
                for item in buckets["anatomy_signals"]
            )
            strong_label = (
                cls._title_like(matched_text)
                or cls._predominantly_uppercase_label(matched_text)
                or cls._CURRENT_STUDY_STATEMENT.search(matched_text) is not None
            )
            if has_modality and has_anatomy and start == first_start and not strong_label:
                modality_start = min(item.start for item in modality_signals)
                prefix = text[start:modality_start].strip()
                nominal_study = text[modality_start:end]
                if prefix:
                    if re.search(r"\bof\b", nominal_study, re.IGNORECASE) is None:
                        continue
                    start = modality_start
                    matched_text = nominal_study
            key = ("RAD_STRUCTURE_STUDY_TITLE", start, end)
            if not (has_modality and has_anatomy) or key in seen:
                continue
            seen.add(key)
            buckets["structure_signals"].append(EvidenceSignal(
                "RAD_STRUCTURE_STUDY_TITLE",
                "RADIOLOGY_STRUCTURE",
                matched_text,
                start,
                end,
                2.0,
                ("MEDNEXUS_STRUCTURAL_REASONING",),
                matched_text,
                attributes=(("structure_type", "STUDY_TITLE"),),
            ))
            return

    @classmethod
    def _study_identity_candidates(cls, text: str):
        first = cls._first_nonempty_line(text)
        first_start = first[1] if first is not None else None
        offset = 0
        for line in text.splitlines(keepends=True):
            content = line.rstrip("\r\n")
            stripped = content.strip()
            if not stripped:
                offset += len(line)
                continue
            leading = len(content) - len(content.lstrip())
            start = offset + leading
            candidate = stripped
            sentence = re.match(r".*?[.!?](?=\s|$)", candidate)
            if sentence is not None and len(candidate.split()) > 14:
                candidate = sentence.group(0).strip()
            end = start + len(candidate)
            is_first = start == first_start
            if (
                (is_first and len(candidate.split()) <= 14)
                or cls._title_like(candidate)
                or cls._CURRENT_STUDY_STATEMENT.search(candidate)
                or cls._predominantly_uppercase_label(candidate)
            ):
                yield candidate, start, end
            offset += len(line)

    @classmethod
    def _add_governed_radiography_codes(cls, text, registry, buckets, seen) -> None:
        canonical = registry.concept("RAD_MODALITY_XRAY")
        by_code = {
            code: next((concept for concept in registry.concepts
                        if concept.concept_family is ConceptFamily.IMAGING_MODALITY
                        and any(mapping.external_id.casefold() == code.casefold()
                                for mapping in concept.external_mappings)), None)
            for code in ("CR", "DX")
        }
        for match in cls._SHORT_RADIOGRAPHY_CODE.finditer(text):
            line = cls._context(text, match.start(), match.end())
            if not (cls._title_like(line) or cls._STUDY_CONTEXT.search(line)):
                continue
            source = by_code.get(match.group(0).upper())
            provenance = tuple(dict.fromkeys((*canonical.provenance, *(source.provenance if source else ()))))
            mappings = tuple(dict.fromkeys(
                tuple((item.source_id, item.external_id) for item in canonical.external_mappings)
                + (tuple((item.source_id, item.external_id) for item in source.external_mappings)
                   if source else ())
            ))
            equivalent_mappings = tuple(dict.fromkeys(
                cls._equivalent_mapping_pairs(canonical)
                + (cls._equivalent_mapping_pairs(source) if source else ())
            ))
            key = (canonical.mednexus_concept_id, match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            buckets["modality_signals"].append(EvidenceSignal(
                canonical.mednexus_concept_id, canonical.concept_family.value,
                match.group(0), match.start(), match.end(), 2.0, provenance, line, mappings,
                tuple((item.relationship_type.value, item.target_concept_id)
                      for item in canonical.relationships),
                canonical.attributes,
                equivalent_mappings,
            ))

    @classmethod
    def _add_governed_short_views(cls, text, registry, buckets, seen) -> None:
        for match in cls._SHORT_VIEW_CODE.finditer(text):
            if not cls._governed_view_context(text, match.start(), match.end()):
                continue
            canonical = next((item.concept for item in registry.resolve(match.group(0))
                              if cls._reference_field(item.concept) == "view_signals"), None)
            if canonical is None:
                continue
            key = (canonical.mednexus_concept_id, match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            buckets["view_signals"].append(EvidenceSignal(
                canonical.mednexus_concept_id, canonical.concept_family.value,
                match.group(0), match.start(), match.end(), 0.75, canonical.provenance,
                cls._context(text, match.start(), match.end()),
                tuple((item.source_id, item.external_id) for item in canonical.external_mappings),
                tuple((item.relationship_type.value, item.target_concept_id)
                      for item in canonical.relationships),
                canonical.attributes,
                cls._equivalent_mapping_pairs(canonical),
            ))

    @classmethod
    def _add_governed_view_counts(cls, text, buckets, seen) -> None:
        for match in cls._VIEW_COUNT.finditer(text):
            count = int(match.group("count"))
            if count < 1 or count > 12:
                continue
            line = cls._context(text, match.start(), match.end())
            if not (cls._title_like(line) or cls._STUDY_CONTEXT.search(line)):
                continue
            key = ("RAD_XRAY_VIEW_COUNT", match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            qualifier = "OR_MORE" if match.group("qualifier") else "EXACT"
            buckets["view_count_signals"].append(EvidenceSignal(
                "RAD_XRAY_VIEW_COUNT", "VIEW_COUNT", match.group(0),
                match.start(), match.end(), 0.75, ("MNX_RAD_REF_V1",), line,
                attributes=(("count", str(count)), ("qualifier", qualifier)),
            ))

    @staticmethod
    def _reference_field(concept) -> str | None:
        attributes = dict(concept.attributes)
        if concept.concept_family is ConceptFamily.PROCEDURE_ATTRIBUTE:
            if attributes.get("part_type") in {
                "RAD_MODALITY_MODALITY_TYPE",
                "RAD_MODALITY_MODALITY_SUBTYPE",
            }:
                return "modality_signals"
            if attributes.get("part_type") in {
                "RAD_GUIDANCE_FOR_OBJECT",
                "RAD_PHARMACEUTICAL_SUBSTANCE_GIVEN",
            } and "contrast" in concept.canonical_name.casefold():
                return "contrast_signals"
            if attributes.get("part_type") == "RAD_VIEW_VIEW_TYPE":
                return "view_signals"
            if attributes.get("part_type") == "RAD_ANATOMIC_LOCATION_LATERALITY":
                return "laterality_signals"
            if attributes.get("part_type") == "RAD_VIEW_AGGREGATION" \
                    and concept.canonical_name.casefold() in {"complete", "limited"}:
                return "study_extent_signals"
            if attributes.get("part_type") == "RAD_VIEW_AGGREGATION":
                return "view_signals"
        if concept.concept_family is ConceptFamily.BODY_REGION \
                and attributes.get("cid") == "2":
            return "laterality_signals"
        return _REFERENCE_FAMILY_FIELD.get(concept.concept_family)

    @classmethod
    def _governed_short_modality_context(cls, text: str, start: int, end: int) -> bool:
        line = cls._context(text, start, end)
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        if line_end < 0:
            line_end = len(text)

        prefix = text[line_start:start]
        previous_lines = [
            value.strip()
            for value in text[:line_start].splitlines()
            if value.strip()
        ]
        previous_line = previous_lines[-1] if previous_lines else ""
        if (
            cls._IDENTIFIER_FIELD_LABEL.search(prefix)
            or cls._IDENTIFIER_FIELD_LABEL.fullmatch(previous_line.rstrip(":"))
        ):
            return False

        before = text[start - 1] if start > line_start else ""
        after = text[end] if end < line_end else ""
        identifier_separator = {"-", "_", "/"}
        if (
            (before in identifier_separator or after in identifier_separator)
            and any(character.isdigit() for character in line)
        ):
            return False

        if cls._STUDY_CONTEXT.search(line):
            return True

        relative_start = start - line_start
        relative_end = end - line_start
        remainder = f"{line[:relative_start]} {line[relative_end:]}"
        companion_words = re.findall(r"[^\W\d_]{3,}", remainder, re.UNICODE)
        return bool(companion_words)

    @staticmethod
    def _ambiguous_short_modality(value: str) -> bool:
        normalized = "".join(character for character in value if character.isalnum())
        return len(normalized) <= 2

    @classmethod
    def _governed_view_context(cls, text: str, start: int, end: int) -> bool:
        line = cls._context(text, start, end)
        return bool(cls._VIEW_CONTEXT.search(line) or cls._STUDY_CONTEXT.search(line))

    @staticmethod
    def _directional_view_laterality(text: str, start: int, end: int) -> bool:
        following = text[end:end + 20]
        return bool(re.match(r"\s+(?:lateral|oblique)\b", following, re.IGNORECASE))

    @staticmethod
    def _title_like(line: str) -> bool:
        letters = [item for item in line if item.isalpha()]
        return bool(letters) and len(line.split()) <= 14 and line == line.upper()

    @staticmethod
    def _predominantly_uppercase_label(line: str) -> bool:
        letters = [item for item in line if item.isalpha()]
        if not letters or len(line.split()) > 14:
            return False
        uppercase = sum(item.isupper() for item in letters)
        return uppercase / len(letters) >= 0.75

    @staticmethod
    def _first_nonempty_line(text: str) -> tuple[str, int, int] | None:
        offset = 0
        for line in text.splitlines(keepends=True):
            content = line.rstrip("\r\n")
            stripped = content.strip()
            if stripped:
                leading = len(content) - len(content.lstrip())
                start = offset + leading
                return stripped, start, start + len(stripped)
            offset += len(line)
        return None

    @staticmethod
    def _matches(text: str, concept: RecognitionConcept):
        matches = []
        for alias in sorted(concept.aliases, key=len, reverse=True):
            for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE):
                matches.append((match.group(0), match.start(), match.end()))
        return matches

    @staticmethod
    def _section_concepts(sections: tuple[DetectedSection, ...]):
        from .sections import RADIOLOGY_SECTION_ALIASES, RADIOLOGY_SECTION_CONCEPTS
        by_canonical = {
            canonical: next((concept.concept_id for concept in RADIOLOGY_SECTION_CONCEPTS
                             if any(alias in concept.aliases for alias in aliases)), None)
            for canonical, aliases in RADIOLOGY_SECTION_ALIASES.items()
        }
        # The shared UNDERSTAND contract defines a Results region as an
        # observation narrative.  Adapt the already-detected canonical region;
        # do not add another heading vocabulary or text-matching path here.
        semantic_equivalents = {
            "results": "findings",
        }
        result: dict[str, list[tuple[str, int, int]]] = {}
        for section in sections:
            canonical = semantic_equivalents.get(
                section.canonical_name, section.canonical_name
            )
            concept_id = by_canonical.get(canonical)
            if concept_id:
                result.setdefault(concept_id, []).append(
                    (section.original_heading, section.start, section.start + len(section.original_heading))
                )
        return result

    @staticmethod
    def _context(text: str, start: int, end: int) -> str:
        left = max(0, text.rfind("\n", 0, start) + 1)
        right = text.find("\n", end)
        return text[left:len(text) if right < 0 else right].strip()
