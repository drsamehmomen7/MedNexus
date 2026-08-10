from dataclasses import dataclass

import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.intelligence_orchestrator import (
    MedNexusIntelligenceOrchestrator,
    MedNexusIntelligenceResult,
)
from backend.app.modules.medical_document_intelligence.intelligence.context_rule_candidate_adapter import (
    ContextRuleCandidateAdapter,
)
from backend.app.modules.medical_document_intelligence.policies.context_rules import (
    ContextRuleEngine,
)


@dataclass
class FakeOpenMedEntity:
    text: str
    start: int
    end: int
    raw_label: str
    canonical_label: str | None = None
    confidence: float | None = 0.90
    surrogate: str | None = None


@dataclass
class FakeOpenMedResult:
    pii_entities: list


def build_candidate(
    source_text,
    entity_text,
    *,
    source=CandidateSource.MEDNEXUS_FIELD_RULE,
    canonical_type=CandidateEntityType.UNKNOWN,
    decision=CandidateDecision.PENDING,
    raw_label=None,
):
    start = source_text.index(entity_text)

    return MedNexusCandidateEntity(
        text=entity_text,
        start=start,
        end=start + len(entity_text),
        source=source,
        raw_label=raw_label,
        canonical_type=canonical_type,
        decision=decision,
        confidence=1.0,
    )


def test_process_openmed_result_returns_intelligence_result():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Ahmed Hassan",
                start=14,
                end=26,
                raw_label="person_name",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert isinstance(
        intelligence_result,
        MedNexusIntelligenceResult,
    )


def test_context_candidates_share_the_authoritative_intelligence_path():
    source_text = "Patient Name: Ahmed Hassan"
    context_candidates = ContextRuleCandidateAdapter.adapt_many(
        detections=ContextRuleEngine.detect(source_text),
        source_text=source_text,
    )
    result = FakeOpenMedResult(pii_entities=[])

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
            context_candidates=context_candidates,
        )
    )

    assert intelligence_result.accepted_count == 1
    candidate = intelligence_result.accepted[0]
    assert candidate.text == "Ahmed Hassan"
    assert candidate.canonical_type == CandidateEntityType.PATIENT_NAME
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.matches_source_text(source_text)


def test_openmed_patient_name_is_resolved_and_accepted():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Ahmed Hassan",
                start=14,
                end=26,
                raw_label="person_name",
                canonical_label="PERSON",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.total_count == 1
    assert intelligence_result.accepted_count == 1

    candidate = intelligence_result.accepted[0]

    assert (
        candidate.canonical_type
        == CandidateEntityType.PATIENT_NAME
    )

    assert (
        candidate.decision
        == CandidateDecision.ACCEPT
    )


def test_openmed_physician_name_is_kept():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    physician_name = "Abdullah Al-Fahad"
    start = source_text.index(
        physician_name
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text=physician_name,
                start=start,
                end=start + len(physician_name),
                raw_label="person_name",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.accepted_count == 1

    assert (
        intelligence_result.accepted[0].canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )


def test_openmed_occupation_false_positive_is_rejected():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Radiologist",
                start=10,
                end=21,
                raw_label="occupation",
                canonical_label="OCCUPATION",
                surrogate="[occupation]",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.rejected_count == 1

    assert (
        intelligence_result.rejected[0].text
        == "Radiologist"
    )

    assert (
        intelligence_result.rejected[0].decision
        == CandidateDecision.REJECT
    )


def test_openmed_bic_false_positive_is_rejected():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="DOCUMENT",
                start=21,
                end=29,
                raw_label="bic",
                canonical_label="BIC",
                surrogate="[bic]",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.rejected_count == 1

    assert (
        intelligence_result.rejected[0].text
        == "DOCUMENT"
    )


def test_openmed_phone_is_accepted():
    source_text = (
        "Phone: +965 52988745"
    )

    phone = "+965 52988745"
    start = source_text.index(phone)

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text=phone,
                start=start,
                end=start + len(phone),
                raw_label="phone_number",
                canonical_label="PHONE",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.accepted_count == 1

    assert (
        intelligence_result.accepted[0].canonical_type
        == CandidateEntityType.PHONE_NUMBER
    )


def test_mednexus_candidate_beats_openmed_duplicate():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    openmed_result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Ahmed Hassan",
                start=14,
                end=26,
                raw_label="person_name",
            )
        ]
    )

    mednexus_candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=openmed_result,
            source_text=source_text,
            mednexus_candidates=[
                mednexus_candidate
            ],
        )
    )

    assert intelligence_result.total_count == 1

    final_candidate = (
        intelligence_result.all_candidates[0]
    )

    assert (
        final_candidate.source
        == CandidateSource.MEDNEXUS_FIELD_RULE
    )


def test_process_candidates_without_openmed():
    source_text = (
        "Phone: +965 52988745"
    )

    candidate = build_candidate(
        source_text,
        "+965 52988745",
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
        decision=CandidateDecision.PENDING,
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=source_text,
            candidates=[candidate],
        )
    )

    assert intelligence_result.accepted_count == 1
    assert intelligence_result.total_count == 1


def test_result_groups_all_decisions():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Consultant: Sara Al-Mutairi\n"
        "Hospital: Al Noor Hospital\n"
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
            "Sara Al-Mutairi",
            canonical_type=(
                CandidateEntityType.PHYSICIAN_NAME
            ),
        ),
        build_candidate(
            source_text,
            "Al Noor Hospital",
            canonical_type=(
                CandidateEntityType.ORGANIZATION
            ),
        ),
        build_candidate(
            source_text,
            "DOCUMENT",
            source=CandidateSource.OPENMED,
            canonical_type=(
                CandidateEntityType.UNKNOWN
            ),
            raw_label="bic",
        ),
    ]

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=source_text,
            candidates=candidates,
        )
    )

    assert intelligence_result.total_count == 4
    assert intelligence_result.accepted_count == 2
    assert intelligence_result.kept_count == 0
    assert intelligence_result.rejected_count == 1
    assert (
        intelligence_result.review_required_count
        == 1
    )


def test_safe_result_has_no_review_or_pending():
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

    result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=source_text,
            candidates=[candidate],
        )
    )

    assert (
        result.is_safe_for_automatic_output
        is True
    )


def test_review_required_result_is_not_safe():
    source_text = (
        "Hospital: Al Noor Hospital"
    )

    candidate = build_candidate(
        source_text,
        "Al Noor Hospital",
        canonical_type=(
            CandidateEntityType.ORGANIZATION
        ),
    )

    result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=source_text,
            candidates=[candidate],
        )
    )

    assert (
        result.is_safe_for_automatic_output
        is False
    )


def test_result_to_dict():
    source_text = (
        "Phone: +965 52988745"
    )

    candidate = build_candidate(
        source_text,
        "+965 52988745",
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
    )

    result = (
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=source_text,
            candidates=[candidate],
        )
    )

    data = result.to_dict()

    assert data["total_count"] == 1
    assert data["accepted_count"] == 1
    assert data["rejected_count"] == 0
    assert (
        data["is_safe_for_automatic_output"]
        is True
    )

    assert len(data["all_candidates"]) == 1
    assert len(data["accepted"]) == 1


def test_empty_openmed_result():
    result = FakeOpenMedResult(
        pii_entities=[]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text="Medical report",
        )
    )

    assert intelligence_result.total_count == 0
    assert intelligence_result.accepted == ()
    assert intelligence_result.kept == ()
    assert intelligence_result.rejected == ()
    assert intelligence_result.review_required == ()
    assert intelligence_result.pending == ()

    assert (
        intelligence_result.is_safe_for_automatic_output
        is True
    )


def test_candidate_order_is_preserved_by_source_position():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Phone: +965 52988745"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="+965 52988745",
                start=34,
                end=47,
                raw_label="phone_number",
            ),
            FakeOpenMedEntity(
                text="Ahmed Hassan",
                start=14,
                end=26,
                raw_label="person_name",
            ),
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert (
        intelligence_result.all_candidates[0].text
        == "Ahmed Hassan"
    )

    assert (
        intelligence_result.all_candidates[1].text
        == "+965 52988745"
    )


def test_arabic_patient_name_is_resolved():
    source_text = (
        "اسم المريض: أحمد حسن"
    )

    name = "أحمد حسن"
    start = source_text.index(name)

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text=name,
                start=start,
                end=start + len(name),
                raw_label="person_name",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.accepted_count == 1

    assert (
        intelligence_result.accepted[0].canonical_type
        == CandidateEntityType.PATIENT_NAME
    )


def test_arabic_physician_name_is_kept():
    source_text = (
        "طبيب الأشعة: د. عبدالله الفهد"
    )

    name = "عبدالله الفهد"
    start = source_text.index(name)

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text=name,
                start=start,
                end=start + len(name),
                raw_label="person_name",
            )
        ]
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.accepted_count == 1
    assert intelligence_result.kept_count == 0

    assert (
        intelligence_result.accepted[0].canonical_type
        == CandidateEntityType.PHYSICIAN_NAME
    )


def test_realistic_radiology_result():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Phone: +965 52988745\n"
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad\n"
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    entities = []

    for text, label in [
        ("Ahmed Hassan", "person_name"),
        ("+965 52988745", "phone_number"),
        ("Radiologist", "occupation"),
        ("Abdullah Al-Fahad", "person_name"),
        ("DOCUMENT", "bic"),
    ]:
        start = source_text.index(text)

        entities.append(
            FakeOpenMedEntity(
                text=text,
                start=start,
                end=start + len(text),
                raw_label=label,
                canonical_label=label.upper(),
                surrogate=f"[{label}]",
            )
        )

    result = FakeOpenMedResult(
        pii_entities=entities
    )

    intelligence_result = (
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert intelligence_result.total_count == 5
    assert intelligence_result.accepted_count == 3
    assert intelligence_result.kept_count == 0
    assert intelligence_result.rejected_count == 2
    assert (
        intelligence_result.review_required_count
        == 0
    )

    rejected_texts = {
        candidate.text
        for candidate
        in intelligence_result.rejected
    }

    assert "Radiologist" in rejected_texts
    assert "DOCUMENT" in rejected_texts


def test_rejects_none_engine_result():
    with pytest.raises(
        TypeError,
        match="engine_result cannot be None",
    ):
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=None,
            source_text="Medical report",
        )


def test_rejects_invalid_source_text():
    result = FakeOpenMedResult(
        pii_entities=[]
    )

    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text=123,
        )


def test_rejects_none_mednexus_candidates():
    result = FakeOpenMedResult(
        pii_entities=[]
    )

    with pytest.raises(
        TypeError,
        match=(
            "mednexus_candidates must be "
            "an iterable"
        ),
    ):
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text="Medical report",
            mednexus_candidates=None,
        )


def test_rejects_invalid_candidate_object():
    result = FakeOpenMedResult(
        pii_entities=[]
    )

    with pytest.raises(
        TypeError,
        match=(
            "All candidates must be "
            "MedNexusCandidateEntity objects"
        ),
    ):
        MedNexusIntelligenceOrchestrator.process_openmed_result(
            engine_result=result,
            source_text="Medical report",
            mednexus_candidates=[
                {
                    "text": "Ahmed"
                }
            ],
        )


def test_process_candidates_rejects_none():
    with pytest.raises(
        TypeError,
        match="candidates must be an iterable",
    ):
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text="Medical report",
            candidates=None,
        )


def test_process_candidates_rejects_invalid_source():
    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        MedNexusIntelligenceOrchestrator.process_candidates(
            source_text=123,
            candidates=[],
        )
