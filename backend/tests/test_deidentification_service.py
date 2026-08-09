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

    print("\n========== POLICY TRANSFORMED TEXT ==========")
    print(response.metadata["policy_transformed_text"])

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

    assert response.metadata["policy"] == "research"

    policy_text = response.metadata["policy_transformed_text"]

    assert "[PATIENT_NAME]" in policy_text
    assert "[CIVIL_ID:" in policy_text
    assert "[MRN:" in policy_text
    assert "[SPECIMEN_NUMBER:" in policy_text
    assert "[ACCESSION_NUMBER:" in policy_text

    # --------------------------------------------------
    # Placeholder Protection
    # --------------------------------------------------

    placeholder_text = response.metadata[
        "placeholder_protected_text"
    ]

    assert "__MNX_PLACEHOLDER_" in placeholder_text

    assert "[PATIENT_NAME]" not in placeholder_text
    assert "[CIVIL_ID:" not in placeholder_text
    assert "[MRN:" not in placeholder_text
    assert "[SPECIMEN_NUMBER:" not in placeholder_text
    assert "[ACCESSION_NUMBER:" not in placeholder_text

    # --------------------------------------------------
    # KEEP Entity Protection
    # --------------------------------------------------

    keep_text = response.metadata["keep_protected_text"]

    assert "__MNX_KEEP_" in keep_text

    assert "Consultant Pathologist" not in keep_text
    assert "Dr. Huda Al-Awadhi" not in keep_text

    # --------------------------------------------------
    # Clinical Context Protection
    # --------------------------------------------------

    protected_text = response.metadata["fully_protected_text"]

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

    # KEEP entities restored
    assert "Consultant Pathologist" in final_text
    assert "Dr. Huda Al-Awadhi" in final_text

    assert "[occupation]" not in final_text
    assert "[first_name]" not in final_text
    assert "[last_name]" not in final_text

    # MedNexus placeholders restored
    assert "[PATIENT_NAME]" in final_text
    assert "[MRN:" in final_text
    assert "[SPECIMEN_NUMBER:" in final_text
    assert "[ACCESSION_NUMBER:" in final_text

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