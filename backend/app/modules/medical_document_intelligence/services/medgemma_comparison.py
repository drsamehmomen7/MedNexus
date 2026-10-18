"""Non-authoritative, protected-text-only MedGemma comparison evaluations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import Lock
from uuid import uuid4

from .medgemma_adapter import MedGemmaTextAdapter, enabled
from .medgemma_generation_guard import LIMIT_CODE, MAX_NEW_TOKENS, repeated_text_block
from .medgemma_evidence import (_tokens as evidence_tokens, claim_features, claim_identity,
                                project_and_validate, validate_claim)


ROOT = Path(r"D:\MedNexus\Debug\MRJ_MedGemma_Comparison")
ROLES = {
    "clinically important findings": "FINDING", "key findings": "FINDING",
    "pertinent negatives": "PERTINENT_NEGATIVE", "measurements": "MEASUREMENT",
    "diagnostic considerations": "DIAGNOSTIC_CONSIDERATION",
    "follow-up recommendations": "RECOMMENDATION", "recommendations": "RECOMMENDATION",
}
STOP = {"a", "an", "the", "is", "are", "of", "in", "on", "at", "to", "for", "with",
        "and", "or", "from", "by", "as", "be", "noted", "present", "seen", "right",
        "left", "bilateral", "no", "without", "evidence", "finding", "findings", "mass",
        "lesion", "clinical", "report", "study", "approximately", "cm", "mm"}
ALIASES = {"dvt": "thrombosis",
           "thrombus": "thrombosis", "clot": "thrombosis", "ultrasonography": "ultrasound"}


def project_markdown(raw: str) -> list[dict]:
    """Only map recognizable Markdown headings/bullets; retain bullet content as emitted."""
    role = None
    rows = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.sub(r"^#{1,4}\s*", "", stripped)
        heading = heading.strip("*_:\t ").casefold()
        if heading in ROLES and not re.match(r"^[-*+]\s", stripped):
            role = ROLES[heading]
            continue
        bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.*)$", stripped)
        if bullet:
            rows.append({"role": role or "UNRESOLVED", "text": bullet.group(1)})
        else:
            rows.append({"role": "UNRESOLVED", "text": stripped})
    return rows


def _tokens(value):
    normalized = re.sub(r"\bdeep (?:vein|venous) thrombosis\b", "thrombosis", str(value).casefold())
    words = re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalized)
    return {ALIASES.get(word, word) for word in words if word not in STOP and len(word) > 1}


def _assertion(text, role):
    if role == "DIAGNOSTIC_CONSIDERATION":
        return "UNCERTAIN"
    if role == "PERTINENT_NEGATIVE" or re.search(r"\b(?:no|without|negative for|absent|not seen|not identified|free of)\b", text, re.I):
        return "ABSENT_NEGATED"
    if re.search(r"\b(?:possible|may|could|versus|vs\.?|suggestive|considered)\b", text, re.I):
        return "UNCERTAIN"
    return "PRESENT"


def _laterality(text):
    found = {word.upper() for word in re.findall(r"\b(?:left|right|bilateral)\b", text, re.I)}
    return next(iter(found)) if len(found) == 1 else None


def _numbers(text):
    return set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:cm|mm)\b", text.casefold()))


def compare(native_facts: list[dict], projected: list[dict], measurements=()) -> dict:
    """One-to-one conservative lexical assistance; ambiguity is never forced."""
    native = [{"statement": f.get("display_label") or f.get("source_expression") or "",
               "assertion": f.get("assertion_state"), "group": f.get("group"),
               "anatomy": f.get("anatomic_site") or ""}
              for f in native_facts if f.get("temporal_status") != "SUPERSEDED" and
              (f.get("display_label") or f.get("source_expression"))]
    owners = {f.get("fact_id"): f for f in native_facts}
    for measurement in measurements:
        value = measurement.get("source_text")
        if not isinstance(value, str) or not value.strip():
            continue
        owner = owners.get(measurement.get("source_fact_id"), {})
        native.append({"statement": f'{owner.get("display_label") or "Measurement"}: {value}',
                       "assertion": "PRESENT", "group": "MEASUREMENT", "anatomy": owner.get("anatomic_site") or ""})
    groups = {key: [] for key in ("AGREEMENT", "MRJ_ONLY", "MEDGEMMA_ONLY", "CONFLICT", "UNRESOLVED")}
    if not any(item["role"] != "UNRESOLVED" for item in projected):
        for fact in native:
            groups["UNRESOLVED"].append({"mrj": fact["statement"], "medgemma": None})
        for item in projected:
            groups["UNRESOLVED"].append({"mrj": None, "medgemma": item["text"]})
        return {"status": "AVAILABLE", "counts": {key: len(value) for key, value in groups.items()}, "groups": groups}
    used = set()
    for item in projected:
        text = item["text"]
        if item["role"] == "UNRESOLVED":
            groups["UNRESOLVED"].append({"mrj": None, "medgemma": text})
            continue
        concept = _tokens(text)
        scored = []
        for index, fact in enumerate(native):
            if item["role"] == "RECOMMENDATION" and fact["group"] != "RECOMMENDATION":
                continue
            if item["role"] == "MEASUREMENT" and fact["group"] not in {"KEY", "SECONDARY", "MEASUREMENT"}:
                continue
            ftokens = _tokens(fact["statement"] + " " + fact["anatomy"])
            overlap = len(concept & ftokens)
            score = overlap / max(1, min(len(concept), len(ftokens)))
            if overlap and score >= 0.7:
                scored.append((score, overlap, index))
        scored.sort(reverse=True)
        if not scored:
            groups["MEDGEMMA_ONLY"].append({"mrj": None, "medgemma": text})
            continue
        if len(scored) > 1 and scored[0][:2] == scored[1][:2]:
            groups["UNRESOLVED"].append({"mrj": None, "medgemma": text})
            continue
        index = scored[0][2]
        fact = native[index]
        med_assertion = _assertion(text, item["role"])
        native_assertion = fact["assertion"]
        left, right = _laterality(fact["statement"] + " " + fact["anatomy"]), _laterality(text)
        a, b = _numbers(fact["statement"]), _numbers(text)
        disagreement = (native_assertion in {"PRESENT", "ABSENT_NEGATED"} and
                        med_assertion in {"PRESENT", "ABSENT_NEGATED"} and native_assertion != med_assertion)
        disagreement |= bool(left and right and left != right and left != "BILATERAL" and right != "BILATERAL")
        disagreement |= bool(a and b and a.isdisjoint(b))
        uncertain = (native_assertion == "UNCERTAIN" or med_assertion == "UNCERTAIN") and not disagreement
        category = "CONFLICT" if disagreement else "UNRESOLVED" if uncertain else "AGREEMENT"
        groups[category].append({"mrj": fact["statement"], "medgemma": text})
        used.add(index)
    for index, fact in enumerate(native):
        if index not in used:
            groups["MRJ_ONLY"].append({"mrj": fact["statement"], "medgemma": None})
    return {"status": "AVAILABLE", "counts": {key: len(value) for key, value in groups.items()}, "groups": groups}


V2_CATEGORIES = ("AGREEMENT", "MRJ_ONLY", "MEDGEMMA_ONLY", "CONFLICT", "UNSUPPORTED", "UNRESOLVED")


def _empty_v2(status="COMPARISON_NOT_VALID", reason="MEDGEMMA_OUTPUT_INCOMPLETE"):
    return {"status": status, "reason": reason, "comparison_valid": False,
            "counts": {key: 0 for key in V2_CATEGORIES},
            "groups": {key: [] for key in V2_CATEGORIES}}


def _native_claims(facts, source, measurements=()):
    rows = []
    for fact in facts:
        if fact.get("temporal_status") == "SUPERSEDED" or "SUPERSEDED_BY_ADDENDUM" in fact.get("review_reason", []):
            continue
        text = fact.get("display_label") or fact.get("source_expression")
        if not text:
            continue
        anchors = fact.get("evidence_anchors") or []
        role = ("PERTINENT_NEGATIVE" if fact.get("group") == "NEGATIVE" else
                "RECOMMENDATION" if fact.get("group") == "RECOMMENDATION" else "FINDING")
        source_check = validate_claim({"text": text, "role": role}, source)
        if source_check["validation_status"] == "SUPERSEDED":
            continue
        anchored = any(a.get("quote") and " ".join(a["quote"].split()).casefold() in
                       " ".join(source.split()).casefold() for a in anchors)
        if not anchored:
            anchored = source_check["validation_status"] == "SUPPORTED"
        if anchored:
            rows.append({"statement": text, "assertion": fact.get("assertion_state"),
                         "group": fact.get("group"), "tokens": evidence_tokens(text),
                         "features": claim_features(text, role),
                         "canonical_concept": fact.get("canonical_concept") or "",
                         "anatomy": fact.get("anatomy") or [],
                         "laterality": fact.get("laterality")})
    owners = {fact.get("fact_id"): fact for fact in facts}
    for measurement in measurements:
        value = measurement.get("source_text")
        if not isinstance(value, str) or not value.strip() or value not in source:
            continue
        owner = owners.get(measurement.get("source_fact_id"), {})
        statement = f'{owner.get("display_label") or "Measurement"}: {value}'
        rows.append({"statement": statement, "assertion": "PRESENT", "group": "MEASUREMENT",
                     "tokens": evidence_tokens(statement),
                     "features": claim_features(statement, "MEASUREMENT"),
                     "canonical_concept": owner.get("canonical_concept") or "",
                     "anatomy": owner.get("anatomy") or [],
                     "laterality": owner.get("laterality")})
    return rows


MEASUREMENT_WORDS = {"size", "mm", "cm", "ml", "cc", "dimension", "length",
                     "width", "depth", "transverse", "greatest", "maximum",
                     "diameter", "thickness"}
RECOMMENDATION_PROCESS_WORDS = {"testing", "evaluation", "workup", "consultation",
                                "imaging", "repeat", "monitoring", "follow", "up",
                                "further", "additional", "diagnostic", "considered",
                                "could", "may", "should", "provided", "clinically",
                                "indicated", "such", "including"}

# These are dimensions of a claim, not terms that establish its base concept.
# Keeping them separate prevents a shared finding from swallowing a supported
# interval change, location, measurement, or recommendation.
TEMPORAL_WORDS = {"new", "stable", "unchanged", "resolved", "persistent",
                  "increased", "decreased", "worsened", "improved"}
LOCATION_PHRASE = re.compile(
    r"\b(?:in|at|within|along)\s+(?:the\s+)?"
    r"((?:upper|lower|inner|outer|medial|lateral|anterior|posterior|"
    r"proximal|distal|superior|inferior|central|peripheral|apical|basal)\s+[a-z]+)\b",
    re.I)
SEVERITY_WORDS = {"trace", "minimal", "mild", "small", "moderate", "large",
                  "marked", "severe", "extensive"}
BASE_FILLER = {"absent", "present", "negative", "study", "evidence", "approximately", "about",
               "again", "also", "have", "has", "had", "remains", "remain",
               "the", "and", "or", "in", "on", "of", "to", "for", "with",
               "there", "this", "that", "both", "not", "identified", "seen"}


def _comparison_parts(text, role, *, anatomy=(), laterality=None,
                      assertion=None, source_authority="SUPPORTED"):
    """Keep clinical dimensions separate from exact normalized base terms."""
    features = claim_features(text, role)
    words = set(features["words"])
    temporal = words & TEMPORAL_WORDS
    severity = words & SEVERITY_WORDS
    excluded = (TEMPORAL_WORDS | SEVERITY_WORDS | MEASUREMENT_WORDS |
                BASE_FILLER | RECOMMENDATION_PROCESS_WORDS |
                {"left", "right", "bilateral"})
    base = {word for word in words - excluded if not re.fullmatch(r"\d+(?:\.\d+)?", word)}
    # A parenthetical initialism repeats its immediately preceding phrase; it
    # does not add a second clinical concept or qualifier.
    for acronym in re.finditer(r"\(([A-Z]{2,6})\)", text):
        preceding = re.findall(r"[A-Za-z]+", text[:acronym.start()])[-len(acronym.group(1)):]
        if len(preceding) == len(acronym.group(1)) and "".join(word[0].upper() for word in preceding) == acronym.group(1):
            base.discard(acronym.group(1).casefold())
    sites = set()
    for item in anatomy:
        sites.update(claim_features(str(item), "FINDING")["words"])
    sides = set(features["laterality"])
    if laterality:
        sides.add(str(laterality).casefold())
    return {"base_concept": base, "anatomy_location": sites,
            "location_detail": {match.group(1).casefold() for match in LOCATION_PHRASE.finditer(text)},
            "assertion": assertion or features["assertion"],
            "temporal_interval": temporal, "severity_descriptor": severity,
            "measurement": set(features["measurements"]),
            "laterality": sides, "recommendation_action": features["kind"],
            "source_authority": source_authority, "ordered_compact": features["ordered_compact"]}


def _base_match_score(med, native, canonical_concept):
    """Exact component overlap only; no approximate semantic equivalence."""
    if med["recommendation_action"] != native["recommendation_action"]:
        return None
    common = med["base_concept"] & native["base_concept"]
    distinctive = {term for term in common if len(term) >= 5}
    if len(common) >= 2 and distinctive:
        return len(common) / max(1, len(native["base_concept"])) + len(common) / max(1, len(med["base_concept"]))
    if len(common) == 1 and native["base_concept"] <= med["base_concept"] and distinctive:
        return 2.0
    if (len(common) == 1 and med["measurement"] and
            med["measurement"] == native["measurement"]):
        return 1.5
    # A structured Native concept can identify an exact joined/split compound.
    # Only the complete distinctive compound is accepted, never an edit distance.
    parts = str(canonical_concept or "").split(":")
    if len(parts) == 3 and parts[1] == "open":
        concept = re.sub(r"[^a-z0-9]", "", parts[2].casefold())
        if len(concept) >= 8 and concept in med["ordered_compact"]:
            return 1.5
    return None


def _meaning_differences(med, native):
    """Return explicit clinical qualifiers, not incidental lexical differences."""
    additions = []
    for key, label in (("temporal_interval", "interval status"),
                       ("severity_descriptor", "severity"),
                       ("laterality", "laterality"),
                       ("location_detail", "location"),
                       ("measurement", "measurement")):
        additional = med[key] - native[key]
        if additional:
            additions.append(f"{label}: {', '.join(map(str, sorted(additional)))}")
    return additions


def compare_validated(native_facts, claims, source, metrics, measurements=()):
    """Give each unique validated atomic child exactly one primary category."""
    groups = {key: [] for key in V2_CATEGORIES}
    native = _native_claims(native_facts, source, measurements)
    used = set()
    seen = set()
    for claim in claims:
        status, text = claim["validation_status"], claim["text"]
        identity = (claim_identity(text, claim["role"]), status)
        if identity in seen:
            metrics["duplicate_claim_count"] = metrics.get("duplicate_claim_count", 0) + 1
            continue
        seen.add(identity)
        claim_id = f"atomic-{len(seen)}"
        if status in {"UNSUPPORTED", "SUPERSEDED"}:
            groups["UNSUPPORTED"].append({"mrj": None, "medgemma": text,
                "atomic_claim_id": claim_id, "validation_status": status,
                "reason": claim["validation_reason"]})
            continue
        if status == "UNRESOLVED":
            groups["UNRESOLVED"].append({"mrj": None, "medgemma": text,
                "atomic_claim_id": claim_id, "validation_status": status,
                "reason": claim["validation_reason"]})
            continue
        med = _comparison_parts(text, claim["role"], source_authority=status)
        matches = []
        for index, fact in enumerate(native):
            current = _comparison_parts(fact["statement"],
                                        "RECOMMENDATION" if fact["group"] == "RECOMMENDATION" else
                                        "PERTINENT_NEGATIVE" if fact["group"] == "NEGATIVE" else "FINDING",
                                        anatomy=fact["anatomy"], laterality=fact["laterality"],
                                        assertion=fact["assertion"], source_authority="ANCHORED")
            score = _base_match_score(med, current, fact["canonical_concept"])
            if score is None:
                continue
            if med["laterality"] and current["laterality"] and med["laterality"].isdisjoint(current["laterality"]):
                continue
            if med["measurement"] and current["measurement"] and med["measurement"] != current["measurement"]:
                continue
            score += .25 * bool(med["measurement"] and med["measurement"] == current["measurement"])
            score += .1 * bool(med["anatomy_location"] & current["anatomy_location"])
            matches.append((score, index, current))
        matches.sort(reverse=True)
        if not matches or len(matches) > 1 and matches[0][0] == matches[1][0]:
            category = "UNRESOLVED" if matches else "MEDGEMMA_ONLY"
            groups[category].append({"mrj": None, "medgemma": text,
                "atomic_claim_id": claim_id, "validation_status": status,
                "reason": "Supported by source; not identified by MRJ Native" if category == "MEDGEMMA_ONLY" else
                          "Native correspondence uncertain"})
            continue
        _, index, current = matches[0]
        fact = native[index]
        incompatible_assertion = (med["assertion"] != current["assertion"] and
                                  {med["assertion"], current["assertion"]} <= {"PRESENT", "ABSENT_NEGATED"})
        incompatible_interval = (med["temporal_interval"] and current["temporal_interval"] and
                                 med["temporal_interval"].isdisjoint(current["temporal_interval"]))
        if incompatible_assertion or incompatible_interval:
            category = "CONFLICT"
        elif med["assertion"] == "UNCERTAIN" or current["assertion"] == "UNCERTAIN":
            category = "UNRESOLVED"
        else:
            category = "MEDGEMMA_ONLY" if _meaning_differences(med, current) else "AGREEMENT"
        additions = _meaning_differences(med, current) if category == "MEDGEMMA_ONLY" else []
        native_additions = _meaning_differences(current, med) if category == "AGREEMENT" else []
        groups[category].append({"mrj": fact["statement"] if category != "MEDGEMMA_ONLY" else None,
            "medgemma": text, "atomic_claim_id": claim_id, "validation_status": status,
            "matched_native": fact["statement"],
            "match_scope": "BASE_CONCEPT" if additions or native_additions else "COMPLETE_CLAIM",
            "additional_components": additions,
            "native_additional_components": native_additions,
            "reason": "Additional source-supported meaning beyond MRJ Native: " + "; ".join(additions)
                      if additions else "Material assertion or interval difference" if category == "CONFLICT" else
                      "Assertion correspondence uncertain" if category == "UNRESOLVED" else
                      "Same source-supported clinical meaning"})
        used.add(index)
    for index, fact in enumerate(native):
        if index not in used:
            groups["MRJ_ONLY"].append({"mrj": fact["statement"], "medgemma": None,
                                       "native_claim_id": f"native-{index + 1}",
                                       "reason": "No matching supported MedGemma claim"})
    counts = {key: len(rows) for key, rows in groups.items()}
    return {"status": "AVAILABLE", "comparison_valid": True, "counts": counts,
            "groups": groups, "metrics": {**metrics,
                "agreement_count": counts["AGREEMENT"], "mrj_only_count": counts["MRJ_ONLY"],
                "medgemma_only_grounded_count": counts["MEDGEMMA_ONLY"],
                "conflict_count": counts["CONFLICT"], "comparison_valid": True}}


def revalidate_payload(payload):
    """Project retained output in memory without rewriting its raw response."""
    result = dict(payload)
    raw = result.get("raw_response")
    source = (result.get("native_document", {}).get("stage_results", {}).get("PROTECT", {})
              .get("protected_document", {}).get("protected_text", ""))
    facts = (result.get("native_document", {}).get("stage_results", {}).get("EXTRACT", {})
             .get("clinical_synthesis", {}).get("canonical_facts", []))
    measurements = (result.get("native_document", {}).get("stage_results", {}).get("EXTRACT", {})
                    .get("clinical_synthesis", {}).get("governed_measurements", []))
    incomplete = (result.get("failure_code") == LIMIT_CODE or result.get("status") != "AVAILABLE" or
                  not isinstance(raw, str) or not raw.strip() or
                  result.get("token_limit_reached") is True or result.get("repetition_detected") is True or
                  isinstance(result.get("output_tokens"), int) and result["output_tokens"] >= MAX_NEW_TOKENS or
                  isinstance(raw, str) and repeated_text_block(raw))
    if incomplete:
        claims, metrics = project_and_validate(raw, source) if isinstance(raw, str) else ([], {
            "raw_medgemma_claim_count": 0, "unique_projected_medgemma_claim_count": 0,
            "duplicate_claim_count": 0, "validation_counts": {}, "model_content_failure": False})
        result["comparison"] = _empty_v2()
        result["validation"] = {"claims": claims, **metrics,
                                "comparison_valid": False, "reason": "MEDGEMMA_OUTPUT_INCOMPLETE"}
        result["comparison_version"] = 9
        return result
    claims, metrics = project_and_validate(raw, source)
    result["validation"] = {"claims": claims, **metrics}
    if metrics["model_content_failure"]:
        result["comparison"] = _empty_v2("MODEL_CONTENT_FAILURE", "MODEL_CONTENT_FAILURE")
        result["validation"]["comparison_valid"] = False
    else:
        result["comparison"] = compare_validated(facts, claims, source, metrics, measurements)
        result["validation"]["comparison_valid"] = True
    result["comparison_version"] = 9
    return result


class ComparisonEvaluationService:
    def __init__(self, root=ROOT, adapter=None):
        self.root = Path(root)
        self.adapter = adapter or MedGemmaTextAdapter()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="medgemma-comparison")
        self.lock = Lock()

    def _path(self, run_id, document_id):
        if not re.fullmatch(r"[0-9a-f-]{32,36}", run_id) or not re.fullmatch(r"[0-9a-f-]{32,36}", document_id):
            raise ValueError("Invalid evaluation identifier")
        return self.root / f"{run_id}_{document_id}.json"

    def _write(self, path, payload):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, run_id, document_id):
        path = self._path(run_id, document_id)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        retained = payload.get("native_document", {}).get("stage_results", {}).get("PROTECT")
        if isinstance(retained, dict) and (set(retained) != {"protected_document", "protection_result"}
                                         or "report_id" not in (retained.get("protected_document") or {})):
            protected = retained.get("protected_document") or {}
            payload["native_document"]["stage_results"]["PROTECT"] = {
                "protected_document": {"protected_text": protected.get("protected_text", ""),
                                       "report_id": document_id},
                "protection_result": {"review_required": (retained.get("protection_result") or {}).get("review_required", False)},
            }
            # Legacy normalization is read-only; retained raw output stays immutable.
        payload = revalidate_payload(payload)
        raw = payload.get("raw_response")
        if payload.get("failure_code") == LIMIT_CODE or (
                payload.get("status") == "AVAILABLE" and isinstance(raw, str) and
                ((isinstance(payload.get("output_tokens"), int) and
                  payload["output_tokens"] >= MAX_NEW_TOKENS) or repeated_text_block(raw))):
            # Preserve the full retained output; the UI exposes it only in a
            # collapsed evaluator disclosure for incomplete generations.
            return {**payload, "status": "FAILED", "failure_code": LIMIT_CODE,
                    "projected": []}
        if payload.get("status") == "PROCESSING" and (run_id, document_id) not in self.active:
            payload["status"] = "FAILED"
            payload["comparison"] = {"status": "NOT_AVAILABLE"}
        return payload

    def list(self):
        if not self.root.is_dir():
            return []
        entries = []
        for path in sorted(self.root.glob("*_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or not payload.get("run_id") or not payload.get("document_id"):
                    continue
                entries.append({key: payload.get(key) for key in ("run_id", "document_id", "status", "created_at", "display_name")})
            except (OSError, ValueError):
                continue
        return entries

    @property
    def active(self):
        return getattr(self, "_active", set())

    def start(self, run_id, document_id, document):
        path = self._path(run_id, document_id)
        protect = document.get("stage_results", {}).get("PROTECT", {}).get("protected_document", {})
        extract = document.get("stage_results", {}).get("EXTRACT", {})
        text = protect.get("protected_text")
        if (document.get("stage_status", {}).get("EXTRACT", {}).get("status") not in {"COMPLETE", "NEEDS_REVIEW"}
                or not isinstance(text, str) or not text.strip()
                or protect.get("report_id") != document_id
                or not isinstance(extract.get("clinical_synthesis"), dict)):
            raise ValueError("Completed protected Radiology EXTRACT is required")
        import hashlib
        if protect.get("integrity_sha256") != hashlib.sha256(text.encode()).hexdigest():
            raise ValueError("Protected input integrity check failed")
        native_facts = extract["clinical_synthesis"].get("canonical_facts") or []
        # Only safe protected/native display state is retained; UNDERSTAND source text is excluded.
        snapshot = {"document_id": document_id, "original_filename": "Radiology report",
                    "review_status": document.get("review_status"), "stage_status": document.get("stage_status"),
                    "stage_results": {"PROTECT": {"protected_document": {"protected_text": text,
                                                       "report_id": document_id},
                        "protection_result": {"review_required": (document.get("stage_results", {}).get("PROTECT", {})
                                           .get("protection_result") or {}).get("review_required", False)}},
                        "EXTRACT": extract, "STANDARDIZE": document.get("stage_results", {}).get("STANDARDIZE", {})}}
        payload = {"run_id": run_id, "document_id": document_id,
                   "created_at": datetime.now(timezone.utc).isoformat(), "display_name": "Radiology report",
                   "status": "PROCESSING", "raw_response": None, "elapsed_seconds": None,
                   "comparison": {"status": "NOT_AVAILABLE"}, "native_document": snapshot}
        with self.lock:
            existing = self.get(run_id, document_id)
            if existing:
                return existing
            self._write(path, payload)
            self._active = self.active | {(run_id, document_id)}
            self.executor.submit(self._run, path, payload, text, native_facts)
        return payload

    def _run(self, path, payload, text, native_facts):
        try:
            response = self.adapter.extract(text)
            if response.get("status") == "AVAILABLE" and isinstance(response.get("raw_response"), str):
                raw = response["raw_response"]
                payload.update(status="AVAILABLE", raw_response=raw)
            else:
                payload.update(status="FAILED", failure_code=response.get("code"),
                               comparison={"status": "NOT_AVAILABLE"})
                if response.get("code") == LIMIT_CODE and isinstance(response.get("raw_response"), str):
                    payload["raw_response"] = response["raw_response"]
            payload["elapsed_seconds"] = response.get("elapsed_seconds")
            payload["input_tokens"] = response.get("input_tokens")
            payload["output_tokens"] = response.get("output_tokens")
            payload["token_limit_reached"] = response.get("token_limit_reached", False)
            payload["repetition_detected"] = response.get("repetition_detected", False)
            payload["natural_stop_before_limit"] = response.get("natural_stop_before_limit")
            payload = revalidate_payload(payload)
        except Exception:
            payload.update(status="FAILED", comparison={"status": "NOT_AVAILABLE"})
        finally:
            with self.lock:
                self._write(path, payload)
                self._active = self.active - {(payload["run_id"], payload["document_id"])}


comparison_service = ComparisonEvaluationService()


def comparison_enabled():
    return enabled() and os.environ.get("MRJ_MEDGEMMA_COMPARISON_MODE", "").strip().lower() in {"1", "true", "yes"}
