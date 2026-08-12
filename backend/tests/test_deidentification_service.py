from dataclasses import dataclass

import pytest

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.schemas.processing_response import (
    ProcessingResponse,
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
    confidence: float = 0.90


@dataclass
class FakeOpenMedResult:
    pii_entities: list
    deidentified_text: str = "EXTERNAL OUTPUT MUST NOT WIN"


class FakeEngineManager:
    def __init__(self, entities=None):
        self.entities = entities or []
        self.received_text = None

    def deidentify(self, text):
        self.received_text = text
        return FakeOpenMedResult(self.entities)

    @staticmethod
    def get_engine_name():
        return "FakeOpenMed"

    @staticmethod
    def get_engine_version():
        return "test"


def test_deidentification_service_returns_processing_response():

    text = """
Pathology Department

Patient:
Mariam Saleh

Civil ID:
290020203333

MRN:
MRN-998122

Specimen Number:
SP-2026-77881

Accession Number:
PATH-2026-4455

==================================================

Specimen

Left breast lumpectomy.

==================================================

Gross Description

Irregular white firm tissue measuring 4.2 cm.

==================================================

Microscopic Description

Invasive ductal carcinoma.

Grade II.

Margins free.

No lymphovascular invasion.

==================================================

Final Diagnosis

Invasive ductal carcinoma.

ER Positive.

PR Positive.

HER2 Negative.

Ki67 18%.

==================================================

Consultant Pathologist

Dr. Huda Al-Awadhi
"""

    service = DeidentificationService()

    response = service.process(
        text=text,
        policy=PolicyProfile.RESEARCH,
    )

    # --------------------------------------------------
    # Diagnostic Output
    # --------------------------------------------------

    print("\n========== CONTEXT ENTITIES ==========")

    for detected in response.context_entities:
        print(
            {
                "entity": detected.entity,
                "value": detected.value,
                "start": detected.start,
                "end": detected.end,
                "source": detected.source,
                "label": detected.label,
                "normalized_label": detected.normalized_label,
            }
        )

    print("\n========== DETECTION TEXT ==========")
    print(response.metadata["detection_text"])

    print("\n========== FINAL DEIDENTIFIED TEXT ==========")
    print(response.data.deidentified_text)

    # --------------------------------------------------
    # Generic Response
    # --------------------------------------------------

    assert isinstance(response, ProcessingResponse)

    assert response.success is True
    assert response.error is None
    assert response.data is not None

    assert response.engine_name == "OpenMed"
    assert response.engine_version == "1.9.1"
    assert response.module_name == "medical_document_intelligence"

    assert response.processing_time is not None
    assert response.processing_time >= 0

    # --------------------------------------------------
    # Policy
    # --------------------------------------------------

    assert response.metadata["policy"] == "mednexus_research"

    # --------------------------------------------------
    # Clinical Context Protection
    # --------------------------------------------------

    protected_text = response.metadata["detection_text"]

    assert "__CTX_" in protected_text
    assert "white firm tissue" not in protected_text.lower()

    # --------------------------------------------------
    # Final Output
    # --------------------------------------------------

    final_text = response.data.deidentified_text

    # Clinical terms restored
    assert "white" in final_text.lower()
    assert "firm" in final_text.lower()
    assert "[race_ethnicity]" not in final_text.lower()

    # Professional role remains useful, but clinician identity is removed
    # by the selected research policy.
    assert "Consultant Pathologist" in final_text
    assert "Huda Al-Awadhi" not in final_text

    assert "[occupation]" not in final_text
    assert "[first_name]" not in final_text
    assert "[last_name]" not in final_text

    # MedNexus policy output
    assert "[PATIENT_NAME]" in final_text
    assert "[MRN:" in final_text
    assert "[SPECIMEN_NUMBER:" in final_text
    assert "[ACCESSION_NUMBER:" in final_text

    assert response.metadata["privacy_decision_path"] == "unified"
    assert response.metadata["external_engine_role"] == "candidate_detector"
    assert "policy_transformed_text" not in response.metadata
    assert "keep_protected_text" not in response.metadata
    assert "placeholder_protected_text" not in response.metadata

    # --------------------------------------------------
    # Context Detection
    # --------------------------------------------------

    detected_entities = {
        detected.entity
        for detected in response.context_entities
    }

    assert MedicalContextEntity.PATIENT_NAME in detected_entities
    assert MedicalContextEntity.CIVIL_ID in detected_entities
    assert MedicalContextEntity.MRN in detected_entities
    assert MedicalContextEntity.SPECIMEN_NUMBER in detected_entities
    assert MedicalContextEntity.ACCESSION_NUMBER in detected_entities


def test_service_uses_mednexus_output_and_selected_policy_for_openmed_candidate():
    text = "Contact email: patient@example.com"
    value = "patient@example.com"
    start = text.index(value)
    manager = FakeEngineManager(
        [
            FakeOpenMedEntity(
                text=value,
                start=start,
                end=start + len(value),
                raw_label="email",
            )
        ]
    )

    response = DeidentificationService(
        engine_manager=manager
    ).process(text, policy=PolicyProfile.STRICT_PRIVACY)

    assert manager.received_text == response.metadata["detection_text"]
    assert response.data.deidentified_text == (
        "Contact email: [REMOVED]"
    )
    assert "EXTERNAL OUTPUT MUST NOT WIN" not in response.data.deidentified_text
    assert response.metadata["mednexus_output"]["replacements"][0][
        "policy_action"
    ] == "remove"


def test_service_authoritative_path_does_not_call_compatibility_transformers(
    monkeypatch,
):
    from backend.app.modules.medical_document_intelligence.policies.keep_entity_protector import (
        KeepEntityProtector,
    )
    from backend.app.modules.medical_document_intelligence.policies.policy_transformer import (
        PolicyTransformer,
    )

    def fail(*args, **kwargs):
        raise AssertionError("compatibility path executed")

    monkeypatch.setattr(PolicyTransformer, "transform", fail)
    monkeypatch.setattr(KeepEntityProtector, "protect", fail)
    monkeypatch.setattr(KeepEntityProtector, "restore", fail)

    response = DeidentificationService(
        engine_manager=FakeEngineManager()
    ).process("Patient: Ahmed Hassan")

    assert response.success
    assert response.metadata["privacy_decision_path"] == "unified"


def test_explicit_physician_field_remains_role_resolvable_and_policy_governed():
    text = "Reporting Physician: Huda Al-Awadhi\nDiagnosis: Pneumonia"
    value = "Huda Al-Awadhi"
    start = text.index(value)
    entity = FakeOpenMedEntity(
        text=value,
        start=start,
        end=start + len(value),
        raw_label="person_name",
    )

    clinical = DeidentificationService(
        engine_manager=FakeEngineManager([entity])
    ).process(text, PolicyProfile.MEDNEXUS_CLINICAL)
    research = DeidentificationService(
        engine_manager=FakeEngineManager([entity])
    ).process(text, PolicyProfile.MEDNEXUS_RESEARCH)

    clinical_candidate = clinical.metadata["intelligence_result"][
        "accepted"
    ][0]
    research_candidate = research.metadata["intelligence_result"][
        "accepted"
    ][0]

    assert clinical_candidate["canonical_type"] == "physician_name"
    assert research_candidate["canonical_type"] == "physician_name"
    assert "Huda Al-Awadhi" in clinical.data.deidentified_text
    assert "Huda Al-Awadhi" not in research.data.deidentified_text
    assert "Diagnosis: Pneumonia" in clinical.data.deidentified_text
    assert "Diagnosis: Pneumonia" in research.data.deidentified_text


@pytest.mark.parametrize(
    ("field", "title", "name"),
    [
        ("Reporting Physician", "Dr.", "Huda Khaled"),
        ("Admitting Consultant", "Dr.", "Mohamed Al-Sabah"),
        ("Consultant Pathologist", "د.", "خالد العيسى"),
        ("طبيب الأشعة", "د.", "عبدالله الفهد"),
    ],
)
def test_explicit_clinician_names_are_consistently_policy_governed(
    field,
    title,
    name,
):
    text = f"{field}: {title} {name}\nDiagnosis: Pneumonia"
    service = DeidentificationService(
        engine_manager=FakeEngineManager(),
    )

    clinical = service.process(text, PolicyProfile.MEDNEXUS_CLINICAL)
    research = service.process(text, PolicyProfile.MEDNEXUS_RESEARCH)

    assert name in clinical.data.deidentified_text
    assert name not in research.data.deidentified_text
    assert f"{field}: {title}" in research.data.deidentified_text
    assert "Diagnosis: Pneumonia" in clinical.data.deidentified_text
    assert "Diagnosis: Pneumonia" in research.data.deidentified_text
