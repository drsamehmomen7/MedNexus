"""R2.0C bounded synthesis tests; all report fragments here are invented."""
import copy

import pytest

from backend.app.modules.medical_document_intelligence.services.clinical_synthesis import synthesize


def raw(text, mentions, *, candidate_count=None):
    """Make exactly grounded pilot evidence without invoking a model."""
    findings = []
    for index, (expression, sentence, section, assertion) in enumerate(mentions, 1):
        start = text.index(sentence)
        assert expression.lower() in sentence.lower()
        anchor = {"start_offset": start, "end_offset": start + len(sentence), "quote": sentence,
                  "role": "SUMMARY_ASSERTION" if section == "DIAGNOSTIC_SUMMARY" else "DETAIL_SUPPORT",
                  "source_section": section}
        findings.append({"finding_id": f"finding-{index}", "source_expression": expression,
                         "assertion_state": assertion, "evidence_anchors": [anchor]})
    result = {"radiology_findings": findings, "candidate_count": candidate_count or len(findings)}
    before = copy.deepcopy(result)
    synthesized = synthesize(result, text, [])
    assert result == before, "Synthesis must never mutate raw evidence"
    return synthesized


def facts(output, concept):
    return [item for item in output["canonical_facts"] if item["canonical_concept"] == concept]


def test_compatible_summary_and_detail_merge_with_both_anchors():
    a = "Impression: Vasogenic edema is present."
    b = "Findings: Vasogenic edema surrounds the lesion."
    output = raw(a + "\n" + b, [("edema", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                                  ("edema", b, "FINDINGS_DESCRIPTION", "PRESENT")])
    merged = facts(output, "vasogenic_edema")
    assert len(merged) == 1
    assert {x["section_role"] for x in merged[0]["evidence_anchors"]} == {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"}
    assert merged[0]["salience"] == "ASSOCIATED"


def test_measurement_is_observation_not_fact_and_source_contexts_remain_distinct():
    a = "Non-contrast: a single annular right temporal and parietal lesion measures 26 x 23 mm."
    b = "Post-contrast: 3 adjacent annular enhancing right temporal and parietal lesions measure 13-22 mm."
    text = a + "\n" + b
    output = raw(text, [("lesion", a, "FINDINGS_DESCRIPTION", "PRESENT"),
                        ("lesions", b, "DIAGNOSTIC_SUMMARY", "PRESENT")], candidate_count=41)
    principal = facts(output, "lesion_complex")
    assert len(principal) == 1
    assert output["counts"]["technical_engine_entities"] == 2
    assert output["counts"]["raw_engine_candidates"] == 41
    assert output["counts"]["key_findings"] == 1
    assert len(output["canonical_facts"]) != 41
    contexts = {o["source_context"]: o for o in principal[0]["observations"]}
    assert contexts["NON_CONTRAST"]["count"] == 1
    assert contexts["POST_CONTRAST"]["count"] == 3
    assert "26 x 23 mm" in contexts["NON_CONTRAST"]["measurements"]
    assert "13-22 mm" in contexts["POST_CONTRAST"]["measurements"]
    assert "Multifocal right temporoparietal enhancing lesion complex" == principal[0]["display_label"]


@pytest.mark.parametrize("word", ["process", "problem", "change", "extensive", "adjacent", "persistent", "major"])
def test_generic_noun_or_modifier_is_not_a_clinical_fact(word):
    sentence = f"The report mentions {word}."
    output = raw(sentence, [(word, sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert output["canonical_facts"] == []


def test_diagnostic_hypotheses_are_never_present_findings():
    a = "Metastatic tumor is favored over multifocal abscess."
    b = "Primary brain tumor remains a possible consideration."
    c = "Infarct is less likely."
    output = raw("\n".join((a, b, c)), [
        ("Metastatic tumor", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("abscess", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("Primary brain tumor", b, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("Infarct", c, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    statuses = {f["canonical_concept"]: f["hypothesis_status"] for f in output["canonical_facts"]}
    assert statuses == {"metastatic_tumor": "FAVORED", "multifocal_abscess": "LESS_FAVORED",
                        "primary_brain_tumor": "POSSIBLE", "infarct": "LESS_LIKELY"}
    assert all(f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and f["assertion_state"] == "UNCERTAIN"
               and f["review_required"] for f in output["canonical_facts"])
    assert "Metastatic tumor is favored" in output["clinical_synthesis"]


def test_opposing_assertions_remain_separate_and_targeted_for_review():
    a, b = "Vasogenic edema is present.", "Vasogenic edema is absent."
    output = raw(a + "\n" + b, [("edema", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                                  ("edema", b, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    edema = facts(output, "vasogenic_edema")
    assert len(edema) == 2
    assert all("CONFLICTING_SOURCE_ASSERTION" in f["review_reason"] for f in edema)


def test_optic_disc_equivalence_and_unrelated_calcifications():
    sentences = ["Bilateral optic disc calcifications are present.", "Bilateral optic disc drusen are noted.",
                 "Degenerative left scleral calcification is present.",
                 "Dystrophic right superior oblique tendon calcification is present.",
                 "Vascular atherosclerotic calcifications are present."]
    phrases = ["calcifications", "drusen", "calcification", "calcification", "atherosclerotic"]
    output = raw("\n".join(sentences), [(phrase, sentence, "FINDINGS_DESCRIPTION", "PRESENT")
                                          for phrase, sentence in zip(phrases, sentences)])
    assert len(facts(output, "optic_drusen")) == 1
    assert len(facts(output, "optic_drusen")[0]["evidence_anchors"]) == 2
    for separate in ("scleral_calcification", "tendon_calcification", "atherosclerosis"):
        assert len(facts(output, separate)) == 1


def test_focal_frontal_lesion_stays_separate_from_senescent_white_matter():
    a = "Chronic right frontal white-matter hypoattenuation increased in prominence."
    b = "Mild senescent white-matter changes are present."
    output = raw(a + "\n" + b, [("hypoattenuation", a, "FINDINGS_DESCRIPTION", "PRESENT"),
                                  ("white-matter", b, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(facts(output, "frontal_wm")) == 1
    assert len(facts(output, "senescent_wm")) == 1
    assert facts(output, "frontal_wm")[0]["temporal_change"] == "INCREASED"


def test_no_eligible_fact_preserves_technical_count_without_false_success():
    output = raw("An extensive process.", [("process", "An extensive process.", "FINDINGS_DESCRIPTION", "PRESENT")], candidate_count=41)
    assert output["canonical_facts"] == []
    assert output["clinical_synthesis"] == ""
    assert output["counts"]["technical_engine_entities"] == 1
    assert output["counts"]["raw_engine_candidates"] == 41


def test_grounded_diagnostic_candidate_retains_favored_without_becoming_present():
    sentence = "Metastatic tumor is favored over multifocal abscess."
    candidates = []
    for expression in ("Metastatic tumor", "abscess"):
        start = sentence.index(expression)
        candidates.append({"candidate_id": f"candidate-{start}", "candidate_type": "Observation",
                           "source_text": expression, "source_start": start, "source_end": start + len(expression),
                           "source_section_role": "DIAGNOSTIC_SUMMARY", "assertion_candidate": "UNCERTAIN"})
    result = {"radiology_findings": [], "candidate_count": len(candidates)}
    output = synthesize(result, sentence, candidates)
    assert facts(output, "metastatic_tumor")[0]["hypothesis_status"] == "FAVORED"
    assert facts(output, "multifocal_abscess")[0]["hypothesis_status"] == "LESS_FAVORED"
    assert all(f["assertion_state"] == "UNCERTAIN" for f in output["canonical_facts"])


def test_exact_grounding_can_recover_chronic_focal_candidate_held_by_pilot_firewall():
    sentence = "Chronic right frontal white-matter hypoattenuation has increased in prominence."
    expression = "hypoattenuation"
    start = sentence.index(expression)
    candidate = {"candidate_id": "candidate-focal", "candidate_type": "Observation",
                 "source_text": expression, "source_start": start, "source_end": start + len(expression),
                 "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}
    output = synthesize({"radiology_findings": [], "candidate_count": 1}, sentence, [candidate])
    focal = facts(output, "frontal_wm")
    assert len(focal) == 1
    assert focal[0]["temporal_change"] == "INCREASED"
    assert focal[0]["synthesis_provenance"]["engine_evidence_ids"] == ["candidate-focal"]


def test_source_rule_less_likely_requires_nearby_grounded_candidate():
    sentence = "Multifocal abscess is possible; infarct is less likely."
    start = sentence.index("abscess")
    candidate = {"candidate_id": "candidate-abscess", "candidate_type": "Observation",
                 "source_text": "abscess", "source_start": start, "source_end": start + len("abscess"),
                 "source_section_role": "DIAGNOSTIC_SUMMARY", "assertion_candidate": "UNCERTAIN"}
    section = {"role": "DIAGNOSTIC_SUMMARY", "start": 0, "text": sentence}
    result = {"radiology_findings": [], "candidate_count": 1}
    output = synthesize(result, sentence, [candidate], [section])
    infarct = facts(output, "infarct")
    assert len(infarct) == 1 and infarct[0]["hypothesis_status"] == "LESS_LIKELY"
    assert infarct[0]["synthesis_provenance"]["engine_evidence_ids"] == []
    assert infarct[0]["synthesis_provenance"]["source_rule_evidence_ids"]
    assert not facts(synthesize(result, sentence, [], [section]), "infarct")


def test_compatible_possible_and_less_favored_mentions_are_one_consideration():
    a = "Multifocal abscess is possible."
    b = "Multifocal abscess is less favored."
    output = raw(a + "\n" + b, [("abscess", a, "DIAGNOSTIC_SUMMARY", "UNCERTAIN"),
                                  ("abscess", b, "FINDINGS_DESCRIPTION", "UNCERTAIN")])
    combined = facts(output, "multifocal_abscess")
    assert len(combined) == 1
    assert combined[0]["hypothesis_statuses"] == ["LESS_FAVORED", "POSSIBLE"]
    assert len(combined[0]["evidence_anchors"]) == 2


def test_noncontrast_principal_lesion_can_use_nearby_exactly_grounded_context():
    a = "Non-contrast: an annular right temporal lesion measures 26 x 23 mm."
    b = "Post-contrast: three adjacent annular enhancing right temporal lesions measure 13-22 mm."
    text = a + "\n" + b
    start = text.index("lesion")
    candidate = {"candidate_id": "candidate-noncontrast", "candidate_type": "Observation",
                 "source_text": "lesion", "source_start": start, "source_end": start + 6,
                 "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}
    result = {"radiology_findings": [], "candidate_count": 1}
    output = synthesize(result, text, [candidate])
    principal = facts(output, "lesion_complex")
    assert len(principal) == 1
    observation = next(o for o in principal[0]["observations"] if o["source_context"] == "NON_CONTRAST")
    assert observation["count"] == 1
    assert "26 x 23 mm" in observation["measurements"]


def test_maxillary_sinusitis_is_secondary_not_a_generic_noun():
    sentence = "Chronic maxillary sinusitis is present."
    output = raw(sentence, [("sinusitis", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    sinus = facts(output, "sinus_disease")
    assert len(sinus) == 1
    assert sinus[0]["group"] == "SECONDARY"


def test_temporoparietal_word_is_recognized_and_observations_are_not_repeated():
    sentence = "Three adjacent enhancing right temporoparietal lesions measure 13-22 mm."
    output = raw(sentence, [("lesions", sentence, "FINDINGS_DESCRIPTION", "PRESENT"),
                            ("enhancing", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    principal = facts(output, "lesion_complex")[0]
    assert principal["display_label"] == "Multifocal right temporoparietal enhancing lesion complex"
    assert len(principal["observations"]) == 1


def test_shared_sentence_enhancement_stays_with_lesion_and_abscess_precedes_primary_tumor():
    a = "Enhancing annular lesion with vasogenic edema is present."
    b = "Primary brain tumor is possible."
    c = "Metastatic tumor is favored over multifocal abscess."
    output = raw("\n".join((a, b, c)), [("lesion", a, "FINDINGS_DESCRIPTION", "PRESENT"),
                                         ("edema", a, "FINDINGS_DESCRIPTION", "PRESENT"),
                                         ("Primary brain tumor", b, "DIAGNOSTIC_SUMMARY", "UNCERTAIN"),
                                         ("Metastatic tumor", c, "DIAGNOSTIC_SUMMARY", "UNCERTAIN"),
                                         ("abscess", c, "DIAGNOSTIC_SUMMARY", "UNCERTAIN")])
    assert facts(output, "lesion_complex")[0]["observations"][0]["enhancement"] == "ENHANCING"
    assert all("enhancement" not in obs for obs in facts(output, "vasogenic_edema")[0]["observations"])
    summary = output["clinical_synthesis"]
    assert summary.index("over multifocal abscess") < summary.index("Primary brain tumor")


def test_explicit_maxillary_mucosal_disease_can_use_grounded_anatomy_candidate():
    sentence = "Chronic maxillary sinus inflammatory disease with thickening is present."
    start = sentence.index("sinus")
    candidate = {"candidate_id": "candidate-sinus", "candidate_type": "Anatomy",
                 "source_text": "sinus", "source_start": start, "source_end": start + 5,
                 "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}
    result = {"radiology_findings": [], "candidate_count": 1}
    output = synthesize(result, sentence, [candidate])
    sinus = facts(output, "sinus_disease")
    assert len(sinus) == 1
    assert sinus[0]["temporal_status"] == "CHRONIC"
    assert sinus[0]["synthesis_provenance"]["engine_evidence_ids"] == ["candidate-sinus"]
    assert not facts(synthesize(result, "The maxillary sinus is clear.", [candidate]), "sinus_disease")


def test_acquisition_context_does_not_bleed_from_findings_into_impression():
    finding_sentence = "Post-contrast: three annular right temporal lesions measure 13-22 mm."
    summary_sentence = "An annular right temporal lesion complex remains."
    text = finding_sentence + "\n" + summary_sentence
    findings = []
    for index, (sentence, role) in enumerate(((finding_sentence, "FINDINGS_DESCRIPTION"),
                                               (summary_sentence, "DIAGNOSTIC_SUMMARY")), 1):
        start = text.index(sentence)
        findings.append({"finding_id": f"finding-{index}", "source_expression": "lesion",
                         "assertion_state": "PRESENT", "evidence_anchors": [{"start_offset": start,
                         "end_offset": start + len(sentence), "quote": sentence, "role": "DETAIL_SUPPORT",
                         "source_section": role}]})
    sections = [{"start": 0, "end": len(finding_sentence), "role": "FINDINGS_DESCRIPTION",
                 "text": finding_sentence},
                {"start": len(finding_sentence) + 1, "end": len(text), "role": "DIAGNOSTIC_SUMMARY",
                 "text": summary_sentence}]
    output = synthesize({"radiology_findings": findings, "candidate_count": 2}, text, [], sections)
    observations = facts(output, "lesion_complex")[0]["observations"]
    assert {item["source_context"] for item in observations} == {"POST_CONTRAST", "UNSPECIFIED"}


def test_technique_context_carries_into_findings_and_explicit_enhancement_into_summary():
    technique = "Technique: Without contrast images were acquired. "
    finding = "An annular lesion measures 26 x 23 mm. "
    contrast = "Post-contrast images were acquired. "
    summary = "Three enhancing annular lesions measure 13-22 mm."
    text = technique + finding + contrast + summary
    findings = []
    for index, (sentence, role) in enumerate(((finding.strip(), "FINDINGS_DESCRIPTION"),
                                               (summary, "DIAGNOSTIC_SUMMARY")), 1):
        start = text.index(sentence)
        findings.append({"finding_id": f"finding-{index}", "source_expression": "lesion",
                         "assertion_state": "PRESENT", "evidence_anchors": [{"start_offset": start,
                         "end_offset": start + len(sentence), "quote": sentence, "role": "DETAIL_SUPPORT",
                         "source_section": role}]})
    sections = [{"start": len(technique), "end": len(technique) + len(finding),
                 "role": "FINDINGS_DESCRIPTION", "text": finding},
                {"start": len(technique) + len(finding) + len(contrast), "end": len(text),
                 "role": "DIAGNOSTIC_SUMMARY", "text": summary}]
    output = synthesize({"radiology_findings": findings, "candidate_count": 2}, text, [], sections)
    observations = facts(output, "lesion_complex")[0]["observations"]
    assert {item["source_context"]: item["count"] for item in observations} == {
        "NON_CONTRAST": 1, "POST_CONTRAST": 3}


def test_mass_effect_label_does_not_assert_unsupported_ventricular_effect():
    sentence = "Mass effect is present."
    output = raw(sentence, [("Mass effect", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert facts(output, "mass_effect")[0]["display_label"] == "Mass effect"


def test_comparison_can_qualify_existing_focal_lesion_without_creating_prior_only_fact():
    current = "Right frontal white-matter lesion increased in prominence."
    prior = "A chronic right frontal white-matter lesion was seen previously."
    text = current + "\n" + prior
    candidate_start = text.index("white-matter", len(current))
    candidate = {"candidate_id": "candidate-comparison-wm", "candidate_type": "Anatomy",
                 "source_text": "white-matter", "source_start": candidate_start,
                 "source_end": candidate_start + len("white-matter"),
                 "source_section_role": "COMPARISON", "assertion_candidate": "PRESENT"}
    anchor = {"start_offset": 0, "end_offset": len(current), "quote": current,
              "role": "DETAIL_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}
    result = {"radiology_findings": [{"finding_id": "finding-current", "source_expression": "white-matter",
                                     "assertion_state": "PRESENT", "evidence_anchors": [anchor]}],
              "candidate_count": 1}
    output = synthesize(result, text, [candidate])
    focal = facts(output, "frontal_wm")
    assert len(focal) == 1
    assert focal[0]["display_label"] == "Chronic right frontal white-matter lesion"
    assert {a["source_section"] for a in focal[0]["evidence_anchors"]} == {
        "FINDINGS_DESCRIPTION", "COMPARISON"}
    assert not facts(synthesize({"radiology_findings": [], "candidate_count": 1}, text, [candidate]), "frontal_wm")


def test_impression_condition_and_functional_abnormalities_are_distinct_grounded_facts():
    sentences = [
        "Impression: Pharyngeal dyskinesia with complete absence of relaxation.",
        "This results in partial obstruction with considerable residual in the inlet.",
        "Mild transient penetration into the larynx occurred from the residual.",
        "There is abnormal valvular motion with delayed return.",
        "Mild early spillage from the oral cavity occurred.",
    ]
    mentions = [("dyskinesia", sentences[0], "DIAGNOSTIC_SUMMARY", "PRESENT"),
                ("relaxation", sentences[0], "DIAGNOSTIC_SUMMARY", "ABSENT_NEGATED"),
                ("obstruction", sentences[1], "DIAGNOSTIC_SUMMARY", "PRESENT"),
                ("residual", sentences[1], "DIAGNOSTIC_SUMMARY", "PRESENT"),
                ("penetration", sentences[2], "DIAGNOSTIC_SUMMARY", "PRESENT"),
                ("motion", sentences[3], "DIAGNOSTIC_SUMMARY", "PRESENT"),
                ("spillage", sentences[4], "DIAGNOSTIC_SUMMARY", "PRESENT")]
    text = "\n".join(sentences)
    output = raw(text, mentions)
    clinical = output["canonical_facts"]
    assert len(clinical) == 6
    assert clinical[0]["salience"] == "PRIMARY"
    assert clinical[0]["display_label"].startswith("Pharyngeal dyskinesia")
    assert "absent relaxation" in clinical[0]["display_label"].lower()
    assert not facts(output, "general:functional_absence:relaxation")
    for concept in ("obstruction", "residual", "penetration", "motion", "spillage"):
        assert len(facts(output, "general:" + concept)) == 1
    assert all(text[a["start_offset"]:a["end_offset"]] == a["quote"]
               for fact in clinical for a in fact["evidence_anchors"])
    assert {r["relation_type"] for r in clinical[0]["relationships"]} == {"CAUSES"}
    residual = facts(output, "general:residual")[0]
    assert residual["relationships"][0]["relation_type"] == "ASSOCIATED_WITH"
    assert "partial obstruction" in output["clinical_synthesis"].lower()


def test_absent_normal_function_alone_is_a_positive_abnormal_finding():
    sentence = "There is complete absence of relaxation during examination."
    output = raw(sentence, [("relaxation", sentence, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    fact = facts(output, "general:functional_absence:relaxation")[0]
    assert fact["assertion_state"] == "PRESENT"
    assert fact["fact_type"] == "FUNCTIONAL_ABNORMALITY"
    assert fact["display_label"] == "Absent relaxation"


def test_source_explicit_cause_uses_nearest_same_section_anchor_after_merge():
    detail = "Complete lack of relaxation was observed."
    principal = "Pharyngeal dyskinesia with absent relaxation."
    effect = "This results in partial obstruction."
    text = "\n".join((detail, principal, effect))
    output = raw(text, [
        ("relaxation", detail, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED"),
        ("dyskinesia", principal, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("relaxation", principal, "DIAGNOSTIC_SUMMARY", "ABSENT_NEGATED"),
        ("obstruction", effect, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    condition = facts(output, "general:condition:dyskinesia")[0]
    assert len(condition["relationships"]) == 1
    assert condition["relationships"][0]["relation_type"] == "CAUSES"


def test_qualified_negative_is_separate_from_transient_positive_and_no_diverticulum():
    a = "Transient penetration occurred from retained material."
    b = "No penetration or aspiration occurring during the act itself."
    c = "No diverticulum is seen."
    output = raw("\n".join((a, b, c)), [
        ("penetration", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("penetration", b, "DIAGNOSTIC_SUMMARY", "ABSENT_NEGATED"),
        ("aspiration", b, "DIAGNOSTIC_SUMMARY", "ABSENT_NEGATED"),
        ("diverticulum", c, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(output["canonical_facts"]) == 4
    assert len([f for f in output["canonical_facts"] if f["group"] == "NEGATIVE"]) == 3
    assert facts(output, "general:penetration")[0]["assertion_state"] == "PRESENT"
    assert facts(output, "general:penetration:qualified_negative")[0]["assertion_state"] == "ABSENT_NEGATED"
    assert not any("CONFLICTING_SOURCE_ASSERTION" in f["review_reason"] for f in output["canonical_facts"])


def test_impression_open_vocabulary_requires_condition_cue_and_suppresses_modifiers():
    meaningful = "Impression: Tendinous dyskinesia with impaired movement."
    output = raw(meaningful, [("dyskinesia", meaningful, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert output["canonical_facts"][0]["salience"] == "PRIMARY"
    assert output["canonical_facts"][0]["display_label"].startswith("Tendinous dyskinesia")
    for word in ("normal", "similar", "greater", "slow", "centered", "swallowing"):
        sentence = f"The {word} appearance was recorded."
        assert raw(sentence, [(word, sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])["canonical_facts"] == []


def test_generalized_negative_and_peripheral_edema_across_other_radiology_subtypes():
    doppler = "No DVT identified.\nThere is bilateral edema of the lower extremities."
    output = raw(doppler, [("DVT", "No DVT identified.", "DIAGNOSTIC_SUMMARY", "ABSENT_NEGATED"),
                           ("edema", "There is bilateral edema of the lower extremities.", "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert {f["display_label"] for f in output["canonical_facts"]} == {"No DVT", "Bilateral edema"}
    assert not facts(output, "vasogenic_edema")
    thyroid = "There are no discrete nodules."
    output = raw(thyroid, [("nodules", thyroid, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(output["canonical_facts"]) == 1
    assert output["canonical_facts"][0]["group"] == "NEGATIVE"


def test_exact_grounded_negative_candidate_survives_validator_modifier_firewall():
    sentence = "No aspiration occurred during the procedure."
    start = sentence.index("aspiration")
    candidate = {"candidate_id": "candidate-1", "candidate_type": "Observation", "source_text": "aspiration",
                 "source_start": start, "source_end": start + len("aspiration"),
                 "source_section_role": "DIAGNOSTIC_SUMMARY", "assertion_candidate": "ABSENT_NEGATED"}
    output = synthesize({"radiology_findings": [], "candidate_count": 1}, sentence, [candidate])
    negative = output["canonical_facts"][0]
    assert negative["group"] == "NEGATIVE"
    assert negative["synthesis_provenance"]["engine_evidence_ids"] == ["candidate-1"]
    assert negative["evidence_anchors"][0]["quote"] == sentence


def test_mixed_lesion_and_functional_report_retains_distinct_functional_finding():
    lesion = "A ring enhancing lesion is present."
    motion = "Abnormal diaphragmatic motion is seen."
    negative = "No fracture is seen."
    output = raw("\n".join((lesion, motion, negative)), [
        ("lesion", lesion, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("motion", motion, "FINDINGS_DESCRIPTION", "PRESENT"),
        ("fracture", negative, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(facts(output, "lesion_complex")) == 1
    assert len(facts(output, "general:motion")) == 1
    assert output["counts"]["pertinent_negatives"] == 0
    assert "abnormal diaphragmatic motion" in output["clinical_synthesis"].lower()


def test_unfamiliar_grounded_abnormality_needs_no_named_concept_rule():
    impression = "Fascial dehiscence is present."
    detail = "Fascial dehiscence is seen along the repair."
    output = raw(impression + "\n" + detail, [
        ("dehiscence", impression, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("dehiscence", detail, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 1
    fact = output["canonical_facts"][0]
    assert fact["display_label"] == "Fascial dehiscence"
    assert fact["group"] == "KEY" and fact["assertion_state"] == "PRESENT"
    assert len(fact["evidence_anchors"]) == 2
    assert output["technical_diagnostics"]["merged_mention_count"] >= 1


def test_findings_only_open_condition_and_injury_are_secondary_not_lost():
    a = "Fascial dehiscence is seen."
    b = "A complex capsular rupture is present."
    output = raw(a + "\n" + b, [("dehiscence", a, "FINDINGS_DESCRIPTION", "PRESENT"),
                                  ("rupture", b, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 2
    assert {fact["group"] for fact in output["canonical_facts"]} == {"SECONDARY"}
    assert all(fact["fact_type"] == "FINDING" for fact in output["canonical_facts"])


def test_isolated_anatomy_measurement_modifier_and_generic_noun_do_not_become_facts():
    anatomy = "The humerus is identified."
    start = anatomy.index("humerus")
    candidate = {"candidate_id": "a1", "candidate_type": "Anatomy", "source_text": "humerus",
                 "source_start": start, "source_end": start + 7,
                 "source_section_role": "FINDINGS_DESCRIPTION", "assertion_candidate": "PRESENT"}
    assert synthesize({"radiology_findings": [], "candidate_count": 1}, anatomy, [candidate])["canonical_facts"] == []
    for expression, sentence in (("4 mm", "The defect measures 4 mm."),
                                 ("extensive", "Extensive findings were recorded."),
                                 ("process", "The process is noted.")):
        assert raw(sentence, [(expression, sentence, "FINDINGS_DESCRIPTION", "PRESENT")])["canonical_facts"] == []


def test_present_organ_atrophy_is_positive_and_muscular_absence_is_not_cerebral():
    positive = "Cerebral atrophy is present."
    negative = "There is no muscular tear, contusion, or atrophy."
    present_output = raw(positive, [("atrophy", positive, "FINDINGS_DESCRIPTION", "PRESENT")])
    absent_output = raw(negative, [("atrophy", negative, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert facts(present_output, "atrophy")[0]["group"] == "SECONDARY"
    assert facts(present_output, "atrophy")[0]["assertion_state"] == "PRESENT"
    muscular = next(f for f in absent_output["canonical_facts"] if f["assertion_state"] == "ABSENT_NEGATED")
    assert muscular["display_label"] == "No muscular atrophy"
    assert muscular["group"] == "NEGATIVE"
    assert "cerebral atrophy" not in absent_output["clinical_synthesis"].lower()


def test_explicit_absence_of_meaningful_condition_is_negative_not_positive():
    sentence = "No pleural effusion is seen."
    output = raw(sentence, [("effusion", sentence, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(output["canonical_facts"]) == 1
    fact = output["canonical_facts"][0]
    assert fact["display_label"] == "No pleural effusion"
    assert fact["group"] == "NEGATIVE" and fact["assertion_state"] == "ABSENT_NEGATED"


def test_generic_measurements_attach_to_the_condition_not_a_separate_fact():
    sentence = "Shallow subcapsular defect 1.4 cm transverse and 4 mm deep is present."
    output = raw(sentence, [("defect", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 1
    observation = output["canonical_facts"][0]["observations"][0]
    assert observation["measurements"] == ["1.4 cm", "4 mm"]


def test_second_dimension_after_comma_has_its_own_exact_attribute_anchor():
    sentence = "Shallow subcapsular defect 1.4cm transverse present, and 4mm in depth."
    output = raw(sentence, [("defect", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    fact = output["canonical_facts"][0]
    assert fact["observations"][0]["measurements"] == ["1.4cm", "4mm"]
    support = [a for a in fact["evidence_anchors"] if a["role"] == "ATTRIBUTE_SUPPORT"]
    assert len(support) == 1 and support[0]["quote"] == "4mm"
    assert sentence[support[0]["start_offset"]:support[0]["end_offset"]] == "4mm"


def test_distinct_open_conditions_do_not_merge_for_shared_word_or_anatomy():
    a = "Fascial dehiscence is present."
    b = "Tendon dehiscence is present."
    output = raw(a + "\n" + b, [("dehiscence", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                                  ("dehiscence", b, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 2
    assert {f["display_label"] for f in output["canonical_facts"]} == {"Fascial dehiscence", "Tendon dehiscence"}


def test_repeated_mass_with_matching_morphology_merges_but_distinct_morphology_does_not():
    summary = "A lobulated oval mass in superficial tissues of the upper thigh is present."
    detail = "Incidentally noted in the anterior upper thigh is a lobulated oval mass."
    distinct = "A spiculated mass in superficial tissues of the upper thigh is present."
    output = raw("\n".join((summary, detail, distinct)), [
        ("mass", summary, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("lobulated oval mass", detail, "FINDINGS_DESCRIPTION", "PRESENT"),
        ("mass", distinct, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 2
    repeated = next(f for f in output["canonical_facts"] if "lobulated oval" in f["display_label"].lower())
    assert len(repeated["evidence_anchors"]) == 2
    assert repeated["group"] == "KEY"
    assert "Incidentally noted" not in repeated["display_label"]


def test_opposing_open_assertions_stay_separate_and_both_require_review():
    a = "Pleural effusion is present."
    b = "No pleural effusion is seen."
    output = raw(a + "\n" + b, [("effusion", a, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                                  ("effusion", b, "FINDINGS_DESCRIPTION", "ABSENT_NEGATED")])
    assert len(output["canonical_facts"]) == 2
    assert {f["assertion_state"] for f in output["canonical_facts"]} == {"PRESENT", "ABSENT_NEGATED"}
    assert all("CONFLICTING_SOURCE_ASSERTION" in f["review_reason"] for f in output["canonical_facts"])


def test_open_vocabulary_diagnostic_hypothesis_keeps_uncertainty():
    sentence = "Seroma is possible."
    output = raw(sentence, [("Seroma", sentence, "DIAGNOSTIC_SUMMARY", "UNCERTAIN")])
    fact = output["canonical_facts"][0]
    assert fact["fact_type"] == "DIAGNOSTIC_HYPOTHESIS"
    assert fact["assertion_state"] == "UNCERTAIN" and fact["hypothesis_status"] == "POSSIBLE"
    assert fact["display_label"] == "Seroma"


def test_unexplained_zero_fact_synthesis_has_coverage_diagnostic_and_reason_counts():
    sentence = "The rotator cuff is normal."
    output = raw(sentence, [("rotator cuff", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert output["canonical_facts"] == []
    diagnostics = output["technical_diagnostics"]
    assert diagnostics["code"] == "SYNTHESIS_COVERAGE_FAILURE"
    assert diagnostics["validated_evidence_count"] == 1
    assert diagnostics["clinically_grounded_evidence_count"] == 1
    assert diagnostics["suppressed_candidate_count"] == 1
    assert diagnostics["rejection_reason_counts"]["ROUTINE_NORMAL_OBSERVATION"] == 1
    assert diagnostics["candidate_decisions"][0]["semantic_role_candidate"] == "NORMAL_OBSERVATION"
    assert "SYNTHESIS_COVERAGE_FAILURE" in output["review_summary"]["reasons"]


def test_cross_section_source_recovery_needs_explicit_corrob_or_it_abstains():
    detail = "Extensive lateral capsular rupture is seen."
    summary = "Extensive lateral capsular rupture."
    text = detail + "\n" + summary
    sections = [{"role": "FINDINGS_DESCRIPTION", "start": 0, "end": len(detail), "text": detail},
                {"role": "DIAGNOSTIC_SUMMARY", "start": len(detail) + 1, "end": len(text), "text": summary}]
    result = {"radiology_findings": [], "candidate_count": 0}
    recovered = synthesize(result, text, [], sections)
    assert len(recovered["canonical_facts"]) == 1
    fact = recovered["canonical_facts"][0]
    assert fact["group"] == "KEY" and len(fact["evidence_anchors"]) == 2
    assert len(fact["synthesis_provenance"]["source_rule_evidence_ids"]) == 2
    assert all(text[a["start_offset"]:a["end_offset"]] == a["quote"] for a in fact["evidence_anchors"])
    assert synthesize(result, summary, [], [
        {"role": "DIAGNOSTIC_SUMMARY", "start": 0, "end": len(summary), "text": summary}])["canonical_facts"] == []


def test_synthesis_does_not_branch_on_report_filename_or_identifier():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "app/modules/medical_document_intelligence/services/clinical_synthesis.py"
    code = source.read_text(encoding="utf-8")
    assert not any(report_id in code for report_id in ("US_CT_07", "US_X-ray_04", "IN_MRI_02"))


def test_report_disclaimer_and_routine_normal_descriptions_are_not_abnormalities():
    administrative = "Patient identification in online reporting is not established."
    normal = "The lungs are well aerated with regular contours."
    output = raw(administrative + "\n" + normal, [
        ("identification", administrative, "DIAGNOSTIC_SUMMARY", "PRESENT"),
        ("well aerated", normal, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert output["canonical_facts"] == []
    reasons = output["technical_diagnostics"]["rejection_reason_counts"]
    assert reasons["ADMINISTRATIVE_TEXT"] == 1
    assert reasons["ROUTINE_NORMAL_OBSERVATION"] == 1


def test_procedural_compression_is_not_pathologic_mass_effect():
    sentence = "Venous flow augments normally with compression of the extremity."
    output = raw(sentence, [("compression", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert output["canonical_facts"] == []
    assert output["technical_diagnostics"]["rejection_reason_counts"]["PROCEDURE_OR_TECHNIQUE"] == 1


def test_soft_wrapped_location_and_preposed_measurement_yield_complete_mass_label():
    sentence = "Incidentally noted is a lobulated oval 3.5-cm mass in the\nleft thigh."
    output = raw(sentence, [("mass", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert len(output["canonical_facts"]) == 1
    assert output["canonical_facts"][0]["display_label"] == "Lobulated oval mass in the left thigh"
    assert output["canonical_facts"][0]["group"] == "KEY"


def test_soft_wrapped_noun_phrase_keeps_its_leading_assertion():
    sentence = "Again noted is a\nhiatal hernia."
    output = raw(sentence, [("hiatal hernia", sentence, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert len(output["canonical_facts"]) == 1
    assert output["canonical_facts"][0]["display_label"] == "Hiatal hernia"


def test_differential_bridge_does_not_turn_possible_diagnosis_into_present_lesion():
    sentence = "Both lesions may represent hemangiomas."
    output = raw(sentence, [("lesions", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT"),
                            ("hemangiomas", sentence, "DIAGNOSTIC_SUMMARY", "PRESENT")])
    assert len(output["canonical_facts"]) == 1
    fact = output["canonical_facts"][0]
    assert fact["display_label"] == "Hemangiomas"
    assert fact["fact_type"] == "DIAGNOSTIC_HYPOTHESIS"
    assert fact["assertion_state"] == "UNCERTAIN" and fact["hypothesis_status"] == "POSSIBLE"


def test_source_negation_conflict_and_morphology_attribute_do_not_create_independent_facts():
    negated = "This lesion does not meet cyst criteria."
    morphology = "The mass is predominantly hypoechoic but contains echogenic areas."
    output = raw(negated + "\n" + morphology, [
        ("lesion", negated, "FINDINGS_DESCRIPTION", "PRESENT"),
        ("mass", morphology, "FINDINGS_DESCRIPTION", "PRESENT")])
    assert output["canonical_facts"] == []
    reasons = output["technical_diagnostics"]["rejection_reason_counts"]
    assert reasons["SOURCE_ASSERTION_CONFLICT"] == 1
    assert reasons["MORPHOLOGY_ATTRIBUTE"] == 1


def test_long_source_supported_possibility_and_postposed_possibility_remain_hypotheses():
    a = "This likely represents a benign vascular lesion such as a\nhemangioma."
    b = "An atypical lymph node is a possibility."
    output = raw(a + "\n" + b, [("hemangioma", a, "DIAGNOSTIC_SUMMARY", "UNCERTAIN"),
                                  ("lymph node", b, "DIAGNOSTIC_SUMMARY", "UNCERTAIN")])
    assert len(output["canonical_facts"]) == 2
    assert all(f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and f["assertion_state"] == "UNCERTAIN"
               and f["hypothesis_status"] == "POSSIBLE" for f in output["canonical_facts"])
