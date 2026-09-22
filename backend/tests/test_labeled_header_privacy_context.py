from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
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
from backend.app.modules.medical_document_intelligence.services.deidentification import (
    DeidentificationService,
)


@dataclass
class FakeOpenMedEntity:
    text: str
    start: int
    end: int
    raw_label: str
    confidence: float = 0.95


@dataclass
class FakeOpenMedResult:
    pii_entities: list[FakeOpenMedEntity]
    deidentified_text: str = "EXTERNAL OUTPUT MUST NOT WIN"


class FakeEngineManager:
    def __init__(self, entities=()):
        self.entities = list(entities)

    def deidentify(self, _text):
        return FakeOpenMedResult(self.entities)

    @staticmethod
    def get_engine_name():
        return "FakeOpenMed"

    @staticmethod
    def get_engine_version():
        return "test"


def _process(text: str, entities=()):
    return DeidentificationService(
        engine_manager=FakeEngineManager(entities)
    ).process(text, policy=PolicyProfile.MEDNEXUS_CLINICAL)


def _candidates(response):
    return response.metadata["intelligence_result"]["all_candidates"]


def _candidate_for_role(response, semantic_role: str):
    matches = [
        candidate
        for candidate in _candidates(response)
        if candidate["metadata"].get("semantic_role") == semantic_role
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    (
        "text",
        "semantic_role",
        "entity_type",
        "action",
        "source_value",
        "expected_fragment",
    ),
    [
        (
            "Patient Name:\nAmit Deshpande",
            "patient_name",
            CandidateEntityType.PATIENT_NAME,
            PolicyAction.REPLACE,
            "Amit Deshpande",
            "Patient Name:\n[PATIENT_NAME]",
        ),
        (
            "Patient ID: IN-P-510518",
            "patient_id",
            CandidateEntityType.DOCUMENT_ID,
            PolicyAction.HASH,
            "IN-P-510518",
            "[DOCUMENT_ID:",
        ),
        (
            "Visit ID    IN20260115",
            "visit_id",
            CandidateEntityType.VISIT_NUMBER,
            PolicyAction.HASH,
            "IN20260115",
            "[VISIT_NUMBER:",
        ),
        (
            "Age: 055Y",
            "age",
            CandidateEntityType.AGE,
            PolicyAction.KEEP,
            "055Y",
            "Age: 055Y",
        ),
        (
            "Gender: Female",
            "gender",
            CandidateEntityType.GENDER,
            PolicyAction.KEEP,
            "Female",
            "Gender: Female",
        ),
        (
            "Referring Physician: Dr. Anthony Blake",
            "referring_physician",
            CandidateEntityType.PHYSICIAN_NAME,
            PolicyAction.KEEP,
            "Anthony Blake",
            "Dr. Anthony Blake",
        ),
        (
            "Registered: 22/08/2026 08:18 PM",
            "registered_datetime",
            CandidateEntityType.GENERAL_DATE,
            PolicyAction.KEEP,
            "22/08/2026 08:18 PM",
            "22/08/2026 08:18 PM",
        ),
    ],
)
def test_explicit_fields_control_classification_validation_policy_and_output(
    text,
    semantic_role,
    entity_type,
    action,
    source_value,
    expected_fragment,
):
    response = _process(text)
    candidate = _candidate_for_role(response, semantic_role)

    assert candidate["canonical_type"] == entity_type.value
    assert candidate["decision"] == CandidateDecision.ACCEPT.value
    assert candidate["text"] == source_value
    assert candidate["metadata"]["authority"] == "explicit_labeled_field"
    assert candidate["metadata"]["detector"] == "labeled_header_field_detector"
    assert (
        PolicyEngine.get_action(
            entity_type,
            PolicyProfile.MEDNEXUS_CLINICAL,
            require_mapping=True,
        )
        is action
    )
    assert expected_fragment in response.data.deidentified_text
    if action is not PolicyAction.KEEP:
        assert source_value not in response.data.deidentified_text
    assert response.metadata["protection_complete"] is True


@pytest.mark.parametrize(
    ("text", "age", "gender"),
    [
        ("Age/Sex: 67/F", "67", "F"),
        ("Age / Sex: 51 / Male", "51", "Male"),
        ("Age/Sex\n019Y/M", "019Y", "M"),
    ],
)
def test_combined_age_and_sex_fields_are_separate_clinical_attributes(
    text, age, gender
):
    response = _process(text)
    age_candidate = _candidate_for_role(response, "age")
    gender_candidate = _candidate_for_role(response, "gender")

    assert age_candidate["canonical_type"] == CandidateEntityType.AGE.value
    assert age_candidate["text"] == age
    assert age_candidate["decision"] == CandidateDecision.ACCEPT.value
    assert gender_candidate["canonical_type"] == CandidateEntityType.GENDER.value
    assert gender_candidate["text"] == gender
    assert gender_candidate["decision"] == CandidateDecision.ACCEPT.value
    assert response.data.deidentified_text == text


def test_explicit_age_rejects_conflicting_employee_number_guess():
    text = "Age: 055Y"
    value = "055Y"
    response = _process(
        text,
        [
            FakeOpenMedEntity(
                text=value,
                start=text.index(value),
                end=text.index(value) + len(value),
                raw_label="employee_id",
            )
        ],
    )

    assert _candidate_for_role(response, "age")["canonical_type"] == "age"
    assert all(
        candidate["canonical_type"] != CandidateEntityType.EMPLOYEE_NUMBER.value
        for candidate in _candidates(response)
    )
    assert response.data.deidentified_text == text


def test_explicit_visit_id_outranks_conflicting_mrn_guess():
    text = "Visit ID: IN20260115"
    value = "IN20260115"
    response = _process(
        text,
        [
            FakeOpenMedEntity(
                text=value,
                start=text.index(value),
                end=text.index(value) + len(value),
                raw_label="mrn",
            )
        ],
    )

    candidate = _candidate_for_role(response, "visit_id")
    assert candidate["canonical_type"] == CandidateEntityType.VISIT_NUMBER.value
    assert "[VISIT_NUMBER:" in response.data.deidentified_text
    assert "[MRN:" not in response.data.deidentified_text


def test_generic_address_cannot_cross_explicit_header_field_boundaries():
    text = (
        "Age\n90\nGender\nFemale\nReferred By\nDr. Anthony Blake\n"
        "Patient ID\nUS-P-510296"
    )
    guessed = "90\nGender\nFemale\nReferred By\nDr. Anthony Blake"
    response = _process(
        text,
        [
            FakeOpenMedEntity(
                text=guessed,
                start=text.index(guessed),
                end=text.index(guessed) + len(guessed),
                raw_label="address",
            )
        ],
    )

    assert not any(
        candidate["canonical_type"] == CandidateEntityType.ADDRESS.value
        and candidate["decision"] == CandidateDecision.ACCEPT.value
        for candidate in _candidates(response)
    )
    assert "Age\n90\nGender\nFemale" in response.data.deidentified_text
    assert "Dr. Anthony Blake" in response.data.deidentified_text
    assert "US-P-510296" not in response.data.deidentified_text


def test_source_redaction_placeholder_is_rejected_without_review():
    text = "Patient Name: [REDACTED]"
    response = _process(text)
    candidate = next(
        candidate
        for candidate in _candidates(response)
        if candidate["metadata"].get("authority") == "pre_redacted_placeholder"
    )

    assert candidate["canonical_type"] == CandidateEntityType.UNKNOWN.value
    assert candidate["decision"] == CandidateDecision.REJECT.value
    assert response.data.deidentified_text == text
    assert response.metadata["requires_review"] is False


@pytest.mark.parametrize("term", ["Bankart lesion", "Bony structures"])
def test_unresolved_clinical_person_guess_remains_review_only(term):
    text = f"FINDINGS\n{term} are described in the current study."
    token = term.split()[0]
    response = _process(
        text,
        [
            FakeOpenMedEntity(
                text=token,
                start=text.index(token),
                end=text.index(token) + len(token),
                raw_label="person_name",
            )
        ],
    )
    candidate = next(
        candidate
        for candidate in _candidates(response)
        if candidate["text"] == token
    )

    assert candidate["canonical_type"] == CandidateEntityType.PERSON_NAME.value
    assert candidate["decision"] == CandidateDecision.REVIEW_REQUIRED.value
    assert token in response.data.deidentified_text
    assert response.metadata["requires_review"] is True


def test_realistic_radiology_header_is_resolved_field_by_field():
    text = """RADIOLOGY REPORT
Name
Olivia Bennett
Registered
22/08/2026 08:18 PM
Collected
22/08/2026 08:31 PM
Validated
23/08/2026 02:55 AM
Printed
23/08/2026 03:14 AM
Visit ID
US20260109
Age
90
Gender
Female
Referred By
Dr. Anthony Blake
Patient ID
US-P-510296

FINDINGS
No focal pulmonary opacity.
IMPRESSION
No acute cardiopulmonary abnormality."""
    response = _process(text)
    expected = {
        "patient_name": ("patient_name", "accept", "Olivia Bennett"),
        "registered_datetime": (
            "general_date",
            "accept",
            "22/08/2026 08:18 PM",
        ),
        "collected_datetime": (
            "collection_date",
            "accept",
            "22/08/2026 08:31 PM",
        ),
        "validated_datetime": (
            "general_date",
            "accept",
            "23/08/2026 02:55 AM",
        ),
        "printed_datetime": (
            "general_date",
            "accept",
            "23/08/2026 03:14 AM",
        ),
        "visit_id": ("visit_number", "accept", "US20260109"),
        "age": ("age", "accept", "90"),
        "gender": ("gender", "accept", "Female"),
        "referring_physician": (
            "physician_name",
            "accept",
            "Anthony Blake",
        ),
        "patient_id": ("document_id", "accept", "US-P-510296"),
    }

    for semantic_role, trace in expected.items():
        candidate = _candidate_for_role(response, semantic_role)
        assert (
            candidate["canonical_type"],
            candidate["decision"],
            candidate["text"],
        ) == trace
        assert candidate["metadata"]["authority"] == "explicit_labeled_field"

    protected = response.data.deidentified_text
    assert "Olivia Bennett" not in protected
    assert "[PATIENT_NAME]" in protected
    assert "US20260109" not in protected
    assert "[VISIT_NUMBER:" in protected
    assert "US-P-510296" not in protected
    assert "[DOCUMENT_ID:" in protected
    assert "Age\n90" in protected
    assert "Gender\nFemale" in protected
    assert "Dr. Anthony Blake" in protected
    assert "22/08/2026 08:18 PM" in protected
    assert "22/08/2026 08:31 PM" in protected
    assert "23/08/2026 02:55 AM" in protected
    assert "23/08/2026 03:14 AM" in protected
    assert "No focal pulmonary opacity." in protected
    assert response.metadata["protection_complete"] is True
    assert response.metadata["protection_blockers"] == []
