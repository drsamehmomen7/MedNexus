from dataclasses import dataclass
from typing import Optional

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)


@dataclass(frozen=True)
class DetectedEntity:
    """
    Standard MedNexus representation of an entity detected
    inside a medical document.

    Every detection engine must return this object, regardless
    of whether the entity was detected using:

    - Structured medical fields
    - Canonical label mapping
    - Deterministic patterns
    - AI / medical NER
    """

    entity: MedicalContextEntity
    value: str
    start: int
    end: int

    source: str
    confidence: float = 1.0

    label: Optional[str] = None
    normalized_label: Optional[str] = None

    def __post_init__(self):
        """
        Validate entity integrity immediately after creation.
        """

        if not isinstance(self.entity, MedicalContextEntity):
            raise TypeError(
                "entity must be an instance of MedicalContextEntity."
            )

        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(
                "value must be a non-empty string."
            )

        if not isinstance(self.start, int) or not isinstance(self.end, int):
            raise TypeError(
                "start and end must be integers."
            )

        if self.start < 0:
            raise ValueError(
                "start cannot be negative."
            )

        if self.end <= self.start:
            raise ValueError(
                "end must be greater than start."
            )

        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError(
                "source must be a non-empty string."
            )

        if not isinstance(self.confidence, (int, float)):
            raise TypeError(
                "confidence must be a number."
            )

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                "confidence must be between 0.0 and 1.0."
            )

    @property
    def length(self) -> int:
        """
        Return the number of characters occupied by the entity.
        """

        return self.end - self.start

    def matches_source_text(self, text: str) -> bool:
        """
        Verify that the entity offsets point to its exact value
        inside the original document.
        """

        if not isinstance(text, str):
            return False

        if self.end > len(text):
            return False

        return text[self.start:self.end] == self.value