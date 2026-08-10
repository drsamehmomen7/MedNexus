import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.context_validator import (
    ContextValidator,
)


def build_candidate(
    source_text,
    entity_text,
    *,
    canonical_type,
    raw_label=None,
    decision=CandidateDecision.PENDING,
    metadata=None,
):
    start = source_text.index(entity_text)

    return MedNexusCandidateEntity(
        text=entity_text,
        start=start,
        end=start + len(entity_text),
        source=CandidateSource.OPENMED,
        raw_label=raw_label,
        canonical_type=canonical_type,
        decision=decision,
        confidence=0.91,
        metadata=metadata or {},
    )


def test_accepts_patient_name():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_accepts_arabic_patient_name():
    source_text = (
        "اسم المريض: أحمد حسن"
    )

    candidate = build_candidate(
        source_text,
        "أحمد حسن",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


@pytest.mark.parametrize(
    "entity_type",
    [
        CandidateEntityType.GUARDIAN_NAME,
        CandidateEntityType.RELATIVE_NAME,
        CandidateEntityType.EMPLOYEE_NAME,
        CandidateEntityType.STUDENT_NAME,
    ],
)
def test_accepts_role_specific_identifying_names(
    entity_type,
):
    source_text = (
        "Name: Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=entity_type,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


@pytest.mark.parametrize(
    "entity_type",
    [
        CandidateEntityType.PHYSICIAN_NAME,
        CandidateEntityType.NURSE_NAME,
    ],
)
def test_accepts_healthcare_professional_names_for_policy_resolution(
    entity_type,
):
    source_text = (
        "Consultant: Dr. Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=entity_type,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


@pytest.mark.parametrize(
    "role_text",
    [
        "Radiologist",
        "Reporting Radiologist",
        "Consultant",
        "Consultant Pathologist",
        "Nurse",
        "Pathologist",
        "طبيب الأشعة",
        "استشاري",
        "ممرضة",
    ],
)
def test_rejects_safe_professional_roles(
    role_text,
):
    source_text = (
        f"Reporting Role: {role_text}"
    )

    candidate = build_candidate(
        source_text,
        role_text,
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        raw_label="occupation",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )


def test_rejects_reporting_radiologist_false_positive():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    candidate = build_candidate(
        source_text,
        "Radiologist",
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        raw_label="occupation",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )

    assert "not patient-identifying" in (
        validated.reason
    )


def test_rejects_arabic_physician_role():
    source_text = (
        "طبيب الأشعة: د. عبدالله الفهد"
    )

    candidate = build_candidate(
        source_text,
        "طبيب الأشعة",
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        raw_label="occupation",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )


@pytest.mark.parametrize(
    "document_text",
    [
        "Document",
        "MEDICAL DOCUMENT",
        "Medical Record",
        "Medical Report",
        "Hospital Information System",
        "CONFIDENTIAL MEDICAL DOCUMENT",
        "مستند طبي",
        "تقرير طبي",
        "نظام معلومات المستشفى",
    ],
)
def test_rejects_document_terms_misclassified_as_bic(
    document_text,
):
    source_text = document_text

    candidate = build_candidate(
        source_text,
        document_text,
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        raw_label="bic",
        metadata={
            "openmed_canonical_label": "BIC",
        },
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )


def test_rejects_medical_document_real_example():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT\n"
        "Prepared for authorized clinical use only."
    )

    candidate = build_candidate(
        source_text,
        "DOCUMENT",
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        raw_label="bic",
        metadata={
            "openmed_canonical_label": "BIC",
        },
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )

    assert "document or clinical terminology" in (
        validated.reason
    )


@pytest.mark.parametrize(
    "placeholder",
    [
        "[occupation]",
        "[bic]",
        "[first_name]",
        "[last_name]",
        "[user_name]",
        "[organization]",
    ],
)
def test_rejects_raw_engine_placeholders(
    placeholder,
):
    source_text = placeholder

    candidate = build_candidate(
        source_text,
        placeholder,
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        raw_label="unknown",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REJECT
    )


@pytest.mark.parametrize(
    "phone",
    [
        "+965 52988745",
        "+965-52988745",
        "52988745",
        "96552988745",
    ],
)
def test_accepts_phone_numbers(
    phone,
):
    source_text = f"Phone: {phone}"

    candidate = build_candidate(
        source_text,
        phone,
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
        raw_label="phone_number",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_invalid_phone_requires_review():
    source_text = "Phone: ABC123"

    candidate = build_candidate(
        source_text,
        "ABC123",
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


def test_accepts_email():
    source_text = (
        "Email: patient@example.com"
    )

    candidate = build_candidate(
        source_text,
        "patient@example.com",
        canonical_type=(
            CandidateEntityType.EMAIL
        ),
        raw_label="email",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_invalid_email_requires_review():
    source_text = (
        "Email: patient-at-example"
    )

    candidate = build_candidate(
        source_text,
        "patient-at-example",
        canonical_type=(
            CandidateEntityType.EMAIL
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


@pytest.mark.parametrize(
    "civil_id",
    [
        "290020203333",
        "٢٩٠٠٢٠٢٠٣٣٣٣",
    ],
)
def test_accepts_civil_id(
    civil_id,
):
    source_text = (
        f"Civil ID: {civil_id}"
    )

    candidate = build_candidate(
        source_text,
        civil_id,
        canonical_type=(
            CandidateEntityType.CIVIL_ID
        ),
        raw_label="civil_id",
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_invalid_civil_id_requires_review():
    source_text = (
        "Civil ID: 12345"
    )

    candidate = build_candidate(
        source_text,
        "12345",
        canonical_type=(
            CandidateEntityType.CIVIL_ID
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


@pytest.mark.parametrize(
    ("value", "entity_type"),
    [
        (
            "MRN-998122",
            CandidateEntityType.MRN,
        ),
        (
            "VIS-2026-11223",
            CandidateEntityType.VISIT_NUMBER,
        ),
        (
            "ACC-2026-334455",
            CandidateEntityType.ACCESSION_NUMBER,
        ),
        (
            "SP-2026-77881",
            CandidateEntityType.SPECIMEN_NUMBER,
        ),
        (
            "LAB-882211",
            CandidateEntityType.LAB_NUMBER,
        ),
        (
            "DOC-0001",
            CandidateEntityType.DOCUMENT_ID,
        ),
        (
            "EMP-88771",
            CandidateEntityType.EMPLOYEE_NUMBER,
        ),
        (
            "STU-55661",
            CandidateEntityType.STUDENT_NUMBER,
        ),
    ],
)
def test_accepts_structured_identifiers(
    value,
    entity_type,
):
    source_text = f"Identifier: {value}"

    candidate = build_candidate(
        source_text,
        value,
        canonical_type=entity_type,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_incomplete_identifier_requires_review():
    source_text = "MRN: AB"

    candidate = build_candidate(
        source_text,
        "AB",
        canonical_type=(
            CandidateEntityType.MRN
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


def test_generic_person_in_patient_context_is_accepted():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_generic_unresolved_person_requires_review():
    source_text = (
        "Ahmed Hassan attended the hospital."
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


@pytest.mark.parametrize(
    "entity_type",
    [
        CandidateEntityType.ORGANIZATION,
        CandidateEntityType.LOCATION,
    ],
)
def test_contextual_entities_require_review(
    entity_type,
):
    source_text = (
        "Al Noor General Hospital"
    )

    candidate = build_candidate(
        source_text,
        "Al Noor General Hospital",
        canonical_type=entity_type,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


@pytest.mark.parametrize(
    "entity_type",
    [
        CandidateEntityType.ADMISSION_DATE,
        CandidateEntityType.DISCHARGE_DATE,
        CandidateEntityType.COLLECTION_DATE,
        CandidateEntityType.EXAM_DATE,
        CandidateEntityType.GENERAL_DATE,
    ],
)
def test_accepts_date_candidates(
    entity_type,
):
    source_text = "Date: 02/08/2026"

    candidate = build_candidate(
        source_text,
        "02/08/2026",
        canonical_type=entity_type,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.ACCEPT
    )


def test_invalid_offsets_require_review():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = MedNexusCandidateEntity(
        text="Ahmed Hassan",
        start=0,
        end=12,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert (
        validated.decision
        == CandidateDecision.REVIEW_REQUIRED
    )


def test_existing_decision_is_preserved():
    source_text = "Document"

    candidate = build_candidate(
        source_text,
        "Document",
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        raw_label="bic",
        decision=CandidateDecision.REJECT,
    )

    validated = ContextValidator.validate(
        candidate,
        source_text,
    )

    assert validated is candidate


def test_validate_many_preserves_order():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Phone: +965 52988745\n"
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    candidates = [
        build_candidate(
            source_text,
            "Ahmed Hassan",
            canonical_type=(
                CandidateEntityType.PATIENT_NAME
            ),
        ),
        build_candidate(
            source_text,
            "+965 52988745",
            canonical_type=(
                CandidateEntityType.PHONE_NUMBER
            ),
        ),
        build_candidate(
            source_text,
            "DOCUMENT",
            canonical_type=(
                CandidateEntityType.UNKNOWN
            ),
            raw_label="bic",
            metadata={
                "openmed_canonical_label": "BIC",
            },
        ),
    ]

    validated = ContextValidator.validate_many(
        candidates,
        source_text,
    )

    assert isinstance(validated, tuple)

    assert (
        validated[0].decision
        == CandidateDecision.ACCEPT
    )

    assert (
        validated[1].decision
        == CandidateDecision.ACCEPT
    )

    assert (
        validated[2].decision
        == CandidateDecision.REJECT
    )


def test_validate_rejects_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidate must be "
            "a MedNexusCandidateEntity"
        ),
    ):
        ContextValidator.validate(
            {"text": "Ahmed"},
            "Patient Name: Ahmed",
        )


def test_validate_rejects_invalid_source_text():
    source_text = (
        "Patient Name: Ahmed"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        ContextValidator.validate(
            candidate,
            123,
        )


def test_validate_many_rejects_none():
    with pytest.raises(
        TypeError,
        match="candidates must be an iterable",
    ):
        ContextValidator.validate_many(
            None,
            "Medical report",
        )


def test_validate_many_rejects_invalid_source():
    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        ContextValidator.validate_many(
            [],
            123,
        )
