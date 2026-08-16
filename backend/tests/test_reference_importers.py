import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.modules.medical_document_intelligence.understanding.reference_model.importers import (
    ArtifactError, DicomDcmrImporter, DicomPart6Importer, LoincRsnaImporter, RadLexOwlImporter, SnomedRf2Importer,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model.cli import main as reference_cli
from backend.app.modules.medical_document_intelligence.understanding.reference_model.models import ConceptFamily
from backend.app.modules.medical_document_intelligence.understanding.reference_model.registry import load_reference_sources
from backend.app.modules.medical_document_intelligence.understanding.reference_model.runtime import build_active_reference_registry
from backend.app.modules.medical_document_intelligence.understanding.reference_model.store import ReferenceDataStore, merge_concepts, sha256_file


def source(source_id):
    return next(item for item in load_reference_sources() if item.source_id == source_id)


def test_loinc_playbook_parser_preserves_attributes_and_external_code(tmp_path):
    csv = tmp_path / "LoincRsnaRadiologyPlaybook.csv"
    csv.write_text("LOINC_NUM,LONG_COMMON_NAME,Modality,Anatomic Location,Contrast\n24627-2,CT Chest with contrast,CT,Chest,With contrast\n", encoding="utf-8")
    concepts = LoincRsnaImporter().import_artifact(source("LOINC_RSNA_2_82"), csv)
    assert concepts[0].external_mappings[0].external_id == "24627-2"
    assert concepts[0].concept_family is ConceptFamily.IMAGING_PROCEDURE
    assert ("record_type", "RADIOLOGY_PROCEDURE") in concepts[0].attributes


def test_loinc_complete_zip_preserves_composition_crosswalks_and_documents(tmp_path):
    package = tmp_path / "Loinc_2.82.zip"
    playbook = (
        "LoincNumber,LongCommonName,PartNumber,PartTypeName,PartName,PartSequenceOrder,RID,PreferredName,RPID,LongName\n"
        "24627-2,CT Chest Report,LP100,MODALITY,CT,1,RID10321,computed tomography,RPID24,CT Chest\n"
        "24627-2,CT Chest Report,LP200,REGION_IMAGED,Chest,2,RID1243,chest,RPID24,CT Chest\n"
    )
    parts = (
        "PartNumber,PartTypeName,PartName,PartDisplayName,Status\n"
        "LP100,MODALITY,Computed tomography,CT,ACTIVE\n"
        "LP200,REGION_IMAGED,Chest,Chest,ACTIVE\n"
        "LP300,Document.TypeOfService,Radiology,Radiology service,ACTIVE\n"
    )
    related = "PartNumber,PartName,PartTypeName,ExtCodeId,ExtCodeDisplayName,ExtCodeSystem,Equivalence,ContentOrigin,ExtCodeSystemVersion,ExtCodeSystemCopyrightNotice\nLP100,Computed tomography,MODALITY,RID10321,computed tomography,http://www.radlex.org,Equivalent,LN,4.3,\n"
    docs = "LoincNumber,PartNumber,PartTypeName,PartSequenceOrder,PartName\n24627-2,LP300,Document.TypeOfService,1,Radiology\n"
    imaging = "LOINC_NUM,LONG_COMMON_NAME\n24627-2,CT Chest Report\n"
    loinc = "LOINC_NUM,LONG_COMMON_NAME\n24627-2,CT Chest Report\n"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("AccessoryFiles/LoincRsnaRadiologyPlaybook/LoincRsnaRadiologyPlaybook.csv", playbook)
        archive.writestr("AccessoryFiles/PartFile/Part.csv", parts)
        archive.writestr("AccessoryFiles/PartFile/PartRelatedCodeMapping.csv", related)
        archive.writestr("AccessoryFiles/DocumentOntology/DocumentOntology.csv", docs)
        archive.writestr("AccessoryFiles/ImagingDocuments/ImagingDocumentCodes.csv", imaging)
        archive.writestr("LoincTable/Loinc.csv", loinc)
    concepts = LoincRsnaImporter().import_artifact(source("LOINC_RSNA_2_82"), package)
    procedure = next(item for item in concepts if item.concept_family is ConceptFamily.IMAGING_PROCEDURE)
    assert [item.sequence_order for item in procedure.relationships] == ["1", "2"]
    assert {item.external_id for item in procedure.external_mappings} >= {"24627-2", "RID10321", "RPID24"}
    assert any(dict(item.attributes).get("record_type") == "IMAGING_DOCUMENT" for item in concepts)
    modality = next(item for item in concepts if item.concept_family is ConceptFamily.IMAGING_MODALITY)
    assert modality.canonical_name == "Computed tomography"
    assert modality.synonyms == ("CT",)
    assert any(item.source_id == "RADLEX_CURRENT" and item.external_id == "RID10321" for item in modality.external_mappings)
    document = next(item for item in concepts if dict(item.attributes).get("record_type") == "IMAGING_DOCUMENT")
    assert document.relationships[0].sequence_order == "1"
    assert document.relationships[0].target_external_id == "LP300"


def test_dicom_docbook_parser_selects_relevant_attributes(tmp_path):
    xml = tmp_path / "part06.xml"
    xml.write_text("""<book xmlns='http://docbook.org/ns/docbook'><table><tbody><tr>
      <td><para>(0008,0060)</para></td><td><para>Modality</para></td><td><para>Modality</para></td>
      <td><para>CS</para></td><td><para>1</para></td></tr></tbody></table></book>""", encoding="utf-8")
    concepts = DicomPart6Importer().import_artifact(source("DICOM_2026_CURRENT"), xml)
    assert concepts[0].external_mappings[0].external_id == "(0008,0060)"
    assert concepts[0].attributes == (("record_type", "PS3.6"), ("keyword", "Modality"), ("vr", "CS"), ("vm", "1"))


def test_dcmr_parser_preserves_cid_and_inactive_external_code_system(tmp_path):
    xml = tmp_path / "part16.xml"
    xml.write_text("""<book xmlns='http://docbook.org/ns/docbook'><section xml:id='sect_CID_4' xmlns:xml='http://www.w3.org/XML/1998/namespace'><title>Anatomic Region</title><table><tbody><tr><td>SCT</td><td>80891009</td><td>Heart</td></tr></tbody></table></section></book>""", encoding="utf-8")
    concepts = DicomDcmrImporter().import_artifact(source("DICOM_DCMR_2026C"), xml)
    member = next(item for item in concepts if dict(item.attributes).get("record_type") == "DCMR_CODE")
    assert member.external_mappings[0].source_id == "SNOMED_INT_20260701"
    assert member.relationships[0].target_external_id == "CID:4"


def test_radlex_owl_parser_preserves_synonyms_and_hierarchy(tmp_path):
    owl = tmp_path / "PunRadLex4.3.owl"
    owl.write_text("""<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' xmlns:owl='http://www.w3.org/2002/07/owl#' xmlns:rdfs='http://www.w3.org/2000/01/rdf-schema#'>
      <owl:Class rdf:about='http://radlex.org/RID10321'><rdfs:label>computed tomography imaging</rdfs:label><rdfs:label>CT imaging</rdfs:label><rdfs:subClassOf rdf:resource='http://radlex.org/RID10311'/></owl:Class></rdf:RDF>""", encoding="utf-8")
    (tmp_path / "Radlex.csv").write_text(
        "Class ID,Preferred Label,Synonyms,Definitions,Obsolete,Semantic Types,Parents\n"
        "http://radlex.org/RID10321,computed tomography imaging,CT imaging,CT procedure,false,Diagnostic Procedure,http://radlex.org/RID10311\n",
        encoding="utf-8",
    )
    concepts = RadLexOwlImporter().import_artifact(source("RADLEX_CURRENT"), tmp_path)
    assert concepts[0].external_mappings[0].external_id == "RID10321"
    assert concepts[0].synonyms == ("CT imaging",)
    assert concepts[0].relationships[0].target_external_id == "RID10311"


def test_snomed_rf2_requires_subset_and_reads_only_requested_active_concepts(tmp_path):
    rf2 = tmp_path / "sct2_Description_Snapshot-en_INT_20260701.txt"
    rf2.write_text("id\teffectiveTime\tactive\tmoduleId\tconceptId\tlanguageCode\ttypeId\tterm\tcaseSignificanceId\n1\t20260701\t1\t0\t123\ten\t900000000000003001\tStructure of liver (body structure)\t0\n", encoding="utf-8")
    with pytest.raises(ArtifactError): SnomedRf2Importer().import_artifact(source("SNOMED_INT_20260701"), rf2)
    concepts = SnomedRf2Importer().import_artifact(source("SNOMED_INT_20260701"), rf2, subset_ids={"123", "999"})
    assert [item.external_mappings[0].external_id for item in concepts] == ["123"]


def test_store_checksum_activation_runtime_and_version_replacement(tmp_path):
    artifact = tmp_path / "part06.xml"; artifact.write_text("official", encoding="utf-8")
    concept = DicomPart6Importer().import_artifact(source("DICOM_2026_CURRENT"), _dicom_fixture(tmp_path)) [0]
    store = ReferenceDataStore(tmp_path / "reference")
    receipt = store.save_import("DICOM_2026_CURRENT", "2026c", artifact, (concept,))
    assert receipt["checksum"] == sha256_file(artifact)
    store.activate("DICOM_2026_CURRENT", "2026c")
    assert store.verify("DICOM_2026_CURRENT", "2026c")["checksum_valid"] is True
    registry = build_active_reference_registry(store)
    assert registry.resolve("Modality")[0].concept.provenance == ("DICOM_2026_CURRENT",)
    assert registry.active_configuration == {"DICOM_2026_CURRENT": "2026c", "MNX_RAD_REF_V1": "1.0"}
    store.save_import("DICOM_2026_CURRENT", "2026d", artifact, (replace(concept, canonical_name="Modality field"),))
    store.activate("DICOM_2026_CURRENT", "2026d")
    assert store.active_configuration()["DICOM_2026_CURRENT"] == "2026d"


def test_cli_can_verify_imported_expected_version_before_activation(tmp_path, monkeypatch, capsys):
    root = tmp_path / "reference"
    artifact = tmp_path / "Loinc_2.82.zip"
    artifact.write_bytes(b"official")
    ReferenceDataStore(root).save_import("LOINC_RSNA_2_82", "2.82", artifact, ())
    monkeypatch.setenv("MEDNEXUS_REFERENCE_DATA_DIR", str(root))
    assert reference_cli(["verify", "loinc"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["checksum_valid"] is True


def test_exact_cross_source_dedup_retains_both_authoritative_mappings(tmp_path):
    dicom = DicomPart6Importer().import_artifact(source("DICOM_2026_CURRENT"), _dicom_fixture(tmp_path))[0]
    other = replace(dicom, mednexus_concept_id="OTHER", external_mappings=(), provenance=("MNX_RAD_REF_V1",))
    merged = merge_concepts((dicom, other))
    assert len(merged) == 1
    assert set(merged[0].provenance) == {"DICOM_2026_CURRENT", "MNX_RAD_REF_V1"}


def test_dedup_does_not_collapse_same_term_across_distinct_families(tmp_path):
    concept = DicomPart6Importer().import_artifact(source("DICOM_2026_CURRENT"), _dicom_fixture(tmp_path))[0]
    other = replace(concept, mednexus_concept_id="OTHER", concept_family=ConceptFamily.DOCUMENT_REPORT)
    assert len(merge_concepts((concept, other))) == 2


def test_malformed_artifacts_fail_clearly(tmp_path):
    bad = tmp_path / "bad.xml"; bad.write_text("<bad", encoding="utf-8")
    with pytest.raises(ArtifactError, match="Malformed"):
        DicomPart6Importer().import_artifact(source("DICOM_2026_CURRENT"), bad)


def _dicom_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "dicom.xml"
    path.write_text("<book><tr><td>(0008,0060)</td><td>Modality</td><td>Modality</td><td>CS</td><td>1</td></tr></book>", encoding="utf-8")
    return path
