"""Offline R3.0A contract tests. All clinical examples are synthetic."""
import copy
from types import SimpleNamespace

import pytest

from backend.app.modules.medical_document_intelligence.services.clinical_standardization import (
    ClinicalStandardizationService, OptionalSnomedProvider, ReferenceTerminologyProvider,
    TerminologyCandidate, normalize_measurement,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model.models import (
    CanonicalConcept, ConceptFamily, ExternalMapping,
)
from backend.app.modules.medical_document_intelligence.understanding.reference_model.registry import (
    ReferenceModelRegistry, load_reference_sources,
)


class Provider:
    def __init__(self, system, entries=None, version="fixture-1", available=True):
        self.system, self.version, self.available = system, version, available
        self.entries = entries or {}

    def get_candidates(self, text):
        return tuple(self.entries.get(text, ()))


def candidate(code, label="Preferred", kind="EXACT_LABEL"):
    return TerminologyCandidate(code, label, kind)


def context(exam="MR Shoulder - left", laterality="LEFT"):
    domain = SimpleNamespace(examination=exam, modality_context=SimpleNamespace(laterality=laterality))
    clinical = SimpleNamespace(examination=exam, modality="MRI", body_region="shoulder", domain_extension=domain)
    return SimpleNamespace(identity=SimpleNamespace(healthcare_domain="RADIOLOGY"), clinical_context=clinical)


def fact(index=1, *, label="labral tear", assertion="PRESENT", hypothesis=None, measures=None, anatomy=None):
    item = {"fact_id": f"canonical-{index}", "display_label": label, "assertion_state": assertion,
            "salience": "PRIMARY", "evidence_anchors": [{"quote": "synthetic evidence", "start_offset": 2}],
            "review_reason": ["EXTRACT_REVIEW"], "relationships": [{"type": "ASSOCIATED_WITH"}],
            "anatomy": anatomy or ["glenoid labrum"],
            "observations": [{"source_context": "synthetic", "measurements": measures or []}]}
    if hypothesis:
        item["hypothesis_status"] = hypothesis
    return item


def extracted(facts):
    return {"report_id": "synthetic-report", "state": "NEEDS_REVIEW",
            "clinical_synthesis": {"canonical_facts": facts}}


def service(concepts=None, anatomy=None, studies=None, available=True):
    return ClinicalStandardizationService(
        concept_provider=Provider("RADLEX_CURRENT", concepts, available=available),
        anatomy_provider=Provider("RADLEX_CURRENT", anatomy, available=available),
        procedure_provider=Provider("LOINC_RSNA_2_82", studies, available=available))


@pytest.mark.parametrize("assertion,hypothesis", [
    ("PRESENT", None), ("ABSENT_NEGATED", None), ("UNCERTAIN", "FAVORED"),
    ("UNCERTAIN", "POSSIBLE"), ("UNCERTAIN", "LESS_LIKELY"),
])
def test_source_fact_meaning_and_evidence_unchanged(assertion, hypothesis):
    source = extracted([fact(assertion=assertion, hypothesis=hypothesis)])
    before = copy.deepcopy(source)
    result = service().standardize(source, context())
    assert source == before
    assert result["standardized_facts"][0]["source_fact_id"] == source["clinical_synthesis"]["canonical_facts"][0]["fact_id"]
    assert len(result["standardized_facts"]) == 1
    assert result["source_extract_state"] == "NEEDS_REVIEW"


def test_exact_label_and_synonym_with_unique_authoritative_code():
    source = extracted([fact(1, label="edema"), fact(2, label="swelling")])
    mapped = service(concepts={"edema": [candidate("RID1", "Edema")],
                               "swelling": [candidate("RID1", "Edema", "EXACT_SYNONYM")]})
    result = mapped.standardize(source, context())
    mappings = [item["concept_mappings"][0] for item in result["standardized_facts"]]
    assert [(item["code"], item["match_type"], item["mapping_status"]) for item in mappings] == [
        ("RID1", "EXACT_LABEL", "MATCHED"), ("RID1", "EXACT_SYNONYM", "MATCHED")]
    assert mappings[0]["terminology_version"] == "fixture-1"
    assert mappings[0]["mapping_method"] == "LOCAL_REFERENCE_EXACT"


def test_ambiguous_and_related_candidates_require_review():
    mapped = service(concepts={"tear": [candidate("RID1"), candidate("RID2")],
                               "injury": [candidate("RID3", kind="RELATED")]})
    result = mapped.standardize(extracted([fact(1, label="tear"), fact(2, label="injury")]), context())
    mappings = [item["concept_mappings"][0] for item in result["standardized_facts"]]
    assert all(item["mapping_status"] == "NEEDS_REVIEW" and item["code"] is None for item in mappings)
    assert len(mappings[0]["candidate_mappings"]) == 2
    assert result["state"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("kind", ["BROADER", "NARROWER", "RELATED", "AMBIGUOUS"])
def test_non_equivalent_candidate_never_authoritative(kind):
    result = service(concepts={"tear": [candidate("RID1", kind=kind)]}).standardize(
        extracted([fact(label="tear")]), context())
    assert result["standardized_facts"][0]["concept_mappings"][0]["code"] is None


def test_unmapped_and_unavailable_are_successful_without_fabricated_code():
    for mapped in (service(), service(available=False)):
        result = mapped.standardize(extracted([fact()]), context())
        mapping = result["standardized_facts"][0]["concept_mappings"][0]
        assert result["state"] == "COMPLETE"
        assert mapping["mapping_status"] == "UNMAPPED" and mapping["code"] is None
        assert result["summary"]["clinical_concepts"]["unmapped"] == 1
    assert "RADLEX_CURRENT" in service(available=False).standardize(extracted([fact()]), context())["technical_diagnostics"]["provider_unavailable"]


def test_anatomy_and_study_identity_are_independent_of_finding_mapping():
    mapped = service(anatomy={"glenoid labrum": [candidate("RID-ANATOMY", "Glenoid labrum")]},
                     studies={"MR Shoulder - left": [candidate("12345-6", "MR Shoulder - left")]})
    result = mapped.standardize(extracted([fact()]), context())
    standardized = result["standardized_facts"][0]
    assert standardized["concept_mappings"][0]["mapping_status"] == "UNMAPPED"
    assert standardized["anatomy_mappings"][0]["code"] == "RID-ANATOMY"
    assert result["standardized_study_context"]["procedure_mapping"]["code"] == "12345-6"
    assert result["standardized_study_context"]["normalized_laterality"] == "LEFT"
    assert standardized["concept_mappings"][0]["code"] is None


@pytest.mark.parametrize("original,normalized,unit,converted", [
    ("1.4 cm", "14", "cm", True), ("4 mm", "4", "mm", False),
    ("0.04 CM", "0.4", "CM", True), ("1.230 cm", "12.3", "cm", True),
])
def test_safe_precise_length_normalization(original, normalized, unit, converted):
    value = normalize_measurement(original, "source-1")
    assert (value["normalized_value"], value["normalized_unit"], value["conversion_applied"]) == (normalized, "mm", converted)
    assert value["original_text"] == original and value["original_unit"] == unit
    assert value["mapping_status"] == "MATCHED"


@pytest.mark.parametrize("original,status", [
    ("1.4", "NEEDS_REVIEW"), ("approximately 1.4 cm", "NEEDS_REVIEW"),
    ("1.4 kg", "UNMAPPED"), ("1.4 cm x 4 mm", "NEEDS_REVIEW"),
])
def test_missing_ambiguous_or_incompatible_units_are_not_converted(original, status):
    value = normalize_measurement(original, "source-1")
    assert value["mapping_status"] == status
    assert value["normalized_value"] is None
    assert value["original_text"] == original


def test_multiple_source_specific_measurements_remain_separate():
    source = extracted([fact(measures=["1.4 cm", "4 mm"])])
    source["clinical_synthesis"]["canonical_facts"][0]["observations"].append(
        {"source_context": "second acquisition", "measurements": ["3 mm"]})
    before = copy.deepcopy(source)
    output = service().standardize(source, context())
    measurements = output["standardized_facts"][0]["standardized_measurements"]
    assert [item["source_measurement_id"] for item in measurements] == [
        "canonical-1:o0:m0", "canonical-1:o0:m1", "canonical-1:o1:m0"]
    assert [item["normalized_value"] for item in measurements] == ["14", "4", "3"]
    assert source == before


def test_duplicate_or_missing_fact_id_is_contract_failure():
    for facts in ([fact(1), fact(1)], [{**fact(), "fact_id": ""}]):
        with pytest.raises(ValueError):
            service().standardize(extracted(facts), context())


def test_reference_provider_uses_only_active_source_backed_equivalent_mappings():
    sources = load_reference_sources()
    official = CanonicalConcept("official", "edema", ConceptFamily.IMAGING_OBSERVATION, "RADIOLOGY",
        ("edema",), ("swelling",), external_mappings=(ExternalMapping("RADLEX_CURRENT", "RID1", "Edema"),),
        provenance=("RADLEX_CURRENT",))
    curated = CanonicalConcept("curated", "tear", ConceptFamily.IMAGING_OBSERVATION, "RADIOLOGY",
        ("tear",), external_mappings=(ExternalMapping("RADLEX_CURRENT", "RID-FAKE", "Tear"),),
        provenance=("MNX_RAD_REF_V1",))
    related = CanonicalConcept("related", "injury", ConceptFamily.IMAGING_OBSERVATION, "RADIOLOGY",
        ("injury",), external_mappings=(ExternalMapping("RADLEX_CURRENT", "RID-RELATED", "Injury", "RELATED"),),
        provenance=("RADLEX_CURRENT",))
    registry = ReferenceModelRegistry(sources, (official, curated, related), {"RADLEX_CURRENT": "4.3"})
    provider = ReferenceTerminologyProvider("RADLEX_CURRENT", {ConceptFamily.IMAGING_OBSERVATION}, registry)
    assert provider.get_candidates("edema")[0].code == "RID1"
    assert provider.get_candidates("Swelling")[0].match_type == "EXACT_SYNONYM"
    assert not provider.get_candidates("tear") and not provider.get_candidates("injury")
    assert provider.version == "4.3"


def test_optional_snomed_absence_and_determinism():
    assert not OptionalSnomedProvider().available
    assert OptionalSnomedProvider().get_candidates("edema") == ()
    source = extracted([fact()])
    mapped = service()
    assert mapped.standardize(source, context()) == mapped.standardize(source, context())


def test_structured_negative_maps_underlying_concept_without_changing_assertion():
    source_fact = {**fact(label="No diverticulum", assertion="ABSENT_NEGATED", anatomy=[]),
                   "canonical_concept": "general:diverticulum", "hypothesis_status": "LESS_LIKELY"}
    original = extracted([source_fact])
    before = copy.deepcopy(original)
    result = service(concepts={"diverticulum": [candidate("RID4817", "diverticulum")]}).standardize(
        original, context())
    item = result["standardized_facts"][0]
    mapping = item["concept_mappings"][0]
    assert (mapping["code"], mapping["mapping_status"], mapping["match_type"]) == (
        "RID4817", "MATCHED", "EXACT_LABEL")
    assert mapping["lookup_text"] == "diverticulum"
    assert item["source_assertion_state"] == "ABSENT_NEGATED"
    assert original == before


@pytest.mark.parametrize("label,key,base,code", [
    ("Partial obstruction", "general:obstruction", "obstruction", "RID4962"),
    ("Vasogenic edema", "vasogenic_edema", "edema", "RID4865"),
    ("Cerebral atrophy", "atrophy", "atrophy", "RID5046"),
    ("No bursal effusion", "general:effusion", "effusion", "RID4872"),
    ("Coracoid process fracture", "general:open:coracoid:fracture:process", "fracture", "RID4650"),
    ("Labral tear", "general:open:labral:tear", "tear", "RID4714"),
])
def test_exact_base_component_is_not_a_whole_fact_equivalence(label, key, base, code):
    original = extracted([{**fact(label=label, assertion="ABSENT_NEGATED" if label.startswith("No ") else "PRESENT"),
                           "canonical_concept": key}])
    before = copy.deepcopy(original)
    result = service(concepts={base: [candidate(code, base)]}).standardize(original, context())
    item = result["standardized_facts"][0]
    whole = item["concept_mappings"][0]
    assert whole["mapping_status"] == "NEEDS_REVIEW" and whole["match_type"] == "BROADER"
    assert whole["code"] is None and whole["review_required"]
    assert [(part["source_text"], part["code"], part["match_type"])
            for part in item["component_mappings"]] == [(base, code, "EXACT_LABEL")]
    assert item["standardization_status"] == "NEEDS_REVIEW"
    assert item["source_assertion_state"] == original["clinical_synthesis"]["canonical_facts"][0]["assertion_state"]
    assert original == before
    assert result["summary"]["whole_fact_exact_mappings"] == 0
    assert result["summary"]["component_exact_mappings"] == 1


def test_existing_anatomy_is_independent_and_provenanced_for_partial_finding():
    original = extracted([{**fact(label="Coracoid process fracture", anatomy=["coracoid process"]),
                           "canonical_concept": "general:open:coracoid:fracture:process"}])
    result = service(concepts={"fracture": [candidate("RID4650", "fracture")]},
                     anatomy={"coracoid process": [candidate("RID1863", "coracoid process")]}).standardize(
                         original, context())
    item = result["standardized_facts"][0]
    assert item["anatomy_mappings"][0]["code"] == "RID1863"
    assert item["anatomy_mappings"][0]["source_fact_id"] == item["source_fact_id"]
    assert item["anatomy_mappings"][0]["terminology_version"] == "fixture-1"
    assert item["concept_mappings"][0]["code"] is None


def test_whole_preferred_label_precedes_synonym_and_components():
    original = extracted([{**fact(label="Vasogenic edema"), "canonical_concept": "vasogenic_edema"}])
    mapped = service(concepts={"Vasogenic edema": [candidate("RID-PREFERRED", kind="EXACT_LABEL"),
                                                     candidate("RID-SYNONYM", kind="EXACT_SYNONYM")],
                               "edema": [candidate("RID-BASE")]})
    result = mapped.standardize(original, context())
    item = result["standardized_facts"][0]
    assert item["concept_mappings"][0]["code"] == "RID-PREFERRED"
    assert item["component_mappings"] == []
    assert result["summary"]["whole_fact_exact_mappings"] == 1


def test_open_concept_uses_only_accepted_identifier_atoms_not_display_words():
    original = extracted([{**fact(label="No invented edema", assertion="ABSENT_NEGATED", anatomy=[]),
                           "canonical_concept": "general:open:invented:process"}])
    result = service(concepts={"edema": [candidate("RID4865")]}).standardize(original, context())
    item = result["standardized_facts"][0]
    assert item["concept_mappings"][0]["mapping_status"] == "UNMAPPED"
    assert item["component_mappings"] == []


@pytest.mark.parametrize("label,key,misleading", [
    ("Mass effect", "mass_effect", "mass"),
    ("Lesion complex", "lesion_complex", "lesion"),
])
def test_ordered_identifier_does_not_promote_nonterminal_token(label, key, misleading):
    original = extracted([{**fact(label=label), "canonical_concept": key}])
    result = service(concepts={misleading: [candidate("RID-WRONG")]}).standardize(original, context())
    item = result["standardized_facts"][0]
    assert item["concept_mappings"][0]["mapping_status"] == "UNMAPPED"
    assert item["component_mappings"] == []


def test_related_and_ambiguous_whole_labels_are_never_promoted_by_components():
    for candidates in ([candidate("RID1", kind="RELATED")],
                       [candidate("RID1"), candidate("RID2")]):
        original = extracted([{**fact(label="Hill-Sachs lesion"),
                               "canonical_concept": "general:open:hill-sachs:lesion"}])
        result = service(concepts={"Hill-Sachs lesion": candidates,
                                   "lesion": [candidate("RID-BASE")]}).standardize(original, context())
        item = result["standardized_facts"][0]
        assert item["concept_mappings"][0]["mapping_status"] == "NEEDS_REVIEW"
        assert item["concept_mappings"][0]["code"] is None
        assert item["component_mappings"] == []


def test_mri_modality_alias_uses_exact_target_without_inventing_anatomy():
    output = service(studies={"MR Extremity": [candidate("69193-1", "MR Extremity")]}).standardize(
        extracted([fact()]), context(exam="MRI Extremity", laterality=None))
    study = output["standardized_study_context"]
    assert study["procedure_mapping"]["code"] == "69193-1"
    assert study["procedure_mapping"]["lookup_text"] == "MR Extremity"
    assert study["normalized_body_region"] == "shoulder"  # carried from fixture context
    assert study["normalized_laterality"] is None
    unresolved = service().standardize(extracted([fact()]), context(exam="MRI Extremity", laterality=None))
    assert unresolved["standardized_study_context"]["procedure_mapping"]["mapping_status"] == "UNMAPPED"


@pytest.mark.parametrize("extract_state", [StageStatus.NOT_STARTED, StageStatus.FAILED, StageStatus.BLOCKED])
def test_journey_requires_completed_extract_and_preserves_original_result(extract_state):
    store = JourneyStore()
    run = store.create_run("SINGLE")
    item = JourneyDocument("report", "synthetic.txt", 0, "txt", context=context())
    item.stage_status[JourneyStage.EXTRACT] = extract_state
    run.documents.append(item)
    with pytest.raises(ValueError):
        store.standardize_document(run.run_id, item.document_id, service())
    assert item.stage_status[JourneyStage.STANDARDIZE] is StageStatus.BLOCKED
    item.stage_status[JourneyStage.EXTRACT] = StageStatus.NEEDS_REVIEW
    source = extracted([fact(measures=["1.4 cm", "4 mm"])])
    item.stage_results[JourneyStage.EXTRACT] = source
    before = copy.deepcopy(source)
    store.standardize_document(run.run_id, item.document_id, service())
    assert item.stage_status[JourneyStage.STANDARDIZE] is StageStatus.COMPLETE
    assert item.stage_results[JourneyStage.EXTRACT] == before
    assert len(item.stage_results[JourneyStage.STANDARDIZE]["standardized_facts"]) == 1


def test_stage_04_http_route_and_prerequisite(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.modules.medical_document_intelligence.api import understanding as api

    store = JourneyStore()
    run = store.create_run("SINGLE")
    item = JourneyDocument("report", "synthetic.txt", 0, "txt", context=context())
    run.documents.append(item)
    monkeypatch.setattr(api, "journey_store", store)
    client = TestClient(app)
    path = f"/api/v1/understanding/journey-runs/{run.run_id}/documents/report/standardize"
    assert client.post(path).status_code == 409
    item.stage_status[JourneyStage.EXTRACT] = StageStatus.NEEDS_REVIEW
    item.stage_results[JourneyStage.EXTRACT] = extracted([fact()])
    response = client.post(path)
    assert response.status_code == 200
    payload = response.json()["documents"][0]
    assert payload["stage_status"]["STANDARDIZE"]["status"] == "COMPLETE"
    assert payload["stage_results"]["STANDARDIZE"]["summary"]["facts_received"] == 1
    assert payload["stage_results"]["EXTRACT"] == item.stage_results[JourneyStage.EXTRACT]
    assert response.headers["Cache-Control"] == "no-store, private"


def test_extract_rerun_invalidates_prior_stage_04_even_when_new_extract_blocks():
    store = JourneyStore()
    run = store.create_run("SINGLE")
    item = JourneyDocument("report", "synthetic.txt", 0, "txt", context=context())
    item.stage_status[JourneyStage.STANDARDIZE] = StageStatus.COMPLETE
    item.stage_results[JourneyStage.STANDARDIZE] = {"state": "COMPLETE"}
    run.documents.append(item)
    with pytest.raises(ValueError):
        store.extract_document(run.run_id, item.document_id)
    assert JourneyStage.STANDARDIZE not in item.stage_results
    assert item.stage_status[JourneyStage.STANDARDIZE] is StageStatus.NOT_STARTED
