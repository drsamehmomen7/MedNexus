from pathlib import Path

from backend.app.modules.medical_document_intelligence.understanding.document_classifier import DocumentClassifier
from backend.app.modules.medical_document_intelligence.understanding.models import (
    DocumentDomain, DocumentNature, DocumentSubtype, DocumentType,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model import (
    ConceptFamily, DistributionPolicy, RADIOLOGY_REFERENCE_MODEL, RelationshipType,
    build_default_reference_registry,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model.normalization import normalize_reference_term
from backend.app.modules.medical_document_intelligence.understanding.reference_model.provenance import configuration_snapshot


def test_manifest_registry_exposes_versions_and_distribution_governance():
    registry = build_default_reference_registry()
    assert registry.source("LOINC_RSNA_2_82").version == "2.82"
    assert registry.source("DICOM_2026_CURRENT").version == "2026c"
    assert registry.source("DICOM_DCMR_2026C").enabled is False
    assert registry.source("RADLEX_CURRENT").distribution_policy is DistributionPolicy.EXTERNAL_DOWNLOAD_REQUIRED
    assert registry.source("SNOMED_INT_20260701").distribution_policy is DistributionPolicy.LICENSE_RESTRICTED
    assert registry.active_configuration == {"MNX_RAD_REF_V1": "1.0"}
    assert configuration_snapshot(registry)["active"] == {"MNX_RAD_REF_V1": "1.0"}


def test_canonical_ids_crosswalk_multiple_sources_without_external_primary_key():
    concept = RADIOLOGY_REFERENCE_MODEL.concept("RAD_MODALITY_MRI")
    assert concept.mednexus_concept_id == "RAD_MODALITY_MRI"
    assert concept.concept_family is ConceptFamily.IMAGING_MODALITY
    assert {(item.source_id, item.external_id) for item in concept.external_mappings} == {
        ("DICOM_2026_CURRENT", "MR")
    }
    assert {item.relationship_type for item in concept.relationships} == {RelationshipType.IS_A}
    assert {"LOINC_RSNA_2_82", "DICOM_2026_CURRENT", "RADLEX_CURRENT"} < set(concept.provenance)


def test_reference_normalization_and_resolution_are_deterministic():
    assert normalize_reference_term("  T1–WEIGHTED  ") == "t1 weighted"
    resolved = RADIOLOGY_REFERENCE_MODEL.resolve("Magnetic Resonance")
    assert resolved[0].concept.mednexus_concept_id == "RAD_MODALITY_MRI"


def test_relationships_support_modality_technique_coherence():
    dwi = RADIOLOGY_REFERENCE_MODEL.concept("RAD_TECH_DWI")
    assert any(item.relationship_type is RelationshipType.USED_WITH and item.target_concept_id == "RAD_MODALITY_MRI"
               for item in dwi.relationships)


def test_strong_radiology_template_keeps_parent_identity_when_modality_conflicts():
    text = (
        "RADIOLOGY REPORT TEMPLATE\nPROCEDURE INFORMATION: CT MRI liver imaging\n"
        "TECHNIQUE: Select protocol\nFINDINGS: Select applicable option\nIMPRESSION: Select conclusion"
    )
    outcome = DocumentClassifier.classify(text)
    assert outcome.domain is DocumentDomain.RADIOLOGY
    assert outcome.document_type is DocumentType.RADIOLOGY_REPORT
    assert outcome.document_subtype is DocumentSubtype.UNKNOWN
    assert outcome.document_nature is DocumentNature.STRUCTURED_TEMPLATE


def test_reference_manifest_is_machine_readable_and_contains_no_bundled_terminology_archive():
    package = Path(__file__).parents[1] / "app/modules/medical_document_intelligence/understanding/reference_model"
    assert (package / "manifest.json").is_file()
    assert not any(path.suffix.lower() in {".zip", ".owl", ".rf2"} for path in package.rglob("*"))
