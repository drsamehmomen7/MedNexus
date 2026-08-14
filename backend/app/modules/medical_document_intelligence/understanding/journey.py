from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import PolicyProfile
from backend.app.modules.medical_document_intelligence.services.deidentification import DeidentificationService

from .context_models import MedNexusDocumentContext


@dataclass(frozen=True, slots=True)
class JourneyRecord:
    document: DocumentContent
    context: MedNexusDocumentContext


class JourneyStore:
    """Process-local bounded POC handoff; deliberately not durable workflow storage."""

    def __init__(self, capacity: int = 32):
        self._capacity = capacity
        self._records: OrderedDict[str, JourneyRecord] = OrderedDict()
        self._lock = RLock()

    def retain(self, document: DocumentContent, context: MedNexusDocumentContext) -> str:
        journey_id = context.document.document_id
        with self._lock:
            self._records[journey_id] = JourneyRecord(document, context)
            self._records.move_to_end(journey_id)
            while len(self._records) > self._capacity:
                self._records.popitem(last=False)
        return journey_id

    def get(self, journey_id: str) -> JourneyRecord:
        with self._lock:
            try:
                record = self._records[journey_id]
            except KeyError as exc:
                raise LookupError("Journey session was not found or has expired.") from exc
            self._records.move_to_end(journey_id)
            return record

    def protect(self, journey_id: str, policy: PolicyProfile, service: DeidentificationService):
        return service.process(self.get(journey_id).document.text, policy=policy)


journey_store = JourneyStore()
