from __future__ import annotations

import re
from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
    MedNexusCandidateEntity,
)


class EntityCanonicalizer:
    """
    Convert engine-specific labels into the MedNexus candidate taxonomy.

    External engines are allowed to suggest labels, but those labels do
    not become authoritative MedNexus entities automatically.

    The canonicalizer performs only taxonomy normalization.

    It does not:
        - accept or reject detections
        - resolve patient/physician/nurse roles
        - apply privacy policies
        - transform document text

    Those responsibilities belong to later MedNexus Intelligence layers.
    """

    LABEL_MAP = {
        # --------------------------------------------------
        # Generic person-name labels
        # --------------------------------------------------
        "name": CandidateEntityType.PERSON_NAME,
        "person": CandidateEntityType.PERSON_NAME,
        "person_name": CandidateEntityType.PERSON_NAME,
        "full_name": CandidateEntityType.PERSON_NAME,
        "firstname": CandidateEntityType.PERSON_NAME,
        "first_name": CandidateEntityType.PERSON_NAME,
        "given_name": CandidateEntityType.PERSON_NAME,
        "lastname": CandidateEntityType.PERSON_NAME,
        "last_name": CandidateEntityType.PERSON_NAME,
        "surname": CandidateEntityType.PERSON_NAME,
        "family_name": CandidateEntityType.PERSON_NAME,
        "middle_name": CandidateEntityType.PERSON_NAME,
        "username": CandidateEntityType.PERSON_NAME,
        "user_name": CandidateEntityType.PERSON_NAME,

        # --------------------------------------------------
        # Role-specific person labels
        # --------------------------------------------------
        "patient": CandidateEntityType.PATIENT_NAME,
        "patient_name": CandidateEntityType.PATIENT_NAME,

        "doctor": CandidateEntityType.PHYSICIAN_NAME,
        "doctor_name": CandidateEntityType.PHYSICIAN_NAME,
        "physician": CandidateEntityType.PHYSICIAN_NAME,
        "physician_name": CandidateEntityType.PHYSICIAN_NAME,
        "clinician": CandidateEntityType.PHYSICIAN_NAME,
        "consultant_name": CandidateEntityType.PHYSICIAN_NAME,
        "provider_name": CandidateEntityType.PHYSICIAN_NAME,

        "nurse": CandidateEntityType.NURSE_NAME,
        "nurse_name": CandidateEntityType.NURSE_NAME,

        "guardian": CandidateEntityType.GUARDIAN_NAME,
        "guardian_name": CandidateEntityType.GUARDIAN_NAME,

        "relative": CandidateEntityType.RELATIVE_NAME,
        "relative_name": CandidateEntityType.RELATIVE_NAME,
        "next_of_kin": CandidateEntityType.RELATIVE_NAME,

        "employee_name": CandidateEntityType.EMPLOYEE_NAME,
        "student_name": CandidateEntityType.STUDENT_NAME,

        # --------------------------------------------------
        # Identifiers
        # --------------------------------------------------
        "civil_id": CandidateEntityType.CIVIL_ID,
        "civil_number": CandidateEntityType.CIVIL_ID,
        "national_id": CandidateEntityType.CIVIL_ID,
        "national_identifier": CandidateEntityType.CIVIL_ID,
        "government_id": CandidateEntityType.CIVIL_ID,
        "identity_number": CandidateEntityType.CIVIL_ID,

        "mrn": CandidateEntityType.MRN,
        "medical_record_number": CandidateEntityType.MRN,
        "medical_record_no": CandidateEntityType.MRN,
        "medical_record_id": CandidateEntityType.MRN,
        "patient_id": CandidateEntityType.MRN,

        "visit_number": CandidateEntityType.VISIT_NUMBER,
        "visit_id": CandidateEntityType.VISIT_NUMBER,
        "encounter_number": CandidateEntityType.VISIT_NUMBER,
        "encounter_id": CandidateEntityType.VISIT_NUMBER,
        "episode_number": CandidateEntityType.VISIT_NUMBER,

        "accession_number": CandidateEntityType.ACCESSION_NUMBER,
        "accession_id": CandidateEntityType.ACCESSION_NUMBER,

        "specimen_number": CandidateEntityType.SPECIMEN_NUMBER,
        "specimen_id": CandidateEntityType.SPECIMEN_NUMBER,

        "lab_number": CandidateEntityType.LAB_NUMBER,
        "laboratory_number": CandidateEntityType.LAB_NUMBER,
        "laboratory_id": CandidateEntityType.LAB_NUMBER,

        "document_id": CandidateEntityType.DOCUMENT_ID,
        "document_number": CandidateEntityType.DOCUMENT_ID,
        "record_checksum": CandidateEntityType.DOCUMENT_ID,

        "insurance_number": CandidateEntityType.INSURANCE_NUMBER,
        "insurance_id": CandidateEntityType.INSURANCE_NUMBER,
        "policy_number": CandidateEntityType.INSURANCE_NUMBER,

        "employee_number": CandidateEntityType.EMPLOYEE_NUMBER,
        "employee_id": CandidateEntityType.EMPLOYEE_NUMBER,

        "student_number": CandidateEntityType.STUDENT_NUMBER,
        "student_id": CandidateEntityType.STUDENT_NUMBER,

        # --------------------------------------------------
        # Contact information
        # --------------------------------------------------
        "phone": CandidateEntityType.PHONE_NUMBER,
        "phone_number": CandidateEntityType.PHONE_NUMBER,
        "telephone": CandidateEntityType.PHONE_NUMBER,
        "telephone_number": CandidateEntityType.PHONE_NUMBER,
        "mobile": CandidateEntityType.PHONE_NUMBER,
        "mobile_number": CandidateEntityType.PHONE_NUMBER,
        "fax": CandidateEntityType.PHONE_NUMBER,

        "email": CandidateEntityType.EMAIL,
        "email_address": CandidateEntityType.EMAIL,
        "e_mail": CandidateEntityType.EMAIL,

        "address": CandidateEntityType.ADDRESS,
        "street_address": CandidateEntityType.ADDRESS,
        "postal_address": CandidateEntityType.ADDRESS,
        "home_address": CandidateEntityType.ADDRESS,

        # --------------------------------------------------
        # Dates
        # --------------------------------------------------
        "date_of_birth": CandidateEntityType.DATE_OF_BIRTH,
        "dob": CandidateEntityType.DATE_OF_BIRTH,
        "birth_date": CandidateEntityType.DATE_OF_BIRTH,

        "admission_date": CandidateEntityType.ADMISSION_DATE,
        "admit_date": CandidateEntityType.ADMISSION_DATE,

        "discharge_date": CandidateEntityType.DISCHARGE_DATE,

        "collection_date": CandidateEntityType.COLLECTION_DATE,
        "collection_time": CandidateEntityType.COLLECTION_DATE,
        "specimen_collection_date": CandidateEntityType.COLLECTION_DATE,

        "exam_date": CandidateEntityType.EXAM_DATE,
        "examination_date": CandidateEntityType.EXAM_DATE,
        "study_date": CandidateEntityType.EXAM_DATE,
        "order_date": CandidateEntityType.EXAM_DATE,

        "date": CandidateEntityType.GENERAL_DATE,
        "datetime": CandidateEntityType.GENERAL_DATE,
        "date_time": CandidateEntityType.GENERAL_DATE,

        # --------------------------------------------------
        # Contextual candidates
        # --------------------------------------------------
        "organization": CandidateEntityType.ORGANIZATION,
        "organisation": CandidateEntityType.ORGANIZATION,
        "hospital": CandidateEntityType.ORGANIZATION,
        "facility": CandidateEntityType.ORGANIZATION,
        "company": CandidateEntityType.ORGANIZATION,

        "location": CandidateEntityType.LOCATION,
        "place": CandidateEntityType.LOCATION,
        "city": CandidateEntityType.LOCATION,
        "country": CandidateEntityType.LOCATION,
        "geographic_location": CandidateEntityType.LOCATION,

        "occupation": CandidateEntityType.PROFESSIONAL_ROLE,
        "job_title": CandidateEntityType.PROFESSIONAL_ROLE,
        "profession": CandidateEntityType.PROFESSIONAL_ROLE,
        "professional_role": CandidateEntityType.PROFESSIONAL_ROLE,

        # --------------------------------------------------
        # Labels that must not be trusted automatically
        # --------------------------------------------------
        "bic": CandidateEntityType.UNKNOWN,
        "iban": CandidateEntityType.UNKNOWN,
        "swift": CandidateEntityType.UNKNOWN,
        "credit_card": CandidateEntityType.UNKNOWN,
        "credit_card_number": CandidateEntityType.UNKNOWN,
        "cryptocurrency_address": CandidateEntityType.UNKNOWN,
        "ip_address": CandidateEntityType.UNKNOWN,
        "url": CandidateEntityType.UNKNOWN,
        "license_plate": CandidateEntityType.UNKNOWN,
    }

    @classmethod
    def canonicalize(
        cls,
        candidate: MedNexusCandidateEntity,
        *,
        overwrite_existing: bool = False,
    ) -> MedNexusCandidateEntity:
        """
        Return a candidate containing a MedNexus canonical entity type.

        Existing MedNexus classifications are preserved by default.

        Args:
            candidate:
                Candidate entity produced by MedNexus rules or an
                external engine.

            overwrite_existing:
                When True, the canonicalizer may replace an existing
                non-UNKNOWN canonical type.

        Returns:
            A new immutable MedNexusCandidateEntity.
        """

        if not isinstance(
            candidate,
            MedNexusCandidateEntity,
        ):
            raise TypeError(
                "candidate must be a MedNexusCandidateEntity."
            )

        if (
            candidate.canonical_type
            != CandidateEntityType.UNKNOWN
            and not overwrite_existing
        ):
            return candidate

        normalized_label = cls.normalize_label(
            candidate.raw_label
            or candidate.normalized_label
            or ""
        )

        canonical_type = cls.LABEL_MAP.get(
            normalized_label,
            CandidateEntityType.UNKNOWN,
        )

        if canonical_type == CandidateEntityType.UNKNOWN:
            reason = (
                "The source label could not be mapped safely "
                "to the MedNexus entity taxonomy."
            )
        else:
            reason = (
                f"Mapped source label '{normalized_label}' "
                f"to MedNexus type '{canonical_type.value}'."
            )

        return candidate.with_canonical_type(
            canonical_type,
            normalized_label=normalized_label or None,
            reason=reason,
        )

    @classmethod
    def canonicalize_many(
        cls,
        candidates: Iterable[MedNexusCandidateEntity],
        *,
        overwrite_existing: bool = False,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Canonicalize multiple candidates while preserving order.
        """

        if candidates is None:
            raise TypeError(
                "candidates must be an iterable."
            )

        canonicalized = []

        for candidate in candidates:
            canonicalized.append(
                cls.canonicalize(
                    candidate,
                    overwrite_existing=overwrite_existing,
                )
            )

        return tuple(canonicalized)

    @staticmethod
    def normalize_label(
        label: str,
    ) -> str:
        """
        Normalize an engine-specific label for stable mapping.

        Examples:
            FIRST-NAME      -> first_name
            Phone Number    -> phone_number
            <BIC>           -> bic
            [occupation]    -> occupation
        """

        if not isinstance(label, str):
            raise TypeError(
                "label must be a string."
            )

        normalized = label.strip().lower()

        normalized = re.sub(
            r"^[\[\]<>():{}\s]+",
            "",
            normalized,
        )

        normalized = re.sub(
            r"[\[\]<>():{}\s]+$",
            "",
            normalized,
        )

        normalized = re.sub(
            r"[^a-z0-9\u0600-\u06ff]+",
            "_",
            normalized,
        )

        normalized = re.sub(
            r"_+",
            "_",
            normalized,
        )

        return normalized.strip("_")

    @classmethod
    def resolve_label(
        cls,
        label: str,
    ) -> CandidateEntityType:
        """
        Resolve a raw label without constructing a candidate.
        """

        normalized_label = cls.normalize_label(
            label
        )

        return cls.LABEL_MAP.get(
            normalized_label,
            CandidateEntityType.UNKNOWN,
        )

    @classmethod
    def is_known_label(
        cls,
        label: str,
    ) -> bool:
        """
        Return True when a label has an explicit MedNexus mapping.
        """

        normalized_label = cls.normalize_label(
            label
        )

        return normalized_label in cls.LABEL_MAP