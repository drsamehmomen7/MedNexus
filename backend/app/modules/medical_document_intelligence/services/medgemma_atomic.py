"""Conservative, surface-derived atomic claims for comparison-only output.

This module has no source access. It never decides support, corrects a model
statement, or changes the raw response. Every child is traceable to one parent.
"""
from __future__ import annotations

import re


MEASUREMENT = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mm|cm|ml|cc)\b", re.I)
TEMPORAL = re.compile(r"\b(?:new|stable|unchanged|persistent|resolved|decreased|increased|improved|worsened)\b", re.I)
OBSERVATION = re.compile(r"\b(?:is|are|was|were|has|have|shows?|demonstrates?|measures?|measured|decreased|increased|resolved|stable|new)\b", re.I)
DIAGNOSTIC_LINK = re.compile(r"\b(?:suggests?|consistent with|concerning for)\b", re.I)
RECOMMENDATION = re.compile(r"\b(?:recommend\w*|consider\w*|repeat|reevaluat\w*|follow[ -]?up|consult\w*|obtain|perform|should|could be provided)\b", re.I)
INTRODUCTION = re.compile(r"\b(?:includes?|including|such as|comprises?)\s+", re.I)
TRAILING_CONTEXT = re.compile(r"\s+\b(?:during|based upon|according to)\b.{8,}$", re.I)
PARENTHETICAL_NUMBER = re.compile(r"\s*\((?:19|20)\d{2}\)|\s*\([^)]*\b\d+(?:\.\d+)?\s*(?:mm|cm|ml|cc)\b[^)]*\)", re.I)
COMPARISON_PERIOD = re.compile(r"\s+(?:of|for|over)\s+\d+\s+(?:days?|weeks?|months?|years?)\s+(?:ago|prior|earlier)\b", re.I)
MEASURE_VERB = re.compile(r"\b(?:measures?|measured|measuring|sizing|size(?:\s+of)?)\b", re.I)
PRIOR_MENTION = re.compile(r"\b(?:seen|identified|noted)\s+(?:before|previously)\s*$", re.I)
TRAILING_HELPER = re.compile(r"\s+\b(?:has|have|had|is|are|was|were|now|appears?\s+to\s+have)\s*$", re.I)


def _trim(text: str) -> str:
    text = text.strip(" \t,;:.=-")
    return re.sub(r"\s+\b(?:and|or|also|approximately|about|up to)\s*$", "", text, flags=re.I).strip(" \t,;:.=-")


def _independent_segments(text: str, role: str) -> list[str]:
    """Split only overt independent propositions; preserve shared negation."""
    pieces = [text]
    for pattern in (r"\s*;\s*", r"\s+along\s+with\s+", r"\s+as\s+well\s+as\s+"):
        pieces = [part for value in pieces for part in re.split(pattern, value, flags=re.I) if _trim(part)]
    result = []
    for value in pieces:
        contrast = re.search(r"\s+but\s+", value, re.I)
        if contrast and TEMPORAL.search(value[:contrast.start()]) and TEMPORAL.search(value[contrast.end():]):
            left, right = _trim(value[:contrast.start()]), _trim(value[contrast.end():])
            first_status = TEMPORAL.search(left)
            subject = _trim(TRAILING_HELPER.sub("", left[:first_status.start()]))
            subject = _trim(TRAILING_HELPER.sub("", subject))
            if len(subject.split()) >= 2:
                result.extend((left, _trim(subject + " " + right)))
                continue
        separated = re.split(r"\s+and\s+", value, maxsplit=1, flags=re.I)
        if (len(separated) == 2 and len(separated[0].split()) >= 2 and
                len(separated[1].split()) >= 2 and
                ((role == "RECOMMENDATION" and all(RECOMMENDATION.search(part) for part in separated)) or
                 (role != "RECOMMENDATION" and all(OBSERVATION.search(part) for part in separated)))):
            result.extend(_trim(part) for part in separated)
        else:
            result.append(_trim(value))
    return result


def _diagnostic_items(text: str) -> list[str]:
    lead = INTRODUCTION.search(text)
    if not lead:
        return [text]
    tail = text[lead.end():]
    items = [part.strip(" .,;:") for part in re.split(r"\s*(?:,|\bor\b|\bversus\b|\bvs\.?\b)\s*", tail, flags=re.I)]
    # Only enumerate explicit short alternatives. Complex connective prose is
    # retained as one claim for the validator to leave unresolved/rejected.
    if not 2 <= len(items) <= 8 or any(not item or len(item.split()) > 7 for item in items):
        return [text]
    return items


def _child(text: str, role: str, kind: str) -> dict:
    return {"text": _trim(text), "role": role, "atomic_type": kind}


def _within_segment(segment: str, role: str) -> list[dict]:
    if not segment:
        return []
    if role == "DIAGNOSTIC_CONSIDERATION":
        items = _diagnostic_items(segment)
        if len(items) > 1:
            return [_child(item, role, "DIAGNOSTIC_CONSIDERATION") for item in items]
    if role == "RECOMMENDATION":
        return [_child(segment, role, "RECOMMENDATION")]

    link = DIAGNOSTIC_LINK.search(segment)
    if link and _trim(segment[:link.start()]) and _trim(segment[link.end():]):
        return (_within_segment(_trim(segment[:link.start()]),
                                "PERTINENT_NEGATIVE" if role == "PERTINENT_NEGATIVE" else "FINDING") +
                [_child(segment[link.end():], "DIAGNOSTIC_CONSIDERATION", "DIAGNOSTIC_CONSIDERATION")])

    # A trailing circumstance is not an independent finding. Its original text
    # remains on the parent; the assertion is a literal prefix of the parent.
    context = TRAILING_CONTEXT.search(segment)
    if context and not MEASUREMENT.search(context.group()) and not TEMPORAL.search(context.group()):
        segment = _trim(segment[:context.start()])

    children = []
    measured = MEASUREMENT.search(segment)
    if measured:
        verb = MEASURE_VERB.search(segment)
        if verb and verb.start() < measured.start():
            base = _trim(segment[:verb.end()])
            if len(base.split()) >= 2:
                children.append(_child(base, "FINDING", "BASE_FINDING"))
        elif len(_trim(segment[:measured.start()]).split()) >= 2:
            base = re.sub(r"\b(?:size|thickness|diameter|length|width|depth)\b\s*(?:=|:)?\s*(?:approximately|about|up\s+to)?\s*$",
                          "", segment[:measured.start()], flags=re.I)
            base = re.sub(r"[=:]\s*(?:approximately|about|up\s+to)?\s*$", "", base, flags=re.I)
            if len(_trim(base).split()) >= 2:
                children.append(_child(base, "FINDING", "BASE_FINDING"))
        children.append(_child(segment, "MEASUREMENT", "MEASUREMENT"))
        return children

    temporal = TEMPORAL.search(segment)
    if temporal and role != "PERTINENT_NEGATIVE":
        before = _trim(segment[:temporal.start()])
        after = _trim(segment[temporal.start():])
        if not before:
            # An attributive qualifier before the noun: retain the qualified
            # child and derive only the literal, unqualified noun phrase.
            noun = _trim(segment[temporal.end():])
            if len(noun.split()) >= 2 and temporal.group().casefold() != "resolved":
                children.append(_child(noun, "FINDING", "BASE_FINDING"))
        else:
            before = _trim(TRAILING_HELPER.sub("", before))
            before = _trim(PRIOR_MENTION.sub("", before))
            before = _trim(TRAILING_HELPER.sub("", before))
            if len(before.split()) >= 2 and temporal.group().casefold() != "resolved":
                children.append(_child(before, "FINDING", "BASE_FINDING"))
        temporal_text = _trim(" ".join(part for part in (before, after) if part))
        without_detail = _trim(COMPARISON_PERIOD.sub("", PARENTHETICAL_NUMBER.sub("", temporal_text)))
        if without_detail and without_detail != temporal_text:
            children.append(_child(without_detail, "FINDING", "TEMPORAL"))
            children.append(_child(temporal_text, "FINDING", "QUALIFIER_DETAIL"))
        else:
            children.append(_child(temporal_text, "FINDING", "TEMPORAL"))
        return children

    return [_child(segment, role, "NEGATIVE" if role == "PERTINENT_NEGATIVE" else "FINDING")]


def decompose_occurrence(parent: dict, occurrence_index: int) -> list[dict]:
    """Produce independently testable children with parent and span audit data."""
    original = parent["text"]
    candidates = []
    for segment in _independent_segments(original, parent["role"]):
        candidates.extend(_within_segment(segment, parent["role"]))
    children = []
    for ordinal, candidate in enumerate(candidates):
        if not candidate["text"] or len(candidate["text"]) < 3:
            continue
        # A contiguous child has an exact character span. A composed child
        # retains its exact parent plus surface terms for audit instead.
        start = original.casefold().find(candidate["text"].casefold())
        child = {**candidate, "source_section": parent.get("source_section"),
                 "line_number": parent.get("line_number"),
                 "parent_id": f"parent-{occurrence_index}",
                 "parent_text": original, "parent_role": parent["role"],
                 "parent_occurrence": occurrence_index,
                 "child_ordinal": ordinal,
                 "parent_span": [start, start + len(candidate["text"])] if start >= 0 else None,
                 "surface_derived": True}
        children.append(child)
    return children
