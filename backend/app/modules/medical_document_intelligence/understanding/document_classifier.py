from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    ClassificationEvidence,
    ConfidenceBand,
    DetectedSection,
    DocumentDomain,
    DocumentSubtype,
    DocumentType,
)
from .profiles import PROFILES, SECTION_ALIASES, SUBTYPE_SIGNALS, DocumentProfile, WeightedSignal
from .section_detector import SectionDetector


@dataclass(frozen=True, slots=True)
class ClassificationOutcome:
    domain: DocumentDomain
    document_type: DocumentType
    document_subtype: DocumentSubtype
    confidence: float
    confidence_band: ConfidenceBand
    evidence: tuple[ClassificationEvidence, ...]


class DocumentClassifier:
    """Explainable deterministic classification with conservative ambiguity handling."""

    MINIMUM_ACCEPTED_SCORE = 5.0
    MINIMUM_MARGIN = 2.0
    MINIMUM_MARGIN_RATIO = 1.25

    @classmethod
    def classify(
        cls,
        text: str,
        sections: tuple[DetectedSection, ...] | None = None,
    ) -> ClassificationOutcome:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        detected_sections = SectionDetector.detect(text) if sections is None else sections
        scored = [
            cls._score_profile(text, profile, detected_sections)
            for profile in PROFILES
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_profile, best_evidence = scored[0]
        second_score = scored[1][0]
        all_evidence = tuple(
            item for score, _, entries in scored if score > 0 for item in entries
        )
        if best_score <= 0:
            return cls._unknown(0.0, ConfidenceBand.UNKNOWN, ())

        margin = best_score - second_score
        ratio = best_score / second_score if second_score else float("inf")
        diversity = len({entry.category for entry in best_evidence})
        confidence = cls._confidence(best_score, margin, diversity)
        if (
            best_score < cls.MINIMUM_ACCEPTED_SCORE
            or margin < cls.MINIMUM_MARGIN
            or ratio < cls.MINIMUM_MARGIN_RATIO
        ):
            return cls._unknown(min(confidence, 0.49), ConfidenceBand.LOW, all_evidence)

        band = ConfidenceBand.HIGH if confidence >= 0.80 else ConfidenceBand.MEDIUM if confidence >= 0.58 else ConfidenceBand.LOW
        if band is ConfidenceBand.LOW:
            return cls._unknown(confidence, band, all_evidence)

        subtype = (
            cls._detect_subtype(text, detected_sections)
            if best_profile.domain is DocumentDomain.RADIOLOGY
            else DocumentSubtype.UNKNOWN
        )
        return ClassificationOutcome(
            best_profile.domain,
            best_profile.document_type,
            subtype,
            confidence,
            band,
            all_evidence,
        )

    @classmethod
    def _score_profile(
        cls,
        text: str,
        profile: DocumentProfile,
        sections: tuple[DetectedSection, ...],
    ):
        evidence = []
        matched_section_concepts: set[str] = set()
        for signal in profile.signals:
            section_concept = (
                cls._section_concept(signal.phrase)
                if signal.category == "section"
                else None
            )
            if section_concept in matched_section_concepts:
                continue
            reference = cls._find_signal(text, signal, sections)
            if reference is not None:
                evidence.append(ClassificationEvidence(
                    profile.document_type, signal.phrase, signal.category, signal.weight, reference
                ))
                if section_concept is not None:
                    matched_section_concepts.add(section_concept)
        return sum(item.weight for item in evidence), profile, tuple(evidence)

    @staticmethod
    def _section_concept(phrase: str) -> str | None:
        normalized = SectionDetector.normalize_heading(phrase)
        for canonical, aliases in SECTION_ALIASES.items():
            if normalized in {
                SectionDetector.normalize_heading(alias) for alias in aliases
            }:
                return canonical
        return None

    @staticmethod
    def _find_signal(
        text: str,
        signal: WeightedSignal,
        sections: tuple[DetectedSection, ...],
    ) -> str | None:
        if signal.category == "section":
            signal_name = SectionDetector.normalize_heading(signal.phrase)
            for section in sections:
                aliases = SECTION_ALIASES.get(section.canonical_name, ())
                if signal_name in {
                    SectionDetector.normalize_heading(alias) for alias in aliases
                }:
                    return section.original_heading
            return None
        match = re.search(rf"(?<!\w){re.escape(signal.phrase)}(?!\w)", text, re.IGNORECASE)
        return match.group(0) if match else None

    @staticmethod
    def _confidence(score: float, margin: float, diversity: int) -> float:
        value = 0.45 * min(score / 12.0, 1.0)
        value += 0.25 * min(diversity / 3.0, 1.0)
        value += 0.30 * min(max(margin, 0.0) / 6.0, 1.0)
        return round(value, 3)

    @staticmethod
    def _detect_subtype(
        text: str,
        sections: tuple[DetectedSection, ...],
    ) -> DocumentSubtype:
        header_lines = [line for line in text.splitlines() if line.strip()]
        header_text = header_lines[:1]
        technique_text = "\n".join(
            text[section.start:section.end]
            for section in sections
            if section.canonical_name == "technique"
        )
        modality_context = f"{' '.join(header_text)}\n{technique_text}"
        matched = [
            subtype for subtype, phrases in SUBTYPE_SIGNALS.items()
            if any(
                re.search(
                    rf"(?<!\w){re.escape(phrase)}(?!\w)",
                    modality_context,
                    re.IGNORECASE,
                )
                for phrase in phrases
            )
        ]
        return matched[0] if len(matched) == 1 else DocumentSubtype.UNKNOWN

    @staticmethod
    def _unknown(confidence, band, evidence) -> ClassificationOutcome:
        return ClassificationOutcome(
            DocumentDomain.UNKNOWN, DocumentType.UNKNOWN, DocumentSubtype.UNKNOWN,
            round(confidence, 3), band, evidence,
        )
