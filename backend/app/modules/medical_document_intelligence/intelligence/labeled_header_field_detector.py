from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)


@dataclass(frozen=True)
class _Line:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class _FieldSpec:
    semantic_role: str
    entity_type: CandidateEntityType
    value_kind: str


def _label_alternation(labels: Iterable[str]) -> str:
    return "|".join(
        re.escape(label)
        .replace(r"\ ", r"\s+")
        .replace(r"/", r"\s*/\s*")
        for label in sorted(labels, key=len, reverse=True)
    )


class LabeledHeaderFieldDetector:
    """Detect authoritative values from common medical header fields.

    The detector is deliberately bounded to explicit labels and conservative
    value grammars. It does not infer identities from narrative text. Its
    output enters the normal MedNexus canonicalize/resolve/validate/merge
    pipeline and therefore does not create a second privacy-decision path.
    """

    FIELD_SPECS = {
        "patient name": _FieldSpec(
            "patient_name", CandidateEntityType.PATIENT_NAME, "name"
        ),
        "name": _FieldSpec(
            "patient_name", CandidateEntityType.PATIENT_NAME, "name"
        ),
        "patient id": _FieldSpec(
            "patient_id", CandidateEntityType.DOCUMENT_ID, "identifier"
        ),
        "mrn": _FieldSpec("mrn", CandidateEntityType.MRN, "identifier"),
        "medical record number": _FieldSpec(
            "mrn", CandidateEntityType.MRN, "identifier"
        ),
        "visit id": _FieldSpec(
            "visit_id", CandidateEntityType.VISIT_NUMBER, "identifier"
        ),
        "visit number": _FieldSpec(
            "visit_id", CandidateEntityType.VISIT_NUMBER, "identifier"
        ),
        "accession": _FieldSpec(
            "accession_number",
            CandidateEntityType.ACCESSION_NUMBER,
            "identifier",
        ),
        "accession number": _FieldSpec(
            "accession_number",
            CandidateEntityType.ACCESSION_NUMBER,
            "identifier",
        ),
        "report no": _FieldSpec(
            "report_number", CandidateEntityType.DOCUMENT_ID, "identifier"
        ),
        "report number": _FieldSpec(
            "report_number", CandidateEntityType.DOCUMENT_ID, "identifier"
        ),
        "age": _FieldSpec("age", CandidateEntityType.AGE, "age"),
        "gender": _FieldSpec("gender", CandidateEntityType.GENDER, "gender"),
        "sex": _FieldSpec("gender", CandidateEntityType.GENDER, "gender"),
        "age/sex": _FieldSpec("age_sex", CandidateEntityType.AGE, "age_sex"),
        "referred by": _FieldSpec(
            "referring_physician", CandidateEntityType.PHYSICIAN_NAME, "clinician"
        ),
        "referring physician": _FieldSpec(
            "referring_physician", CandidateEntityType.PHYSICIAN_NAME, "clinician"
        ),
        "reporting radiologist": _FieldSpec(
            "reporting_radiologist", CandidateEntityType.PHYSICIAN_NAME, "clinician"
        ),
        "reported by": _FieldSpec(
            "reporting_clinician", CandidateEntityType.PHYSICIAN_NAME, "clinician"
        ),
        "signed by": _FieldSpec(
            "signing_clinician", CandidateEntityType.PHYSICIAN_NAME, "clinician"
        ),
        "registered": _FieldSpec(
            "registered_datetime", CandidateEntityType.GENERAL_DATE, "datetime"
        ),
        "collected": _FieldSpec(
            "collected_datetime", CandidateEntityType.COLLECTION_DATE, "datetime"
        ),
        "validated": _FieldSpec(
            "validated_datetime", CandidateEntityType.GENERAL_DATE, "datetime"
        ),
        "printed": _FieldSpec(
            "printed_datetime", CandidateEntityType.GENERAL_DATE, "datetime"
        ),
        "study date": _FieldSpec(
            "study_datetime", CandidateEntityType.EXAM_DATE, "datetime"
        ),
    }

    _LABEL_ALTERNATION = _label_alternation(FIELD_SPECS)
    LABEL_PATTERN = re.compile(
        rf"(?<![A-Za-z0-9_])(?P<label>{_LABEL_ALTERNATION})(?![A-Za-z0-9_])",
        flags=re.IGNORECASE,
    )
    PLACEHOLDER_PATTERN = re.compile(
        r"\[\s*REDACTED\s*\]|\bREDACTED\b",
        flags=re.IGNORECASE,
    )
    IDENTIFIER_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9._/\-]{2,}", re.IGNORECASE)
    AGE_PATTERN = re.compile(r"(?:0{0,2}[0-9]{1,3})(?:\s*[YyMmDd])?")
    GENDER_PATTERN = re.compile(r"(?:M|F|Male|Female)", re.IGNORECASE)
    AGE_SEX_PATTERN = re.compile(
        r"(?P<age>0{0,2}[0-9]{1,3}(?:\s*[YyMmDd])?)"
        r"\s*/\s*"
        r"(?P<gender>M|F|Male|Female)",
        flags=re.IGNORECASE,
    )
    DATETIME_PATTERN = re.compile(
        r"(?:"
        r"[0-3]?\d/[01]?\d/(?:19|20)\d{2}"
        r"|(?:19|20)\d{2}-[01]\d-[0-3]\d"
        r")"
        r"(?:\s+(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*[AP]M)?)?",
        flags=re.IGNORECASE,
    )
    NAME_PATTERN = re.compile(
        r"[^\W\d_][^\W\d_.'\-]*"
        r"(?:[ .'\-]+[^\W\d_][^\W\d_.'\-]*){0,5}",
        flags=re.UNICODE,
    )
    TITLE_PATTERN = re.compile(
        r"(?:Dr|Doctor|Prof)\.?\s+",
        flags=re.IGNORECASE,
    )

    @classmethod
    def detect(cls, text: str) -> tuple[MedNexusCandidateEntity, ...]:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        if not text:
            return ()

        lines = cls._lines(text)
        candidates: list[MedNexusCandidateEntity] = []
        candidates.extend(cls._detect_inline(lines))
        candidates.extend(cls._detect_adjacent(lines))
        candidates.extend(cls._detect_placeholders(text))
        return cls._deduplicate(candidates)

    @classmethod
    def explicit_fields(
        cls, text: str
    ) -> tuple[MedNexusCandidateEntity, ...]:
        """Return explicit header fields without pre-redacted placeholders."""

        return tuple(
            candidate
            for candidate in cls.detect(text)
            if candidate.metadata.get("authority") == "explicit_labeled_field"
        )

    @staticmethod
    def _lines(text: str) -> list[_Line]:
        lines: list[_Line] = []
        for match in re.finditer(r"[^\r\n]+", text):
            raw = match.group(0)
            stripped = raw.strip()
            if not stripped:
                continue
            leading = len(raw) - len(raw.lstrip())
            lines.append(
                _Line(
                    text=stripped,
                    start=match.start() + leading,
                    end=match.start() + leading + len(stripped),
                )
            )
        return lines

    @classmethod
    def _detect_inline(cls, lines: Iterable[_Line]) -> list[MedNexusCandidateEntity]:
        candidates: list[MedNexusCandidateEntity] = []
        for line in lines:
            matches = list(cls.LABEL_PATTERN.finditer(line.text))
            if not matches or matches[0].start() != 0:
                continue

            accepted_matches = [matches[0]]
            first_spec = cls._spec(matches[0].group("label"))
            if first_spec and first_spec.value_kind in {"age", "age_sex", "gender"}:
                accepted_matches.extend(matches[1:])

            for index, match in enumerate(accepted_matches):
                next_start = (
                    accepted_matches[index + 1].start()
                    if index + 1 < len(accepted_matches)
                    else len(line.text)
                )
                segment = line.text[match.end():next_start]
                separator = re.match(
                    r"(?P<separator>[ \t]*(?:[:#=]|[-–—])?[ \t]*)",
                    segment,
                )
                if separator is None:
                    continue
                separator_text = separator.group("separator")
                spec = cls._spec(match.group("label"))
                if spec is None or not cls._inline_separator_allowed(
                    separator_text, spec
                ):
                    continue
                raw_value = segment[separator.end():]
                value = raw_value.strip()
                if not value:
                    continue
                value_offset = len(raw_value) - len(raw_value.lstrip())
                value_start = line.start + match.end() + separator.end() + value_offset
                candidates.extend(
                    cls._candidates_for_value(
                        value=value,
                        value_start=value_start,
                        label=match.group("label"),
                        spec=spec,
                        layout="inline",
                    )
                )
        return candidates

    @classmethod
    def _detect_adjacent(cls, lines: list[_Line]) -> list[MedNexusCandidateEntity]:
        candidates: list[MedNexusCandidateEntity] = []
        index = 0
        while index < len(lines):
            spec = cls._full_label_spec(lines[index].text)
            if spec is None:
                index += 1
                continue

            labels: list[tuple[_Line, _FieldSpec]] = []
            cursor = index
            while cursor < len(lines):
                current_spec = cls._full_label_spec(lines[cursor].text)
                if current_spec is None:
                    break
                labels.append((lines[cursor], current_spec))
                cursor += 1

            if len(labels) > 1 and cursor + len(labels) <= len(lines):
                values = lines[cursor:cursor + len(labels)]
                if all(cls._full_label_spec(value.text) is None for value in values):
                    for (label_line, field_spec), value_line in zip(labels, values):
                        candidates.extend(
                            cls._candidates_for_value(
                                value=value_line.text,
                                value_start=value_line.start,
                                label=label_line.text,
                                spec=field_spec,
                                layout="label_block",
                            )
                        )
                    index = cursor + len(labels)
                    continue

            if cursor < len(lines) and cls._full_label_spec(lines[cursor].text) is None:
                value_line = lines[cursor]
                candidates.extend(
                    cls._candidates_for_value(
                        value=value_line.text,
                        value_start=value_line.start,
                        label=lines[index].text,
                        spec=spec,
                        layout="adjacent_line",
                    )
                )
            index += 1
        return candidates

    @classmethod
    def _detect_placeholders(cls, text: str) -> list[MedNexusCandidateEntity]:
        return [
            cls._build_candidate(
                text=match.group(0),
                start=match.start(),
                end=match.end(),
                entity_type=CandidateEntityType.UNKNOWN,
                raw_label="pre_redacted_placeholder",
                semantic_role="pre_redacted_placeholder",
                layout="source_placeholder",
                authority="pre_redacted_placeholder",
            )
            for match in cls.PLACEHOLDER_PATTERN.finditer(text)
        ]

    @classmethod
    def _candidates_for_value(
        cls,
        *,
        value: str,
        value_start: int,
        label: str,
        spec: _FieldSpec,
        layout: str,
    ) -> list[MedNexusCandidateEntity]:
        if spec.value_kind == "age_sex":
            match = cls.AGE_SEX_PATTERN.fullmatch(value)
            if match is None:
                return []
            return [
                cls._build_candidate(
                    text=match.group("age"),
                    start=value_start + match.start("age"),
                    end=value_start + match.end("age"),
                    entity_type=CandidateEntityType.AGE,
                    raw_label=label,
                    semantic_role="age",
                    layout=layout,
                ),
                cls._build_candidate(
                    text=match.group("gender"),
                    start=value_start + match.start("gender"),
                    end=value_start + match.end("gender"),
                    entity_type=CandidateEntityType.GENDER,
                    raw_label=label,
                    semantic_role="gender",
                    layout=layout,
                ),
            ]

        candidate_start = value_start
        candidate_value = value
        if spec.value_kind == "clinician":
            title = cls.TITLE_PATTERN.match(value)
            if title is not None:
                candidate_start += title.end()
                candidate_value = value[title.end():]

        pattern = {
            "identifier": cls.IDENTIFIER_PATTERN,
            "age": cls.AGE_PATTERN,
            "gender": cls.GENDER_PATTERN,
            "datetime": cls.DATETIME_PATTERN,
            "name": cls.NAME_PATTERN,
            "clinician": cls.NAME_PATTERN,
        }.get(spec.value_kind)
        if pattern is None or pattern.fullmatch(candidate_value) is None:
            return []

        return [
            cls._build_candidate(
                text=candidate_value,
                start=candidate_start,
                end=candidate_start + len(candidate_value),
                entity_type=spec.entity_type,
                raw_label=label,
                semantic_role=spec.semantic_role,
                layout=layout,
            )
        ]

    @classmethod
    def _build_candidate(
        cls,
        *,
        text: str,
        start: int,
        end: int,
        entity_type: CandidateEntityType,
        raw_label: str,
        semantic_role: str,
        layout: str,
        authority: str = "explicit_labeled_field",
    ) -> MedNexusCandidateEntity:
        return MedNexusCandidateEntity(
            text=text,
            start=start,
            end=end,
            source=CandidateSource.MEDNEXUS_FIELD_RULE,
            raw_label=raw_label,
            canonical_type=entity_type,
            confidence=1.0,
            decision=CandidateDecision.PENDING,
            normalized_label=entity_type.value,
            metadata={
                "detector": "labeled_header_field_detector",
                "authority": authority,
                "semantic_role": semantic_role,
                "field_label": raw_label,
                "layout": layout,
            },
        )

    @classmethod
    def _full_label_spec(cls, value: str) -> _FieldSpec | None:
        return cls.FIELD_SPECS.get(cls._normalize_label(value))

    @classmethod
    def _spec(cls, value: str) -> _FieldSpec | None:
        return cls.FIELD_SPECS.get(cls._normalize_label(value))

    @staticmethod
    def _normalize_label(value: str) -> str:
        normalized = value.strip().rstrip(":").lower()
        normalized = re.sub(r"\s*/\s*", "/", normalized)
        return re.sub(r"\s+", " ", normalized)

    @staticmethod
    def _inline_separator_allowed(separator: str, spec: _FieldSpec) -> bool:
        if any(character in separator for character in ":#=–—"):
            return True
        if separator.strip() == "-":
            return True
        if "\t" in separator or len(separator) >= 2:
            return True
        return spec.value_kind in {"age", "age_sex", "gender"} and bool(separator)

    @staticmethod
    def _deduplicate(
        candidates: Iterable[MedNexusCandidateEntity],
    ) -> tuple[MedNexusCandidateEntity, ...]:
        unique: dict[tuple[int, int, CandidateEntityType], MedNexusCandidateEntity] = {}
        for candidate in candidates:
            unique.setdefault(
                (candidate.start, candidate.end, candidate.canonical_type), candidate
            )
        return tuple(
            sorted(
                unique.values(),
                key=lambda candidate: (
                    candidate.start,
                    candidate.end,
                    candidate.canonical_type.value,
                ),
            )
        )
