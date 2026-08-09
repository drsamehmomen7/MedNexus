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
from backend.app.modules.medical_document_intelligence.policies.policy_transformer import (
    PolicyTransformer,
)


def get_test_profile():
    """
    Return any available PolicyProfile member.

    PolicyEngine behavior is mocked in these unit tests, so the exact
    profile is not relevant.
    """

    return next(iter(PolicyProfile))


def fake_transform_value(value, entity, profile):
    """
    Return a predictable placeholder for transformer unit tests.
    """

    return f"[{entity.name}]"


def fake_get_action(entity, profile):
    """
    Ensure all valid entities are transformed during transformer unit tests.

    Policy applicability itself is tested separately in PolicyEngine tests.
    """

    return PolicyAction.REPLACE


def apply_policy_engine_mocks(monkeypatch):
    """
    Mock PolicyEngine decisions and transformations consistently.
    """

    monkeypatch.setattr(
        PolicyEngine,
        "get_action",
        fake_get_action,
    )

    monkeypatch.setattr(
        PolicyEngine,
        "transform_value",
        fake_transform_value,
    )


def build_detected_entity(text, label, value, entity):
    value_start = text.index(value)

    return {
        "entity": entity,
        "value": value,
        "start": value_start,
        "end": value_start + len(value),
        "label": label,
    }


def test_transform_uses_context_entities(monkeypatch):
    apply_policy_engine_mocks(monkeypatch)

    text = (
        "Patient Name: Ahmed Hassan\n"
        "Civil ID: 298010112345\n"
        "MRN: MRN-90021\n"
        "Visit Number: ED-2026-7781\n"
        "Authorized Physician: Dr. Michael Reed\n"
    )

    context_entities = [
        build_detected_entity(
            text,
            "Patient Name",
            "Ahmed Hassan",
            MedicalContextEntity.PATIENT_NAME,
        ),
        build_detected_entity(
            text,
            "Civil ID",
            "298010112345",
            MedicalContextEntity.CIVIL_ID,
        ),
        build_detected_entity(
            text,
            "MRN",
            "MRN-90021",
            MedicalContextEntity.MRN,
        ),
        build_detected_entity(
            text,
            "Visit Number",
            "ED-2026-7781",
            MedicalContextEntity.VISIT_NUMBER,
        ),
        build_detected_entity(
            text,
            "Authorized Physician",
            "Dr. Michael Reed",
            MedicalContextEntity.PHYSICIAN_NAME,
        ),
    ]

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
        context_entities=context_entities,
    )

    assert "Ahmed Hassan" not in result
    assert "298010112345" not in result
    assert "MRN-90021" not in result
    assert "ED-2026-7781" not in result
    assert "Dr. Michael Reed" not in result

    assert "Patient Name: [PATIENT_NAME]" in result
    assert "Civil ID: [CIVIL_ID]" in result
    assert "MRN: [MRN]" in result
    assert "Visit Number: [VISIT_NUMBER]" in result
    assert "Authorized Physician: [PHYSICIAN_NAME]" in result


def test_transform_supports_specimen_and_accession_numbers(monkeypatch):
    apply_policy_engine_mocks(monkeypatch)

    text = (
        "Specimen Number: SP-2026-00192\n"
        "Accession Number: AC-991827\n"
    )

    context_entities = [
        build_detected_entity(
            text,
            "Specimen Number",
            "SP-2026-00192",
            MedicalContextEntity.SPECIMEN_NUMBER,
        ),
        build_detected_entity(
            text,
            "Accession Number",
            "AC-991827",
            MedicalContextEntity.ACCESSION_NUMBER,
        ),
    ]

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
        context_entities=context_entities,
    )

    assert result == (
        "Specimen Number: [SPECIMEN_NUMBER]\n"
        "Accession Number: [ACCESSION_NUMBER]\n"
    )


def test_transform_preserves_non_transformable_context_entities(
    monkeypatch,
):
    apply_policy_engine_mocks(monkeypatch)

    text = (
        "Gross Description: White firm tissue measuring 2.0 cm.\n"
        "Patient Name: Ahmed Hassan\n"
    )

    patient_value = "Ahmed Hassan"
    patient_start = text.index(patient_value)

    context_entities = [
        {
            "entity": MedicalContextEntity.PATIENT_NAME,
            "value": patient_value,
            "start": patient_start,
            "end": patient_start + len(patient_value),
        },
        {
            "entity": "CLINICAL_CONTEXT",
            "value": "White firm tissue",
        },
    ]

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
        context_entities=context_entities,
    )

    assert "White firm tissue measuring 2.0 cm" in result
    assert "Ahmed Hassan" not in result
    assert "Patient Name: [PATIENT_NAME]" in result


def test_transform_supports_entities_without_offsets(monkeypatch):
    apply_policy_engine_mocks(monkeypatch)

    text = (
        "Patient Name: Ahmed Hassan\n"
        "Visit Number: ED-77881\n"
    )

    context_entities = [
        {
            "entity": MedicalContextEntity.PATIENT_NAME,
            "value": "Ahmed Hassan",
        },
        {
            "entity": MedicalContextEntity.VISIT_NUMBER,
            "value": "ED-77881",
        },
    ]

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
        context_entities=context_entities,
    )

    assert result == (
        "Patient Name: [PATIENT_NAME]\n"
        "Visit Number: [VISIT_NUMBER]\n"
    )


def test_transform_accepts_string_entity_names(monkeypatch):
    apply_policy_engine_mocks(monkeypatch)

    text = "Visit Number: ED-2026-1001"

    context_entities = [
        {
            "entity": "VISIT_NUMBER",
            "value": "ED-2026-1001",
        }
    ]

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
        context_entities=context_entities,
    )

    assert result == "Visit Number: [VISIT_NUMBER]"


def test_transform_preserves_backward_compatibility(monkeypatch):
    apply_policy_engine_mocks(monkeypatch)

    text = (
        "Patient: Ahmed Hassan\n"
        "MRN: MRN-10022\n"
        "Civil ID: 298010112345\n"
        "Specimen Number: SP-8821\n"
        "Accession Number: AC-1029\n"
    )

    result = PolicyTransformer.transform(
        text=text,
        profile=get_test_profile(),
    )

    assert "Patient: [PATIENT_NAME]" in result
    assert "MRN: [MRN]" in result
    assert "Civil ID: [CIVIL_ID]" in result
    assert "Specimen Number: [SPECIMEN_NUMBER]" in result
    assert "Accession Number: [ACCESSION_NUMBER]" in result


def test_transform_does_not_modify_empty_text():
    result = PolicyTransformer.transform(
        text="",
        profile=get_test_profile(),
        context_entities=[],
    )

    assert result == ""