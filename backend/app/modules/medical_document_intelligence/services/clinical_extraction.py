"""MRJ-owned protected evidence grounding and conservative Radiology pilot synthesis."""
from difflib import SequenceMatcher
import hashlib
import re
from time import perf_counter

from .radgraph_adapter import RadGraphXLAdapter
from .clinical_synthesis import classify_clause, synthesize

ROLES = {
    "CONCLUSION_OR_STATUS": "DIAGNOSTIC_SUMMARY",
    "OBSERVATION_NARRATIVE": "FINDINGS_DESCRIPTION",
    "CLINICAL_OR_REPORTING_INDICATION": "CLINICAL_CONTEXT",
    "COMPARISON_OR_PRIOR_CONTEXT": "COMPARISON",
    "TECHNIQUE_OR_ACQUISITION": "TECHNIQUE",
    "RECOMMENDATION_OR_FUTURE_ACTION": "RECOMMENDATION",
}
ASSERTIONS = {"definitely present": "PRESENT", "definitely absent": "ABSENT_NEGATED", "uncertain": "UNCERTAIN"}
TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
TEMPORAL = re.compile(r"\b(previous(?:ly)?|prior|resolved|history of|compared|recommend|follow.up|if)\b", re.I)
MEASUREMENT = re.compile(r"\b\d+(?:\.\d+)?(?:\s*(?:mm|cm))?(?:\s*[x×]\s*\d+(?:\.\d+)?(?:\s*(?:mm|cm))?){0,2}\s*(?:mm|cm)\b", re.I)


def protected_sections(original, protected, context):
    """Transport existing UNDERSTAND boundaries, never reclassify sections.

    Source is used only for coordinate transport inside MRJ. Only protected
    slices leave this function. A boundary inside a changed span is rejected.
    """
    blocks = SequenceMatcher(None, original, protected, autojunk=False).get_opcodes()
    def boundary(offset):
        values = set()
        for tag, a, b, c, d in blocks:
            if tag == "equal" and a <= offset <= b:
                values.add(c + offset - a)
            elif a == offset:
                values.add(c)
            elif b == offset:
                values.add(d)
        return next(iter(values)) if len(values) == 1 else None
    sections, review = [], []
    for region in context.semantic_regions:
        role = ROLES.get(getattr(region.role, "value", region.role), "OTHER")
        if role not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION", "CLINICAL_CONTEXT", "COMPARISON"}:
            continue
        start, end = boundary(region.start), boundary(region.end)
        if start is None or end is None or not 0 <= start < end <= len(protected):
            review.append({"reason": "SECTION_ALIGNMENT_UNAVAILABLE", "source_section": role})
            continue
        # Heading is copied only from the protected representation, never raw metadata.
        text = protected[start:end]
        heading = text.split(":", 1)[0] if ":" in text.split("\n", 1)[0] else None
        sections.append({"section_id": region.region_id, "role": role, "heading": heading,
                         "start": start, "end": end, "text": text})
    sections.sort(key=lambda s: ({"DIAGNOSTIC_SUMMARY": 0, "FINDINGS_DESCRIPTION": 1,
                                 "CLINICAL_CONTEXT": 2, "COMPARISON": 3}[s["role"]], s["start"]))
    return sections, review


def align_entity(section, result, entity):
    """Require whole-token-stream equivalence; repeated words stay index-addressed."""
    source_tokens = list(TOKEN.finditer(section["text"]))
    engine_words = result.get("text", "").split()
    engine_tokens = list(TOKEN.finditer(result.get("text", "")))
    if [m.group() for m in source_tokens] != [m.group() for m in engine_tokens]:
        return None
    a, b = entity.get("start_ix"), entity.get("end_ix")
    if not isinstance(a, int) or not isinstance(b, int) or not 0 <= a <= b < len(engine_words):
        return None
    if " ".join(engine_words[a:b + 1]) != entity.get("tokens"):
        return None
    word_matches = list(re.finditer(r"\S+", result["text"]))
    indexes = [i for i, m in enumerate(engine_tokens) if word_matches[a].start() <= m.start() < word_matches[b].end()]
    if not indexes:
        return None
    start, end = source_tokens[indexes[0]].start(), source_tokens[indexes[-1]].end()
    return {"start_offset": section["start"] + start, "end_offset": section["start"] + end,
            "quote": section["text"][start:end]}


def sentence_anchor(section, anchor):
    local_start, local_end = anchor["start_offset"] - section["start"], anchor["end_offset"] - section["start"]
    # Split at sentence punctuation only when followed by whitespace/end; preserve decimals.
    boundaries = [0] + [m.end() for m in re.finditer(r"[.!?](?:\s+|$)", section["text"])] + [len(section["text"])]
    start = max(x for x in boundaries if x <= local_start)
    end = min(x for x in boundaries if x >= local_end)
    while start < end and section["text"][start].isspace():
        start += 1
    return {"start_offset": section["start"] + start, "end_offset": section["start"] + end,
            "quote": section["text"][start:end]}


class ClinicalExtractionService:
    def __init__(self, adapter=None):
        self.adapter = adapter or RadGraphXLAdapter()

    def extract(self, *, protected_text, sections, report_id, run_id, protected_document, initial_review=()):
        started = perf_counter()
        if not sections:
            raise ValueError("No eligible protected clinical sections are available")
        output = self.adapter.extract(sections)
        review = list(initial_review)
        candidates, findings, contexts, relationships, measurements = [], [], [], [], []
        provenance = {"report_id": report_id, "journey_run_id": run_id,
            "source_document_version": protected_document["output_version"],
            "protected_integrity_sha256": hashlib.sha256(protected_text.encode()).hexdigest(),
            "source_representation": "protected_canonical_text", "adapter_version": "1.0-pilot",
            "validator_version": "1.0-pilot", "extraction_profile": "radiology-pilot-1.0",
            "policy_id": protected_document["selected_policy_id"]}
        confidence = {"value": None, "state": "NOT_CALIBRATED"}
        entity_to_fact = {}
        for section, raw in zip(sections, output["sections"]):
            entities = raw.get("entities", {})
            grounded = {key: align_entity(section, raw, value) for key, value in entities.items()}
            for key, entity in entities.items():
                anchor = grounded[key]
                label = entity.get("label", "")
                assertion = ASSERTIONS.get(label.split("::")[-1])
                candidate = {"candidate_id": f'{section["section_id"]}:{key}', "candidate_type": label.split("::")[0],
                    "source_text": anchor["quote"] if anchor else None, "source_section_role": section["role"],
                    "source_section_heading": section["heading"], "source_start": anchor["start_offset"] if anchor else None,
                    "source_end": anchor["end_offset"] if anchor else None, "engine_entity_id": key, "engine_label": label,
                    "assertion_candidate": assertion, "relations": entity.get("relations", []),
                    "engine_name": "RadGraph-XL", "engine_version": "0.1.18", "model_type": "modern-radgraph-xl",
                    "review_state": "NEEDS_REVIEW", "provenance": provenance}
                candidates.append(candidate)
                if not anchor:
                    review.append({"candidate_id": candidate["candidate_id"], "reason": "EXACT_ALIGNMENT_FAILED"})
                    continue
                assert protected_text[anchor["start_offset"]:anchor["end_offset"]] == anchor["quote"]
                if not label.startswith("Observation::"):
                    continue
                evidence = sentence_anchor(section, anchor)
                source_function, _ = classify_clause(anchor["quote"], evidence, section["role"], protected_text)
                reason = None
                if not assertion:
                    reason = "UNSUPPORTED_ASSERTION"
                elif section["role"] == "COMPARISON" and source_function != "COMPARISON_CURRENT_FINDING":
                    reason = "PRIOR_ONLY_COMPARISON_REVIEW"
                elif section["role"] != "CLINICAL_CONTEXT" and source_function != "COMPARISON_CURRENT_FINDING" and TEMPORAL.search(evidence["quote"]):
                    reason = "TEMPORAL_OR_CONDITIONAL_REVIEW"
                elif re.search(r"\[[^]]+\]|\b(?:patient|male|female|years? old)\b", anchor["quote"], re.I) or not re.search(r"[A-Za-z]{2}", anchor["quote"]):
                    reason = "NON_CLINICAL_OR_PROTECTED_PLACEHOLDER"
                elif "::measurement::" in label:
                    reason = "MEASUREMENT_REQUIRES_OWNERSHIP"
                if reason:
                    review.append({"candidate_id": candidate["candidate_id"], "source_text": anchor["quote"], "reason": reason, "evidence_span": evidence})
                    continue
                evidence["role"] = "CONTEXT_SUPPORT" if section["role"] == "CLINICAL_CONTEXT" else "SUMMARY_ASSERTION" if section["role"] == "DIAGNOSTIC_SUMMARY" else "DETAIL_SUPPORT"
                evidence["source_section"] = section["role"]
                common = {"assertion_state": assertion, "source_section": section["role"], "evidence_span": anchor,
                    "evidence_anchors": [evidence], "extraction_confidence": confidence,
                    "validation_state": "PARTIAL", "review_state": "NEEDS_REVIEW", "provenance": provenance,
                    "review_reason": "Pilot model assertion requires human clinical acceptance."}
                if section["role"] == "CLINICAL_CONTEXT":
                    contexts.append({**common, "context_fact_id": f"context-{len(contexts)+1}",
                        "context_concept": {"display": anchor["quote"]}, "context_role": "OTHER_CLINICAL_CONTEXT",
                        "semantic_role": "CLINICAL_CONTEXT"})
                    continue
                anatomy = []
                anatomy_anchors = []
                for relation, target in entity.get("relations", []):
                    if relation == "located_at" and target in entities and entities[target].get("label", "").startswith("Anatomy::") and grounded.get(target):
                        anatomy.append(grounded[target]["quote"])
                        anatomy_anchors.append({**grounded[target], "role": "ATTRIBUTE_SUPPORT", "source_section": section["role"]})
                # Pure model modifiers remain review candidates, not independent disease facts.
                if any(r[0] == "modify" for r in entity.get("relations", [])):
                    review.append({"candidate_id": candidate["candidate_id"], "source_text": anchor["quote"], "reason": "MODIFIER_RETAINED_FOR_REVIEW", "evidence_span": anchor})
                    continue
                concept = anchor["quote"]
                match = next((f for f in findings if f["source_expression"].casefold() == concept.casefold()
                    and f["assertion_state"] == assertion and f.get("anatomic_site") == ("; ".join(anatomy) or None)
                    and section["role"] not in f["source_sections"]), None)
                if match:
                    match["evidence_anchors"].extend([evidence, *anatomy_anchors])
                    match["source_sections"].append(section["role"])
                    entity_to_fact[(section["section_id"], key)] = match
                    continue
                fact = {**common, "finding_id": f"finding-{len(findings)+1}", "finding_concept": {"display": concept},
                    "source_expression": concept, "semantic_class": "OTHER_CLINICAL_OBSERVATION",
                    "clinical_salience": "PRIMARY" if section["role"] == "DIAGNOSTIC_SUMMARY" else "SECONDARY",
                    "anatomic_site": "; ".join(anatomy) or None, "source_sections": [section["role"]],
                    "measurements": [], "extraction_method": "EXTERNAL_CANDIDATE_MRJ_VALIDATED"}
                fact["evidence_anchors"].extend(anatomy_anchors)
                if assertion == "ABSENT_NEGATED":
                    fact["evidence_anchors"].append({**evidence, "role": "NEGATION_SUPPORT"})
                for other in findings:
                    if other["source_expression"].casefold() == concept.casefold() and other.get("anatomic_site") == fact["anatomic_site"] and other["assertion_state"] != assertion:
                        conflict = {"summary_assertion": other["assertion_state"], "detail_assertion": assertion}
                        other["internal_report_conflict"] = fact["internal_report_conflict"] = conflict
                        other["review_reason"] = fact["review_reason"] = "INTERNAL_REPORT_CONFLICT"
                        review.append({"reason": "INTERNAL_REPORT_CONFLICT", "source_text": concept})
                findings.append(fact)
                entity_to_fact[(section["section_id"], key)] = fact
            for key, entity in entities.items():
                source = entity_to_fact.get((section["section_id"], key))
                if not source:
                    continue
                for rel, target in entity.get("relations", []):
                    dest = entity_to_fact.get((section["section_id"], target))
                    if rel != "suggestive_of" or not dest or source is dest:
                        continue
                    evidence = sentence_anchor(section, grounded[key])
                    target_anchor = grounded[target]
                    if not (evidence["start_offset"] <= target_anchor["start_offset"] < evidence["end_offset"]) or not re.search(r"\b(?:suggestive of|suggests?|suspicious for|consistent with)\b", evidence["quote"], re.I):
                        review.append({"reason": "RELATION_NOT_EXPLICIT", "candidate_id": f'{section["section_id"]}:{key}'})
                        continue
                    relationships.append({"relationship_id": f"relation-{len(relationships)+1}",
                        "relationship_type": "SUGGESTIVE_OF", "source_fact_id": source["finding_id"],
                        "target_fact_or_attribute_id": dest["finding_id"], "source_finding": source["source_expression"],
                        "target_finding": dest["source_expression"], "relation_origin": "EXPLICIT_SOURCE_RELATION",
                        "evidence_span": {**evidence, "role": "RELATION_SUPPORT"}, "extraction_confidence": confidence,
                        "validation_state": "PARTIAL", "review_state": "NEEDS_REVIEW", "provenance": provenance})
            if section["role"] not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"}:
                continue
            for m in MEASUREMENT.finditer(section["text"]):
                anchor = {"start_offset": section["start"]+m.start(), "end_offset": section["start"]+m.end(), "quote": m.group()}
                sentence = sentence_anchor(section, anchor)
                owners = [f for f in findings if any(a["start_offset"] == sentence["start_offset"] and a["end_offset"] == sentence["end_offset"] for a in f["evidence_anchors"])]
                if len(owners) != 1 or TEMPORAL.search(sentence["quote"]):
                    review.append({"reason": "AMBIGUOUS_MEASUREMENT_OWNERSHIP", "source_text": m.group(), "evidence_span": anchor})
                    continue
                measurement = {"measurement_id": f"measurement-{len(measurements)+1}", "quantity_type": "UNKNOWN",
                    "source_value": m.group(), "source_unit": re.search(r"(?:mm|cm)$", m.group(), re.I).group(),
                    "evidence_span": anchor, "finding_id": owners[0]["finding_id"], "extraction_confidence": confidence,
                    "validation_state": "PARTIAL", "provenance": provenance}
                measurements.append(measurement)
                owners[0]["measurements"].append(measurement)
        result = {"report_id": report_id, "journey_run_id": run_id, "state": "NEEDS_REVIEW",
            "radiology_findings": findings, "clinical_context_facts": contexts, "measurements": measurements,
            "radiology_finding_relationships": relationships, "review_candidates": review,
            "raw_engine_evidence": {"sections": output["sections"], "candidates": candidates},
            "review_reasons": ["PILOT_HUMAN_CLINICAL_ACCEPTANCE_PENDING", "CONFIDENCE_NOT_CALIBRATED", "SEMANTIC_CLASS_FALLBACK"],
            "candidate_count": len(candidates), "validation_state": "PARTIAL", "extraction_profile": "radiology-pilot-1.0",
            "pack_version": "1.0", "extraction_method": "EXTERNAL_CANDIDATE_MRJ_VALIDATED",
            "engine_metadata": output["engine_metadata"], "timing": {**output["timing"], "total_seconds": perf_counter()-started},
            "peak_gpu_memory_bytes": output.get("peak_gpu_memory_bytes"), "provenance": provenance}
        result["clinical_synthesis"] = synthesize(result, protected_text, candidates, sections)
        if not contexts and any(f["canonical_concept"].startswith("general:")
                for f in result["clinical_synthesis"]["canonical_facts"]):
            # When the model emits no Observation in a history region, keep
            # its explicit protected indication as context, never as a
            # confirmed current finding. The source slice remains exact.
            context_sections = [section for section in sections if section["role"] == "CLINICAL_CONTEXT"]
            # A heading can be missed by UNDERSTAND's region classifier. An
            # exact protected heading/value pair remains context only; it is
            # never passed to synthesis as a current finding.
            if not context_sections:
                context_sections = [{"role": "CLINICAL_CONTEXT", "start": 0, "text": protected_text}]
            for section in context_sections:
                if section["role"] != "CLINICAL_CONTEXT":
                    continue
                match = re.search(r"\b(?:clinical\s+(?:history|details)|history|indication)\s*:\s*([^\r\n]+)", section["text"], re.I)
                if not match or not match.group(1).strip():
                    continue
                phrase = match.group(1).strip()
                if (re.search(r"\b(?:patient|male|female|\d+[- ]year[- ]old)\b", phrase, re.I)
                        or re.search(r"\b(?:a|an|the|in|of|with|and|or|but|for|to)\s*$", phrase, re.I)
                        or (len(phrase) > 60 and not re.search(r"[.!?]$", phrase))):
                    continue
                start = section["start"] + match.start(1)
                end = start + len(phrase)
                if protected_text[start:end] != phrase:
                    continue
                anchor = {"start_offset": start, "end_offset": end, "quote": phrase,
                          "role": "CONTEXT_SUPPORT", "source_section": "CLINICAL_CONTEXT"}
                contexts.append({"context_fact_id": f"context-{len(contexts)+1}",
                    "context_concept": {"display": phrase.rstrip(" .")},
                    "context_role": "INDICATION", "semantic_role": "CLINICAL_CONTEXT",
                    "assertion_state": "PRESENT", "evidence_anchors": [anchor],
                    "validation_state": "PARTIAL", "review_state": "NEEDS_REVIEW",
                    "extraction_method": "PROTECTED_SECTION_SOURCE_CONTEXT", "provenance": provenance})
        return result
