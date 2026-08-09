import re
from typing import Any, Iterable, Optional

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)


class PolicyTransformer:
    """
    Applies MedNexus privacy policies to a medical report before it is sent
    to the AI engine.

    Processing modes:

    1. Context-aware mode:
       Uses entities detected by ContextRuleEngine.

    2. Legacy mode:
       Uses field-label regular expressions when no detected entities
       are supplied.

    Policy applicability is resolved exclusively by PolicyEngine. This avoids
    maintaining a separate entity whitelist inside PolicyTransformer.
    """

    @classmethod
    def transform(
        cls,
        text: str,
        profile: PolicyProfile,
        context_entities: Optional[Iterable[Any]] = None,
    ) -> str:
        """
        Transform healthcare identifiers according to the selected policy.
        """

        if not text:
            return text

        detected_entities = list(context_entities or [])

        if detected_entities:
            return cls._transform_context_entities(
                text=text,
                profile=profile,
                context_entities=detected_entities,
            )

        return cls._transform_legacy_patterns(
            text=text,
            profile=profile,
        )

    @classmethod
    def _transform_context_entities(
        cls,
        text: str,
        profile: PolicyProfile,
        context_entities: Iterable[Any],
    ) -> str:
        """
        Transform entities returned by ContextRuleEngine.

        Entities with valid character offsets are replaced from right to left
        so earlier replacements do not invalidate later offsets.

        Entities without valid offsets are replaced by their first exact
        occurrence.

        Only entities whose configured policy action is not KEEP are
        transformed.
        """

        positioned_entities = []
        unpositioned_entities = []
        seen_positioned = set()
        seen_unpositioned = set()

        for detected_entity in context_entities:
            normalized = cls._normalize_context_entity(detected_entity)

            if normalized is None:
                continue

            entity, value, start, end = normalized

            if not value:
                continue

            action = PolicyEngine.get_action(
                entity=entity,
                profile=profile,
            )

            if action == PolicyAction.KEEP:
                continue

            if cls._has_valid_position(
                text=text,
                value=value,
                start=start,
                end=end,
            ):
                key = (entity, value, start, end)

                if key in seen_positioned:
                    continue

                seen_positioned.add(key)
                positioned_entities.append(
                    {
                        "entity": entity,
                        "value": value,
                        "start": start,
                        "end": end,
                    }
                )
            else:
                key = (entity, value)

                if key in seen_unpositioned:
                    continue

                seen_unpositioned.add(key)
                unpositioned_entities.append(
                    {
                        "entity": entity,
                        "value": value,
                    }
                )

        output = text

        positioned_entities = cls._remove_overlapping_entities(
            positioned_entities
        )

        positioned_entities.sort(
            key=lambda item: item["start"],
            reverse=True,
        )

        for item in positioned_entities:
            transformed = PolicyEngine.transform_value(
                value=item["value"].strip(),
                entity=item["entity"],
                profile=profile,
            )

            output = (
                output[: item["start"]]
                + transformed
                + output[item["end"] :]
            )

        for item in unpositioned_entities:
            transformed = PolicyEngine.transform_value(
                value=item["value"].strip(),
                entity=item["entity"],
                profile=profile,
            )

            output = output.replace(
                item["value"],
                transformed,
                1,
            )

        return output

    @classmethod
    def _transform_legacy_patterns(
        cls,
        text: str,
        profile: PolicyProfile,
    ) -> str:
        """
        Preserve Regex-based behavior for callers that do not provide
        ContextRuleEngine entities.

        Legacy rules remain a compatibility fallback. PolicyEngine still
        decides whether each matched entity should be transformed.
        """

        rules = cls._build_legacy_rules()
        output = text

        for entity, pattern in rules:
            action = PolicyEngine.get_action(
                entity=entity,
                profile=profile,
            )

            if action == PolicyAction.KEEP:
                continue

            matches = list(
                re.finditer(
                    pattern,
                    output,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
            )

            for match in reversed(matches):
                value = match.group("value")
                start = match.start("value")
                end = match.end("value")

                transformed = PolicyEngine.transform_value(
                    value=value.strip(),
                    entity=entity,
                    profile=profile,
                )

                output = output[:start] + transformed + output[end:]

        return output

    @classmethod
    def _build_legacy_rules(cls):
        """
        Build compatibility Regex rules dynamically.

        Context-aware mode is the primary MedNexus processing path. These
        patterns exist only for callers that have not yet supplied detected
        entities.
        """

        field_patterns = {
            "PATIENT_NAME": (
                r"Patient(?:\s+Name)?\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "PHYSICIAN_NAME": (
                r"(?:Authorized\s+By|Authorized\s+Physician|"
                r"Attending\s+Physician|Referring\s+Physician|"
                r"Physician|Doctor)\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "CIVIL_ID": (
                r"Civil\s+ID\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "MRN": (
                r"MRN\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "VISIT_NUMBER": (
                r"(?:Emergency\s+)?Visit\s+Number\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "LAB_NUMBER": (
                r"Lab(?:oratory)?\s+Number\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "ACCESSION_NUMBER": (
                r"Accession\s+Number\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "SPECIMEN_NUMBER": (
                r"Specimen\s+Number\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "INSURANCE_NUMBER": (
                r"Insurance\s+Number\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "DOCUMENT_ID": (
                r"Document\s+ID\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "PHONE_NUMBER": (
                r"(?:Phone|Telephone|Mobile)\s*(?:Number)?\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "EMAIL": (
                r"Email\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "ADDRESS": (
                r"Address\s*:\s*(?P<value>[^\r\n]+)"
            ),
            "DATE_OF_BIRTH": (
                r"(?:Date\s+of\s+Birth|DOB)\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "ADMISSION_DATE": (
                r"Admission\s+Date\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "DISCHARGE_DATE": (
                r"Discharge\s+Date\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "EXAM_DATE": (
                r"Exam(?:ination)?\s+Date\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
            "COLLECTION_DATE": (
                r"Collection\s+(?:Date|Time)\s*:\s*"
                r"(?P<value>[^\r\n]+)"
            ),
        }

        rules = []

        for entity_name, pattern in field_patterns.items():
            entity = getattr(
                MedicalContextEntity,
                entity_name,
                None,
            )

            if entity is not None:
                rules.append((entity, pattern))

        return rules

    @classmethod
    def _normalize_context_entity(
        cls,
        detected_entity: Any,
    ):
        """
        Normalize supported ContextRuleEngine result representations.
        """

        entity = None
        value = None
        start = None
        end = None

        if isinstance(detected_entity, dict):
            entity = (
                detected_entity.get("entity")
                or detected_entity.get("type")
                or detected_entity.get("entity_type")
            )
            value = (
                detected_entity.get("value")
                or detected_entity.get("text")
            )
            start = detected_entity.get("start")
            end = detected_entity.get("end")

        elif isinstance(detected_entity, (tuple, list)):
            if len(detected_entity) >= 2:
                entity = detected_entity[0]
                value = detected_entity[1]

            if len(detected_entity) >= 4:
                start = detected_entity[2]
                end = detected_entity[3]

        else:
            entity = (
                getattr(detected_entity, "entity", None)
                or getattr(detected_entity, "type", None)
                or getattr(detected_entity, "entity_type", None)
            )
            value = (
                getattr(detected_entity, "value", None)
                or getattr(detected_entity, "text", None)
            )
            start = getattr(detected_entity, "start", None)
            end = getattr(detected_entity, "end", None)

        entity = cls._normalize_entity_type(entity)

        if entity is None or value is None:
            return None

        return entity, str(value), start, end

    @staticmethod
    def _normalize_entity_type(entity: Any):
        """
        Convert strings into MedicalContextEntity members.
        """

        if isinstance(entity, MedicalContextEntity):
            return entity

        if not isinstance(entity, str):
            return None

        normalized_name = entity.strip().upper()

        enum_member = getattr(
            MedicalContextEntity,
            normalized_name,
            None,
        )

        if enum_member is not None:
            return enum_member

        try:
            return MedicalContextEntity(entity.strip().lower())
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _remove_overlapping_entities(positioned_entities):
        """
        Remove overlapping detections deterministically.

        When two detections overlap, the longer detection is preferred.
        This prevents the same text span from being transformed twice.
        """

        ordered = sorted(
            positioned_entities,
            key=lambda item: (
                -(item["end"] - item["start"]),
                item["start"],
            ),
        )

        accepted = []

        for candidate in ordered:
            overlaps = any(
                candidate["start"] < existing["end"]
                and candidate["end"] > existing["start"]
                for existing in accepted
            )

            if not overlaps:
                accepted.append(candidate)

        return accepted

    @staticmethod
    def _has_valid_position(
        text: str,
        value: str,
        start: Any,
        end: Any,
    ) -> bool:
        """
        Verify that supplied offsets point exactly to the detected value.
        """

        if not isinstance(start, int) or not isinstance(end, int):
            return False

        if start < 0 or end <= start or end > len(text):
            return False

        return text[start:end] == value
