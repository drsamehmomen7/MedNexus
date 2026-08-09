from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any, Optional, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.entity_canonicalizer import (
    EntityCanonicalizer,
)


class OpenMedCandidateAdapter:
    """
    Convert OpenMed entity detections into MedNexus candidate entities.

    OpenMed objects must never flow directly into MedNexus policy,
    validation, or output layers.

    This adapter is responsible only for:

    - reading OpenMed entity attributes safely
    - validating source spans
    - preserving OpenMed evidence and metadata
    - converting the result into MedNexusCandidateEntity
    - applying MedNexus taxonomy canonicalization

    It does not:

    - accept or reject a candidate
    - apply privacy policies
    - alter the medical document
    - restore incorrectly replaced text
    """

    @classmethod
    def adapt_result(
        cls,
        engine_result: Any,
        source_text: str,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Adapt all PII entities contained in an OpenMed result.

        Args:
            engine_result:
                OpenMed DeidentificationResult or a compatible object.

            source_text:
                Exact text sent to OpenMed.

        Returns:
            Tuple of canonicalized MedNexus candidates.
        """

        if engine_result is None:
            raise TypeError(
                "engine_result cannot be None."
            )

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        raw_entities = cls._get_value(
            engine_result,
            "pii_entities",
            default=(),
        )

        if raw_entities is None:
            return ()

        if isinstance(
            raw_entities,
            (str, bytes, Mapping),
        ):
            raise TypeError(
                "OpenMed pii_entities must be an iterable "
                "of entity objects."
            )

        if not isinstance(raw_entities, Iterable):
            raise TypeError(
                "OpenMed pii_entities must be iterable."
            )

        adapted = []

        for raw_entity in raw_entities:
            candidate = cls.adapt_entity(
                raw_entity=raw_entity,
                source_text=source_text,
            )

            if candidate is not None:
                adapted.append(candidate)

        return tuple(adapted)

    @classmethod
    def adapt_entity(
        cls,
        *,
        raw_entity: Any,
        source_text: str,
    ) -> Optional[MedNexusCandidateEntity]:
        """
        Convert one OpenMed entity into a canonical MedNexus candidate.

        Invalid entities are ignored conservatively.

        A candidate is ignored when:

        - the object is None
        - offsets are missing or invalid
        - the span falls outside the source text
        - the source span cannot be resolved
        """

        if raw_entity is None:
            return None

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        start = cls._coerce_integer(
            cls._get_first_value(
                raw_entity,
                (
                    "start",
                    "start_index",
                    "begin",
                    "offset_start",
                ),
            )
        )

        end = cls._coerce_integer(
            cls._get_first_value(
                raw_entity,
                (
                    "end",
                    "end_index",
                    "stop",
                    "offset_end",
                ),
            )
        )

        if start is None or end is None:
            evidence = cls._get_value(
                raw_entity,
                "evidence",
                default={},
            )

            if isinstance(evidence, Mapping):
                start = start or cls._coerce_integer(
                    evidence.get("normalized_start")
                )

                end = end or cls._coerce_integer(
                    evidence.get("normalized_end")
                )

        if (
            start is None
            or end is None
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            return None

        source_span = source_text[start:end]

        entity_text = cls._normalize_optional_text(
            cls._get_first_value(
                raw_entity,
                (
                    "text",
                    "value",
                    "entity_text",
                    "matched_text",
                    "original_text",
                ),
            )
        )

        # Source offsets are authoritative inside MedNexus.
        if not entity_text or entity_text != source_span:
            entity_text = source_span

        if not entity_text:
            return None

        raw_label = cls._normalize_optional_text(
            cls._get_first_value(
                raw_entity,
                (
                    "raw_label",
                    "label",
                    "entity_type",
                    "type",
                ),
            )
        )

        canonical_label = cls._normalize_optional_text(
            cls._get_first_value(
                raw_entity,
                (
                    "canonical_label",
                    "normalized_label",
                ),
            )
        )

        confidence = cls._coerce_confidence(
            cls._get_first_value(
                raw_entity,
                (
                    "confidence",
                    "score",
                    "probability",
                ),
            )
        )

        surrogate = cls._normalize_optional_text(
            cls._get_first_value(
                raw_entity,
                (
                    "surrogate",
                    "replacement",
                    "masked_value",
                ),
            )
        )

        metadata = cls._build_metadata(
            raw_entity=raw_entity,
            canonical_label=canonical_label,
        )

        candidate = MedNexusCandidateEntity(
            text=entity_text,
            start=start,
            end=end,
            source=CandidateSource.OPENMED,
            raw_label=raw_label or canonical_label,
            canonical_type=CandidateEntityType.UNKNOWN,
            confidence=confidence,
            normalized_label=None,
            surrogate=surrogate,
            metadata=metadata,
        )

        return EntityCanonicalizer.canonicalize(
            candidate
        )

    @classmethod
    def _build_metadata(
        cls,
        *,
        raw_entity: Any,
        canonical_label: Optional[str],
    ) -> dict[str, Any]:
        """
        Preserve useful OpenMed evidence without leaking its objects.
        """

        metadata: dict[str, Any] = {
            "openmed_canonical_label": canonical_label,
        }

        simple_fields = (
            "model_id",
            "threshold",
            "action",
            "language",
            "reversible_id",
            "hash_value",
        )

        for field_name in simple_fields:
            value = cls._get_value(
                raw_entity,
                field_name,
                default=None,
            )

            if value is not None:
                metadata[field_name] = (
                    cls._make_serializable(value)
                )

        evidence = cls._get_value(
            raw_entity,
            "evidence",
            default=None,
        )

        if evidence is not None:
            metadata["evidence"] = (
                cls._make_serializable(evidence)
            )

        sources = cls._get_value(
            raw_entity,
            "sources",
            default=None,
        )

        if sources is not None:
            metadata["sources"] = (
                cls._make_serializable(sources)
            )

        raw_metadata = cls._get_value(
            raw_entity,
            "metadata",
            default=None,
        )

        if raw_metadata is not None:
            metadata["openmed_metadata"] = (
                cls._make_serializable(
                    raw_metadata
                )
            )

        return {
            key: value
            for key, value in metadata.items()
            if value is not None
        }

    @staticmethod
    def _get_first_value(
        source: Any,
        names: tuple[str, ...],
    ) -> Any:
        """
        Return the first present non-None field.
        """

        for name in names:
            value = OpenMedCandidateAdapter._get_value(
                source,
                name,
                default=None,
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _get_value(
        source: Any,
        name: str,
        *,
        default: Any = None,
    ) -> Any:
        """
        Read a value from either an object or mapping.
        """

        if isinstance(source, Mapping):
            return source.get(
                name,
                default,
            )

        return getattr(
            source,
            name,
            default,
        )

    @staticmethod
    def _coerce_integer(
        value: Any,
    ) -> Optional[int]:
        """
        Convert valid integer-like values safely.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if value.is_integer():
                return int(value)

            return None

        if isinstance(value, str):
            stripped = value.strip()

            if stripped.isdigit():
                return int(stripped)

        return None

    @staticmethod
    def _coerce_confidence(
        value: Any,
    ) -> Optional[float]:
        """
        Convert OpenMed confidence into a MedNexus-safe value.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return None

        if not 0.0 <= confidence <= 1.0:
            return None

        return confidence

    @staticmethod
    def _normalize_optional_text(
        value: Any,
    ) -> Optional[str]:
        """
        Convert supported values into normalized optional text.
        """

        if value is None:
            return None

        if isinstance(value, Enum):
            value = value.value

        normalized = str(value).strip()

        return normalized or None

    @classmethod
    def _make_serializable(
        cls,
        value: Any,
    ) -> Any:
        """
        Convert nested OpenMed values into serialization-safe data.

        MedNexus must not retain engine-specific mutable objects inside
        its internal candidate contract.
        """

        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, Mapping):
            return {
                str(key): cls._make_serializable(
                    nested_value
                )
                for key, nested_value
                in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set, frozenset),
        ):
            return [
                cls._make_serializable(item)
                for item in value
            ]

        if hasattr(value, "model_dump"):
            try:
                return cls._make_serializable(
                    value.model_dump()
                )
            except Exception:
                pass

        if hasattr(value, "__dict__"):
            try:
                return cls._make_serializable(
                    vars(value)
                )
            except Exception:
                pass

        return str(value)