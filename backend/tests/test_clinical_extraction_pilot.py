import hashlib
from types import SimpleNamespace
import pytest

from backend.app.modules.medical_document_intelligence.services.clinical_extraction import (
    ClinicalExtractionService, align_entity, protected_sections,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import JourneyStore, JourneyDocument, JourneyStage, StageStatus


def entity(tokens, start=0, end=0, label="Observation::definitely present", relations=None):
    return dict(tokens=tokens, start_ix=start, end_ix=end, label=label, relations=relations or [])


class Adapter:
    def __init__(self, results):
        self.results = results
        self.received = None

    def extract(self, sections):
        self.received = sections
        return dict(sections=self.results, engine_metadata={"engine": "RadGraph-XL"}, timing={})


def synth(texts, roles, raws):
    text = "\n".join(texts)
    offset = 0
    sections = []
    for i, (part, role) in enumerate(zip(texts, roles)):
        sections.append(dict(section_id=str(i), text=part, role=role, heading=None, start=offset, end=offset+len(part)))
        offset += len(part)+1
    return ClinicalExtractionService(Adapter(raws)).extract(protected_text=text, sections=sections,
        report_id="report", run_id="run", protected_document={"output_version": "1", "selected_policy_id": "test"})


@pytest.mark.parametrize("suffix,expected", [("definitely present", "PRESENT"), ("definitely absent", "ABSENT_NEGATED"), ("uncertain", "UNCERTAIN")])
def test_assertion_mapping(suffix, expected):
    result=synth(["effusion"], ["DIAGNOSTIC_SUMMARY"], [{"text":"effusion", "entities":{"1":entity("effusion",label="Observation::"+suffix)}}])
    assert result["radiology_findings"][0]["assertion_state"] == expected
    assert result["radiology_findings"][0]["clinical_salience"] == "PRIMARY"
    assert "entities" not in result


def test_anatomy_is_attribute_not_finding():
    raw={"text":"pleural effusion", "entities":{"1":entity("pleural",label="Anatomy::definitely present"), "2":entity("effusion",1,1,relations=[["located_at","1"]])}}
    result=synth([raw["text"]],["FINDINGS_DESCRIPTION"],[raw])
    assert len(result["radiology_findings"]) == 1
    assert result["radiology_findings"][0]["anatomic_site"] == "pleural"
    assert result["radiology_findings"][0]["clinical_salience"] == "SECONDARY"


@pytest.mark.parametrize("role", ["CLINICAL_CONTEXT", "COMPARISON"])
def test_role_firewall(role):
    result=synth(["effusion"],[role],[{"text":"effusion","entities":{"1":entity("effusion")}}])
    assert not result["radiology_findings"]
    assert bool(result["clinical_context_facts"]) == (role == "CLINICAL_CONTEXT")


def test_temporal_firewall_inside_findings():
    text="Previously seen effusion has resolved."
    result=synth([text],["FINDINGS_DESCRIPTION"],[{"text":text,"entities":{"1":entity("effusion",2,2)}}])
    assert not result["radiology_findings"]
    assert result["review_candidates"][0]["reason"] == "TEMPORAL_OR_CONDITIONAL_REVIEW"


def test_exact_alignment_and_repeated_words():
    section={"text":"effusion, no effusion.", "start":10}
    raw={"text":"effusion , no effusion ."}
    anchor=align_entity(section,raw,entity("effusion",3,3))
    assert anchor == {"start_offset":23,"end_offset":31,"quote":"effusion"}
    assert align_entity(section,{"text":"unknown effusion"},entity("effusion",1,1)) is None


def test_bad_alignment_is_review_only():
    result=synth(["effusion"],["DIAGNOSTIC_SUMMARY"],[{"text":"invented effusion","entities":{"1":entity("effusion",1,1)}}])
    assert not result["radiology_findings"]
    assert "source_start" not in result["review_candidates"][0]


@pytest.mark.parametrize("different", [False, True])
def test_summary_detail_merge_and_unsafe_merge(different):
    labels=["Observation::definitely present", "Observation::definitely absent" if different else "Observation::definitely present"]
    raws=[{"text":"effusion","entities":{"1":entity("effusion",label=label)}} for label in labels]
    result=synth(["effusion","effusion"],["DIAGNOSTIC_SUMMARY","FINDINGS_DESCRIPTION"],raws)
    assert len(result["radiology_findings"]) == (2 if different else 1)
    if different:
        assert all(f["internal_report_conflict"] for f in result["radiology_findings"])
    else:
        assert len(result["radiology_findings"][0]["evidence_anchors"]) == 2


@pytest.mark.parametrize("explicit", [True, False])
def test_suggestive_relation_requires_source_cue(explicit):
    text="opacity suggests pneumonia" if explicit else "opacity and pneumonia"
    raw={"text":text,"entities":{"1":entity("opacity",relations=[["suggestive_of","2"]]),"2":entity("pneumonia",2,2)}}
    result=synth([text],["DIAGNOSTIC_SUMMARY"],[raw])
    assert len(result["radiology_finding_relationships"]) == int(explicit)


@pytest.mark.parametrize("ambiguous", [False, True])
def test_measurement_ownership(ambiguous):
    text="mass 28 mm and edema" if ambiguous else "mass 28 mm"
    entities={"1":entity("mass")}
    if ambiguous: entities["2"]=entity("edema",4,4)
    result=synth([text],["FINDINGS_DESCRIPTION"],[{"text":text,"entities":entities}])
    assert len(result["measurements"]) == (0 if ambiguous else 1)


def make_store(status="COMPLETE", domain="RADIOLOGY", source_type="txt", safe=True):
    store=JourneyStore()
    run=store.create_run("SINGLE")
    original="Patient: Identified Person\neffusion"
    protected="Patient: [PATIENT_NAME]\neffusion"
    region=SimpleNamespace(region_id="clinical",role="OBSERVATION_NARRATIVE",start=original.index("effusion"),end=len(original))
    context=SimpleNamespace(identity=SimpleNamespace(healthcare_domain=domain),semantic_regions=[region])
    item=JourneyDocument(document_id="report", original_filename="test.txt",order=0,source_type=source_type,
        document=SimpleNamespace(text=original),context=context)
    item.stage_status[JourneyStage.PROTECT]=StageStatus(status)
    item.stage_results[JourneyStage.PROTECT]={"protection_result":{"status":status},"protected_document":{
        "report_id":"report","protected_text":protected,"integrity_sha256":hashlib.sha256(protected.encode()).hexdigest() if safe else "bad",
        "output_version":"1","selected_policy_id":"test"}}
    run.documents.append(item)
    return store,run,item


@pytest.mark.parametrize("status", ["COMPLETE","NEEDS_REVIEW"])
def test_protected_only_safe_review_can_proceed_and_stage_ownership(status):
    store,run,item=make_store(status)
    adapter=Adapter([{"text":"effusion","entities":{"1":entity("effusion")}}])
    store.extract_document(run.run_id,"report",ClinicalExtractionService(adapter))
    assert adapter.received[0]["text"] == "effusion"
    assert "Identified Person" not in str(adapter.received)
    assert [e["status"] for e in item.stage_history if e["stage"]=="EXTRACT"] == ["PROCESSING","NEEDS_REVIEW"]
    result=item.stage_results[JourneyStage.EXTRACT]
    assert result["report_id"] == "report" and result["journey_run_id"] == run.run_id
    for fact in result["radiology_findings"]:
        for a in fact["evidence_anchors"]:
            assert item.stage_results[JourneyStage.PROTECT]["protected_document"]["protected_text"][a["start_offset"]:a["end_offset"]] == a["quote"]


@pytest.mark.parametrize("kwargs", [{"status":"BLOCKED"},{"safe":False},{"domain":"LABORATORY"},{"source_type":"pdf"}])
def test_unsafe_or_ineligible_blocks(kwargs):
    store,run,item=make_store(**kwargs)
    adapter=Adapter([])
    with pytest.raises(ValueError): store.extract_document(run.run_id,"report",ClinicalExtractionService(adapter))
    assert adapter.received is None
    assert item.stage_status[JourneyStage.EXTRACT] == StageStatus.BLOCKED


def test_report_cannot_cross_runs():
    store,run,item=make_store()
    other=store.create_run("SINGLE")
    with pytest.raises(LookupError): store.extract_document(other.run_id,"report")


def test_understand_roles_reused_technique_not_sent():
    regions=[SimpleNamespace(region_id="tech",role="TECHNIQUE_OR_ACQUISITION",start=0,end=8)]
    sections,_=protected_sections("CT scan.","CT scan.",SimpleNamespace(semantic_regions=regions))
    assert sections == []


def test_pdf_linewrap_does_not_break_measurement_evidence():
    text="A mass measures\n26 mm x 23 mm."
    result=synth([text],["FINDINGS_DESCRIPTION"],[{"text":"A mass measures 26 mm x 23 mm .","entities":{"1":entity("mass",1,1)}}])
    assert [m["source_value"] for m in result["measurements"]] == ["26 mm x 23 mm"]
    assert result["radiology_findings"][0]["evidence_anchors"][0]["quote"] == text


def test_protected_history_without_engine_entity_stays_context_not_current_finding():
    history = "CLINICAL HISTORY: Dysphagia with aspiration."
    impression = "Impression: Pharyngeal dyskinesia with absent relaxation."
    output = synth([history, impression], ["CLINICAL_CONTEXT", "DIAGNOSTIC_SUMMARY"], [
        {"text": history, "entities": {}},
        {"text": impression, "entities": {"1": entity("dyskinesia", 2, 2)}},
    ])
    assert output["clinical_synthesis"]["canonical_facts"]
    assert all("Dysphagia" not in fact["display_label"] for fact in output["clinical_synthesis"]["canonical_facts"])
    context = output["clinical_context_facts"][0]
    assert context["context_concept"]["display"] == "Dysphagia with aspiration"
    anchor = context["evidence_anchors"][0]
    protected = history + "\n" + impression
    assert protected[anchor["start_offset"]:anchor["end_offset"]] == anchor["quote"]


def test_protected_clinical_details_heading_is_context_when_region_classifier_misses_it():
    context = "Clinical Details: Sports injury"
    finding = "A complex capsular rupture is seen."
    output = synth([context, finding], ["OTHER", "FINDINGS_DESCRIPTION"], [
        {"text": context, "entities": {}},
        {"text": finding, "entities": {"1": entity("rupture", 3, 3)}},
    ])
    assert len(output["clinical_synthesis"]["canonical_facts"]) == 1
    assert all("Sports injury" not in fact["display_label"]
               for fact in output["clinical_synthesis"]["canonical_facts"])
    assert [fact["context_concept"]["display"] for fact in output["clinical_context_facts"]] == ["Sports injury"]
    anchor = output["clinical_context_facts"][0]["evidence_anchors"][0]
    protected = context + "\n" + finding
    assert protected[anchor["start_offset"]:anchor["end_offset"]] == anchor["quote"]
