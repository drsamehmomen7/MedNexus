"""Conservative, non-authoritative source validation for comparison-only claims.

This module never changes the model response or the Native clinical record. A
claim is allowed into a grounded comparison only when local report evidence is
strong enough; uncertain paraphrases remain unresolved for human review.
"""
from __future__ import annotations

from decimal import Decimal
import re
import unicodedata

from .medgemma_atomic import TEMPORAL as ATOMIC_TEMPORAL, decompose_occurrence


ROLES = {
    "clinically important findings": "FINDING", "clinical findings": "FINDING",
    "key findings": "FINDING", "findings": "FINDING",
    "pertinent negatives": "PERTINENT_NEGATIVE", "negative findings": "PERTINENT_NEGATIVE",
    "measurements": "MEASUREMENT", "measures": "MEASUREMENT",
    "diagnostic considerations": "DIAGNOSTIC_CONSIDERATION",
    "differential diagnosis": "DIAGNOSTIC_CONSIDERATION",
    "follow-up recommendations": "RECOMMENDATION",
    "follow up recommendations": "RECOMMENDATION",
    "recommendations for follow-up": "RECOMMENDATION",
    "recommendations": "RECOMMENDATION", "follow-up": "RECOMMENDATION",
}
STOP = set("a an the and or is are was were be been being this that these those it its "
           "of in on at to for with from by as not noted present seen report study patient "
           "finding findings lesion lesions mass masses clinical approximately about there "
           "evidence demonstrated identified shows show today prior previous current "
           "comparison exam date based relative mentioned more characteristics".split())
NEGATIVE = re.compile(r"\b(?:no|without|negative for|absent|not seen|not identified|free of|no evidence of)\b", re.I)
UNCERTAIN = re.compile(r"\b(?:possible|possibly|may|might|could|suggests?|suspected|considered|likely)\b", re.I)
MEASURE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mm|cm|mL|cc)\b", re.I)
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
RECOMMEND = re.compile(r"\b(?:recommend\w*|should|consider\w*|reevaluat\w*|repeat|follow(?:ing)?[ -]?up|further\s+(?:evaluation|testing|workup|diagnostic)|could be provided|would be (?:helpful|valuable)|requires?|required)\b", re.I)
META = re.compile(r"\b(?:transcri\w*|dictat\w*|signed|reported by|the request asks|thinking process|patient is \d+ years|patient had a prior .*replacement in \d{4})\b", re.I)
REFUSAL = re.compile(r"\b(?:cannot|can't|unable to)\s+(?:extract|provide|identify)|\b(?:report|text)\s+(?:is\s+)?(?:incomplete|missing)\b", re.I)
AUTHORITY = re.compile(r"(?im)^\s*(?:ADDENDUM|AMENDED REPORT|CORRECTION)\s*$")
CORRECTION = re.compile(r"\b(?:stable|unchanged|definitely|confirmed|no further|already|available|resolved|not new)\b", re.I)
HISTORICAL = re.compile(r"\b(?:new|indeterminate|uncertain|deeper.seated|may have|possible|requires?|further\s+(?:evaluation|characterization)|compare|comparison)\b", re.I)
SECTION = re.compile(r"(?im)^\s*(?:FINDINGS|IMPRESSION|CONCLUSION|RECOMMENDATIONS?|ADDENDUM|AMENDED REPORT|CORRECTION)\s*:?\s*")
CONTEXT = {"left", "right", "bilateral", "breast", "lung", "liver", "hip", "kidney", "chest", "abdomen", "region", "tissue", "structure"}
IDENTITY_STOP = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "this", "that", "these", "those", "it", "its", "show", "shows", "shown", "seen", "noted", "identified", "present", "finding", "findings", "study"}
IDENTITY_MEASURE = re.compile(r"\b(\d+(?:\.\d+)?)\s*[- ]?\s*(mm|cm|ml|cc)\b", re.I)
RECOMMENDATION_ACTION = re.compile(r"\b(?:testing|evaluation|workup|consultation|imaging|follow[ -]?up|repeat|monitoring)\b", re.I)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", value)).strip(" -:;,.\t")


def _tokens(value: str) -> set[str]:
    value = re.sub(r"\b(?:deep vein thrombosis|dvt)\b", "thrombosis", value.casefold())
    value = re.sub(r"\b(?:no|negative for|absent|free of)\b", "absent", value)
    return {w[:-1] if w.endswith("s") and not w.endswith(("ss", "is", "us")) and len(w) > 4 else w
            for w in re.findall(r"[a-z]{3,}|\d+(?:\.\d+)?", value)
            if w not in STOP and not w.isdigit()}


def claim_features(text: str, role: str) -> dict:
    """Exact, format-insensitive claim features; never substitutes for source validation."""
    value = unicodedata.normalize("NFKC", text).casefold()
    kind = ("RECOMMENDATION" if role == "RECOMMENDATION" or
            RECOMMEND.search(value) and RECOMMENDATION_ACTION.search(value) else "CLINICAL")
    assertion = ("NOT_APPLICABLE" if kind == "RECOMMENDATION" else
                 "ABSENT_NEGATED" if role == "PERTINENT_NEGATIVE" or NEGATIVE.search(value) else
                 "UNCERTAIN" if role == "DIAGNOSTIC_CONSIDERATION" or UNCERTAIN.search(value) else "PRESENT")
    laterality = tuple(sorted({"bilateral" if side == "bilaterally" else side for side in
                              re.findall(r"\b(?:left|right|bilateral|bilaterally)\b", value)}))
    measurements = tuple(sorted((str(Decimal(number).normalize()), unit.casefold())
                                for number, unit in IDENTITY_MEASURE.findall(value)))
    numbers = tuple(sorted(str(Decimal(number).normalize()) for number in NUMBER.findall(value)))
    value = re.sub(r"\b(?:negative\s+for|not\s+(?:seen|identified)|free\s+of|without|no|absent)\b",
                   "absent", value)
    value = re.sub(r"\b(?:measures?|measured|measuring|measurement|sizing|size)\b", "size", value)
    value = re.sub(r"\bbilaterally\b", "bilateral", value)
    words = []
    for word in re.findall(r"\d+(?:\.\d+)?|[a-z]+", value):
        if word in IDENTITY_STOP:
            continue
        if word.endswith("s") and not word.endswith(("ss", "is", "us")) and len(word) > 4:
            word = word[:-1]
        words.append(word)
    core = tuple(sorted(words))
    qualifiers = tuple(sorted(set(words) & {"new", "stable", "resolved", "unchanged",
                                            "increased", "decreased", "worsened", "improved"}))
    return {"kind": kind, "assertion": assertion, "laterality": laterality,
            "measurements": measurements, "numbers": numbers,
            "words": core, "compact": "".join(core),
            "ordered_compact": "".join(words), "qualifiers": qualifiers}


def claim_identity(text: str, role: str) -> tuple:
    features = claim_features(text, role)
    return (features["kind"], features["assertion"], features["laterality"],
            features["measurements"], features["numbers"], features["ordered_compact"])


def _sentences(value: str) -> list[str]:
    # Decimal points and abbreviations remain within the same claim.
    return [_clean(part) for part in re.split(r"(?<=[.!?])\s+(?=[A-Z*])|;\s+", value)
            if _clean(part)]


def _heading(value: str) -> tuple[str | None, str, str | None]:
    text = re.sub(r"^\s*(?:#{1,4}\s*|[-*+]\s+|\d+[.)]\s+)", "", value).strip()
    match = re.match(r"^\*\*([^*]+?)\*\*\s*:?[ \t]*(.*)$", text)
    if match:
        label, rest = match.groups()
    else:
        match = re.match(r"^([^:]{3,42}):\s*(.*)$", text)
        if not match:
            return None, text, None
        label, rest = match.groups()
    label = re.sub(r"[^a-z -]", "", label.casefold()).strip().replace("  ", " ")
    return ROLES.get(label), rest, label


def _project_occurrences(raw: str) -> list[dict]:
    if not isinstance(raw, str):
        return []
    if REFUSAL.search(raw[:250]):
        return []
    # Some model checkpoints expose a thought delimiter; no reasoning may be
    # promoted even if it imitates clinical headings.
    if "<unused95>" in raw:
        raw = raw.rsplit("<unused95>", 1)[1]
    elif re.search(r"<unused\d+>thought", raw, re.I):
        return []
    role = None
    section = None
    claims = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("<unused") or line in {"---", "***"}:
            continue
        heading, rest, label = _heading(line)
        if heading:
            role = heading
            section = label
            line = rest
        elif re.match(r"^\s*(?:#{1,4}\s+|\*\*[^*]+\*\*:?\s*$)", line):
            # Unknown top-level sections are not clinical source claims.
            if role is not None and re.search(r"\b(?:right|left|bilateral)\s+(?:breast|hip|lung|kidney)\b", line, re.I):
                continue
            role = None
            section = None
            continue
        else:
            bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.*)$", line)
            if not bullet:
                continue
            line = bullet.group(1)
        if role is None or not line:
            continue
        # Nested anatomical labels are context, not independent findings.
        nested = re.match(r"^\*\*[^*]{2,45}\*\*\s*:?[ \t]*(.*)$", line)
        if nested:
            line = nested.group(1)
            if not line:
                continue
        for part in _sentences(line):
            part = _clean(part)
            if len(part) < 8 or META.search(part) or REFUSAL.search(part):
                continue
            if role == "RECOMMENDATION" and not RECOMMEND.search(part):
                continue
            if role == "MEASUREMENT" and re.search(r"\b(?:no specific measurements|measurements? (?:are|is) missing)\b", part, re.I):
                continue
            claims.append({"role": role, "text": part, "source_section": section,
                           "line_number": line_number})
    return claims


def _deduplicate_claims(claims: list[dict], *, validated: bool = False) -> list[dict]:
    unique = []
    seen = {}
    for claim in claims:
        key = claim_identity(claim["text"], claim["role"])
        if validated:
            # Validate each raw occurrence first. A supported wording must
            # never absorb a rejected or superseded variant.
            key += (claim["validation_status"],)
        occurrence = {"source_section": claim.get("source_section") or claim["role"],
                      "line_number": claim.get("line_number"), "text": claim["text"]}
        if "parent_id" in claim:
            occurrence.update(parent_id=claim["parent_id"], parent_text=claim["parent_text"],
                              parent_span=claim.get("parent_span"),
                              atomic_type=claim.get("atomic_type"),
                              parent_occurrence=claim.get("parent_occurrence"))
        prior = seen.get(key)
        if prior is None:
            item = {**claim, "source_sections": [occurrence["source_section"]],
                    "raw_occurrence_count": 1, "raw_text_variants": [claim["text"]],
                    "raw_occurrences": [occurrence]}
            unique.append(item)
            seen[key] = item
        else:
            prior["raw_occurrence_count"] += 1
            prior["raw_occurrences"].append(occurrence)
            if occurrence["source_section"] not in prior["source_sections"]:
                prior["source_sections"].append(occurrence["source_section"])
            if claim["text"] not in prior["raw_text_variants"]:
                prior["raw_text_variants"].append(claim["text"])
    return unique


def project_clinical_claims(raw: str) -> tuple[list[dict], int]:
    """Project clinical sections with deterministic cross-section provenance."""
    occurrences = _project_occurrences(raw)
    return _deduplicate_claims(occurrences), len(occurrences)


def _source_clauses(source: str) -> list[tuple[str, int]]:
    markers = list(SECTION.finditer(source))
    if not markers:
        return [(part, 0) for part in _sentences(source)]
    # Reports can put all imaging observations before their first formal
    # IMPRESSION heading without a FINDINGS label.
    clauses = [(part, 0) for part in _sentences(re.sub(r"\s+", " ", source[:markers[0].start()]))]
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(source)
        body = source[marker.end():end]
        # Header/signature metadata is not evidence of a clinical assertion.
        body = re.split(r"(?im)^\s*(?:\*\*\s*(?:REPORT|ADDENDUM)|Reported By:|Signed By:|Transcribed)", body)[0]
        for part in _sentences(re.sub(r"\s+", " ", body)):
            clauses.append((part, marker.start()))
    return clauses


def _same_measurements(claim: str, source: str) -> bool:
    values = {re.sub(r"\s+", "", x.casefold()) for x in MEASURE.findall(claim)}
    available = {re.sub(r"\s+", "", x.casefold()) for x in MEASURE.findall(source)}
    return values <= available


def _laterality(value: str) -> set[str]:
    return set(re.findall(r"\b(?:left|right|bilateral)\b", value.casefold()))


def _source_negative(value: str) -> bool:
    return bool(NEGATIVE.search(value) or re.search(r"\bnormal\b", value, re.I))


def _addendum_supersedes(claim: dict, source: str, best: str, best_position: int) -> bool:
    marker = list(AUTHORITY.finditer(source))
    if not marker or best_position >= marker[-1].start() or not HISTORICAL.search(claim["text"]):
        return False
    addendum = source[marker[-1].end():]
    if not CORRECTION.search(addendum):
        return False
    overlap = _tokens(claim["text"]) & _tokens(addendum)
    # A recommendation to obtain prior comparison is overtaken when the
    # addendum explicitly records that those prior studies became available.
    prior_request_resolved = bool(claim["role"] == "RECOMMENDATION" and
                                  re.search(r"\b(?:compare|comparison|previous films|prior studies)\b", claim["text"], re.I)
                                  and re.search(r"\bprior\s+(?:films|studies).*\bavailable\b", addendum, re.I | re.S))
    return prior_request_resolved or len(overlap) >= 2


def _later_interpretation_supersedes(claim: dict, source: str, best_position: int) -> bool:
    if claim["role"] not in {"FINDING", "PERTINENT_NEGATIVE"} or re.search(
            r"\b(?:mention|specif|cannot be excluded|possible|might|could|may|suggest)\w*\b", claim["text"], re.I):
        return False
    later = [(m, source[m.end():]) for m in re.finditer(r"(?im)^\s*(?:IMPRESSION|CONCLUSION)\s*:?", source)
             if m.start() > best_position]
    if not later:
        return False
    claim_negative = bool(NEGATIVE.search(claim["text"]))
    terms = _tokens(claim["text"])
    for marker, body in later:
        end = SECTION.search(body)
        for sentence in _sentences(re.sub(r"\s+", " ", body[:end.start() if end else len(body)])):
            overlap = terms & _tokens(sentence)
            if len(overlap) >= 2 and overlap - CONTEXT and bool(NEGATIVE.search(sentence)) != claim_negative:
                return True
    return False


def validate_claim(claim: dict, source: str) -> dict:
    """Validate one claim; uncertainty is never promoted to source support."""
    text, role = claim["text"], claim["role"]
    result = {**claim, "validation_status": "UNRESOLVED", "validation_reason": "Source support uncertain"}
    if re.search(r"\b(?:no mention|not mentioned|does not mention)\b", text, re.I):
        result.update(validation_status="UNSUPPORTED", validation_reason="Negative not explicitly stated")
        return result
    clauses = _source_clauses(source)
    wanted = _tokens(text)
    scored = []
    for clause, position in clauses:
        have = _tokens(clause)
        overlap = len(wanted & have)
        score = overlap / max(1, len(wanted))
        scored.append((score, overlap, clause, position))
    if not scored:
        return result
    score, overlap, best, position = max(scored, key=lambda x: (x[0], x[1]))
    if _addendum_supersedes(claim, source, best, position):
        result.update(validation_status="SUPERSEDED", validation_reason="Superseded by addendum")
        return result
    if _later_interpretation_supersedes(claim, source, position):
        result.update(validation_status="SUPERSEDED", validation_reason="Superseded by final interpretation")
        return result
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", text))
    if years and not years <= set(re.findall(r"\b(?:19|20)\d{2}\b", source)):
        result.update(validation_status="UNSUPPORTED", validation_reason="Unsupported date")
        return result
    if not _same_measurements(text, source) or not set(NUMBER.findall(text)) <= set(NUMBER.findall(source)):
        reason = "Measurement mismatch" if role == "MEASUREMENT" or MEASURE.search(text) else "Unsupported quantitative detail"
        result.update(validation_status="UNSUPPORTED", validation_reason=reason)
        return result
    if role == "RECOMMENDATION":
        options = [(s, p) for s, p in clauses if RECOMMEND.search(s)]
        if not options:
            result.update(validation_status="UNSUPPORTED", validation_reason="Invented recommendation")
            return result
        rec_best = max(options, key=lambda x: len(wanted & _tokens(x[0])) / max(1, len(wanted)))
        rec_score = len(wanted & _tokens(rec_best[0])) / max(1, len(wanted))
        if rec_score < .56:
            result.update(validation_status="UNSUPPORTED", validation_reason="Invented recommendation")
            return result
        if _addendum_supersedes(claim, source, rec_best[0], rec_best[1]):
            result.update(validation_status="SUPERSEDED", validation_reason="Superseded by addendum")
            return result
        if re.search(r"\b(?:recommended|required|must)\b", text, re.I) and re.search(
                r"\b(?:should be considered|could be provided|may be considered)\b", rec_best[0], re.I):
            result.update(validation_status="UNSUPPORTED", validation_reason="Stronger than source recommendation")
            return result
        score, overlap, best, position = rec_score, len(wanted & _tokens(rec_best[0])), *rec_best
    if re.search(r"\b(?:recommended|required|must)\b", text, re.I) and re.search(
            r"\b(?:should be considered|could be provided|may be considered)\b", best, re.I):
        result.update(validation_status="UNSUPPORTED", validation_reason="Stronger than source recommendation")
        return result
    if re.search(r"\b(?:no|not)\s+(?:additional|further)?\s*(?:workup|evaluation|testing)|\bdo not require\b", text, re.I):
        no_workup = [(s, p) for s, p in clauses if re.search(
            r"\b(?:no|not)\s+(?:additional|further)?\s*(?:workup|evaluation|testing)|\bdo not require\b", s, re.I)]
        if not no_workup:
            result.update(validation_status="UNSUPPORTED", validation_reason="Invented no-workup recommendation")
            return result
        best_no = max(no_workup, key=lambda x: len(wanted & _tokens(x[0])))
        extra = wanted - _tokens(best_no[0])
        if len(extra) >= 3 and any(RECOMMEND.search(s) and s != best_no[0] for s, _ in clauses):
            result.update(validation_status="UNSUPPORTED", validation_reason="No-workup claim exceeds source scope")
            return result
    if role == "DIAGNOSTIC_CONSIDERATION":
        if score < .65 or overlap < 2:
            result.update(validation_status="UNSUPPORTED", validation_reason="Unsupported diagnostic consideration")
            return result
    if (role == "FINDING" and NEGATIVE.search(best) and not NEGATIVE.search(text)
            and overlap >= 1 and score >= .55):
        result.update(validation_status="UNSUPPORTED", validation_reason="Contradicts source assertion")
        return result
    no_workup_claim = bool(re.search(
        r"\b(?:no|not)\s+(?:additional|further)?\s*(?:workup|evaluation|testing)|\bdo not require\b", text, re.I))
    if no_workup_claim and re.search(r"\bthis finding\b", text, re.I):
        return result
    if (role == "PERTINENT_NEGATIVE" or NEGATIVE.search(text)) and not no_workup_claim:
        if not _source_negative(best):
            result.update(validation_status="UNSUPPORTED", validation_reason="Negative not explicitly stated")
            return result
    side = _laterality(text)
    source_side = _laterality(best)
    if side and source_side and not (side & source_side or "bilateral" in source_side):
        result.update(validation_status="UNSUPPORTED", validation_reason="Laterality mismatch")
        return result
    if score >= .68 and overlap >= 2 or (role == "MEASUREMENT" and MEASURE.search(text) and score >= .5):
        result.update(validation_status="SUPPORTED", validation_reason="Supported by protected report")
    elif role == "RECOMMENDATION" and score >= .56 and overlap >= 2:
        result.update(validation_status="SUPPORTED", validation_reason="Explicit source recommendation")
    elif score < .35 and overlap < 2 and role in {"DIAGNOSTIC_CONSIDERATION", "RECOMMENDATION"}:
        result.update(validation_status="UNSUPPORTED", validation_reason="Unsupported by source")
    return result


def _validate_atomic(child: dict, source: str) -> dict:
    """Apply unchanged source rules, then require explicit atomic interval support."""
    result = validate_claim(child, source)
    if child.get("atomic_type") != "TEMPORAL" or result["validation_status"] == "SUPERSEDED":
        return result
    qualifiers = {term.casefold() for term in ATOMIC_TEMPORAL.findall(child["text"])}
    if not qualifiers:
        return result
    core = _tokens(ATOMIC_TEMPORAL.sub("", child["text"]))
    if not core:
        result.update(validation_status="UNRESOLVED",
                      validation_reason="Temporal qualifier lacks a clinical target")
        return result
    needed = min(2, len(core))
    supported = False
    for clause, _ in _source_clauses(source):
        available = {term.casefold() for term in ATOMIC_TEMPORAL.findall(clause)}
        if (qualifiers <= available and
                len(core & _tokens(clause)) >= needed and
                not any(re.search(r"\bnot\s+" + re.escape(term) + r"\b", clause, re.I)
                        for term in qualifiers)):
            supported = True
            break
    if not supported:
        result.update(validation_status="UNSUPPORTED",
                      validation_reason="Temporal qualifier not supported for this source finding")
    return result


def project_and_validate(raw: str, source: str) -> tuple[list[dict], dict]:
    occurrences = _project_occurrences(raw)
    raw_count = len(occurrences)
    # Parents remain immutable audit records. Only independently validated
    # atomic children contribute to comparison counts.
    parents = _deduplicate_claims([validate_claim(claim, source) for claim in occurrences], validated=True)
    atomic = [child for index, parent in enumerate(occurrences, start=1)
              for child in decompose_occurrence(parent, index)]
    validated = _deduplicate_claims([_validate_atomic(child, source) for child in atomic], validated=True)
    nonempty_lines = [re.sub(r"\s+", " ", line).strip().casefold()
                      for line in raw.splitlines() if line.strip()]
    repeated_lines = len(nonempty_lines) - len(set(nonempty_lines))
    statuses = {status: sum(item["validation_status"] == status for item in validated)
                for status in ("SUPPORTED", "UNSUPPORTED", "SUPERSEDED", "UNRESOLVED")}
    return validated, {"raw_medgemma_claim_count": raw_count,
                       "unique_projected_medgemma_claim_count": len(parents),
                       "duplicate_claim_count": raw_count - len(parents),
                       "parents": parents,
                       "raw_atomic_claim_count": len(atomic),
                       "unique_atomic_claim_count": len(validated),
                       "atomic_duplicate_count": len(atomic) - len(validated),
                       "raw_repeated_line_count": repeated_lines,
                       "validation_counts": statuses,
                       "model_content_failure": bool(not validated and raw.strip() and
                                                     re.search(r"(?im)^\s*FINDINGS\b", source))}
