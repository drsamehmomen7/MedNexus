from backend.app.modules.medical_document_intelligence.policies.context_rules import (
    ContextRuleEngine,
)
from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.schemas.detected_entity import (
    DetectedEntity,
)


def get_detection(
    detections,
    entity,
):
    return next(
        detection
        for detection in detections
        if detection.entity == entity
    )


def test_detect_patient_name_on_next_line():
    text = (
        "Patient Name:\n"
        "Fatima Abdullah Al-Dosari\n"
    )

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.PATIENT_NAME,
    )

    assert isinstance(detection, DetectedEntity)
    assert detection.value == "Fatima Abdullah Al-Dosari"
    assert detection.entity == MedicalContextEntity.PATIENT_NAME
    assert detection.source == "context_rule_engine.field"
    assert detection.confidence == 1.0
    assert detection.label == "Patient Name"
    assert detection.normalized_label == "patient_name"
    assert detection.matches_source_text(text) is True


def test_detect_patient_name_on_same_line():
    text = "Patient Name: Ahmed Hassan"

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.PATIENT_NAME,
    )

    assert detection.value == "Ahmed Hassan"
    assert detection.matches_source_text(text) is True


def test_detect_multiple_structured_identifiers():
    text = (
        "Civil ID:\n"
        "287010101234\n"
        "\n"
        "MRN:\n"
        "MRN-245879\n"
        "\n"
        "Visit Number:\n"
        "ER-2026-99182\n"
    )

    detections = ContextRuleEngine.detect(text)

    civil_id = get_detection(
        detections,
        MedicalContextEntity.CIVIL_ID,
    )

    mrn = get_detection(
        detections,
        MedicalContextEntity.MRN,
    )

    visit_number = get_detection(
        detections,
        MedicalContextEntity.VISIT_NUMBER,
    )

    assert civil_id.value == "287010101234"
    assert mrn.value == "MRN-245879"
    assert visit_number.value == "ER-2026-99182"

    assert civil_id.matches_source_text(text) is True
    assert mrn.matches_source_text(text) is True
    assert visit_number.matches_source_text(text) is True


def test_detect_lab_number_field():
    text = (
        "Lab Number:\n"
        "LAB-2026-99182\n"
    )

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.LAB_NUMBER,
    )

    assert detection.value == "LAB-2026-99182"
    assert detection.label == "Lab Number"
    assert detection.normalized_label == "lab_number"
    assert detection.matches_source_text(text) is True


def test_detect_specimen_and_accession_numbers():
    text = (
        "Specimen Number:\n"
        "SP-2026-00192\n"
        "\n"
        "Accession Number:\n"
        "ACC-2026-88412\n"
    )

    detections = ContextRuleEngine.detect(text)

    specimen = get_detection(
        detections,
        MedicalContextEntity.SPECIMEN_NUMBER,
    )

    accession = get_detection(
        detections,
        MedicalContextEntity.ACCESSION_NUMBER,
    )

    assert specimen.value == "SP-2026-00192"
    assert accession.value == "ACC-2026-88412"
    assert specimen.matches_source_text(text) is True
    assert accession.matches_source_text(text) is True


def test_detect_physician_name():
    text = (
        "Requesting Physician:\n"
        "Dr. Sarah Al-Mutairi\n"
    )

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.PHYSICIAN_NAME,
    )

    assert detection.value == "Dr. Sarah Al-Mutairi"
    assert detection.label == "Requesting Physician"
    assert detection.normalized_label == "requesting_physician"
    assert detection.matches_source_text(text) is True


def test_detect_inline_mrn():
    text = "The patient record is MRN-123456."

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.MRN,
    )

    assert detection.value == "MRN-123456"
    assert detection.source == "context_rule_engine.inline"
    assert detection.label is None
    assert detection.normalized_label is None
    assert detection.matches_source_text(text) is True


def test_detect_inline_lab_number():
    text = "Sample registered as LAB-2026-99182."

    detections = ContextRuleEngine.detect(text)

    detection = get_detection(
        detections,
        MedicalContextEntity.LAB_NUMBER,
    )

    assert detection.value == "LAB-2026-99182"
    assert detection.source == "context_rule_engine.inline"
    assert detection.matches_source_text(text) is True


def test_empty_text_returns_empty_list():
    assert ContextRuleEngine.detect("") == []
    assert ContextRuleEngine.detect("   ") == []
    assert ContextRuleEngine.detect(None) == []


def test_results_are_sorted_by_source_position():
    text = (
        "MRN:\n"
        "MRN-245879\n"
        "\n"
        "Civil ID:\n"
        "287010101234\n"
    )

    detections = ContextRuleEngine.detect(text)

    starts = [
        detection.start
        for detection in detections
    ]

    assert starts == sorted(starts)


def test_duplicate_detection_is_not_returned_twice():
    text = (
        "MRN:\n"
        "MRN-245879\n"
    )

    detections = ContextRuleEngine.detect(text)

    mrn_detections = [
        detection
        for detection in detections
        if detection.entity == MedicalContextEntity.MRN
    ]

    assert len(mrn_detections) == 1
    assert mrn_detections[0].value == "MRN-245879"


def test_all_detections_use_unified_contract():
    text = (
        "Patient Name:\n"
        "Ahmed Hassan\n"
        "\n"
        "Civil ID:\n"
        "287010101234\n"
        "\n"
        "Lab Number:\n"
        "LAB-2026-99182\n"
    )

    detections = ContextRuleEngine.detect(text)

    assert detections
    assert all(
        isinstance(detection, DetectedEntity)
        for detection in detections
    )

    assert all(
        detection.matches_source_text(text)
        for detection in detections
    )