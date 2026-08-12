import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.role_resolver import (
    RoleResolver,
)


def build_name_candidate(
    source_text,
    name,
    *,
    canonical_type=CandidateEntityType.PERSON_NAME,
):
    start = source_text.index(name)

    return MedNexusCandidateEntity(
        text=name,
        start=start,
        end=start + len(name),
        source=CandidateSource.OPENMED,
        raw_label="first_name",
        canonical_type=canonical_type,
        confidence=0.93,
    )


@pytest.mark.parametrize(
    ("label", "expected_type"),
    [
        (
            "Patient Name",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "Patient",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "اسم المريض",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "اسم المريضة",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "Consultant",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "Admitting Consultant",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "Reporting Radiologist",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "Authorized By",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "طبيب الأشعة",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "الاستشاري",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "Assigned Nurse",
            CandidateEntityType.NURSE_NAME,
        ),
        (
            "School Nurse",
            CandidateEntityType.NURSE_NAME,
        ),
        (
            "الممرضة",
            CandidateEntityType.NURSE_NAME,
        ),
        (
            "Guardian Name",
            CandidateEntityType.GUARDIAN_NAME,
        ),
        (
            "اسم ولي الأمر",
            CandidateEntityType.GUARDIAN_NAME,
        ),
        (
            "Next of Kin",
            CandidateEntityType.RELATIVE_NAME,
        ),
        (
            "Emergency Contact",
            CandidateEntityType.RELATIVE_NAME,
        ),
        (
            "أقرب الأقارب",
            CandidateEntityType.RELATIVE_NAME,
        ),
        (
            "Employee Name",
            CandidateEntityType.EMPLOYEE_NAME,
        ),
        (
            "اسم الموظف",
            CandidateEntityType.EMPLOYEE_NAME,
        ),
        (
            "Student Name",
            CandidateEntityType.STUDENT_NAME,
        ),
        (
            "Child Name",
            CandidateEntityType.STUDENT_NAME,
        ),
        (
            "اسم الطالب",
            CandidateEntityType.STUDENT_NAME,
        ),
        (
            "اسم الطفل",
            CandidateEntityType.STUDENT_NAME,
        ),
    ],
)
def test_resolve_inline_field(
    label,
    expected_type,
):
    source_text = (
        f"{label}: Ahmed Hassan"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert (
        resolved.canonical_type
        == expected_type
    )


@pytest.mark.parametrize(
    ("label", "expected_type"),
    [
        (
            "Patient Name:",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "اسم المريض:",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "Reporting Radiologist:",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "طبيب الأشعة:",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "Assigned Nurse:",
            CandidateEntityType.NURSE_NAME,
        ),
        (
            "Guardian Name:",
            CandidateEntityType.GUARDIAN_NAME,
        ),
        (
            "اسم ولي الأمر:",
            CandidateEntityType.GUARDIAN_NAME,
        ),
        (
            "Next of Kin:",
            CandidateEntityType.RELATIVE_NAME,
        ),
        (
            "Employee Name:",
            CandidateEntityType.EMPLOYEE_NAME,
        ),
        (
            "Student Name:",
            CandidateEntityType.STUDENT_NAME,
        ),
    ],
)
def test_resolve_multiline_field(
    label,
    expected_type,
):
    source_text = (
        f"{label}\n"
        f"Ahmed Hassan"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert (
        resolved.canonical_type
        == expected_type
    )


def test_preserves_existing_patient_role():
    source_text = (
        "Consultant: Ahmed Hassan"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert resolved is candidate

    assert (
        resolved.canonical_type
        == CandidateEntityType.PATIENT_NAME
    )


def test_non_person_entity_is_unchanged():
    source_text = (
        "Phone: +965 55555555"
    )

    phone = "+965 55555555"
    start = source_text.index(phone)

    candidate = MedNexusCandidateEntity(
        text=phone,
        start=start,
        end=start + len(phone),
        source=CandidateSource.OPENMED,
        raw_label="phone_number",
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert resolved is candidate


def test_unresolved_generic_name_is_preserved():
    source_text = (
        "Ahmed Hassan attended the clinic."
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert resolved is candidate

    assert (
        resolved.canonical_type
        == CandidateEntityType.PERSON_NAME
    )


def test_reason_is_added_after_resolution():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert resolved.reason == (
        "Resolved person role from document "
        "context as 'patient_name'."
    )


def test_resolve_many_preserves_order():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Consultant: Sara Al-Mutairi"
    )

    candidates = [
        build_name_candidate(
            source_text,
            "Ahmed Hassan",
        ),
        build_name_candidate(
            source_text,
            "Sara Al-Mutairi",
        ),
    ]

    resolved = RoleResolver.resolve_many(
        candidates=candidates,
        source_text=source_text,
    )

    assert isinstance(resolved, tuple)

    assert len(resolved) == 2

    assert (
        resolved[0].canonical_type
        == CandidateEntityType.PATIENT_NAME
    )

    assert (
        resolved[1].canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )


def test_arabic_multiple_roles():
    source_text = (
        "اسم المريض: أحمد حسن\n"
        "طبيب الأشعة: د. خالد العيسى\n"
        "اسم ولي الأمر: يوسف حسن"
    )

    candidates = [
        build_name_candidate(
            source_text,
            "أحمد حسن",
        ),
        build_name_candidate(
            source_text,
            "خالد العيسى",
        ),
        build_name_candidate(
            source_text,
            "يوسف حسن",
        ),
    ]

    resolved = RoleResolver.resolve_many(
        candidates=candidates,
        source_text=source_text,
    )

    assert (
        resolved[0].canonical_type
        == CandidateEntityType.PATIENT_NAME
    )

    assert (
        resolved[1].canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )

    assert (
        resolved[2].canonical_type
        == CandidateEntityType.GUARDIAN_NAME
    )


def test_rejects_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidate must be "
            "a MedNexusCandidateEntity"
        ),
    ):
        RoleResolver.resolve(
            candidate={
                "text": "Ahmed"
            },
            source_text=(
                "Patient Name: Ahmed"
            ),
        )


def test_rejects_invalid_source_text():
    source_text = (
        "Patient Name: Ahmed"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed",
    )

    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        RoleResolver.resolve(
            candidate=candidate,
            source_text=123,
        )


def test_resolve_many_rejects_none():
    with pytest.raises(
        TypeError,
        match="candidates must be an iterable",
    ):
        RoleResolver.resolve_many(
            candidates=None,
            source_text="Medical report",
        )


def test_resolve_many_rejects_invalid_source():
    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        RoleResolver.resolve_many(
            candidates=[],
            source_text=123,
        )


def test_reporting_radiologist_real_example():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    candidate = build_name_candidate(
        source_text,
        "Abdullah Al-Fahad",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert (
        resolved.canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )


def test_arabic_radiologist_real_example():
    source_text = (
        "طبيب الأشعة: د. عبدالله الفهد"
    )

    candidate = build_name_candidate(
        source_text,
        "عبدالله الفهد",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert (
        resolved.canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )


def test_patient_name_multiline_real_example():
    source_text = (
        "PATIENT DEMOGRAPHICS\n"
        "Patient Name:\n"
        "Ahmed Hassan\n"
        "Civil ID: 290000000000"
    )

    candidate = build_name_candidate(
        source_text,
        "Ahmed Hassan",
    )

    resolved = RoleResolver.resolve(
        candidate=candidate,
        source_text=source_text,
    )

    assert (
        resolved.canonical_type
        == CandidateEntityType.PATIENT_NAME
    )
