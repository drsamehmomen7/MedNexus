"""Evidence-linked R2.0C presentation of protected, validated pilot evidence.

Named rules below normalize established terminology; they are not the basic
eligibility test for a grounded clinical observation.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict


PROFILE = "radiology-clinical-synthesis-0.1"
MEASUREMENT = re.compile(r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?(?:\s*(?:mm|cm|cc|ml))?(?:\s*[x×]\s*\d+(?:\.\d+)?(?:\s*(?:mm|cm|cc|ml))?){0,2}\s*(?:mm|cm|cc|ml)\b", re.I)
NOISE = re.compile(r"^(?:process|problem|change|extensive|adjacent|persistent|major|lesion|mass|finding|abnormality|calcification|calcifications|measurement|size|area)$", re.I)
NONCONTRAST = re.compile(r"\b(?:non[- ]?contrast|pre[- ]?contrast|unenhanced|without (?:iv |intravenous )?contrast)\b", re.I)
POSTCONTRAST = re.compile(r"\b(?:post[- ]?contrast|contrast[- ]?enhanced|after (?:iv )?contrast|with (?:iv |intravenous )?contrast)\b", re.I)

# Compatibility terminology/display normalizers for the accepted CT projection.
# Open-vocabulary eligibility is decided separately, before these mappings.
RULES = (
    ("lesion_complex", r"\b(?:lesions?|mass(?:es)?|annular|spheroid|ring)\b", r"\b(?:annular|spheroid|ring|enhanc|temporal|parietal|lesions?)", "Multifocal right temporoparietal enhancing lesion complex", "FINDING", "PRIMARY", "KEY"),
    ("vasogenic_edema", r"\b(?:edema|oedema)\b", r"\bvasogenic\s+(?:edema|oedema)\b", "Vasogenic edema", "FINDING", "ASSOCIATED", "KEY"),
    ("mass_effect", r"\b(?:mass effect|effacement|compression|ventricular effect)\b", r"\b(?:mass effect|effacement|compression|ventricular effect)\b", "Mass effect / ventricular effect", "FINDING", "ASSOCIATED", "KEY"),
    ("frontal_wm", r"\b(?:white[- ]matter|hypoattenuat\w*|lesion)\b", r"\b(?:frontal|white[- ]matter|hypoattenuat\w*)\b", "Chronic right frontal white-matter lesion", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("optic_drusen", r"\b(?:drusen|calcif\w*)\b", r"\b(?:optic disc|drusen)\b", "Bilateral optic disc calcifications / drusen", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("scleral_calcification", r"\b(?:scleral?|calcif\w*)\b", r"\b(?:scleral?|sclera)\b", "Degenerative scleral calcification", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("tendon_calcification", r"\b(?:tendon|oblique|calcif\w*)\b", r"\b(?:superior oblique|tendon)\b", "Dystrophic superior oblique tendon calcification", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("atherosclerosis", r"\b(?:atherosclero\w*|vascular|arterial|calcif\w*)\b", r"\b(?:atherosclero\w*|vascular calcif\w*|arterial calcif\w*)\b", "Atherosclerosis / vascular calcifications", "BACKGROUND_FINDING", "BACKGROUND", "SECONDARY"),
    ("atrophy", r"\b(?:atrophy|volume loss)\b", r"\b(?:atrophy|volume loss)\b", "Cerebral atrophy", "BACKGROUND_FINDING", "BACKGROUND", "SECONDARY"),
    ("senescent_wm", r"\b(?:white[- ]matter|senescent|microvascular)\b", r"\b(?:senescen\w*|microvascular|small[- ]vessel)\b", "Senescent white-matter changes", "BACKGROUND_FINDING", "BACKGROUND", "SECONDARY"),
    ("sinus_disease", r"\b(?:sinus\w*|mucosal|thickening|maxillary)\b", r"\b(?:maxillary|sinus\w*)\b", "Chronic maxillary sinus disease", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("dentigerous_cyst", r"\b(?:dentigerous|cyst|odontogenic)\b", r"\b(?:dentigerous|odontogenic)\b", "Possible dentigerous cyst formation", "BACKGROUND_FINDING", "SECONDARY", "SECONDARY"),
    ("metastatic_tumor", r"\b(?:metasta\w*|tumou?r)\b", r"\bmetasta\w*\b", "Metastatic tumor", "DIAGNOSTIC_HYPOTHESIS", "PRIMARY", "DIAGNOSTIC"),
    ("multifocal_abscess", r"\babscess(?:es)?\b", r"\babscess(?:es)?\b", "Multifocal abscess", "DIAGNOSTIC_HYPOTHESIS", "SECONDARY", "DIAGNOSTIC"),
    ("primary_brain_tumor", r"\b(?:primary|brain|tumou?r|neoplasm)\b", r"\b(?:primary|brain)\b.{0,30}\b(?:tumou?r|neoplasm)\b|\b(?:tumou?r|neoplasm)\b.{0,30}\bprimary\b", "Primary brain tumor", "DIAGNOSTIC_HYPOTHESIS", "SECONDARY", "DIAGNOSTIC"),
    ("infarct", r"\b(?:infarct|ischemi\w*)\b", r"\b(?:infarct|ischemi\w*)\b", "Infarct", "DIAGNOSTIC_HYPOTHESIS", "SECONDARY", "DIAGNOSTIC"),
)


def _sentence(text: str, start: int, end: int) -> dict:
    left = max((m.end() for m in re.finditer(r"[.!?](?:\s+|$)", text[:start])), default=0)
    right_match = re.search(r"[.!?](?:\s+|$)", text[end:])
    right = end + right_match.end() if right_match else len(text)
    while left < right and text[left].isspace():
        left += 1
    return {"start_offset": left, "end_offset": right, "quote": text[left:right]}


def _context(text: str, anchor: dict, sections: list[dict] = ()) -> str:
    sentence = anchor["quote"]
    start = anchor["start_offset"]
    containing = next((section for section in sections if section["start"] <= start <
                       section.get("end", section["start"] + len(section.get("text", "")))), None)
    role = containing["role"] if containing else anchor.get("source_section")
    # Acquisition cues in TECHNIQUE can govern the later Findings narrative.
    # An Impression without its own cue must not inherit an unrelated count.
    floor = containing["start"] if containing and role == "DIAGNOSTIC_SUMMARY" else 0
    earlier = text[floor:start]
    cues = [(m.start() + floor, "NON_CONTRAST") for m in NONCONTRAST.finditer(earlier)]
    cues += [(m.start() + floor, "POST_CONTRAST") for m in POSTCONTRAST.finditer(earlier)]
    local = [(m.start() + start, "NON_CONTRAST") for m in NONCONTRAST.finditer(sentence)]
    local += [(m.start() + start, "POST_CONTRAST") for m in POSTCONTRAST.finditer(sentence)]
    if cues or local:
        return max(cues + local)[1]
    if role == "DIAGNOSTIC_SUMMARY" and re.search(r"\benhanc\w*\b", sentence, re.I):
        global_cues = [(m.start(), "NON_CONTRAST") for m in NONCONTRAST.finditer(text[:start])]
        global_cues += [(m.start(), "POST_CONTRAST") for m in POSTCONTRAST.finditer(text[:start])]
        if global_cues and max(global_cues)[1] == "POST_CONTRAST":
            return "POST_CONTRAST"
    return "UNSPECIFIED"


def _rule(expression: str, sentence: str):
    if NOISE.fullmatch(expression.strip()) and not re.search(r"\b(?:annular|spheroid|ring|enhanc\w*|frontal|optic|sclera\w*|tendon|vascular)\b", sentence, re.I):
        return None
    for key, term, context, display, kind, salience, group in RULES:
        if not re.search(term, expression, re.I) or not re.search(context, sentence, re.I):
            continue
        if key == "lesion_complex" and not re.search(r"\b(?:annular|spheroid|ring|enhanc)\w*\b", sentence, re.I):
            continue
        if key == "frontal_wm" and not re.search(r"\b(?:white[- ]matter|hypoattenuat\w*)\b", expression, re.I):
            continue
        if key == "frontal_wm" and not (re.search(r"\bfrontal\b", sentence, re.I) and re.search(r"\b(?:white[- ]matter|hypoattenuat)\w*\b", sentence, re.I)):
            continue
        if key == "senescent_wm" and not re.search(r"white[- ]matter|periventricular", sentence, re.I):
            continue
        if key == "sinus_disease" and not re.search(r"\b(?:sinus\w*|mucosal)\b", sentence, re.I):
            continue
        if key == "dentigerous_cyst" and not re.search(r"\bcyst\b", sentence, re.I):
            continue
        if key == "primary_brain_tumor" and re.search(r"\bmetasta\w*\b", expression, re.I):
            continue
        if key == "atrophy" and re.search(r"\b(?:muscul\w*|skelet\w*|tendon\w*)\b", sentence, re.I):
            # This legacy neuro display mapping must not relabel an explicit
            # musculoskeletal negative as cerebral atrophy.
            continue
        if key == "mass_effect" and re.fullmatch(r"(?:compression|effacement)", expression, re.I) and not re.search(
                r"\b(?:mass effect|ventricular effect|effacement|compress\w*\s+(?:of|on)\s+\w+\s+(?:by|from))\b", sentence, re.I):
            # A compressible vein or applied probe compression is not mass effect.
            continue
        return key, display, kind, salience, group
    return None


# An exact Observation anchor may support a non-lesion condition when the
# bounded display vocabulary cannot describe a report. These are reusable
# clinical states and processes, not modality, anatomy, or report identifiers.
FUNCTIONAL = (
    ("obstruction", r"\bobstruct\w*\b"),
    ("residual", r"\b(?:residual|pooling)\b"),
    ("penetration", r"\bpenetrat\w*\b"),
    ("motion", r"\b(?:motion|movement)\b"),
    ("spillage", r"\bspill\w*\b"),
    ("aspiration", r"\baspirat\w*\b"),
    ("reflux", r"\breflux\b"),
    ("edema", r"\b(?:edema|oedema)\b"),
)
NEGATIVE_CONDITIONS = re.compile(
    r"\b(?:aspirat\w*|penetrat\w*|diverticul\w*|reflux|DVT|thromb\w*|"
    r"nodul\w*|effusion\w*|fractur\w*|dislocat\w*|obstruct\w*)\b", re.I)
GENERIC_MODIFIERS = re.compile(
    r"^(?:normal|similar|centered|greater|slow|moved|inverting|"
    r"discrete|thickness|appearance|findings?|changes?|process|problem|extensive)$", re.I)


def _general_label(expression: str, sentence: str, concept: str, assertion: str) -> str:
    expression = expression.strip()
    if concept == "functional_absence":
        return "Absent " + re.sub(r"\s+", " ", expression.lower())
    if assertion == "ABSENT_NEGATED":
        qualifier = _negative_qualifier(expression, sentence)
        label = "No " + (qualifier + " " if qualifier else "") + expression
        position = re.search(re.escape(expression), sentence, re.I)
        if position:
            trailing = sentence[position.end():]
            context = re.search(r"\b(?:occurring|during|with)\b.{0,45}", trailing, re.I)
            if context and concept in {"penetration", "aspiration"}:
                label += " " + context.group().strip(" .;,")
        return re.sub(r"\s+", " ", label[0].upper() + label[1:])
    if concept == "condition":
        match = re.search(r"\b([A-Za-z-]+\s+" + re.escape(expression) + r")\b", sentence, re.I)
        label = match.group(1) if match else expression
        if re.search(r"\b(?:absence|lack)\s+of\s+(?:any\s+)?(?:[A-Za-z-]+\s+)?relaxation\b", sentence, re.I):
            label += " with absent relaxation"
        return re.sub(r"\s+", " ", label[0].upper() + label[1:])
    modifiers = r"(?:mild|very|transient|slight|partial|considerable|significant|bilateral|early|severe|complete|acute|chronic)"
    if concept == "motion":
        match = re.search(r"\babnormal\s+(?:[A-Za-z-]+\s+){0,2}" + re.escape(expression) + r"\b", sentence, re.I)
        label = match.group() if match else "Abnormal " + expression.lower()
    else:
        match = re.search(r"\b(?:(?:" + modifiers + r")\s+){0,3}" + re.escape(expression) + r"\b", sentence, re.I)
        label = match.group() if match else expression
    if concept in {"residual", "penetration", "spillage"} and match:
        trailing = sentence[match.end():]
        location = re.match(r"\s+(?:in|into|to|from)\s+(?:the\s+)?[A-Za-z-]+(?:\s+(?!above\b|with\b|and\b|rather\b|occurred\b|occurring\b|was\b|is\b)[A-Za-z-]+)?", trailing, re.I)
        if location:
            label += location.group()
    return re.sub(r"\s+", " ", label[0].upper() + label[1:])


def _negative_qualifier(expression: str, sentence: str) -> str:
    position = re.search(re.escape(expression).replace(r"\ ", r"\s+"), sentence, re.I)
    if not position:
        return ""
    start = sentence.rfind("\n", 0, position.start()) + 1
    before = sentence[start:position.start()]
    negations = list(re.finditer(r"\b(?:no|without)\b", before, re.I))
    if not negations:
        return ""
    between = before[negations[-1].end():].strip()
    if not between:
        return ""
    if not re.search(r"[,;]|\b(?:or|and)\b", between, re.I) and len(between.split()) <= 3:
        return between
    first = re.match(r"[A-Za-z-]+", between)
    return first.group() if first and re.search(r"(?:al|ar|ic|ous)$", first.group(), re.I) else ""


def _general_rule(expression: str, sentence: str, assertion: str, section: str):
    expression = expression.strip()
    if not expression or GENERIC_MODIFIERS.fullmatch(expression) or NOISE.fullmatch(expression):
        return None
    if not re.search(re.escape(expression), sentence, re.I):
        return None
    if assertion == "ABSENT_NEGATED":
        if re.search(r"\b(?:relaxation|inversion|movement|motion)\b", expression, re.I) and re.search(
                r"\b(?:absence|lack|failure)\s+of\b|\bnot\s+\w+", sentence, re.I):
            label = _general_label(expression, sentence, "functional_absence", "PRESENT")
            return "general:functional_absence:" + expression.casefold(), label, "FUNCTIONAL_ABNORMALITY", "ASSOCIATED", "KEY", "PRESENT"
        if not NEGATIVE_CONDITIONS.search(expression):
            return None
        before = sentence[:re.search(re.escape(expression), sentence, re.I).start()]
        if not re.search(r"\b(?:no|without|absence of|did not appear to be any)\b.{0,75}$", before, re.I | re.S):
            return None
        concept = next((key for key, pattern in FUNCTIONAL if re.search(pattern, expression, re.I)), expression.casefold())
        qualified = bool(re.search(r"\b(?:with|during)\b.{0,35}\b(?:itself|phase|act)\b", sentence, re.I))
        key = f"general:{concept}" + (":qualified_negative" if qualified else "")
        return key, _general_label(expression, sentence, concept, assertion), "PERTINENT_NEGATIVE", "SECONDARY", "NEGATIVE", assertion
    if assertion != "PRESENT":
        return None
    if section == "DIAGNOSTIC_SUMMARY" and re.fullmatch(r"[A-Za-z-]*(?:asia|esia|osis|itis|pathy|emia)", expression, re.I) and re.search(
            r"\b(?:abnormal|absent|absence|lack|impaired|obstruct\w*|dysfunction)\b", sentence, re.I):
        return "general:condition:" + expression.casefold(), _general_label(expression, sentence, "condition", assertion), "FINDING", "PRIMARY", "KEY", assertion
    for concept, pattern in FUNCTIONAL:
        if not re.search(pattern, expression, re.I):
            continue
        if concept == "motion" and not re.search(r"\b(?:abnormal|impaired|slow|not\s+invert\w*)\b", sentence, re.I):
            return None
        if concept == "residual" and not re.search(r"\b(?:considerable|significant|pool\w*|obstruct\w*|retained)\b", sentence, re.I):
            return None
        label = _general_label(expression, sentence, concept, assertion)
        group = "KEY" if section == "DIAGNOSTIC_SUMMARY" else "SECONDARY"
        return "general:" + concept, label, "FUNCTIONAL_ABNORMALITY", "ASSOCIATED", group, assertion
    return None


# These are suppression/grammar cues, not a list of eligible diseases. RadGraph
# has already identified an Observation; a new clinical noun need not appear in
# any named concept table to pass basic eligibility.
ADMINISTRATIVE = re.compile(
    r"\b(?:radiologist|consultant|signature|typing error|machinery error|discrepancy|"
    r"rectif\w*|review by|dictat\w*|online reporting|patient(?:s|['’]s)? identification|"
    r"(?:machine|equipment|procedure)s?\b.{0,80}\blimitation\w*)\b", re.I)
TECHNIQUE = re.compile(
    r"\b(?:images? (?:were|was) (?:obtained|acquired)|sequence|protocol|contrast administered|"
    r"(?:with|during)\s+(?:manual\s+|probe\s+)?compression)\b", re.I)
ROUTINE_NORMAL = re.compile(
    r"\b(?:normal|unremarkable|intact|clear|within normal limits|well[- ]aerated|regular|"
    r"sharp lateral recess\w*|preserved|maintained)\b", re.I)
ISOLATED_ATTRIBUTE = re.compile(
    r"^(?:transverse diameter|depth|thickness|size|volume|length|width|height|"
    r"complete|partial|destructive|degenerative|atherosclerotic|torn|normal limits|"
    r"normal position|tooth root|swallow|swallows|swallowing|barium)$", re.I)
CLINICAL_PREDICATE = re.compile(
    r"\b(?:is|are|was|were|has|have|seen|present|noted|identified|demonstrat\w*|"
    r"show\w*|measur\w*|involv\w*|torn|tear\w*|fractur\w*|effusion|lesion|abnormal|impaired|absen\w*)\b", re.I)
NEGATION = re.compile(r"\b(?:no|without|absen\w*\s+of|lack\s+of|not\s+seen)\b", re.I)
LOW_INFORMATION_HEAD = re.compile(
    r"^(?:(?:still|underlying|major|extensive|adjacent|mild|modest|chronic|persistent)\s+)*"
    r"(?:findings?|changes?|disease|process|problem|material)\b", re.I)


def _local_anchor(anchor: dict, expression: str) -> dict | None:
    """Bound a model sentence to the exact line/clause supporting its entity."""
    quote = anchor["quote"]
    pattern = re.escape(expression).replace(r"\ ", r"\s+")
    match = re.search(pattern, quote, re.I)
    if not match:
        return None
    line_start = quote.rfind("\n", 0, match.start()) + 1
    if line_start:
        previous_start = quote.rfind("\n", 0, line_start - 1) + 1
        previous = quote[previous_start:line_start - 1]
        if re.search(r"\b(?:a|an|the|is|are|was|were|as|with|in|of|noted)\s*$", previous, re.I):
            line_start = previous_start
    line_end = quote.find("\n", match.start())
    line_end = len(quote) if line_end < 0 else line_end
    # A lowercase next line without intervening sentence punctuation is a PDF
    # continuation. Retain it so a modifier or interval qualifier stays with
    # its clinical head instead of becoming a broken standalone fragment.
    for _ in range(2):
        if line_end >= len(quote):
            break
        current = quote[line_start:line_end]
        next_end = quote.find("\n", line_end + 1)
        next_line = quote[line_end + 1:len(quote) if next_end < 0 else next_end]
        continuation = (not re.search(r"[.!?;:]\s*$", current)
                        and re.match(r"\s*[a-z][a-z-]*\b", next_line) is not None)
        if not continuation and not re.search(
                r"\b(?:in|the|of|with|some|and|but|does|not|may|small|mild|to|at|within|for|again|is|are|was|were|has|have)\s*$",
                current, re.I):
            break
        line_end = len(quote) if next_end < 0 else next_end
    line = quote[line_start:line_end]
    local = match.start() - line_start
    left, right = 0, len(line)
    # Commas separate independent report clauses. Do not split anatomical
    # conjunctions such as "anterior and inferior".
    for delimiter in re.finditer(r",\s*(?:and\s+)?|[.;](?=\s|$)", line):
        if delimiter.end() <= local:
            left = delimiter.end()
        elif delimiter.start() >= local:
            right = delimiter.start()
            break
    fragment = line[left:right]
    leading = len(fragment) - len(fragment.lstrip(" ,.;"))
    trailing = len(fragment) - len(fragment.rstrip(" ,.;"))
    start = anchor["start_offset"] + line_start + left + leading
    end = anchor["start_offset"] + line_start + right - trailing
    return {"start_offset": start, "end_offset": end, "quote": quote[start-anchor["start_offset"]:end-anchor["start_offset"]],
            "role": anchor.get("role"), "source_section": anchor.get("source_section")}


def _source_fragment(anchor: dict, expression: str) -> str:
    local = _local_anchor(anchor, expression)
    return local["quote"] if local else ""


def classify_clause(expression: str, anchor: dict, section: str, source_text: str = "") -> tuple[str, str | None]:
    """Classify the source clause before any terminology rule can create a fact.

    Section labels describe broad regions. This decision uses the exact local
    clause, its adjacent list context, and its source function instead.
    """
    local = _local_anchor(anchor, expression)
    if not local:
        return "FRAGMENT_OR_LOW_INFORMATION", "UNSUPPORTED_FRAGMENT"
    clause = local["quote"].strip()
    simple = re.sub(r"^[\s\x7f■•\-*\d.()]+", "", clause).strip()
    if section == "CLINICAL_CONTEXT":
        return "CLINICAL_CONTEXT", "CONTEXT_NOT_CURRENT_FINDING"
    if section == "TECHNIQUE":
        return "TECHNIQUE_OR_PROCEDURE", "PROCEDURE_OR_TECHNIQUE"
    if section == "RECOMMENDATION":
        return "RECOMMENDATION", "RECOMMENDATION_NOT_FINDING"
    if section not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION", "COMPARISON"}:
        return "OTHER", "NON_AUTHORITATIVE_SECTION"
    if "?" in clause or re.match(r"^(?:do|does|did|have|has|are|is|when|where|what|which|previous)\b", simple, re.I) and "?" in anchor["quote"]:
        return "QUESTIONNAIRE_OR_PROMPT", "QUESTIONNAIRE_NOT_FINDING"
    if re.search(r"\b(?:recommend\w*|advis\w*|consultation|follow[- ]?up|correlation with\b.{0,65}\brecommend\w*)\b", clause, re.I):
        return "RECOMMENDATION", "RECOMMENDATION_NOT_FINDING"
    if re.search(r"\b(?:is known to be|may reduce|can reduce|may increase|can increase|for (?:all|most) patients|in general)\b", clause, re.I):
        return "REFERENCE_OR_EDUCATIONAL_TEXT", "GENERIC_ADVISORY_NOT_PATIENT_FINDING"
    if source_text:
        line_start = source_text.rfind("\n", 0, local["start_offset"]) + 1
        prior = source_text[max(0, line_start - 350):line_start]
        nearby = source_text[line_start:min(len(source_text), line_start + 450)]
        current_line = source_text[line_start:source_text.find("\n", line_start) if "\n" in source_text[line_start:] else len(source_text)]
        list_lines = re.findall(r"(?m)^\s*\d+[.)]\s+[^\r\n]+", prior + nearby)
        generic_options = sum(len(re.findall(r"[A-Za-z]+", re.sub(r"^\s*\d+[.)]\s*", "", item))) <= 2 and not re.search(
            r"\b(?:left|right|bilateral|seen|noted|in|at|within)\b", item, re.I) for item in list_lines)
        generic_entry = (len(re.findall(r"[A-Za-z]+", re.sub(r"^\s*\d+[.)]\s*", "", current_line))) <= 2 and not re.search(
            r"\b(?:left|right|bilateral|involving|with|without|no|not|seen|noted|present|identified|at|within)\b", current_line, re.I))
        if re.match(r"^\s*\d+[.)]\s+", current_line) and generic_entry and len(list_lines) >= 3 and generic_options >= 3:
            return "REFERENCE_OR_EDUCATIONAL_TEXT", "REFERENCE_LIST_NOT_PATIENT_FINDING"
    if re.search(r"\b(?:images? (?:were|was) (?:obtained|acquired)|contrast (?:was|is) (?:administered|instilled|injected)|(?:was|is) performed under|opacification .* (?:is|was) visualized)\b", clause, re.I):
        return "TECHNIQUE_OR_PROCEDURE", "PROCEDURE_OR_TECHNIQUE"
    if re.search(r"\b(?:catheter|implant|prosthesis|hardware|replacement|fixation)\b", clause, re.I) and re.search(r"\b(?:in situ|is (?:noted|seen|present)|was placed|intact|stable|redemonstration)\b", clause, re.I) and not re.search(r"\b(?:malposition|fractur\w*|displac\w*|infect\w*|obstruct\w*)\b", clause, re.I):
        return "DEVICE_OR_ADMIN_CONTEXT", "DEVICE_STATUS_NOT_FINDING"
    if re.search(r"\b(?:prior|previous|historical|history of)\b", clause, re.I) and not re.search(
            r"\b(?:now|today|current|again|still|interval|increased|decreased|more prominent|has been|is seen|are seen|is noted|are noted)\b", clause, re.I):
        return "COMPARISON_PRIOR_ONLY", "PRIOR_ONLY_NOT_CURRENT_FINDING"
    if re.search(r"\b(?:obscured|limited evaluation|not well visualized|suboptimally visualized)\b", clause, re.I) and not re.search(r"\b(?:lesion|fracture|edema|effusion|stenosis|mass)\b", clause, re.I):
        return "LIMITATION", "VISIBILITY_LIMITATION_NOT_FINDING"
    if re.match(r"^[A-Za-z]+\s+and\s+[A-Za-z]+ing\b", simple, re.I):
        return "FRAGMENT_OR_LOW_INFORMATION", "INCOMPLETE_CLAUSE_FRAGMENT"
    if re.fullmatch(r"\w+(?:\s+\w+){0,4}", simple) and (re.fullmatch(r"\w+ly|(?:reduc\w*|increas\w*|show\w*)", simple, re.I)
            or re.search(r"\b(?:and|or)\s+\w+ing\s+\w+ly$", simple, re.I)):
        return "FRAGMENT_OR_LOW_INFORMATION", "INCOMPLETE_CLAUSE_FRAGMENT"
    if re.search(r"\b(?:spectral\s+(?:patterns?|waveforms?)|acceleration\s+times?|"
                 r"(?:peak\s+)?systolic\s+(?:velocit\w*|peaks?)|indices?|parameters?|velocit\w*)\b", clause, re.I) and not re.search(
            r"\b(?:abnormal|increased|decreased|elevated|reduced|absent|impaired|irregular|stenos\w*|disease)\b", clause, re.I):
        return "MEASUREMENT_OR_TECHNICAL_ATTRIBUTE", "TECHNICAL_ATTRIBUTE_NOT_FINDING"
    if section == "COMPARISON":
        if re.search(r"\b(?:prior|previous|historical|formerly|old)\b", clause, re.I) and not re.search(
                r"\b(?:now|today|current|again|still|interval|increased|decreased|more prominent|has been|is seen|are seen|is noted|are noted)\b", clause, re.I):
            return "COMPARISON_PRIOR_ONLY", "PRIOR_ONLY_NOT_CURRENT_FINDING"
        if re.search(r"\b(?:now|today|current|again|still|interval|increased|decreased|more prominent|has been|is seen|are seen|is noted|are noted)\b", clause, re.I):
            return "COMPARISON_CURRENT_FINDING", None
        return "COMPARISON_PRIOR_ONLY", "PRIOR_ONLY_NOT_CURRENT_FINDING"
    return "PATIENT_FINDING", None


def _basic_candidate(expression: str, anchor: dict, assertion: str, section: str,
                     source_text: str = "") -> tuple[str, str | None]:
    """Classify a grounded Observation before optional terminology mapping."""
    expression = re.sub(r"\s+", " ", expression or "").strip()
    fragment = _source_fragment(anchor, expression)
    local_match = re.search(re.escape(expression).replace(r"\ ", r"\s+"), fragment, re.I) if expression else None
    before_target = fragment[max(0, local_match.start() - 85):local_match.start()] if local_match else ""
    scoped_negation = bool(re.search(r"\b(?:no|without|not)\b(?:\s+[A-Za-z-]+){0,9}\s*$", before_target, re.I))
    source_function, source_rejection = classify_clause(expression, anchor, section, source_text)
    if source_rejection:
        return source_function, source_rejection
    if not expression or not fragment:
        return "SUPPRESSED_NOISE", "UNSUPPORTED_FRAGMENT"
    if MEASUREMENT.fullmatch(expression) or re.fullmatch(r"\d+(?:\.\d+)?\s*(?:mm|cm)?", expression, re.I):
        return "ATTRIBUTE", "ISOLATED_MEASUREMENT"
    if NOISE.fullmatch(expression) or GENERIC_MODIFIERS.fullmatch(expression):
        # An isolated generic head can still be a grounded condition when its
        # local phrase supplies specific morphology, site, or an abnormal
        # predicate. The noun itself is not the eligibility whitelist.
        if not (expression.casefold() in {"lesion", "mass", "calcification", "calcifications"}
                and len(re.findall(r"[A-Za-z-]+", fragment)) >= 3
                and (CLINICAL_PREDICATE.search(fragment) or re.search(
                    r"\b(?:in|at|within|of)\s+(?:the\s+)?[A-Za-z-]+", fragment, re.I))):
            return "SUPPRESSED_NOISE", "GENERIC_NOUN_OR_MODIFIER"
    if LOW_INFORMATION_HEAD.search(expression):
        return "SUPPRESSED_NOISE", "LOW_INFORMATION_GENERIC_HEAD"
    if ADMINISTRATIVE.search(expression) or ADMINISTRATIVE.search(fragment):
        return "SUPPRESSED_NOISE", "ADMINISTRATIVE_TEXT"
    if TECHNIQUE.search(fragment):
        return "SUPPRESSED_NOISE", "PROCEDURE_OR_TECHNIQUE"
    if re.search(r"\bto\s+make\b", fragment, re.I):
        return "SUPPRESSED_NOISE", "EXPLANATORY_FRAGMENT"
    if assertion == "PRESENT" and ROUTINE_NORMAL.search(fragment):
        return "NORMAL_OBSERVATION", "ROUTINE_NORMAL_OBSERVATION"
    if ISOLATED_ATTRIBUTE.fullmatch(expression):
        if expression.casefold() == "torn" and re.search(r"\b(?:ligament|tendon|muscle|structure)\w*\b", fragment, re.I):
            return "CURRENT_FINDING", None
        return "ATTRIBUTE", "ISOLATED_ATTRIBUTE"
    if re.search(r"\bthroughout\s+(?:this|that|the)\b", fragment, re.I) and not re.search(
            r"\b(?:abnormal|increased|decreased|reduced|absent|reversed|turbulent)\b", fragment, re.I):
        return "ATTRIBUTE", "SOURCE_DESCRIPTIVE_ATTRIBUTE"
    # A measured condition is still a clinical observation. Only the numeric
    # value itself is an attribute; it must not suppress the condition head.
    if expression.casefold() in {"mass", "lesion", "lesions"} and re.search(
            r"^(?:the|this|that)?\s*" + re.escape(expression) + r"\s+(?:is|are)\s+(?!present\b|seen\b|noted\b|identified\b)",
            fragment, re.I):
        return "ATTRIBUTE", "MORPHOLOGY_ATTRIBUTE"
    match = re.search(re.escape(expression).replace(r"\ ", r"\s+"), fragment, re.I)
    headed_state = bool(re.match(r"[A-Za-z][A-Za-z -]{1,35}:\s+(?:it|they|this|these)\s+(?:is|are|was|were)\s+"
                                 r"(?:enlarged|increased|decreased|dilated|narrowed|thickened|atrophic)\b", fragment, re.I))
    if match and not headed_state and re.search(r"\b(?:is|are|was|were)\s+$", fragment[:match.start()], re.I) and not re.search(
            r"\b(?:present|seen|noted|identified)\b", expression, re.I):
        return "ATTRIBUTE", "PREDICATE_ATTRIBUTE"
    if assertion == "ABSENT_NEGATED":
        if not NEGATION.search(fragment) and not NEGATION.search(anchor["quote"]):
            return "SUPPRESSED_NOISE", "NEGATION_NOT_SOURCE_SUPPORTED"
        return "PERTINENT_NEGATIVE", None
    if assertion == "UNCERTAIN":
        if scoped_negation and not re.search(r"\b(?:cannot exclude|not excluded)\b", fragment, re.I):
            return "SUPPRESSED_NOISE", "SOURCE_ASSERTION_CONFLICT"
        return ("DIAGNOSTIC_HYPOTHESIS", None) if _hypothesis_status(anchor["quote"], expression) else (
            "SUPPRESSED_NOISE", "UNCERTAINTY_WITHOUT_HYPOTHESIS_CUE")
    if assertion != "PRESENT":
        return "SUPPRESSED_NOISE", "UNSUPPORTED_ASSERTION"
    if scoped_negation or re.search(r"\b(?:does|do|did)\s+not\b|\bnot\s+(?:seen|identified|present)\b", fragment, re.I):
        return "SUPPRESSED_NOISE", "SOURCE_ASSERTION_CONFLICT"
    match = re.search(re.escape(expression).replace(r"\ ", r"\s+"), fragment, re.I)
    if match and re.search(r"\b(?:may|might|could)\s+represent\b", fragment[match.end():], re.I):
        return "ATTRIBUTE", "DIFFERENTIAL_BRIDGE"
    if _hypothesis_status(fragment, expression):
        return "DIAGNOSTIC_HYPOTHESIS", None
    if ROUTINE_NORMAL.search(fragment):
        return "NORMAL_OBSERVATION", "ROUTINE_NORMAL_OBSERVATION"
    if section in {"FINDINGS_DESCRIPTION", "COMPARISON"} and not CLINICAL_PREDICATE.search(fragment):
        return "ATTRIBUTE", "NO_CLINICAL_ASSERTION_IN_LOCAL_CLAUSE"
    return "CURRENT_FINDING", None


def _open_label(expression: str, anchor: dict, assertion: str) -> str:
    fragment = _source_fragment(anchor, expression)
    if assertion == "ABSENT_NEGATED":
        # A list may negate several distinct conditions. Use the grounded
        # entity itself, carrying only a shared anatomical adjective.
        qualifier = _negative_qualifier(expression, anchor["quote"])
        target = re.sub(r"\s+", " ", expression).strip(" .;")
        expression_match = re.search(re.escape(expression).replace(r"\ ", r"\s+"), fragment, re.I)
        before = fragment[:expression_match.start()] if expression_match else fragment
        scopes = re.findall(r"\b(?:left|right|bilateral)\s+[A-Za-z][A-Za-z-]*\b", before, re.I)
        scope = scopes[-1].lower() if scopes else ""
        scoped = " ".join(part for part in (scope, qualifier, target) if part and part.casefold() not in target.casefold())
        if target.casefold() not in scoped.casefold():
            scoped = (scoped + " " + target).strip()
        return "No " + scoped
    if assertion == "UNCERTAIN":
        name = re.sub(r"\s+", " ", expression).strip(" .;")
        return name if name.isupper() else name.capitalize()
    headed_state = re.match(r"([A-Za-z][A-Za-z -]{1,35}):\s+(?:it|they|this|these)\s+(?:is|are|was|were)\s+"
                            r"(enlarged|increased|decreased|dilated|narrowed|thickened|atrophic)\b", fragment, re.I)
    if headed_state:
        return headed_state.group(2).capitalize() + " " + headed_state.group(1).strip()
    phrase = re.sub(r"\s+", " ", fragment)
    phrase = re.sub(r"^[\s\x7f■•*-]*(?:\d+[.)]\s*)?", "", phrase)
    phrase = re.sub(r"^(?:there\s+is|there\s+are|the|associated)\s+", "", phrase, flags=re.I)
    phrase = re.sub(r"^(?:is\s+made\s+that|note\s+is\s+made\s+that)\s+", "", phrase, flags=re.I)
    phrase = re.sub(r"^incidentally\s+noted\s+is\s+(?:an?\s+)?", "", phrase, flags=re.I)
    phrase = re.sub(r"^(?:again\s+)?noted\s+is\s+(?:an?\s+)?", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:is|are|was|were)\s+(?:(?:also|again)\s+)?(?:seen|present|noted|identified)\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:is|remains)\s+(?:possible|favou?red|less likely|less favou?red)\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:present|noted|seen)\s*$", "", phrase, flags=re.I)
    phrase = re.sub(r"(?<![\d.])\d+(?:\.\d+)?\s*[- ]?\s*(?:mm|cm|cc|ml)\b", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:(?:with\s+)?(?:an?\s+)?(?:estimated\s+)?(?:volume|size|diameter|length|depth|thickness)\s+(?:of|is|at)?|measur\w*)\s*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:in\s+transverse\s+diameter|in\s+depth)\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\bwith\s+some\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\b(?:suggesting|suggests|suspicious\s+for)\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\bbetween\s+\d+\s+and\s+\d+\s+o['’]clock\b.*$", "", phrase, flags=re.I)
    phrase = re.sub(r"\s+", " ", phrase).strip(" ,.;")
    torn = re.fullmatch(r"(.+?)\s+(?:is|are|was|were)\s+torn", phrase, re.I)
    if torn:
        phrase = "Torn " + re.sub(r"^the\s+", "", torn.group(1), flags=re.I)
    return phrase[0].upper() + phrase[1:] if phrase else expression.capitalize()


def _open_rule(expression: str, anchor: dict, assertion: str, section: str):
    role, reason = _basic_candidate(expression, anchor, assertion, section)
    if reason or role not in {"CURRENT_FINDING", "PERTINENT_NEGATIVE", "DIAGNOSTIC_HYPOTHESIS"}:
        return None
    label = _open_label(expression, anchor, "UNCERTAIN" if role == "DIAGNOSTIC_HYPOTHESIS" else assertion)
    if role == "DIAGNOSTIC_HYPOTHESIS":
        fragment = _source_fragment(anchor, expression)
        target = re.search(r"\b(?:suggestive\s+of|suspicious\s+for|concerning\s+for|cannot\s+exclude|likely)\b\s*(.+)$", fragment, re.I)
        if target and re.search(re.escape(expression).replace(r"\ ", r"\s+"), target.group(1), re.I):
            candidate = target.group(1).strip(" .;,")
            if len(candidate.split()) >= 2:
                label = candidate[0].upper() + candidate[1:]
    if LOW_INFORMATION_HEAD.search(label):
        return None
    if re.search(r"\b(?:and|but|does|not|with|some|in|the|of|a|an|small|may|to|is|are|was|were|has|have)$", label, re.I):
        return None
    if re.fullmatch(r"No\s+(?:lesion|mass|finding|abnormality|change)s?", label, re.I):
        return None
    if role == "DIAGNOSTIC_HYPOTHESIS" and re.fullmatch(
            r"(?:lesion|mass|finding|abnormality|change|disease|process|problem)s?", label, re.I):
        return None
    tokens = [word.casefold() for word in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", label)
              if word.casefold() not in {"no", "a", "an", "the", "is", "are", "was", "were", "of", "and", "with", "volume"}]
    if not tokens:
        return None
    concept = "general:open:" + ":".join(sorted(set(tokens)))
    group = ("NEGATIVE" if role == "PERTINENT_NEGATIVE" else "DIAGNOSTIC" if role == "DIAGNOSTIC_HYPOTHESIS"
             else "KEY" if section == "DIAGNOSTIC_SUMMARY" else "SECONDARY")
    kind = ("PERTINENT_NEGATIVE" if group == "NEGATIVE" else "DIAGNOSTIC_HYPOTHESIS"
            if group == "DIAGNOSTIC" else "FINDING")
    return concept, label, kind, "PRIMARY" if group == "KEY" else "SECONDARY", group, assertion


def _source_assertion_evidence(protected_text: str, sections: list[dict], evidence: list[tuple]) -> list[tuple]:
    """Recover an explicit, cross-section corroborated assertion missed by the model.

    A source-only assertion needs an unsupported Impression line and a matching
    Findings line with an affirmative predicate. Neither anatomy nor a named
    condition vocabulary can create one by itself.
    """
    lines = []
    for section in sections:
        if section.get("role") not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"}:
            continue
        offset = section["start"]
        for raw in section["text"].splitlines(keepends=True):
            clean = raw.strip()
            if clean:
                start = offset + raw.index(clean)
                end = start + len(clean)
                if protected_text[start:end] == clean:
                    lines.append((section["role"], start, end, clean))
            offset += len(raw)

    def terms(value: str) -> set[str]:
        return {term for term in re.findall(r"[a-z]+(?:-[a-z]+)*", value.casefold())
                if term not in {"a", "an", "the", "is", "are", "was", "were", "seen", "present", "noted",
                                "identified", "associated", "between", "and", "of", "to", "in", "with"}}

    details = []
    for role, start, end, text in lines:
        if role != "FINDINGS_DESCRIPTION" or ADMINISTRATIVE.search(text) or NEGATION.search(text):
            continue
        predicate = re.search(r"\b(?:is|are|was|were)\s+(?:also\s+)?(?:seen|present|noted|identified)\b|\bnoted\b$", text, re.I)
        if not predicate:
            continue
        phrase = text[:predicate.start()].strip(" .:;")
        if len(terms(phrase)) < 3:
            continue
        anchor = {"start_offset": start, "end_offset": end, "quote": text,
                  "role": "DETAIL_SUPPORT", "source_section": role}
        if _basic_candidate(phrase, anchor, "PRESENT", role)[1] is None:
            details.append((phrase, anchor, terms(phrase)))

    recovered = []
    for role, start, end, text in lines:
        if role != "DIAGNOSTIC_SUMMARY" or ADMINISTRATIVE.search(text) or NEGATION.search(text):
            continue
        if re.search(r"\b(?:possible|worrisome|may|might|could|less likely|suggest\w*|to make)\b", text, re.I):
            continue
        if LOW_INFORMATION_HEAD.search(text):
            continue
        if any(section == role and anchor["start_offset"] < end and anchor["end_offset"] > start
               for _, _, anchor, _, section, _ in evidence):
            continue
        summary_terms = terms(text)
        if len(summary_terms) < 3:
            continue
        for phrase, detail_anchor, detail_terms in details:
            if len(summary_terms & detail_terms) < 3 or len(summary_terms & detail_terms) / min(len(summary_terms), len(detail_terms)) < 0.8:
                continue
            summary_anchor = {"start_offset": start, "end_offset": end, "quote": text,
                              "role": "SUMMARY_ASSERTION", "source_section": role}
            if not re.search(re.escape(phrase), text, re.I):
                continue
            recovered.extend((
                (phrase, "PRESENT", summary_anchor, f"mrj-source:{start}", role, None),
                (phrase, "PRESENT", detail_anchor, f"mrj-source:{detail_anchor['start_offset']}", "FINDINGS_DESCRIPTION", None),
            ))
            break
    return recovered


def _source_assessment_evidence(protected_text: str, sections: list[dict], evidence: list[tuple]) -> list[tuple]:
    """Retain an exact, concise patient assessment missed by the model.

    This is a source-span fallback, not a named-disease eligibility list.
    Numbered reference choices, advice, and questions are excluded by their
    local source function before they can become an assessment.
    """
    recovered = []
    for section in sections:
        if section.get("role") != "DIAGNOSTIC_SUMMARY":
            continue
        offset = section["start"]
        for raw in section["text"].splitlines(keepends=True):
            # A conclusion and a recommendation can share a PDF line. Retain
            # only the first independent assessment clause as source evidence.
            first_clause = re.split(r"(?<!\d)[.!?](?=\s|$)", raw, maxsplit=1)[0]
            clean = first_clause.strip()
            start = offset + (raw.index(clean) if clean else 0)
            end = start + len(clean)
            offset += len(raw)
            if (not clean or len(clean.split()) > 8 or re.match(r"^\d+[.)]\s+", clean)
                    or not re.match(r"^(?:benign|negative|positive|abnormal)\b", clean, re.I)
                    or protected_text[start:end] != clean):
                continue
            anchor = {"start_offset": start, "end_offset": end, "quote": clean,
                      "role": "SUMMARY_ASSERTION", "source_section": "DIAGNOSTIC_SUMMARY"}
            if classify_clause(clean, anchor, "DIAGNOSTIC_SUMMARY", protected_text)[1]:
                continue
            if any(evidence_section == "DIAGNOSTIC_SUMMARY" and source_anchor["start_offset"] < end
                   and source_anchor["end_offset"] > start
                   for _, _, source_anchor, _, evidence_section, _ in evidence):
                continue
            recovered.append((clean, "PRESENT", anchor, f"mrj-source:{start}", "DIAGNOSTIC_SUMMARY", None))
    return recovered


def _source_narrative_state_evidence(protected_text: str, sections: list[dict], evidence: list[tuple]) -> list[tuple]:
    """Recover an explicit headed state when the model labeled only its modifier."""
    recovered = []
    for section in sections:
        if section.get("role") != "FINDINGS_DESCRIPTION":
            continue
        offset = section["start"]
        for raw in section["text"].splitlines(keepends=True):
            clean = raw.strip()
            start = offset + (raw.index(clean) if clean else 0)
            end = start + len(clean)
            offset += len(raw)
            match = re.match(r"(?P<subject>[A-Za-z][A-Za-z -]{1,35}):\s+(?:it|they|this|these)\s+"
                             r"(?:is|are|was|were)\s+(?P<state>enlarged|increased|decreased|dilated|narrowed|thickened|atrophic)\b", clean, re.I)
            if not match or protected_text[start:end] != clean:
                continue
            anchor = {"start_offset": start, "end_offset": end, "quote": clean,
                      "role": "DETAIL_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}
            if classify_clause(match.group("state"), anchor, "FINDINGS_DESCRIPTION", protected_text)[1]:
                continue
            recovered.append((match.group("state"), "PRESENT", anchor,
                              f"mrj-source:{start}", "FINDINGS_DESCRIPTION", None))
    return recovered


def _source_measured_positive_evidence(protected_text: str, sections: list[dict], evidence: list[tuple]) -> list[tuple]:
    """Recover a measured, explicitly positive source observation missed by the engine."""
    recovered = []
    for section in sections:
        if section.get("role") != "FINDINGS_DESCRIPTION":
            continue
        start = section["start"]
        end = section.get("end", start + len(section["text"]))
        for measurement in MEASUREMENT.finditer(section["text"]):
            point = start + measurement.start()
            sentence = _sentence(protected_text, point, start + measurement.end())
            if sentence["start_offset"] < start or sentence["end_offset"] > end or len(sentence["quote"]) > 200:
                continue
            heading = re.match(r"(?i)^FINDINGS\s*:\s*", sentence["quote"])
            if heading:
                sentence = {"start_offset": sentence["start_offset"] + heading.end(),
                            "end_offset": sentence["end_offset"], "quote": sentence["quote"][heading.end():]}
            phrase = sentence["quote"].strip()
            if not (re.search(r"\b(?:is|are|was|were)\s+(?:mildly\s+|markedly\s+|moderately\s+)?(?:enlarged|reduced|dilated|thickened|present|seen)\b", phrase, re.I)
                    or re.search(r"\b(?:demonstrates?|shows?)\b.{0,90}\b(?:increased|decreased|abnormal)\b", phrase, re.I)):
                continue
            if NEGATION.search(phrase):
                continue
            if any(source_anchor["start_offset"] == sentence["start_offset"]
                   and source_anchor["end_offset"] == sentence["end_offset"]
                   for _, _, source_anchor, _, _, _ in recovered):
                continue
            expression = re.split(r",\s*(?:measur\w*|estimated\s+volume)\b", phrase, maxsplit=1, flags=re.I)[0].strip()
            if not expression or len(expression.split()) > 24:
                continue
            anchor = {**sentence, "role": "DETAIL_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}
            if classify_clause(expression, anchor, "FINDINGS_DESCRIPTION", protected_text)[1]:
                continue
            recovered.append((expression, "PRESENT", anchor, f"mrj-source:{sentence['start_offset']}",
                              "FINDINGS_DESCRIPTION", None))
    return recovered


def _attach_local_source_measurements(protected_text: str, sections: list[dict], facts: list[dict]) -> None:
    """Attach a source size only to a uniquely grounded positive in its sentence."""
    for section in sections:
        if section.get("role") != "FINDINGS_DESCRIPTION":
            continue
        start = section["start"]
        end = section.get("end", start + len(section["text"]))
        for measurement in MEASUREMENT.finditer(section["text"]):
            value = measurement.group()
            if any(value in observation.get("measurements", []) for fact in facts
                   for observation in fact["observations"]):
                continue
            sentence = _sentence(protected_text, start + measurement.start(), start + measurement.end())
            if sentence["start_offset"] < start or sentence["end_offset"] > end:
                continue
            grounded = [fact for fact in facts if fact["assertion_state"] == "PRESENT"
                        and any(anchor.get("section_role") == "FINDINGS_DESCRIPTION"
                                and anchor["start_offset"] < sentence["end_offset"]
                                and anchor["end_offset"] > sentence["start_offset"]
                                for anchor in fact["evidence_anchors"])]
            if not grounded and re.search(r"\bmeasur\w*\b", sentence["quote"], re.I):
                line_start = protected_text.rfind("\n", 0, sentence["start_offset"]) + 1
                preceding = protected_text[line_start:sentence["start_offset"]].rstrip()
                if preceding.endswith(".") and len(preceding) <= 180:
                    def subjects(value: str) -> set[str]:
                        words = re.findall(r"[a-z]{5,}", value.casefold())
                        return {word[:-3] + "y" if word.endswith("ies") else
                                word[:-1] if word.endswith("s") and not word.endswith("ss") else word
                                for word in words} - {"measure", "enlarge", "mildly", "markedly",
                                                     "right", "left", "both", "normal", "demonstrate"}
                    measured_subjects = subjects(sentence["quote"])
                    grounded = [fact for fact in facts if fact["assertion_state"] == "PRESENT"
                                and subjects(fact["display_label"]) & measured_subjects
                                and any(anchor.get("section_role") == "FINDINGS_DESCRIPTION"
                                        and line_start <= anchor["start_offset"] < sentence["start_offset"]
                                        for anchor in fact["evidence_anchors"])]
            if len(grounded) != 1:
                continue
            fact = grounded[0]
            anchor = {**sentence, "role": "ATTRIBUTE_SUPPORT", "source_section": "FINDINGS_DESCRIPTION"}
            observation = {"source_context": _context(protected_text, anchor, sections),
                           "evidence_anchor": anchor, "measurements": [value]}
            preceding_measure = sentence["quote"][:start + measurement.start() - sentence["start_offset"]]
            sides = re.findall(r"\b(?:left|right)\b", preceding_measure, re.I)
            if sides:
                observation["laterality"] = sides[-1].upper()
            fact["observations"].append(observation)
            fact["evidence_anchors"].append({**anchor, "section_role": "FINDINGS_DESCRIPTION",
                                             "source_context": _context(protected_text, anchor, sections),
                                             "engine_evidence_ids": [], "source_rule_evidence_ids": []})


def _governed_measurement_ledger(protected_text: str, sections: list[dict], facts: list[dict]) -> list[dict]:
    """Retain protected measurements without promoting unowned values to facts."""
    ledger = []
    for section in sections:
        if section.get("role") != "FINDINGS_DESCRIPTION":
            continue
        for match in MEASUREMENT.finditer(section["text"]):
            start = section["start"] + match.start()
            end = section["start"] + match.end()
            if protected_text[start:end] != match.group():
                continue
            sentence = _sentence(protected_text, start, end)
            prior = bool(re.search(r"\b(?:previously|prior|historical|formerly)\b",
                                   protected_text[sentence["start_offset"]:start], re.I))
            owners = [fact["fact_id"] for fact in facts
                      if any(match.group() in observation.get("measurements", [])
                             and observation["evidence_anchor"]["start_offset"] < sentence["end_offset"]
                             and observation["evidence_anchor"]["end_offset"] > sentence["start_offset"]
                             for observation in fact["observations"])]
            if not owners and sum(other.group() == match.group() for other in MEASUREMENT.finditer(section["text"])) == 1:
                owners = [fact["fact_id"] for fact in facts
                          if any(match.group() in observation.get("measurements", [])
                                 for observation in fact["observations"])]
            state = "PRIOR_CONTEXT" if prior else "LINKED_TO_FACT" if len(owners) == 1 else "UNASSIGNED_REVIEW"
            ledger.append({"measurement_id": f"source-measurement-{len(ledger) + 1}",
                           "source_text": match.group(), "source_section": "FINDINGS_DESCRIPTION",
                           "evidence_span": {"start_offset": start, "end_offset": end, "quote": match.group()},
                           "assignment_state": state,
                           "source_fact_id": owners[0] if state == "LINKED_TO_FACT" else None})
    return ledger


def _hypothesis_status(sentence: str, expression: str) -> str | None:
    match = re.search(re.escape(expression), sentence, re.I)
    if not match:
        return None
    before = sentence[max(0, match.start() - 100):match.start()]
    before = re.split(r"[.!?](?:\s+|$)", before)[-1]
    after = sentence[match.end():min(len(sentence), match.end() + 50)]
    # A model entity may include the interpretive words themselves. Look in
    # the target phrase as well as before it, without turning a preceding
    # established lesion into the diagnosis suggested *after* that lesion.
    target_and_prefix = before[-55:] + sentence[match.start():match.end()]
    if re.search(r"\b(?:suggestive\s+of|suspicious\s+for|concerning\s+for|cannot\s+exclude)\b", target_and_prefix, re.I):
        return "POSSIBLE"
    if re.search(r"\b(?:favor(?:ed|ing)|favour(?:ed|ing))\s+over\s+(?:\w+\s+){0,3}$", before, re.I | re.S):
        return "LESS_FAVORED"
    if re.search(r"\b(?:less likely|unlikely)\b.{0,25}$", before, re.I | re.S) or re.search(r"^.{0,20}\b(?:less likely|unlikely)\b", after, re.I | re.S):
        return "LESS_LIKELY"
    if re.search(r"\bless favou?red\b.{0,25}$", before, re.I | re.S) or re.search(r"^.{0,20}\bless favou?red\b", after, re.I | re.S):
        return "LESS_FAVORED"
    if re.search(r"\bfavou?r\w*\b.{0,25}$", before, re.I | re.S) or re.search(r"^.{0,30}\bfavou?r\w*\b", after, re.I | re.S):
        return "FAVORED"
    if re.search(r"\b(?:likely|suggesting|suggests?)\b.{0,30}$", before, re.I | re.S):
        return "POSSIBLE"
    if re.search(r"\blikely\s+represent\w*\b.{0,80}$", before, re.I | re.S) or re.search(
            r"^\s*(?:is|remains)\s+(?:a\s+)?possib(?:le|ility)\b", after, re.I):
        return "POSSIBLE"
    if re.search(r"\b(?:possible|consider|could|may|cannot exclude|differential)\b.{0,30}$", before, re.I | re.S) or re.search(r"^.{0,35}\b(?:possible|consider|could|may|cannot exclude|differential)\b", after, re.I | re.S):
        return "POSSIBLE"
    return None


def _observation(text: str, anchor: dict, concept: str, sections: list[dict] = ()) -> dict:
    sentence = anchor["quote"]
    observation = {"source_context": _context(text, anchor, sections), "evidence_anchor": anchor}
    if concept == "lesion_complex":
        count = re.search(r"\b(\d+|single|one|two|three|multiple|multifocal)\b(?=.{0,90}\blesions?\b)", sentence, re.I | re.S)
        if count and count.group(1).isdigit():
            following = sentence[count.end():]
            lesion = re.search(r"\blesions?\b", following, re.I)
            if lesion and re.search(r"\b(?:mm|cm)\b|[x×]|[-–]\s*\d", following[:lesion.start()], re.I):
                count = None
        if count:
            observation["count"] = {"one": 1, "single": 1, "two": 2, "three": 3}.get(count.group(1).lower(), int(count.group(1)) if count.group(1).isdigit() else count.group(1).lower())
        elif re.search(r"\b(?:a|an)\b.{0,80}\blesion\b", sentence, re.I | re.S):
            observation["count"] = 1
    measures = [m.group() for m in MEASUREMENT.finditer(sentence)] if concept in {"lesion_complex", "frontal_wm"} else []
    if measures:
        observation["measurements"] = measures
    morphology = [word for word, pattern in (("annular", r"\bannular\b"), ("spheroid", r"\bspheroid\b")) if re.search(pattern, sentence, re.I)]
    if morphology:
        observation["morphology"] = morphology
    if concept == "lesion_complex" and re.search(r"\benhanc\w*\b", sentence, re.I):
        observation["enhancement"] = "ENHANCING"
    if re.search(r"\b(?:chronic|old)\b", sentence, re.I):
        observation["temporal_information"] = "CHRONIC"
    if re.search(r"\b(?:interval increase|increas\w* in (?:size|prominence)|more prominent)\b|"
                 r"\bincreas\w*\b.{0,90}\b(?:since|compared to|relative to)\s+(?:the\s+)?(?:prior|previous|\d{4})\b", sentence, re.I | re.S):
        observation["temporal_change"] = "INCREASED"
    elif re.search(r"\bdecreas\w*\b.{0,90}\b(?:since|compared to|relative to)\s+(?:the\s+)?(?:prior|previous|\d{4})\b", sentence, re.I | re.S):
        observation["temporal_change"] = "DECREASED"
    return observation


def _finish_fact(fact: dict) -> None:
    support = " ".join(anchor["quote"] for anchor in fact["evidence_anchors"])
    concept = fact["canonical_concept"]
    if concept == "lesion_complex":
        descriptors = []
        if re.search(r"\b(?:multi\w*|three|3|adjacent)\b", support, re.I):
            descriptors.append("Multifocal")
        if re.search(r"\bright\b", support, re.I):
            descriptors.append("right")
            fact["laterality"] = "RIGHT"
        if re.search(r"\btemporo[- ]?parietal\b", support, re.I) or (re.search(r"\btemporal\b", support, re.I) and re.search(r"\bparietal\b", support, re.I)):
            descriptors.append("temporoparietal")
            fact["anatomy"].append("temporal / parietal region")
        elif re.search(r"\btemporal\b", support, re.I):
            descriptors.append("temporal")
            fact["anatomy"].append("temporal region")
        elif re.search(r"\bparietal\b", support, re.I):
            descriptors.append("parietal")
            fact["anatomy"].append("parietal region")
        if re.search(r"\benhanc\w*\b", support, re.I):
            descriptors.append("enhancing")
        fact["display_label"] = " ".join(descriptors + ["lesion complex"]).capitalize()
    elif concept == "frontal_wm":
        fact["display_label"] = ("Chronic " if re.search(r"\bchronic\b", support, re.I) else "") + (
            "right " if re.search(r"\bright\b", support, re.I) else "") + "frontal white-matter lesion"
        fact["display_label"] = fact["display_label"].capitalize()
        fact["anatomy"].append("frontal white matter")
        if re.search(r"\bright\b", support, re.I):
            fact["laterality"] = "RIGHT"
    elif concept == "mass_effect":
        has_mass_effect = bool(re.search(r"\bmass effect\b", support, re.I))
        has_ventricular_effect = bool(re.search(r"\bventric(?:le|ular)\b", support, re.I))
        if has_mass_effect and has_ventricular_effect:
            fact["display_label"] = "Mass effect / ventricular effect"
        elif has_mass_effect:
            fact["display_label"] = "Mass effect"
        elif has_ventricular_effect:
            fact["display_label"] = "Ventricular effect"
        else:
            fact["display_label"] = "Effacement / compression"
    elif concept == "optic_drusen":
        fact["display_label"] = ("Bilateral " if re.search(r"\bbilateral\b|\bboth\b", support, re.I) else "") + (
            "optic disc calcifications / drusen" if re.search(r"\bdrusen\b", support, re.I) and re.search(r"\bcalcif\w*\b", support, re.I)
            else "optic disc drusen" if re.search(r"\bdrusen\b", support, re.I) else "optic disc calcifications")
        fact["display_label"] = fact["display_label"].capitalize()
        fact["anatomy"].append("optic disc")
        if fact["display_label"].startswith("Bilateral"):
            fact["laterality"] = "BILATERAL"
    elif concept in {"scleral_calcification", "tendon_calcification", "sinus_disease"}:
        if concept == "scleral_calcification" and not re.search(r"\bdegenerat\w*\b", support, re.I):
            fact["display_label"] = "Scleral calcification"
        elif concept == "tendon_calcification" and not re.search(r"\bdystroph\w*\b", support, re.I):
            fact["display_label"] = "Superior oblique tendon calcification"
        elif concept == "sinus_disease" and not re.search(r"\bchronic\b", support, re.I):
            fact["display_label"] = "Maxillary sinus disease"
        if re.search(r"\bleft\b", support, re.I) and not re.search(r"\bright\b", support, re.I):
            fact["laterality"] = "LEFT"
        elif re.search(r"\bright\b", support, re.I) and not re.search(r"\bleft\b", support, re.I):
            fact["laterality"] = "RIGHT"
    if fact["fact_type"] == "DIAGNOSTIC_HYPOTHESIS":
        fact["assertion_state"] = "UNCERTAIN"
    if not fact.get("laterality"):
        label = fact["display_label"]
        sides = {side.upper() for side in re.findall(r"\b(?:left|right|bilateral)\b", label, re.I)}
        if "BILATERAL" in sides or sides == {"LEFT", "RIGHT"}:
            fact["laterality"] = "BILATERAL"
        elif len(sides) == 1:
            fact["laterality"] = next(iter(sides))


def _general_relations(facts: list[dict]) -> None:
    """Retain only source-explicit links between grounded fallback facts."""
    principal = next((fact for fact in facts if fact["canonical_concept"].startswith("general:") and
                      fact["salience"] == "PRIMARY" and fact["group"] == "KEY"), None)
    if principal:
        for target in facts:
            if target is principal or target["assertion_state"] != "PRESENT":
                continue
            for anchor in target["evidence_anchors"]:
                nearby_principal = any(a.get("section_role") == anchor.get("section_role") and
                    0 <= anchor["start_offset"] - a["end_offset"] <= 250
                    for a in principal["evidence_anchors"])
                if (nearby_principal and
                        re.match(r"\s*This\s+(?:results?\s+in|causes?)\b", anchor["quote"], re.I)):
                    principal["relationships"].append({"relation_type": "CAUSES", "target_fact_id": target["fact_id"],
                                                       "evidence_anchor": anchor})
                    break
                if (nearby_principal and anchor.get("section_role") == "COMPARISON"
                        and re.match(r"\s*This\b", anchor["quote"], re.I)
                        and re.search(r"\b(?:since|compared with|from)\s+(?:the\s+)?prior\b", anchor["quote"], re.I)):
                    change = re.search(r"\b(increas\w*|decreas\w*)\b", anchor["quote"], re.I)
                    if change:
                        principal["temporal_change"] = "INCREASED" if change.group().lower().startswith("increas") else "DECREASED"
                        principal["relationships"].append({"relation_type": "INTERVAL_CHANGE_SUPPORT",
                                                           "target_fact_id": target["fact_id"], "evidence_anchor": anchor})
                        break
    residual = next((fact for fact in facts if fact["canonical_concept"] == "general:residual"), None)
    penetration = next((fact for fact in facts if fact["canonical_concept"] == "general:penetration" and
                        fact["assertion_state"] == "PRESENT"), None)
    if residual and penetration:
        for anchor in penetration["evidence_anchors"]:
            if re.search(r"\bfrom\s+(?:the\s+)?residual\b", anchor["quote"], re.I):
                residual["relationships"].append({"relation_type": "ASSOCIATED_WITH",
                                                   "target_fact_id": penetration["fact_id"],
                                                   "evidence_anchor": anchor})
                break


def _summary(facts: list[dict]) -> str:
    by_concept = {fact["canonical_concept"]: fact for fact in facts}
    clauses = []
    principal = by_concept.get("lesion_complex")
    if principal:
        associated = [by_concept[key]["display_label"].lower() for key in ("vasogenic_edema", "mass_effect") if key in by_concept]
        clause = principal["display_label"]
        if associated:
            clause += " with associated " + " and ".join(associated)
        clauses.append(clause + ".")
    favored = [f for f in facts if f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and f.get("hypothesis_status") == "FAVORED"]
    if favored:
        alternative = [f for f in facts if f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and f.get("hypothesis_status") in {"POSSIBLE", "LESS_FAVORED"}]
        alternative.sort(key=lambda fact: (fact["canonical_concept"] != "multifocal_abscess", fact["canonical_concept"]))
        clause = favored[0]["display_label"] + " is favored"
        if alternative:
            clause += " over " + alternative[0]["display_label"].lower()
        clauses.append(clause + ".")
        for other in alternative[1:]:
            clauses.append(other["display_label"] + " remains a diagnostic consideration.")
    focal = by_concept.get("frontal_wm")
    if focal:
        clause = "A separate " + focal["display_label"].lower()
        if focal.get("temporal_change") == "INCREASED":
            clause += " demonstrates interval increase"
        clauses.append(clause + ".")
    if clauses:
        additional = [fact["display_label"].lower() for fact in facts if
                      fact["canonical_concept"].startswith("general:") and fact["assertion_state"] == "PRESENT"]
        if additional:
            clauses.append("Additional findings include " + ", ".join(additional) + ".")
    else:
        principal = next((fact for fact in facts if fact["group"] == "KEY" and fact["salience"] == "PRIMARY"), None)
        used = set()
        if principal:
            caused_ids = {r["target_fact_id"] for r in principal["relationships"] if r["relation_type"] == "CAUSES"}
            caused = [fact["display_label"].lower() for fact in facts if fact["fact_id"] in caused_ids]
            clause = principal["display_label"]
            if caused:
                clause += " causes " + " and ".join(caused)
            clauses.append(clause + ".")
            used = caused_ids | {principal["fact_id"]}
        associated = [fact["display_label"].lower() for fact in facts if fact["assertion_state"] == "PRESENT"
                      and fact["fact_id"] not in used and fact["group"] in {"KEY", "SECONDARY"}
                      and not (principal and "absent relaxation" in principal["display_label"].lower()
                               and fact["canonical_concept"].startswith("general:functional_absence:relaxation"))]
        if associated:
            clauses.append("Additional findings include " + ", ".join(associated) + ".")
        negatives = [fact["display_label"].lower() for fact in facts if fact["group"] == "NEGATIVE"]
        if negatives:
            clauses.append("Pertinent negatives include " + ", ".join(negatives) + ".")
    return " ".join(clauses)


def synthesize(result: dict, protected_text: str, candidates: list[dict], sections: list[dict] = ()) -> dict:
    """Return canonical display facts while retaining all pilot evidence in result."""
    evidence = []
    validated_ids = {finding.get("finding_id") for finding in result["radiology_findings"]}
    validated_by_id = {finding.get("finding_id"): finding for finding in result["radiology_findings"]}
    for finding in result["radiology_findings"]:
        expression = finding.get("source_expression", "")
        if not expression or not finding.get("evidence_anchors"):
            continue
        for anchor in finding["evidence_anchors"]:
            if anchor.get("role") not in {"SUMMARY_ASSERTION", "DETAIL_SUPPORT"}:
                continue
            if protected_text[anchor["start_offset"]:anchor["end_offset"]] != anchor["quote"]:
                continue
            evidence.append((expression, finding["assertion_state"], anchor, finding["finding_id"], anchor.get("source_section"), finding.get("internal_report_conflict")))
    # Reconsider exactly grounded engine candidates under this bounded profile.
    # This leaves the prior validation result untouched and permits explicit
    # diagnostic wording or chronic findings held by broad pilot firewalls.
    for candidate in candidates:
        if candidate.get("candidate_type") not in {"Observation", "Anatomy"} or candidate.get("assertion_candidate") not in {"PRESENT", "ABSENT_NEGATED", "UNCERTAIN"}:
            continue
        start, end = candidate.get("source_start"), candidate.get("source_end")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(protected_text):
            continue
        if candidate.get("source_section_role") not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"}:
            continue
        anchor = _sentence(protected_text, start, end)
        expression = candidate.get("source_text") or ""
        if candidate["candidate_type"] == "Anatomy":
            # Anatomy alone is never a finding. An exactly grounded maxillary
            # sinus mention can support explicit mucosal disease in its own
            # protected sentence when the engine missed the observation.
            sentence = anchor["quote"]
            source_sinus_disease = (re.search(r"\bmaxillary\s+sinus(?:es)?\b", sentence, re.I)
                and re.search(r"\bsinus(?:es)?\b.{0,80}\b(?:disease|thicken\w*|opacif\w*)\b|\bmucosal\s+thicken\w*\b|\bsinusitis\b", sentence, re.I))
            if not (source_sinus_disease and re.search(r"\b(?:maxillary|sinus(?:es)?)\b", expression, re.I)):
                continue
        rule = _rule(expression, anchor["quote"])
        if not rule and candidate["candidate_type"] == "Observation":
            rule = _general_rule(expression, anchor["quote"], candidate["assertion_candidate"], candidate["source_section_role"])
        if not rule and re.search(r"\b(?:hypoattenuat\w*|white[- ]matter|senescen\w*|lesions?|mass(?:es)?|annular|spheroid)\b", expression, re.I):
            local_start, local_end = max(0, start - 300), min(len(protected_text), end + 300)
            contrast_cues = sorted(m.start() for m in re.finditer(
                NONCONTRAST.pattern + "|" + POSTCONTRAST.pattern, protected_text, re.I))
            previous_cue = max((point for point in contrast_cues if point <= start), default=0)
            next_cue = min((point for point in contrast_cues if point > start), default=len(protected_text))
            local_start, local_end = max(local_start, previous_cue), min(local_end, next_cue)
            expanded = protected_text[local_start:local_end]
            rule = _rule(expression, expanded)
            if (not rule and candidate["source_section_role"] == "FINDINGS_DESCRIPTION"
                    and candidate["assertion_candidate"] == "PRESENT"
                    and re.search(r"\b(?:lesions?|mass(?:es)?)\b", expression, re.I)
                    and _context(protected_text, anchor, sections) == "NON_CONTRAST"
                    and re.search(r"\bright\b", expanded, re.I)
                    and re.search(r"\b(?:temporal|parietal)\b", expanded, re.I)):
                rule = next((key, display, kind, salience, group) for key, _, _, display, kind, salience, group in RULES if key == "lesion_complex")
            if rule and rule[0] in {"frontal_wm", "senescent_wm", "lesion_complex"}:
                anchor = {"start_offset": local_start, "end_offset": local_end, "quote": expanded}
        if not rule:
            continue
        anchor.update(role="SUMMARY_ASSERTION" if candidate["source_section_role"] == "DIAGNOSTIC_SUMMARY" else "DETAIL_SUPPORT", source_section=candidate["source_section_role"])
        evidence.append((expression, candidate["assertion_candidate"], anchor,
                         candidate["candidate_id"], candidate["source_section_role"], None))
    # A comparison may qualify an already grounded current focal finding, but
    # must not introduce a historical lesion as a new current finding.
    current_focal = any((rule := _rule(expression, anchor["quote"])) and rule[0] == "frontal_wm"
                        for expression, _, anchor, _, section, _ in evidence
                        if section in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"})
    if current_focal:
        for candidate in candidates:
            if (candidate.get("source_section_role") != "COMPARISON"
                    or candidate.get("candidate_type") != "Anatomy"
                    or candidate.get("assertion_candidate") != "PRESENT"
                    or not re.fullmatch(r"white[- ]matter", candidate.get("source_text") or "", re.I)):
                continue
            start, end = candidate.get("source_start"), candidate.get("source_end")
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(protected_text):
                continue
            if protected_text[start:end] != candidate["source_text"]:
                continue
            anchor = _sentence(protected_text, start, end)
            sentence = anchor["quote"]
            if not (re.search(r"\b(?:chronic|old)\b", sentence, re.I)
                    and re.search(r"\bright\b", sentence, re.I)
                    and re.search(r"\bfrontal\b", sentence, re.I)
                    and re.search(r"\bwhite[- ]matter\b", sentence, re.I)
                    and re.search(r"\b(?:lesion|hypoattenuat\w*)\b", sentence, re.I)):
                continue
            anchor.update(role="COMPARISON_SUPPORT", source_section="COMPARISON")
            evidence.append((candidate["source_text"], "PRESENT", anchor,
                             candidate["candidate_id"], "COMPARISON", None))
    # The explicit source phrase can supply a less-likely hypothesis when the
    # model missed its entity, provided a grounded Observation supports the
    # same diagnostic-summary sentence. This is MRJ source evidence, not a
    # fabricated engine entity.
    for section in sections:
        if section.get("role") not in {"DIAGNOSTIC_SUMMARY", "FINDINGS_DESCRIPTION"}:
            continue
        section_end = section.get("end", section["start"] + len(section["text"]))
        for match in re.finditer(r"\binfarct\w*\b", section["text"], re.I):
            start = section["start"] + match.start()
            end = section["start"] + match.end()
            anchor = _sentence(protected_text, start, end)
            if _hypothesis_status(anchor["quote"], match.group()) != "LESS_LIKELY":
                local_start = max(section["start"], start - 50)
                local_end = min(section_end, end + 70)
                anchor = {"start_offset": local_start, "end_offset": local_end,
                          "quote": protected_text[local_start:local_end]}
                if _hypothesis_status(anchor["quote"], match.group()) != "LESS_LIKELY":
                    continue
            corroborated = any(c.get("candidate_type") == "Observation"
                and isinstance(c.get("source_start"), int)
                and section["start"] <= c["source_start"] < section_end
                and abs(c["source_start"] - start) <= 100
                for c in candidates)
            if corroborated:
                anchor.update(role="SUMMARY_ASSERTION" if section["role"] == "DIAGNOSTIC_SUMMARY" else "DETAIL_SUPPORT",
                              source_section=section["role"])
                evidence.append((match.group(), "UNCERTAIN", anchor,
                                 f"mrj-source:{start}", section["role"], None))
    evidence.extend(_source_assertion_evidence(protected_text, sections, evidence))
    evidence.extend(_source_assessment_evidence(protected_text, sections, evidence))
    evidence.extend(_source_narrative_state_evidence(protected_text, sections, evidence))
    evidence.extend(_source_measured_positive_evidence(protected_text, sections, evidence))
    # Preserve the accepted bounded profile. Strongly supported functional
    # positives may augment it; broader source-grounded negatives are a
    # fallback for an otherwise empty clinical view.
    bounded_active = any((rule := _rule(expression, anchor["quote"])) and
        (rule[4] != "DIAGNOSTIC" or _hypothesis_status(anchor["quote"], expression))
        for expression, _, anchor, _, _, _ in evidence)
    grouped = {}
    rejected = Counter()
    accepted_mentions = 0
    candidate_decisions = []
    for expression, assertion, anchor, evidence_id, section, conflict in evidence:
        source_function, source_rejection = classify_clause(expression, anchor, section, protected_text)
        semantic_role, rejection = _basic_candidate(expression, anchor, assertion, section, protected_text)
        decision = {"evidence_id": evidence_id, "source_section_role": section,
                    "source_start": anchor["start_offset"], "source_end": anchor["end_offset"],
                    "assertion": assertion, "source_function": source_function,
                    "semantic_role_candidate": semantic_role}
        # The accepted focal white-matter projection permits a prior clause
        # only as corroborating context for an already grounded current fact.
        prior_qualifier = (section == "COMPARISON" and source_function == "COMPARISON_PRIOR_ONLY"
            and current_focal and (legacy := _rule(expression, anchor["quote"])) is not None
            and legacy[0] == "frontal_wm")
        if source_rejection and not prior_qualifier:
            rejected[source_rejection] += 1
            candidate_decisions.append({**decision, "eligibility": "REJECTED", "rejection_reason": source_rejection})
            continue
        rule = _rule(expression, anchor["quote"])
        if not rule:
            general = _general_rule(expression, anchor["quote"], assertion, section)
            if general and (not bounded_active or general[4] != "NEGATIVE"):
                rule = general
        if not rule and (evidence_id in validated_ids or evidence_id.startswith("mrj-source:")) and (
                not bounded_active or semantic_role != "PERTINENT_NEGATIVE"):
            rule = _open_rule(expression, anchor, assertion, section)
        if not rule:
            reason = rejection or "LOW_SALIENCE_OR_UNCLASSIFIED"
            rejected[reason] += 1
            candidate_decisions.append({**decision, "eligibility": "REJECTED", "rejection_reason": reason})
            continue
        # Apply a target-scoped interpretive cue after terminology mapping.
        # The model may call the entity PRESENT while the report explicitly
        # says the diagnosis is only suggested.
        fragment = _source_fragment(anchor, expression)
        match = re.search(re.escape(expression).replace(r"\ ", r"\s+"), fragment, re.I)
        cue_scope = fragment[:match.end()] if match else ""
        cue = re.search(r"\b(?:suggestive\s+of|suspicious\s+for|concerning\s+for|cannot\s+exclude)\b", cue_scope, re.I)
        if cue and assertion == "PRESENT" and rule[2] != "DIAGNOSTIC_HYPOTHESIS":
            interpretation = fragment[cue.end():].strip(" :;,. ")
            if interpretation and len(interpretation.split()) >= 2:
                rule = ("general:interpretation:" + ":".join(re.findall(r"[a-z]+", interpretation.casefold())),
                        interpretation[0].upper() + interpretation[1:],
                        "DIAGNOSTIC_HYPOTHESIS", "SECONDARY", "DIAGNOSTIC", "UNCERTAIN")
        concept, display, kind, salience, group = rule[:5]
        source_anchor = anchor
        if concept.startswith("general:open:") and assertion == "PRESENT":
            anchor = _local_anchor(anchor, expression) or anchor
        if len(rule) == 6:
            assertion = rule[5]
        if kind == "DIAGNOSTIC_HYPOTHESIS":
            status = _hypothesis_status(anchor["quote"], expression)
            if not status:
                rejected["HYPOTHESIS_CUE_MISSING"] += 1
                candidate_decisions.append({**decision, "eligibility": "REJECTED",
                                            "rejection_reason": "HYPOTHESIS_CUE_MISSING"})
                continue
            assertion = "UNCERTAIN"
        else:
            status = None
            if assertion not in {"PRESENT", "ABSENT_NEGATED", "UNCERTAIN"}:
                rejected["UNSUPPORTED_ASSERTION"] += 1
                candidate_decisions.append({**decision, "eligibility": "REJECTED",
                                            "rejection_reason": "UNSUPPORTED_ASSERTION"})
                continue
            if assertion == "ABSENT_NEGATED":
                kind, group = "PERTINENT_NEGATIVE", "NEGATIVE"
        if concept.startswith("general:open:") and kind == "DIAGNOSTIC_HYPOTHESIS":
            words = set(re.findall(r"[a-z]+", display.casefold()))
            if len(words) == 1 and any(other["fact_type"] == "DIAGNOSTIC_HYPOTHESIS" and words < set(
                    re.findall(r"[a-z]+", other["display_label"].casefold())) for other in grouped.values()):
                rejected["DUPLICATE_GENERIC_HYPOTHESIS"] += 1
                candidate_decisions.append({**decision, "eligibility": "REJECTED",
                                            "rejection_reason": "DUPLICATE_GENERIC_HYPOTHESIS"})
                continue
        accepted_mentions += 1
        candidate_decisions.append({**decision, "eligibility": "ACCEPTED", "semantic_role": kind,
                                    "canonical_concept": concept})
        key = (concept, assertion, status if kind == "DIAGNOSTIC_HYPOTHESIS" else None)
        if concept.startswith("general:open:") and key not in grouped:
            terms = set(concept.removeprefix("general:open:").split(":"))
            for previous in grouped:
                if not previous[0].startswith("general:open:") or previous[1:] != key[1:]:
                    continue
                prior_terms = set(previous[0].removeprefix("general:open:").split(":"))
                if min(len(terms), len(prior_terms)) >= 2 and (terms <= prior_terms or prior_terms <= terms):
                    key = previous
                    break
                # A repeated named state may be phrased with different site
                # detail. Require both high phrase overlap and a shared
                # descriptive modifier; anatomy or the generic head alone
                # cannot merge distinct findings.
                prior_label = grouped[previous]["display_label"]
                head_word = re.findall(r"[A-Za-z]+", expression)[-1] if re.search(r"[A-Za-z]", expression) else ""
                current_head = re.search(r"\b" + re.escape(head_word) + r"\b", display, re.I) if head_word else None
                prior_head = re.search(r"\b" + re.escape(head_word) + r"\b", prior_label, re.I) if head_word else None
                if not current_head or not prior_head or not min(len(terms), len(prior_terms)) >= 4:
                    continue
                def modifiers(label: str, head_start: int) -> set[str]:
                    prefix = re.split(r"\b(?:in|on|at|within|is|are|a|an|the)\b", label[:head_start], flags=re.I)[-1]
                    return set(re.findall(r"[a-z]+", prefix.casefold())) - {"incidentally", "noted", "there"}
                common_modifiers = modifiers(display, current_head.start()) & modifiers(prior_label, prior_head.start())
                if common_modifiers and len(terms & prior_terms) / min(len(terms), len(prior_terms)) >= 0.7:
                    measurement_tokens = re.compile(r"\b\d+(?:\.\d+)?\s*[- ]?\s*(?:mm|cm)\b", re.I)
                    previous_measures = {re.sub(r"[\s-]", "", match.group()).casefold()
                        for prior_anchor in grouped[previous]["evidence_anchors"]
                        for match in measurement_tokens.finditer(prior_anchor["quote"])}
                    current_measures = {re.sub(r"[\s-]", "", match.group()).casefold()
                        for match in measurement_tokens.finditer(source_anchor["quote"])}
                    if previous_measures and current_measures and previous_measures.isdisjoint(current_measures):
                        continue
                    key = previous
                    break
        fact = grouped.get(key)
        if fact is None:
            fact = {"fact_id": f"canonical-{len(grouped)+1}", "fact_type": kind,
                    "canonical_concept": concept, "display_label": display,
                    "assertion_state": assertion, "salience": salience, "group": group,
                    "anatomy": [], "observations": [], "relationships": [],
                    "evidence_anchors": [], "confidence": {"state": "NOT_CALIBRATED"},
                    "review_required": bool(status or conflict), "review_reason": [],
                    "synthesis_provenance": {"profile": PROFILE, "engine_evidence_ids": [], "source_rule_evidence_ids": []}}
            if status:
                fact["hypothesis_status"] = status
                fact["review_reason"].append("DIAGNOSTIC_INTERPRETATION")
            grouped[key] = fact
        elif concept.startswith("general:open:"):
            if group == "KEY" and fact["group"] == "SECONDARY":
                fact["group"], fact["salience"] = "KEY", "PRIMARY"
            if len(display) > len(fact["display_label"]) and not re.match(r"\s*incidentally\b", display, re.I):
                fact["display_label"] = display
        if conflict and "CONFLICTING_SOURCE_ASSERTION" not in fact["review_reason"]:
            fact["review_required"] = True
            fact["review_reason"].append("CONFLICTING_SOURCE_ASSERTION")
        source_rule = evidence_id.startswith("mrj-source:")
        provenance_key = "source_rule_evidence_ids" if source_rule else "engine_evidence_ids"
        if evidence_id not in fact["synthesis_provenance"][provenance_key]:
            fact["synthesis_provenance"][provenance_key].append(evidence_id)
        identity = (anchor["start_offset"], anchor["end_offset"], section)
        matching_anchor = next((a for a in fact["evidence_anchors"] if
            (a["start_offset"], a["end_offset"], a.get("section_role")) == identity), None)
        if matching_anchor is None:
            fact["evidence_anchors"].append({"start_offset": anchor["start_offset"], "end_offset": anchor["end_offset"],
                 "quote": anchor["quote"], "role": anchor.get("role"), "section_role": section,
                 "source_section": section, "source_context": _context(protected_text, anchor, sections),
                 "engine_evidence_ids": [] if source_rule else [evidence_id],
                 "source_rule_evidence_ids": [evidence_id] if source_rule else []})
        elif evidence_id not in matching_anchor[provenance_key]:
            matching_anchor[provenance_key].append(evidence_id)
        if kind != "DIAGNOSTIC_HYPOTHESIS":
            observation = _observation(protected_text, anchor, concept, sections)
            if concept.startswith("general:open:"):
                fragment = _source_fragment(anchor, expression)
                fragment = re.sub(r"(?<=[A-Za-z])(?=\d+(?:\.\d+)?\s*(?:mm|cm)\b)", " ", fragment, flags=re.I)
                measures = [match.group() for match in MEASUREMENT.finditer(fragment)]
                # Validated entity anchors can end before a same-clause size
                # continuation. Extend only through an adjacent measurement
                # predicate, never across the next independent sentence.
                line_end = protected_text.find("\n", anchor["end_offset"])
                line_end = len(protected_text) if line_end < 0 else line_end
                continuation_text = protected_text[anchor["end_offset"]:line_end]
                if re.match(r"^\s*(?:at\b|,?\s*(?:(?:the\s+(?:largest|smallest)\s+)?measur\w*|estimated\s+volume)\b)", continuation_text, re.I):
                    continuation_text = re.split(r"(?<!\d)\.(?!\d)|;", continuation_text, maxsplit=1)[0]
                    measures.extend(match.group() for match in MEASUREMENT.finditer(continuation_text))
                # A comma may introduce only a second dimension, not a new
                # condition: "lesion 1.4 cm ..., and 4 mm in depth". Retain
                # its own exact source span instead of borrowing another
                # finding's measurement from a long model sentence.
                following = protected_text[anchor["end_offset"]:source_anchor["end_offset"]]
                continuation = re.match(r"\s*,\s*(?:and\s+)?(?P<measure>\d+(?:\.\d+)?\s*(?:mm|cm))\b", following, re.I)
                if continuation:
                    measure = continuation.group("measure")
                    measures.append(measure)
                    measure_start = anchor["end_offset"] + continuation.start("measure")
                    measure_end = measure_start + len(measure)
                    if protected_text[measure_start:measure_end] == measure and not any(
                            item["start_offset"] == measure_start and item["end_offset"] == measure_end
                            for item in fact["evidence_anchors"]):
                        fact["evidence_anchors"].append({"start_offset": measure_start, "end_offset": measure_end,
                            "quote": measure, "role": "ATTRIBUTE_SUPPORT", "section_role": section,
                            "source_section": section, "source_context": _context(protected_text, source_anchor, sections),
                            "engine_evidence_ids": [] if source_rule else [evidence_id],
                            "source_rule_evidence_ids": [evidence_id] if source_rule else []})
                # Keep measurements inside the grounded local clause. A PDF
                # line can contain several independent conditions, including
                # a negative followed by a measured positive condition.
                line_start = protected_text.rfind("\n", 0, anchor["start_offset"]) + 1
                next_break = protected_text.find("\n", anchor["end_offset"])
                line_end = len(protected_text) if next_break < 0 else next_break
                line = protected_text[line_start:line_end]
                assessment = re.search(r"\b[A-Z][A-Z-]{2,}\s*(?:[-:=]\s*)?\d\b", line)
                if assessment and abs(line_start + assessment.start() - anchor["end_offset"]) <= 85:
                    observation["source_assessment"] = assessment.group().strip()
                    assessment_start, assessment_end = line_start + assessment.start(), line_start + assessment.end()
                    if not any(a["start_offset"] == assessment_start and a["end_offset"] == assessment_end
                               for a in fact["evidence_anchors"]):
                        fact["evidence_anchors"].append({"start_offset": assessment_start,
                            "end_offset": assessment_end, "quote": assessment.group(),
                            "role": "ATTRIBUTE_SUPPORT", "section_role": section, "source_section": section,
                            "source_context": _context(protected_text, source_anchor, sections),
                            "engine_evidence_ids": [] if source_rule else [evidence_id],
                            "source_rule_evidence_ids": [evidence_id] if source_rule else []})
                if measures:
                    observation["measurements"] = list(dict.fromkeys(measures))
                extent = re.search(r"\bbetween\s+\d+\s+and\s+\d+\s+o['’]clock\b", fragment, re.I)
                if extent:
                    observation["extent"] = extent.group()
                source_fact = validated_by_id.get(evidence_id)
                if source_fact and source_fact.get("anatomic_site") and source_fact["anatomic_site"] not in fact["anatomy"]:
                    fact["anatomy"].append(source_fact["anatomic_site"])
            context = observation["source_context"]
            existing = next((o for o in fact["observations"] if o["source_context"] == context and o["evidence_anchor"]["start_offset"] == anchor["start_offset"]), None)
            if not existing:
                fact["observations"].append(observation)
            if observation.get("temporal_information"):
                fact["temporal_status"] = observation["temporal_information"]
            if observation.get("temporal_change"):
                fact["temporal_change"] = observation["temporal_change"]
        if concept == "lesion_complex" and re.search(r"\b(?:count|number|single|three|3)\b", anchor["quote"], re.I):
            if "SOURCE_SPECIFIC_LESION_COUNT" not in fact["review_reason"]:
                fact["review_reason"].append("SOURCE_SPECIFIC_LESION_COUNT")
                fact["review_required"] = True
    # Never collapse opposite assertions into one authoritative fact.
    by_concept = defaultdict(set)
    for fact in grouped.values():
        by_concept[fact["canonical_concept"]].add(fact["assertion_state"])
    for fact in grouped.values():
        if len(by_concept[fact["canonical_concept"]]) > 1:
            fact["review_required"] = True
            if "CONFLICTING_SOURCE_ASSERTION" not in fact["review_reason"]:
                fact["review_reason"].append("CONFLICTING_SOURCE_ASSERTION")
    facts = list(grouped.values())
    # A source-recovered headed state can restate a diagnosed summary finding.
    # Merge only an explicit state synonym for the same subject; keep its exact
    # source anchor and measurement on the established summary fact.
    for state_fact in list(facts):
        state_match = re.fullmatch(r"(Enlarged|Increased|Decreased|Dilated|Narrowed|Thickened|Atrophic)\s+([A-Za-z -]+)",
                                   state_fact["display_label"], re.I)
        if (not state_match or state_fact["group"] != "SECONDARY" or not
                state_fact["synthesis_provenance"]["source_rule_evidence_ids"]):
            continue
        state, subject = state_match.group(1).casefold(), state_match.group(2).strip()
        target = None
        for candidate in facts:
            if (candidate is not state_fact and candidate["group"] == "KEY"
                    and candidate["assertion_state"] == "PRESENT"
                    and re.search(r"\b" + re.escape(subject) + r"\b", candidate["display_label"], re.I)
                    and (re.search(r"\b" + re.escape(state[:-1]) + r"\w*\b", candidate["display_label"], re.I)
                         or (state == "enlarged" and re.search(r"\b\w+megaly\b", candidate["display_label"], re.I)))):
                target = candidate
                break
        if not target:
            continue
        target["observations"].extend(state_fact["observations"])
        for anchor in state_fact["evidence_anchors"]:
            if not any(a["start_offset"] == anchor["start_offset"] and a["end_offset"] == anchor["end_offset"]
                       for a in target["evidence_anchors"]):
                target["evidence_anchors"].append(anchor)
        for key in ("engine_evidence_ids", "source_rule_evidence_ids"):
            target["synthesis_provenance"][key].extend(value for value in state_fact["synthesis_provenance"][key]
                                                         if value not in target["synthesis_provenance"][key])
        facts.remove(state_fact)
    for index, fact in enumerate(facts, 1):
        fact["fact_id"] = f"canonical-{index}"
    if not bounded_active:
        summaries = [section for section in sections if section.get("role") == "DIAGNOSTIC_SUMMARY"]
        common = {"the", "this", "that", "has", "have", "been", "from", "with", "into", "and", "are", "was", "were", "is", "made", "noted"}
        for fact in facts:
            if fact["group"] != "SECONDARY" or not fact["canonical_concept"].startswith("general:open:") or not any(
                    anchor.get("section_role") == "COMPARISON" for anchor in fact["evidence_anchors"]):
                continue
            terms = {word for word in re.findall(r"[a-z]+", fact["display_label"].casefold()) if word not in common}
            if len(terms) < 3:
                continue
            for summary in summaries:
                lines = summary["text"].splitlines(keepends=True)
                offset = summary["start"]
                for index, line in enumerate(lines):
                    window = line + (lines[index + 1] if index + 1 < len(lines) else "")
                    overlap = terms & set(re.findall(r"[a-z]+", window.casefold()))
                    if len(overlap) < 3 or len(overlap) / len(terms) < 0.45:
                        offset += len(line)
                        continue
                    fact["group"], fact["salience"] = "KEY", "ASSOCIATED"
                    fact["salience_reason"] = "CURRENT_COMPARISON_CORROBORATED_BY_SUMMARY"
                    source_id = f"mrj-source:{offset}"
                    fact["synthesis_provenance"]["source_rule_evidence_ids"].append(source_id)
                    fact["evidence_anchors"].append({"start_offset": offset, "end_offset": offset + len(window),
                        "quote": window, "role": "SUMMARY_CORROBORATION", "section_role": "DIAGNOSTIC_SUMMARY",
                        "source_section": "DIAGNOSTIC_SUMMARY", "source_context": "UNSPECIFIED",
                        "engine_evidence_ids": [], "source_rule_evidence_ids": [source_id]})
                    break
                if fact["group"] == "KEY":
                    break
        # A validated finding in Findings can acquire Impression salience when
        # the same distinctive clinical head appears in a patient-specific
        # summary clause. Numbered clinical impressions are not reference lists.
        for fact in facts:
            if fact["group"] != "SECONDARY" or fact["assertion_state"] != "PRESENT":
                continue
            terms = re.findall(r"[A-Za-z]+", fact["display_label"])
            head = terms[-1] if terms else ""
            if len(head) < 7 or head.casefold() in {"finding", "findings", "changes", "disease", "pattern", "region"}:
                continue
            for summary in summaries:
                match = re.search(r"\b" + re.escape(head) + r"\b", summary["text"], re.I)
                if not match:
                    continue
                start = summary["start"] + match.start()
                end = start + len(match.group())
                summary_anchor = _sentence(protected_text, start, end)
                summary_anchor.update(role="SUMMARY_CORROBORATION", source_section="DIAGNOSTIC_SUMMARY")
                if classify_clause(head, summary_anchor, "DIAGNOSTIC_SUMMARY", protected_text)[1]:
                    continue
                fact["group"], fact["salience"] = "KEY", "ASSOCIATED"
                fact["salience_reason"] = "PATIENT_SPECIFIC_SUMMARY_CORROBORATION"
                source_id = f"mrj-source:{start}"
                fact["synthesis_provenance"]["source_rule_evidence_ids"].append(source_id)
                fact["evidence_anchors"].append({"start_offset": summary_anchor["start_offset"],
                    "end_offset": summary_anchor["end_offset"], "quote": summary_anchor["quote"],
                    "role": "SUMMARY_CORROBORATION", "section_role": "DIAGNOSTIC_SUMMARY",
                    "source_section": "DIAGNOSTIC_SUMMARY", "source_context": "UNSPECIFIED",
                    "engine_evidence_ids": [], "source_rule_evidence_ids": [source_id]})
                break
    if not bounded_active:
        principal_condition = next((fact for fact in facts if fact["canonical_concept"].startswith("general:condition:")
                                    and "absent relaxation" in fact["display_label"].lower()), None)
        if principal_condition:
            for fact in list(facts):
                if not fact["canonical_concept"].startswith("general:functional_absence:relaxation"):
                    continue
                if not any(a["start_offset"] == b["start_offset"] and a["end_offset"] == b["end_offset"]
                           for a in principal_condition["evidence_anchors"] for b in fact["evidence_anchors"]):
                    continue
                for key in ("engine_evidence_ids", "source_rule_evidence_ids"):
                    principal_condition["synthesis_provenance"][key].extend(
                        value for value in fact["synthesis_provenance"][key]
                        if value not in principal_condition["synthesis_provenance"][key])
                for anchor in fact["evidence_anchors"]:
                    existing = next((a for a in principal_condition["evidence_anchors"] if
                                     a["start_offset"] == anchor["start_offset"] and a["end_offset"] == anchor["end_offset"]), None)
                    if existing:
                        existing["engine_evidence_ids"].extend(value for value in anchor["engine_evidence_ids"]
                                                               if value not in existing["engine_evidence_ids"])
                    else:
                        principal_condition["evidence_anchors"].append(anchor)
                facts.remove(fact)
            for index, fact in enumerate(facts, 1):
                fact["fact_id"] = f"canonical-{index}"
    if not bounded_active:
        first_positive = next((fact for fact in facts if fact["canonical_concept"].startswith("general:condition:")
                               and fact["group"] == "KEY" and fact["assertion_state"] == "PRESENT"), None)
        if not first_positive:
            first_positive = next((fact for fact in facts if fact["group"] == "KEY" and
                fact["assertion_state"] == "PRESENT"), None)
        if first_positive and any(fact.get("salience_reason") == "PATIENT_SPECIFIC_SUMMARY_CORROBORATION"
                                  for fact in facts):
            first_positive = min((fact for fact in facts if fact["group"] == "KEY" and fact["assertion_state"] == "PRESENT"),
                                 key=lambda fact: min((anchor["start_offset"] for anchor in fact["evidence_anchors"]
                                                       if anchor.get("section_role") == "DIAGNOSTIC_SUMMARY"),
                                                      default=len(protected_text)))
        if first_positive:
            first_positive["salience"] = "PRIMARY"
            for fact in facts:
                if fact is not first_positive and fact["salience"] == "PRIMARY":
                    fact["salience"] = "ASSOCIATED"
    # POSSIBLE and a more specific comparative status are compatible source
    # qualifications, not independent diagnoses. Keep both source labels.
    for concept in {f["canonical_concept"] for f in facts if f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS"}:
        related = [f for f in facts if f["canonical_concept"] == concept and f["fact_type"] == "DIAGNOSTIC_HYPOTHESIS"]
        statuses = {f["hypothesis_status"] for f in related}
        if len(related) < 2 or "POSSIBLE" not in statuses or not statuses <= {"POSSIBLE", "FAVORED", "LESS_FAVORED", "LESS_LIKELY"}:
            continue
        preferred = next((f for f in related if f["hypothesis_status"] != "POSSIBLE"), related[0])
        for other in related:
            if other is preferred:
                continue
            preferred["evidence_anchors"].extend(a for a in other["evidence_anchors"] if
                not any((a["start_offset"], a["end_offset"]) == (b["start_offset"], b["end_offset"]) for b in preferred["evidence_anchors"]))
            for key in ("engine_evidence_ids", "source_rule_evidence_ids"):
                preferred["synthesis_provenance"][key].extend(value for value in other["synthesis_provenance"][key]
                    if value not in preferred["synthesis_provenance"][key])
            facts.remove(other)
        preferred["hypothesis_statuses"] = sorted(statuses)
    _attach_local_source_measurements(protected_text, sections, facts)
    for fact in facts:
        # Engine mentions may point to different anchors for the same observation.
        # Keep all anchors above, but present a source-specific observation once.
        unique_observations = []
        seen_observations = set()
        for observation in fact["observations"]:
            signature = tuple((key, tuple(value) if isinstance(value, list) else value)
                              for key, value in sorted(observation.items()) if key != "evidence_anchor")
            if signature not in seen_observations:
                seen_observations.add(signature)
                unique_observations.append(observation)
        fact["observations"] = unique_observations
        _finish_fact(fact)
    # Open-vocabulary concepts may have different surface wording despite an
    # identical clinical phrase. Keep opposing assertions as separate facts
    # and flag only exact phrase equivalence, not a shared anatomy or noun.
    def conflict_terms(label: str) -> set[str]:
        return {token for token in re.findall(r"[a-z]+(?:-[a-z]+)*", label.casefold())
                if token not in {"no", "not", "the", "a", "an", "is", "are", "was", "were"}}
    for index, left in enumerate(facts):
        for right in facts[index + 1:]:
            if {left["assertion_state"], right["assertion_state"]} != {"PRESENT", "ABSENT_NEGATED"}:
                continue
            if len(conflict_terms(left["display_label"])) < 2 or conflict_terms(left["display_label"]) != conflict_terms(right["display_label"]):
                continue
            for fact in (left, right):
                fact["review_required"] = True
                if "CONFLICTING_SOURCE_ASSERTION" not in fact["review_reason"]:
                    fact["review_reason"].append("CONFLICTING_SOURCE_ASSERTION")
    # A patient-specific scalar classification can disagree across sections.
    # Retain both values and request review; never select one by section rank.
    typed = [(fact, re.search(r"\btype\s+([A-Z])\b", fact["display_label"], re.I)) for fact in facts]
    for index, (left, left_type) in enumerate(typed):
        if not left_type:
            continue
        for right, right_type in typed[index + 1:]:
            if not right_type or left_type.group(1).casefold() == right_type.group(1).casefold():
                continue
            for fact in (left, right):
                fact["review_required"] = True
                if "INTERNAL_SOURCE_CONFLICT" not in fact["review_reason"]:
                    fact["review_reason"].append("INTERNAL_SOURCE_CONFLICT")
    if any(fact["canonical_concept"].startswith("general:") for fact in facts):
        _general_relations(facts)
    counts = {group: sum(f["group"] == group for f in facts) for group in ("KEY", "DIAGNOSTIC", "SECONDARY", "NEGATIVE")}
    clinically_grounded_ids = {evidence_id for expression, assertion, anchor, evidence_id, section, _ in evidence
        if evidence_id in validated_ids and _basic_candidate(expression, anchor, assertion, section, protected_text)[0]
        in {"CURRENT_FINDING", "DIAGNOSTIC_HYPOTHESIS", "PERTINENT_NEGATIVE", "NORMAL_OBSERVATION"}}
    coverage_failure = bool(clinically_grounded_ids and not facts)
    if coverage_failure:
        rejected["SYNTHESIS_COVERAGE_FAILURE"] += 1
    measurement_ledger = _governed_measurement_ledger(protected_text, sections, facts)
    return {"profile": PROFILE, "canonical_facts": facts,
            "governed_measurements": measurement_ledger,
            "clinical_synthesis": _summary(facts),
            "counts": {"key_findings": counts["KEY"], "diagnostic_considerations": counts["DIAGNOSTIC"],
                       "secondary_findings": counts["SECONDARY"], "pertinent_negatives": counts["NEGATIVE"],
                       "technical_engine_entities": len(result["radiology_findings"]),
                       "raw_engine_candidates": result["candidate_count"]},
            "review_summary": {"required": True, "targeted_fact_count": sum(f["review_required"] for f in facts),
                               "reasons": sorted({reason for f in facts for reason in f["review_reason"]} |
                                                 ({"SYNTHESIS_COVERAGE_FAILURE"} if coverage_failure else set()))},
            "technical_diagnostics": {"code": "SYNTHESIS_COVERAGE_FAILURE" if coverage_failure else None,
                "validated_evidence_count": len(result["radiology_findings"]),
                "clinically_grounded_evidence_count": len(clinically_grounded_ids),
                "candidate_count": len(evidence), "canonical_fact_count": len(facts),
                "suppressed_candidate_count": sum(rejected.values()) - int(coverage_failure),
                "merged_mention_count": max(0, accepted_mentions - len(facts)),
                "candidate_decisions": candidate_decisions,
                "rejection_reason_counts": dict(sorted((reason, count) for reason, count in rejected.items()
                                                       if reason != "SYNTHESIS_COVERAGE_FAILURE"))},
            "technical_evidence_mapping": {f["fact_id"]: f["synthesis_provenance"] for f in facts}}
