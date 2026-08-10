import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
)
from backend.app.modules.medical_document_intelligence.intelligence.deterministic_identifier_detector import (
    DeterministicIdentifierDetector,
)
from backend.app.modules.medical_document_intelligence.intelligence.intelligence_orchestrator import (
    MedNexusIntelligenceOrchestrator,
)
from backend.app.modules.medical_document_intelligence.intelligence.output_builder import (
    MedNexusOutputBuilder,
)


def test_detector_rejects_non_string_input():
    with pytest.raises(TypeError):
        DeterministicIdentifierDetector.detect(None)


def test_detector_returns_empty_tuple_for_empty_text():
    assert DeterministicIdentifierDetector.detect("") == ()


def test_detects_confirmed_kuwait_phone_leak_from_phone_field():
    text = "Phone: +965 52988745"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.text == "+965 52988745"
    assert candidate.start == text.index("+965 52988745")
    assert candidate.end == candidate.start + len(candidate.text)
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.canonical_type == CandidateEntityType.PHONE_NUMBER
    assert candidate.decision == CandidateDecision.PENDING
    assert candidate.matches_source_text(text)


def test_detects_inline_kuwait_phone_without_phone_label():
    text = "For urgent contact use +965 52988745 after discharge."

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].text == "+965 52988745"
    assert candidates[0].source == CandidateSource.MEDNEXUS_INLINE_RULE
    assert candidates[0].canonical_type == CandidateEntityType.PHONE_NUMBER


def test_phone_field_detection_beats_duplicate_inline_detection():
    text = "Phone: +965 52988745"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE


def test_detects_local_phone_when_strong_field_label_exists():
    text = "Mobile No: 52988745"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].text == "52988745"
    assert candidates[0].canonical_type == CandidateEntityType.PHONE_NUMBER
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE


def test_does_not_treat_unlabelled_local_eight_digit_number_as_phone():
    text = "Measurement reference 52988745 was imported from the device."

    candidates = DeterministicIdentifierDetector.detect(text)

    assert candidates == ()


def test_detects_email_inline():
    text = "Contact patient at ahmed.patient@example.org for follow-up."

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].text == "ahmed.patient@example.org"
    assert candidates[0].canonical_type == CandidateEntityType.EMAIL
    assert candidates[0].source == CandidateSource.MEDNEXUS_INLINE_RULE


def test_email_field_detection_beats_duplicate_inline_detection():
    text = "Email: ahmed.patient@example.org"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidates[0].canonical_type == CandidateEntityType.EMAIL


def test_detects_civil_id_from_explicit_field():
    text = "Civil ID: 290020203333"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].text == "290020203333"
    assert candidates[0].canonical_type == CandidateEntityType.CIVIL_ID
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE


def test_detects_structured_medical_identifier_fields():
    text = "\n".join(
        [
            "MRN: MRN-998122",
            "Visit Number: VIS-2026-12345",
            "Accession Number: PATH-2026-4455",
            "Specimen Number: SP-2026-77881",
            "Lab Number: LAB-882211",
            "Document ID: DOC-2026-9001",
            "Insurance Number: INS-771199",
            "Employee Number: EMP-440022",
            "Student Number: STU-551133",
        ]
    )

    candidates = DeterministicIdentifierDetector.detect(text)

    detected_types = {
        candidate.canonical_type
        for candidate in candidates
    }

    assert CandidateEntityType.MRN in detected_types
    assert CandidateEntityType.VISIT_NUMBER in detected_types
    assert CandidateEntityType.ACCESSION_NUMBER in detected_types
    assert CandidateEntityType.SPECIMEN_NUMBER in detected_types
    assert CandidateEntityType.LAB_NUMBER in detected_types
    assert CandidateEntityType.DOCUMENT_ID in detected_types
    assert CandidateEntityType.INSURANCE_NUMBER in detected_types
    assert CandidateEntityType.EMPLOYEE_NUMBER in detected_types
    assert CandidateEntityType.STUDENT_NUMBER in detected_types


def test_detects_arabic_phone_field():
    text = "رقم الهاتف: +965 52988745"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].canonical_type == CandidateEntityType.PHONE_NUMBER
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE


def test_phone_candidate_is_accepted_by_existing_intelligence_core():
    text = "Phone: +965 52988745"

    deterministic_candidates = (
        DeterministicIdentifierDetector.detect(text)
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=text,
            candidates=deterministic_candidates,
        )
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    candidate = intelligence_result.accepted[0]

    assert candidate.canonical_type == CandidateEntityType.PHONE_NUMBER
    assert candidate.decision == CandidateDecision.ACCEPT


def test_confirmed_phone_leak_is_replaced_by_mednexus_output_builder():
    text = "Phone: +965 52988745"

    deterministic_candidates = (
        DeterministicIdentifierDetector.detect(text)
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=text,
            candidates=deterministic_candidates,
        )
    )

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "+965 52988745" not in output.text
    assert output.text == "Phone: [PHONE_NUMBER]"
    assert output.replaced_count == 1
    assert output.requires_review is False

def test_detects_record_checksum_as_document_identifier():
    text = "Record checksum: CHK-12963419"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.text == "CHK-12963419"
    assert candidate.start == text.index("CHK-12963419")
    assert candidate.end == candidate.start + len(candidate.text)
    assert candidate.canonical_type == CandidateEntityType.DOCUMENT_ID
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "Record checksum"
    assert candidate.metadata["rule_name"] == "record_checksum_field"
    assert candidate.metadata["field_label"] == "Record checksum"
    assert candidate.matches_source_text(text)


def test_record_checksum_is_replaced_by_existing_mednexus_pipeline():
    text = "Record checksum: CHK-51431708"

    deterministic_candidates = (
        DeterministicIdentifierDetector.detect(text)
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=text,
            candidates=deterministic_candidates,
        )
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "CHK-51431708" not in output.text
    assert output.text.startswith("Record checksum: [DOCUMENT_ID:")
    assert output.text.endswith("]")
    assert output.replaced_count == 1
    assert output.requires_review is False

def test_detects_arabic_patient_name_from_explicit_field():
    text = "اسم المريض: خالد صالح"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.text == "خالد صالح"
    assert candidate.start == text.index("خالد صالح")
    assert candidate.end == candidate.start + len(candidate.text)
    assert candidate.canonical_type == CandidateEntityType.PATIENT_NAME
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "اسم المريض"
    assert candidate.metadata["rule_name"] == "patient_name_field"
    assert candidate.matches_source_text(text)


def test_arabic_patient_name_is_replaced_by_existing_mednexus_pipeline():
    text = "اسم المريض: خالد صالح"

    deterministic_candidates = DeterministicIdentifierDetector.detect(text)

    intelligence_result = MedNexusIntelligenceOrchestrator.process_candidates(
        source_text=text,
        candidates=deterministic_candidates,
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "خالد صالح" not in output.text
    assert output.text == "اسم المريض: [PATIENT_NAME]"
    assert output.replaced_count == 1
    assert output.requires_review is False


def test_detects_electronic_signature_id_as_document_identifier():
    text = "Electronic Signature ID: SIG-76645"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.text == "SIG-76645"
    assert candidate.canonical_type == CandidateEntityType.DOCUMENT_ID
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "Electronic Signature ID"
    assert candidate.metadata["rule_name"] == "document_id_field"
    assert candidate.matches_source_text(text)


def test_electronic_signature_id_is_replaced_by_existing_mednexus_pipeline():
    text = "Electronic Signature ID: SIG-79069"

    deterministic_candidates = DeterministicIdentifierDetector.detect(text)

    intelligence_result = MedNexusIntelligenceOrchestrator.process_candidates(
        source_text=text,
        candidates=deterministic_candidates,
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "SIG-79069" not in output.text
    assert output.text.startswith("Electronic Signature ID: [DOCUMENT_ID:")
    assert output.text.endswith("]")
    assert output.replaced_count == 1
    assert output.requires_review is False


def test_patient_name_rule_does_not_capture_following_line():
    text = "\n".join(
        [
            "اسم المريض: خالد صالح",
            "الرقم المدني: 290020203333",
        ]
    )

    candidates = DeterministicIdentifierDetector.detect(text)

    patient_names = [
        candidate
        for candidate in candidates
        if candidate.canonical_type == CandidateEntityType.PATIENT_NAME
    ]

    assert len(patient_names) == 1
    assert patient_names[0].text == "خالد صالح"

def test_detects_form_number_as_document_identifier():
    text = "Form Number: NF-968254"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.text == "NF-968254"
    assert candidate.start == text.index("NF-968254")
    assert candidate.end == candidate.start + len(candidate.text)
    assert candidate.canonical_type == CandidateEntityType.DOCUMENT_ID
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "Form Number"
    assert candidate.metadata["rule_name"] == "document_id_field"
    assert candidate.matches_source_text(text)


def test_form_number_is_replaced_by_existing_mednexus_pipeline():
    text = "Form Number: NF-968254"

    deterministic_candidates = DeterministicIdentifierDetector.detect(text)

    intelligence_result = MedNexusIntelligenceOrchestrator.process_candidates(
        source_text=text,
        candidates=deterministic_candidates,
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "NF-968254" not in output.text
    assert output.text.startswith("Form Number: [DOCUMENT_ID:")
    assert output.text.endswith("]")
    assert output.replaced_count == 1
    assert output.requires_review is False


@pytest.mark.parametrize(
    "label",
    [
        "Form ID",
        "Form No.",
    ],
)
def test_detects_common_form_identifier_labels(label):
    text = f"{label}: NF-968254"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    assert candidates[0].text == "NF-968254"
    assert candidates[0].canonical_type == CandidateEntityType.DOCUMENT_ID
    assert candidates[0].source == CandidateSource.MEDNEXUS_FIELD_RULE

def test_detects_deceased_name_as_patient_name():
    text = "Deceased Name: مريم الصباح"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    candidate = candidates[0]

    assert candidate.text == "مريم الصباح"
    assert candidate.canonical_type == CandidateEntityType.PATIENT_NAME
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "Deceased Name"
    assert candidate.metadata["rule_name"] == "patient_name_field"
    assert candidate.matches_source_text(text)


def test_deceased_name_is_replaced_by_existing_mednexus_pipeline():
    text = "Deceased Name: مريم الصباح"

    deterministic_candidates = DeterministicIdentifierDetector.detect(text)
    intelligence_result = MedNexusIntelligenceOrchestrator.process_candidates(
        source_text=text,
        candidates=deterministic_candidates,
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "مريم الصباح" not in output.text
    assert output.text == "Deceased Name: [PATIENT_NAME]"
    assert output.replaced_count == 1
    assert output.requires_review is False


def test_detects_medical_license_number_as_employee_number():
    text = "Medical License Number: LIC-3403"

    candidates = DeterministicIdentifierDetector.detect(text)

    assert len(candidates) == 1
    candidate = candidates[0]

    assert candidate.text == "LIC-3403"
    assert candidate.canonical_type == CandidateEntityType.EMPLOYEE_NUMBER
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.raw_label == "Medical License Number"
    assert candidate.metadata["rule_name"] == "employee_number_field"
    assert candidate.matches_source_text(text)


def test_medical_license_number_is_replaced_by_existing_mednexus_pipeline():
    text = "Medical License Number: LIC-3403"

    deterministic_candidates = DeterministicIdentifierDetector.detect(text)
    intelligence_result = MedNexusIntelligenceOrchestrator.process_candidates(
        source_text=text,
        candidates=deterministic_candidates,
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    output = MedNexusOutputBuilder.build(
        source_text=text,
        candidates=intelligence_result.all_candidates,
    )

    assert "LIC-3403" not in output.text
    assert output.text.startswith("Medical License Number: [EMPLOYEE_NUMBER:")
    assert output.text.endswith("]")
    assert output.replaced_count == 1
    assert output.requires_review is False


def test_deceased_name_rule_does_not_capture_following_line():
    text = "\n".join(
        [
            "Deceased Name: مريم الصباح",
            "Civil ID: 290020203333",
        ]
    )

    candidates = DeterministicIdentifierDetector.detect(text)

    patient_names = [
        candidate
        for candidate in candidates
        if candidate.canonical_type == CandidateEntityType.PATIENT_NAME
    ]

    assert len(patient_names) == 1
    assert patient_names[0].text == "مريم الصباح"


def test_medical_license_rule_does_not_redact_unlabelled_clinical_code():
    text = "Clinical code LIC-3403 was documented without a license field label."

    candidates = DeterministicIdentifierDetector.detect(text)

    assert candidates == ()
