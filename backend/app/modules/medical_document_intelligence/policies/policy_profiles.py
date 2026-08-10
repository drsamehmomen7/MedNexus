from __future__ import annotations

from enum import Enum

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_models import (
    PolicyDefinition,
    PolicyRule,
)


class PolicyProfile(str, Enum):
    MEDNEXUS_CLINICAL = "mednexus_clinical"
    MEDNEXUS_RESEARCH = "mednexus_research"
    MEDNEXUS_ANALYTICS_PUBLIC_HEALTH = (
        "mednexus_analytics_public_health"
    )
    MEDNEXUS_STRICT_PRIVACY = "mednexus_strict_privacy"

    # Source-code compatibility aliases. Public legacy string values are
    # handled by resolve_policy_profile below.
    MEDNEXUS_DEFAULT = "mednexus_clinical"
    RESEARCH = "mednexus_research"
    STRICT_PRIVACY = "mednexus_strict_privacy"


LEGACY_POLICY_ALIASES = {
    "mednexus_default": PolicyProfile.MEDNEXUS_CLINICAL,
    "research": PolicyProfile.MEDNEXUS_RESEARCH,
    "strict_privacy": PolicyProfile.MEDNEXUS_STRICT_PRIVACY,
}


def resolve_policy_profile(value: PolicyProfile | str) -> PolicyProfile:
    """Resolve canonical profiles and legacy public identifiers."""

    if isinstance(value, PolicyProfile):
        return value
    if not isinstance(value, str):
        raise TypeError("policy must be a PolicyProfile or string identifier.")
    normalized = value.strip().lower()
    if normalized in LEGACY_POLICY_ALIASES:
        return LEGACY_POLICY_ALIASES[normalized]
    return PolicyProfile(normalized)


def _rule(action: PolicyAction, rationale: str) -> PolicyRule:
    return PolicyRule(action=action, rationale=rationale)


def _rules(
    *,
    patient: PolicyAction,
    clinician: PolicyAction,
    identifier: PolicyAction,
    contact: PolicyAction,
    address: PolicyAction,
    dob: PolicyAction,
    encounter_date: PolicyAction,
    organization: PolicyAction,
    location: PolicyAction,
    unknown: PolicyAction,
) -> dict[str, PolicyRule]:
    result: dict[str, PolicyRule] = {}

    for entity_type in (
        CandidateEntityType.PERSON_NAME,
        CandidateEntityType.PATIENT_NAME,
        CandidateEntityType.GUARDIAN_NAME,
        CandidateEntityType.RELATIVE_NAME,
        CandidateEntityType.EMPLOYEE_NAME,
        CandidateEntityType.STUDENT_NAME,
    ):
        result[entity_type.value] = _rule(
            patient,
            "Direct personal identity governed by purpose of use.",
        )

    for entity_type in (
        CandidateEntityType.PHYSICIAN_NAME,
        CandidateEntityType.NURSE_NAME,
    ):
        result[entity_type.value] = _rule(
            clinician,
            "Treating clinician identity; role and specialty remain separate.",
        )

    for entity_type in (
        CandidateEntityType.CIVIL_ID,
        CandidateEntityType.MRN,
        CandidateEntityType.VISIT_NUMBER,
        CandidateEntityType.ACCESSION_NUMBER,
        CandidateEntityType.SPECIMEN_NUMBER,
        CandidateEntityType.LAB_NUMBER,
        CandidateEntityType.DOCUMENT_ID,
        CandidateEntityType.INSURANCE_NUMBER,
        CandidateEntityType.EMPLOYEE_NUMBER,
        CandidateEntityType.STUDENT_NUMBER,
    ):
        result[entity_type.value] = _rule(
            identifier,
            "Direct or operational identifier.",
        )

    for entity_type in (
        CandidateEntityType.PHONE_NUMBER,
        CandidateEntityType.EMAIL,
    ):
        result[entity_type.value] = _rule(
            contact,
            "Direct contact identifier.",
        )

    result.update(
        {
            CandidateEntityType.ADDRESS.value: _rule(
                address,
                "Exact address; future geography levels use distinct keys.",
            ),
            CandidateEntityType.DATE_OF_BIRTH.value: _rule(
                dob,
                "Exact DOB; age derivation is a planned capability.",
            ),
            CandidateEntityType.ADMISSION_DATE.value: _rule(
                encounter_date,
                "Encounter date; genuine shifting is not implemented.",
            ),
            CandidateEntityType.DISCHARGE_DATE.value: _rule(
                encounter_date,
                "Encounter date; genuine shifting is not implemented.",
            ),
            CandidateEntityType.COLLECTION_DATE.value: _rule(
                encounter_date,
                "Clinical event date.",
            ),
            CandidateEntityType.EXAM_DATE.value: _rule(
                encounter_date,
                "Clinical event date.",
            ),
            CandidateEntityType.GENERAL_DATE.value: _rule(
                encounter_date,
                "Unclassified exact date.",
            ),
            CandidateEntityType.ORGANIZATION.value: _rule(
                organization,
                "Facility identity; coding remains a planned extension.",
            ),
            CandidateEntityType.LOCATION.value: _rule(
                location,
                "Generic location; future geography levels use distinct keys.",
            ),
            CandidateEntityType.PROFESSIONAL_ROLE.value: _rule(
                PolicyAction.KEEP,
                "Non-identifying professional role with analytical value.",
            ),
            CandidateEntityType.UNKNOWN.value: _rule(
                unknown,
                "Unresolved possible identifier.",
            ),
        }
    )
    return result


POLICY_DEFINITIONS = {
    PolicyProfile.MEDNEXUS_CLINICAL: PolicyDefinition(
        profile_id=PolicyProfile.MEDNEXUS_CLINICAL.value,
        display_name="MedNexus Clinical",
        intended_use="Clinical care and authorized operational workflows.",
        privacy_level="balanced",
        analytical_utility="maximum clinical utility",
        selection_guidance=(
            "Choose for authorized clinical use where treating-team and "
            "operational context must remain usable."
        ),
        rules=_rules(
            patient=PolicyAction.REPLACE,
            clinician=PolicyAction.KEEP,
            identifier=PolicyAction.HASH,
            contact=PolicyAction.REPLACE,
            address=PolicyAction.REPLACE,
            dob=PolicyAction.KEEP,
            encounter_date=PolicyAction.KEEP,
            organization=PolicyAction.KEEP,
            location=PolicyAction.KEEP,
            unknown=PolicyAction.MASK,
        ),
    ),
    PolicyProfile.MEDNEXUS_RESEARCH: PolicyDefinition(
        profile_id=PolicyProfile.MEDNEXUS_RESEARCH.value,
        display_name="MedNexus Research",
        intended_use="Approved research datasets and study workflows.",
        privacy_level="high",
        analytical_utility="high research utility",
        selection_guidance=(
            "Choose for approved research when direct identities and contact "
            "details are unnecessary."
        ),
        rules=_rules(
            patient=PolicyAction.REPLACE,
            clinician=PolicyAction.REMOVE,
            identifier=PolicyAction.HASH,
            contact=PolicyAction.REMOVE,
            address=PolicyAction.REMOVE,
            dob=PolicyAction.REMOVE,
            encounter_date=PolicyAction.REMOVE,
            organization=PolicyAction.KEEP,
            location=PolicyAction.KEEP,
            unknown=PolicyAction.REMOVE,
        ),
    ),
    PolicyProfile.MEDNEXUS_ANALYTICS_PUBLIC_HEALTH: PolicyDefinition(
        profile_id=PolicyProfile.MEDNEXUS_ANALYTICS_PUBLIC_HEALTH.value,
        display_name="MedNexus Analytics / Public Health",
        intended_use="Population analytics and public-health surveillance.",
        privacy_level="high",
        analytical_utility="population-level analytical utility",
        selection_guidance=(
            "Choose for analytics where clinical and non-identifying "
            "population attributes are valuable but personal identity is not."
        ),
        rules=_rules(
            patient=PolicyAction.REPLACE,
            clinician=PolicyAction.REMOVE,
            identifier=PolicyAction.HASH,
            contact=PolicyAction.REMOVE,
            address=PolicyAction.REMOVE,
            dob=PolicyAction.REMOVE,
            encounter_date=PolicyAction.REMOVE,
            organization=PolicyAction.KEEP,
            location=PolicyAction.KEEP,
            unknown=PolicyAction.REMOVE,
        ),
    ),
    PolicyProfile.MEDNEXUS_STRICT_PRIVACY: PolicyDefinition(
        profile_id=PolicyProfile.MEDNEXUS_STRICT_PRIVACY.value,
        display_name="MedNexus Strict Privacy",
        intended_use="Maximum-privacy disclosure and external export.",
        privacy_level="maximum",
        analytical_utility="reduced identity and temporal utility",
        selection_guidance=(
            "Choose when minimizing re-identification risk takes precedence "
            "over identity, facility, location, and exact-date utility."
        ),
        rules=_rules(
            patient=PolicyAction.REMOVE,
            clinician=PolicyAction.REMOVE,
            identifier=PolicyAction.REMOVE,
            contact=PolicyAction.REMOVE,
            address=PolicyAction.REMOVE,
            dob=PolicyAction.REMOVE,
            encounter_date=PolicyAction.REMOVE,
            organization=PolicyAction.REMOVE,
            location=PolicyAction.REMOVE,
            unknown=PolicyAction.REMOVE,
        ),
    ),
}


def get_policy_definition(
    profile: PolicyProfile | str,
) -> PolicyDefinition:
    return POLICY_DEFINITIONS[resolve_policy_profile(profile)]


# Compatibility view for components that still inspect action-only rules.
POLICY_RULES = {
    profile: {
        CandidateEntityType(target): rule.action
        for target, rule in definition.rules.items()
    }
    for profile, definition in POLICY_DEFINITIONS.items()
}
