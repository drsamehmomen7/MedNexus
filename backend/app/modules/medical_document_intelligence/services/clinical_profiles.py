"""Versioned, evidence-bound exam coverage profiles owned by MRJ.

Profiles describe expected structure. They neither generate canonical facts nor
change the authority of UNDERSTAND, EXTRACT, or STANDARDIZE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ClinicalCoverageStatus(str, Enum):
    DOCUMENTED = "DOCUMENTED"
    NOT_DOCUMENTED = "NOT_DOCUMENTED"
    LIMITED_OR_NOT_VISUALIZED = "LIMITED_OR_NOT_VISUALIZED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ClinicalAssertion(str, Enum):
    PRESENT = "PRESENT"
    EXPLICITLY_ABSENT_OR_NORMAL = "EXPLICITLY_ABSENT_OR_NORMAL"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class ClinicalProfileReference:
    organization: str
    title: str
    url: str
    version_or_date: str | None
    derivation_note: str
    rights_note: str = "Metadata only; no guideline text reproduced."

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ClinicalProfileElement:
    element_id: str
    label: str
    category: str
    terms: tuple[str, ...]
    optional: bool = True
    measurement_types: tuple[str, ...] = ()
    laterality: str = "NONE"
    evidence_requirement: str = "EXPLICIT_PROTECTED_FINDING_OR_GROUNDED_FACT"


@dataclass(frozen=True, slots=True)
class ClinicalProfileSection:
    section_id: str
    label: str
    category: str
    terms: tuple[str, ...]
    elements: tuple[ClinicalProfileElement, ...]
    applicable_scopes: tuple[str, ...]
    laterality: str = "NONE"


@dataclass(frozen=True, slots=True)
class ClinicalProfileActivationRule:
    domain: str
    modality: str
    body_region: str
    incompatible_families: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClinicalExtractionProfile:
    profile_id: str
    profile_version: str
    name: str
    exam_type: str
    lifecycle_status: str
    activation: ClinicalProfileActivationRule
    supported_scopes: tuple[str, ...]
    sections: tuple[ClinicalProfileSection, ...]
    references: tuple[ClinicalProfileReference, ...]
    radiology_core: tuple[str, ...] = (
        "clinical_indication", "comparison", "exam_identity", "clinical_summary",
        "key_findings", "measurements", "pertinent_negatives",
        "diagnostic_considerations", "recommendations", "technical_limitations",
        "evidence_provenance",
    )


def _element(section_id: str, label: str, *terms: str,
             measurements: tuple[str, ...] = (), laterality: str = "NONE") -> ClinicalProfileElement:
    return ClinicalProfileElement(f"{section_id}.{label.lower().replace(' ', '_')}", label,
                                  section_id, terms, measurement_types=measurements,
                                  laterality=laterality)


def _section(section_id: str, label: str, terms: tuple[str, ...],
             elements: tuple[ClinicalProfileElement, ...], scopes: tuple[str, ...],
             laterality: str = "NONE") -> ClinicalProfileSection:
    return ClinicalProfileSection(section_id, label, "ANATOMIC_STRUCTURE", terms,
                                  elements, scopes, laterality)


_AIUM = ClinicalProfileReference(
    "AIUM", "Abdomen or Retroperitoneum",
    "https://www.aium.org/resources/practice-parameters/abdomen-or-retroperitoneum",
    None, "Official topic page lists 2026, but also displays a 2021 date; bibliographic date pending verification.")
_ACR = ClinicalProfileReference(
    "ACR/SPR/SSR", "ACR–SPR–SSR Practice Parameter for the Performance and Interpretation of Magnetic Resonance Imaging (MRI) of the Shoulder",
    "https://gravitas.acr.org/PPTS/GetDocumentView?docId=45", None,
    "Official practice-parameter portal; current release date pending verification.")
_RSNA = ClinicalProfileReference(
    "RSNA", "RadLex radiology lexicon and LOINC/RSNA Radiology Playbook",
    "https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon",
    None, "Procedure identity provenance only; no licensed terminology content is copied.",
    "Consult RSNA/LOINC terms before any future terminology import.")

_COMPLETE = ("COMPLETE",)
_ABDOMEN = ("COMPLETE", "LIMITED_OR_FOCUSED", "UNKNOWN")
_RENAL = ("COMPLETE", "LIMITED_OR_FOCUSED", "RETROPERITONEAL_OR_URINARY", "UNKNOWN")
_ALL_US = ("COMPLETE", "LIMITED_OR_FOCUSED", "RETROPERITONEAL_OR_URINARY", "UNKNOWN")
_ALL_MRI = ("ROUTINE_MRI", "MR_ARTHROGRAM", "UNKNOWN")


US_ABDOMEN = ClinicalExtractionProfile(
    "MRJ_RAD_US_ABDOMEN", "0.1", "Ultrasound Abdomen", "ABDOMEN", "REFERENCE_V0_1",
    ClinicalProfileActivationRule("RADIOLOGY", "ULTRASOUND", "ABDOMEN", ("DOPPLER",)),
    _ALL_US,
    (
        _section("liver", "Liver", ("liver", "hepatic"), (
            _element("liver", "Size", "hepatomegaly", "liver measures", measurements=("ORGAN_LENGTH",)),
            _element("liver", "Parenchyma", "echogenicity", "echotexture", "steatosis", "cirrhosis"),
            _element("liver", "Focal lesion", "hepatic lesion", "liver lesion", measurements=("LESION_DIMENSIONS",)),
            _element("liver", "Contour", "hepatic contour", "liver contour"),
            _element("liver", "Vessels", "portal vein", "hepatic vein")), _ABDOMEN),
        _section("gallbladder", "Gallbladder", ("gallbladder", "cholecyst"), (
            _element("gallbladder", "Stones", "gallstone", "cholelithiasis", "calculus", measurements=("STONE_SIZE",)),
            _element("gallbladder", "Wall", "gallbladder wall", measurements=("WALL_THICKNESS",)),
            _element("gallbladder", "Polyp", "gallbladder polyp", measurements=("LESION_DIMENSIONS",)),
            _element("gallbladder", "Murphy sign", "murphy sign")), _ABDOMEN),
        _section("biliary_tree", "Biliary tree", ("biliary", "bile duct", "common duct", "cbd", "chd"), (
            _element("biliary_tree", "Dilation", "ductal dilatation", "ductal dilation"),
            _element("biliary_tree", "Duct diameter", "cbd", "chd", "common bile duct", measurements=("DUCT_DIAMETER",))), _ABDOMEN),
        _section("pancreas", "Pancreas", ("pancreas", "pancreatic"), (
            _element("pancreas", "Visualization", "pancreas", "pancreatic"),
            _element("pancreas", "Focal lesion", "pancreatic lesion", measurements=("LESION_DIMENSIONS",)),
            _element("pancreas", "Duct", "pancreatic duct"),
            _element("pancreas", "Calcification", "pancreatic calcification")), _ABDOMEN),
        _section("spleen", "Spleen", ("spleen", "splenic"), (
            _element("spleen", "Size", "splenomegaly", "spleen measures", measurements=("ORGAN_LENGTH",)),
            _element("spleen", "Parenchyma", "splenic lesion", "spleen lesion")), _ABDOMEN),
        _section("right_kidney", "Right kidney", ("right kidney", "right renal"), (
            _element("right_kidney", "Length", "right kidney measures", measurements=("ORGAN_LENGTH",), laterality="RIGHT"),
            _element("right_kidney", "Cortex", "right renal cortex", "right renal echogenicity", laterality="RIGHT"),
            _element("right_kidney", "Collecting system", "right hydronephrosis", "right collecting system", laterality="RIGHT"),
            _element("right_kidney", "Calculus", "right renal calculus", "right kidney stone", measurements=("STONE_SIZE",), laterality="RIGHT"),
            _element("right_kidney", "Cyst or mass", "right renal cyst", "right renal mass", laterality="RIGHT")), _RENAL, "RIGHT"),
        _section("left_kidney", "Left kidney", ("left kidney", "left renal"), (
            _element("left_kidney", "Length", "left kidney measures", measurements=("ORGAN_LENGTH",), laterality="LEFT"),
            _element("left_kidney", "Cortex", "left renal cortex", "left renal echogenicity", laterality="LEFT"),
            _element("left_kidney", "Collecting system", "left hydronephrosis", "left collecting system", laterality="LEFT"),
            _element("left_kidney", "Calculus", "left renal calculus", "left kidney stone", measurements=("STONE_SIZE",), laterality="LEFT"),
            _element("left_kidney", "Cyst or mass", "left renal cyst", "left renal mass", laterality="LEFT")), _RENAL, "LEFT"),
        _section("peritoneal_fluid", "Peritoneal fluid", ("ascites", "free fluid", "peritoneal fluid"), (
            _element("peritoneal_fluid", "Fluid", "ascites", "free fluid", measurements=("FLUID_OR_OTHER_LENGTH",)),), _ABDOMEN),
        _section("aorta", "Aorta", ("aorta", "aortic"), (
            _element("aorta", "Caliber", "aortic caliber", "aortic aneurysm", measurements=("DUCT_DIAMETER",)),), _COMPLETE),
        _section("ivc", "IVC", ("ivc", "inferior vena cava"), (
            _element("ivc", "Visualization", "ivc", "inferior vena cava"),), _COMPLETE),
        _section("bladder", "Bladder", ("bladder", "urinary bladder"), (
            _element("bladder", "Wall or lumen", "bladder wall", "bladder lumen", measurements=("WALL_THICKNESS",)),),
            ("RETROPERITONEAL_OR_URINARY",)),
    ), (_AIUM, _RSNA))

MRI_SHOULDER = ClinicalExtractionProfile(
    "MRJ_RAD_MRI_SHOULDER", "0.1", "MRI Shoulder", "SHOULDER", "REFERENCE_V0_1",
    ClinicalProfileActivationRule("RADIOLOGY", "MRI", "SHOULDER", ("MRA", "MRV")),
    _ALL_MRI,
    (
        _section("rotator_cuff", "Rotator cuff", ("rotator cuff", "supraspinatus", "infraspinatus", "subscapularis", "teres minor"), (
            _element("rotator_cuff", "Supraspinatus", "supraspinatus"),
            _element("rotator_cuff", "Infraspinatus", "infraspinatus"),
            _element("rotator_cuff", "Subscapularis", "subscapularis"),
            _element("rotator_cuff", "Teres minor", "teres minor"),
            _element("rotator_cuff", "Tear dimensions", "tear measures", "tear dimension", measurements=("TEAR_DIMENSIONS",)),
            _element("rotator_cuff", "Retraction", "retraction", measurements=("RETRACTION_DISTANCE",))), _ALL_MRI),
        _section("musculature", "Musculature", ("muscle", "musculature", "atrophy", "fatty infiltration"), (
            _element("musculature", "Atrophy", "atrophy"),
            _element("musculature", "Fatty change", "fatty infiltration", "fatty degeneration")), _ALL_MRI),
        _section("biceps", "Long-head biceps", ("biceps", "bicipital"), (
            _element("biceps", "Position", "biceps position", "biceps subluxation", "biceps dislocation"),
            _element("biceps", "Tendon", "biceps tendon", "biceps tendinopathy", "biceps tear"),
            _element("biceps", "Pulley", "biceps pulley")), _ALL_MRI),
        _section("labrum", "Labrum", ("labrum", "labral"), (
            _element("labrum", "Tear", "labral tear", "labrum tear"),
            _element("labrum", "Location", "superior labrum", "anterior labrum", "posterior labrum")), _ALL_MRI),
        _section("glenohumeral_joint", "Glenohumeral joint", ("glenohumeral", "articular cartilage", "joint effusion"), (
            _element("glenohumeral_joint", "Cartilage", "articular cartilage"),
            _element("glenohumeral_joint", "Effusion", "joint effusion"),
            _element("glenohumeral_joint", "Synovium", "synovitis", "synovium")), _ALL_MRI),
        _section("ac_joint", "AC joint / outlet", ("ac joint", "acromioclavicular", "subacromial outlet", "acromion"), (
            _element("ac_joint", "Degeneration", "ac joint arthrosis", "acromioclavicular degeneration"),
            _element("ac_joint", "Outlet", "subacromial outlet", "acromion")), _ALL_MRI),
        _section("bursae", "Bursae", ("bursa", "bursitis", "subacromial-subdeltoid"), (
            _element("bursae", "Subacromial-subdeltoid", "subacromial-subdeltoid", "bursitis"),), _ALL_MRI),
        _section("bone_marrow", "Bone / marrow", ("marrow", "humerus", "humeral", "glenoid", "hill-sachs", "bankart", "fracture"), (
            _element("bone_marrow", "Fracture", "fracture"),
            _element("bone_marrow", "Marrow edema", "marrow edema"),
            _element("bone_marrow", "Osseous lesion", "osseous lesion", measurements=("LESION_DIMENSIONS",)),
            _element("bone_marrow", "Hill-Sachs", "hill-sachs", measurements=("HILL_SACHS_DIMENSIONS",)),
            _element("bone_marrow", "Glenoid injury", "bony bankart", "glenoid bone loss")), _ALL_MRI),
        _section("capsule_ligaments", "Capsule / ligaments", ("capsule", "capsular", "ligament", "ligamentous"), (
            _element("capsule_ligaments", "Capsular injury", "capsular injury", "capsule tear"),
            _element("capsule_ligaments", "Ligament injury", "ligament tear", "ligament injury")), _ALL_MRI),
    ), (_ACR, _RSNA))


class ClinicalProfileRegistry:
    def __init__(self, profiles: tuple[ClinicalExtractionProfile, ...] = (US_ABDOMEN, MRI_SHOULDER),
                 active_versions: dict[str, str] | None = None):
        self._profiles = {(p.profile_id, p.profile_version): p for p in profiles}
        self._active_versions = dict(active_versions if active_versions is not None else {
            US_ABDOMEN.profile_id: US_ABDOMEN.profile_version,
            MRI_SHOULDER.profile_id: MRI_SHOULDER.profile_version,
        })

    def get(self, profile_id: str, version: str) -> ClinicalExtractionProfile | None:
        return self._profiles.get((profile_id, version))

    def resolve(self, context: Any, protected_text: str = "") -> tuple[ClinicalExtractionProfile, str] | None:
        identity = getattr(context, "identity", None)
        clinical = getattr(context, "clinical_context", None)
        domain = getattr(clinical, "domain_extension", None)
        if getattr(identity, "healthcare_domain", None) != "RADIOLOGY" or domain is None:
            return None
        modality = getattr(domain, "modality", None)
        if getattr(identity, "subdomain_or_family", modality) != modality:
            return None
        region = getattr(domain, "authoritative_anatomy", None) or getattr(domain, "body_region", None)
        if not isinstance(region, str):
            return None
        region = region.upper().replace(" ", "_")
        family = getattr(getattr(domain, "modality_context", None), "study_family", None)
        family = getattr(family, "value", family)
        region_scope = {"KIDNEY": "RETROPERITONEAL_OR_URINARY", "KIDNEYS": "RETROPERITONEAL_OR_URINARY",
                        "RENAL": "RETROPERITONEAL_OR_URINARY", "RETROPERITONEUM": "RETROPERITONEAL_OR_URINARY",
                        "URINARY_SYSTEM": "RETROPERITONEAL_OR_URINARY"}.get(region)
        matches = [p for p in self._profiles.values()
                   if self._active_versions.get(p.profile_id) == p.profile_version
                   and p.activation.domain == identity.healthcare_domain
                   and p.activation.modality == modality and (p.activation.body_region == region
                       or (p.profile_id == US_ABDOMEN.profile_id and region_scope is not None))
                   and family not in p.activation.incompatible_families]
        if len(matches) != 1:
            return None
        profile = matches[0]
        if profile is US_ABDOMEN or profile.profile_id == US_ABDOMEN.profile_id:
            extent = getattr(getattr(domain, "modality_context", None), "study_extent", None)
            extent = getattr(extent, "value", extent)
            scope = region_scope or {"LIMITED": "LIMITED_OR_FOCUSED", "COMPLETE": "COMPLETE"}.get(extent, "UNKNOWN")
            # A protected exam title is stronger scope evidence than an
            # UNKNOWN generic abdomen extent. Do not infer completeness from
            # modality/body region or from an incidental findings mention.
            if region_scope is None and re.search(
                    r"(?im)^\s*(?:[A-Z/ -]+\s+)?(?:RIGHT|LEFT)\s+UPPER\s+QUADRANT\b",
                    protected_text[:700]):
                scope = "LIMITED_OR_FOCUSED"
        else:
            # UNDERSTAND's MRI family does not distinguish arthrography.
            scope = "UNKNOWN"
        return profile, scope


REGISTRY = ClinicalProfileRegistry()

_LIMITATION = re.compile(r"\b(?:not\s+(?:well\s+)?visuali[sz]ed|poorly\s+visuali[sz]ed|obscured|limited\s+(?:evaluation|visualization|view)|cannot\s+(?:be\s+)?(?:seen|evaluated))\b", re.I)
_NORMAL = re.compile(r"\b(?:normal|unremarkable|within\s+normal\s+limits)\b", re.I)


def _has_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I) for term in terms)


def _eligible_sentences(sections: list[dict[str, Any]], profile: ClinicalExtractionProfile) -> list[str]:
    terms = sorted({term for section in profile.sections for term in section.terms}, key=len, reverse=True)
    boundary = re.compile(r"\band\s+(?=(?:the\s+)?(?:" + "|".join(re.escape(term) for term in terms) + r")\b)", re.I)
    return [clause.strip() for section in sections
            if section.get("role") in {"FINDINGS_DESCRIPTION", "DIAGNOSTIC_SUMMARY"}
            for sentence in re.split(r"[\n\r;]+|(?<=[.!?])\s+", str(section.get("text") or ""))
            for clause in boundary.split(sentence) if clause.strip()]


def _fact_evidence(fact: dict[str, Any], protected_text: str) -> bool:
    return any(isinstance(a, dict) and isinstance(a.get("start_offset"), int)
               and isinstance(a.get("end_offset"), int) and isinstance(a.get("quote"), str)
               and 0 <= a["start_offset"] < a["end_offset"] <= len(protected_text)
               and protected_text[a["start_offset"]:a["end_offset"]] == a["quote"]
               and a.get("source_section", a.get("section_role")) in {"FINDINGS_DESCRIPTION", "DIAGNOSTIC_SUMMARY"}
               for a in fact.get("evidence_anchors", []))


_LENGTH_MEASUREMENT = re.compile(
    r"^\s*\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?){0,2}\s*(?:mm|cm|m)\s*$", re.I)


def _profile_measurement_type(quote: str, anatomy: list[str]) -> str | None:
    """Classify only an already linked measurement's source context for coverage."""
    if re.search(r"\bhill[- ]sachs\b", quote, re.I):
        return "HILL_SACHS_DIMENSIONS"
    if re.search(r"\bretract\w*\b", quote, re.I):
        return "RETRACTION_DISTANCE"
    if re.search(r"\bwall\b", quote, re.I) and re.search(r"\b(?:thick\w*|measur\w*)\b", quote, re.I):
        return "WALL_THICKNESS"
    if re.search(r"\b(?:tear|rupture)\b", quote, re.I):
        return "TEAR_DIMENSIONS"
    if re.search(r"\b(?:stone|calculus|calculi)\b", quote, re.I):
        return "STONE_SIZE"
    if re.search(r"\b(?:lesion|mass|nodule|cyst|polyp)\b", quote, re.I):
        return "LESION_DIMENSIONS"
    if re.search(r"\b(?:duct|cbd|chd|diameter|caliber)\b", quote, re.I):
        return "DUCT_DIAMETER"
    if re.search(r"\b(?:fluid|effusion|ascites)\b", quote, re.I):
        return "FLUID_OR_OTHER_LENGTH"
    # A directly measured structure supports its profile length/size element.
    # An intervening lesion or other noun would not match this subject pattern.
    if any(re.search(r"^\s*" + re.escape(site) + r"\s*:?\s+measur\w*\b", quote, re.I)
           for site in anatomy):
        return "ORGAN_LENGTH"
    return None


def _linked_profile_measurements(protected_text: str, facts: list[dict[str, Any]],
                                 governed: list[dict[str, Any]],
                                 standardized: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, str, list[str]]]:
    """Admit only source-exact, fact-linked measurements present after STANDARDIZE."""
    facts_by_id = {fact.get("fact_id"): fact for fact in facts if isinstance(fact, dict)}
    standardized_by_id = {item.get("source_fact_id"): item for item in standardized
                          if isinstance(item, dict)}
    linked = []
    for item in governed:
        if not isinstance(item, dict) or item.get("assignment_state") != "LINKED_TO_FACT":
            continue
        fact_id, value, span = item.get("source_fact_id"), item.get("source_text"), item.get("evidence_span")
        fact, enrichment = facts_by_id.get(fact_id), standardized_by_id.get(fact_id)
        if (not isinstance(fact, dict) or not isinstance(enrichment, dict)
                or not isinstance(value, str) or not _LENGTH_MEASUREMENT.fullmatch(value)
                or not isinstance(span, dict) or not isinstance(span.get("start_offset"), int)
                or not isinstance(span.get("end_offset"), int)):
            continue
        start, end = span["start_offset"], span["end_offset"]
        if (not 0 <= start < end <= len(protected_text)
                or protected_text[start:end] != value or span.get("quote") != value
                or not _fact_evidence(fact, protected_text)
                or not any(value in observation.get("measurements", [])
                           for observation in fact.get("observations", []) if isinstance(observation, dict))
                or not any(measurement.get("original_text") == value
                           for measurement in enrichment.get("standardized_measurements", [])
                           if isinstance(measurement, dict))):
            continue
        anchors = [anchor for anchor in fact.get("evidence_anchors", [])
                   if isinstance(anchor, dict) and isinstance(anchor.get("start_offset"), int)
                   and isinstance(anchor.get("end_offset"), int)
                   and anchor["start_offset"] <= start < end <= anchor["end_offset"]
                   and protected_text[anchor["start_offset"]:anchor["end_offset"]] == anchor.get("quote")]
        if not anchors:
            continue
        quote = anchors[0]["quote"]
        anatomy = [site for site in fact.get("anatomy") or []
                   if isinstance(site, str) and _has_term(quote, (site,))]
        if not anatomy:
            continue
        measurement_type = _profile_measurement_type(quote, anatomy)
        if measurement_type:
            linked.append((fact, quote, measurement_type, anatomy))
    return linked


def _measurement_documents_element(section: ClinicalProfileSection, element: ClinicalProfileElement,
                                   linked: list[tuple[dict[str, Any], str, str, list[str]]]) -> bool:
    if not element.measurement_types:
        return False
    for fact, quote, measurement_type, anatomy in linked:
        if measurement_type not in element.measurement_types or not _has_term(" ".join(anatomy), section.terms):
            continue
        side = element.laterality if element.laterality != "NONE" else section.laterality
        if side in {"LEFT", "RIGHT"} and (fact.get("laterality") not in {None, side}
                                          or not _has_term(quote, (side.lower(),))):
            continue
        if measurement_type == "ORGAN_LENGTH":
            return True
        if (_has_term(quote, element.terms)
                or any(_has_term(quote, (word,)) for word in re.findall(r"[a-z]+", element.label.lower())
                       if word not in {"size", "length", "dimensions", "distance", "diameter", "focal"})):
            return True
    return False


def _coverage(terms: tuple[str, ...], sentences: list[str], facts: list[dict[str, Any]],
              protected_text: str, laterality: str = "NONE") -> tuple[ClinicalCoverageStatus, ClinicalAssertion]:
    matches = [s for s in sentences if _has_term(s, terms)]
    if laterality in {"LEFT", "RIGHT"}:
        # Side-specific terms only; a generic kidney sentence does not cover both.
        matches = [s for s in matches if _has_term(s, (laterality.lower(),))]
    if any(_LIMITATION.search(s) for s in matches):
        return ClinicalCoverageStatus.LIMITED_OR_NOT_VISUALIZED, ClinicalAssertion.INDETERMINATE
    grounded = [f for f in facts if _fact_evidence(f, protected_text) and
                (_has_term(" ".join(f.get("anatomy") or []), terms)
                 or any(_has_term(str(a.get("quote") or ""), terms) for a in f.get("evidence_anchors", [])))
                and (laterality == "NONE" or f.get("laterality") == laterality
                     or any(_has_term(str(a.get("quote") or ""), (laterality.lower(),)) for a in f.get("evidence_anchors", [])))]
    if not matches and not grounded:
        return ClinicalCoverageStatus.NOT_DOCUMENTED, ClinicalAssertion.INDETERMINATE
    assertions = {f.get("assertion_state") for f in grounded}
    if "PRESENT" in assertions:
        assertion = ClinicalAssertion.PRESENT
    elif "ABSENT_NEGATED" in assertions or any(_NORMAL.search(s) for s in matches):
        assertion = ClinicalAssertion.EXPLICITLY_ABSENT_OR_NORMAL
    else:
        assertion = ClinicalAssertion.INDETERMINATE
    return ClinicalCoverageStatus.DOCUMENTED, assertion


def _compatibility(profile: ClinicalExtractionProfile, facts: list[dict[str, Any]],
                   protected_text: str, registry: ClinicalProfileRegistry) -> str:
    """Signal only dominant, source-grounded anatomy outside the exam region."""
    owned = 0
    foreign: dict[str, set[str]] = {}
    foreign_sections: dict[str, set[str]] = {}
    foreign_clauses: dict[str, set[int]] = {}
    # Gross body-region families supplement the small active profile registry.
    # This is an exam safety ontology, never an extraction or relabeling rule.
    gross_regions = {"CRANIAL": ("brain", "cerebral", "cerebellum", "cerebellar", "intracranial", "cranial"),
                     "THORACIC": ("lung", "pulmonary", "pleura", "mediastinum"),
                     "ABDOMINAL": ("liver", "hepatic", "kidney", "renal", "spleen", "pancreas"),
                     "PELVIC": ("uterus", "ovary", "prostate", "bladder")}
    body_region = profile.activation.body_region.upper()
    exam_region = "ABDOMINAL" if body_region.startswith("ABDOM") else body_region
    for fact in facts:
        if not _fact_evidence(fact, protected_text):
            continue
        anatomy = " ".join(fact.get("anatomy") or [])
        if not anatomy:
            continue
        anchors = [a for a in fact.get("evidence_anchors", [])
                   if isinstance(a, dict) and a.get("source_section", a.get("section_role")) in
                   {"FINDINGS_DESCRIPTION", "DIAGNOSTIC_SUMMARY"}]
        # A terminology label alone is not anatomical evidence. The anatomy
        # itself must appear in the protected source support for this fact.
        source_anatomy = [part for part in fact.get("anatomy") or []
                          if any(_has_term(str(a.get("quote") or ""), (part,)) for a in anchors)]
        if not source_anatomy:
            continue
        anatomy = " ".join(source_anatomy)
        owners = {p.profile_id for p in registry._profiles.values()
                  if registry._active_versions.get(p.profile_id) == p.profile_version
                  if any(_has_term(anatomy, section.terms) for section in p.sections)}
        if profile.profile_id in owners:
            owned += 1
        elif len(owners) == 1:
            owner = next(iter(owners))
            foreign.setdefault(owner, set()).add(str(fact.get("fact_id")))
            other = registry.get(owner, registry._active_versions[owner])
            foreign_sections.setdefault(owner, set()).update(
                section.section_id for section in other.sections
                if _has_term(anatomy, section.terms))
            foreign_clauses.setdefault(owner, set()).update(a["start_offset"] for a in anchors
                if isinstance(a.get("start_offset"), int))
        else:
            region = next((name for name, terms in gross_regions.items()
                           if name != exam_region and _has_term(anatomy, terms)), None)
            if region:
                foreign.setdefault(region, set()).add(str(fact.get("fact_id")))
                foreign_clauses.setdefault(region, set()).update(a["start_offset"] for a in anchors
                    if isinstance(a.get("start_offset"), int))
    dominant_owner = max(foreign, key=lambda owner: len(foreign[owner]), default=None)
    dominant = len(foreign[dominant_owner]) if dominant_owner else 0
    if (dominant >= 3 and len(foreign_clauses.get(dominant_owner, ())) >= 2
            and (dominant_owner not in foreign_sections or len(foreign_sections[dominant_owner]) >= 2)
            and dominant >= 3 * max(owned, 1)):
        return "POSSIBLE_ANATOMY_MISMATCH"
    if owned >= 2:
        return "COMPATIBLE"
    return "INSUFFICIENT_INFORMATION"


def evaluate_profile(context: Any, protected_text: str, sections: list[dict[str, Any]],
                     facts: list[dict[str, Any]], registry: ClinicalProfileRegistry = REGISTRY, *,
                     governed_measurements: list[dict[str, Any]] = (),
                     standardized_facts: list[dict[str, Any]] = ()) -> dict[str, Any] | None:
    resolved = registry.resolve(context, protected_text)
    if resolved is None:
        return None
    profile, scope = resolved
    sentences = _eligible_sentences(sections, profile)
    linked_measurements = _linked_profile_measurements(
        protected_text, facts, governed_measurements, standardized_facts)
    upper_quadrant = re.search(r"(?im)^\s*(?:[A-Z/ -]+\s+)?(RIGHT|LEFT)\s+UPPER\s+QUADRANT\b",
                               protected_text[:700])
    focused_side = upper_quadrant.group(1).upper() if scope == "LIMITED_OR_FOCUSED" and upper_quadrant else None
    coverage = []
    for section in profile.sections:
        applicable = scope in section.applicable_scopes
        if focused_side == "RIGHT" and section.section_id in {"spleen", "left_kidney"}:
            applicable = False
        elif focused_side == "LEFT" and section.section_id in {"gallbladder", "biliary_tree", "right_kidney"}:
            applicable = False
        status, assertion = _coverage(section.terms, sentences, facts, protected_text, section.laterality)
        # A silent structure in an unknown or focused exam is still silently
        # undocumented; it is never a negative or a review alert. Only an
        # explicitly known scope can establish NOT_APPLICABLE.
        if not applicable:
            status, assertion = ClinicalCoverageStatus.NOT_APPLICABLE, ClinicalAssertion.INDETERMINATE
        elements = []
        for element in section.elements:
            element_status, element_assertion = _coverage(element.terms, sentences, facts, protected_text,
                                                          element.laterality)
            if not applicable:
                element_status, element_assertion = ClinicalCoverageStatus.NOT_APPLICABLE, ClinicalAssertion.INDETERMINATE
            elif (element_status is ClinicalCoverageStatus.NOT_DOCUMENTED
                  and _measurement_documents_element(section, element, linked_measurements)):
                element_status, element_assertion = ClinicalCoverageStatus.DOCUMENTED, ClinicalAssertion.INDETERMINATE
            elif status is ClinicalCoverageStatus.LIMITED_OR_NOT_VISUALIZED and element_status is ClinicalCoverageStatus.NOT_DOCUMENTED:
                element_status = ClinicalCoverageStatus.LIMITED_OR_NOT_VISUALIZED
            elements.append({"element_id": element.element_id, "label": element.label,
                             "coverage": element_status.value, "assertion": element_assertion.value})
        coverage.append({"section_id": section.section_id, "label": section.label,
                         "coverage": status.value, "assertion": assertion.value,
                         "elements": elements})
    mismatch = _compatibility(profile, facts, protected_text, registry)
    return {"profile_id": profile.profile_id, "profile_version": profile.profile_version,
            "profile_name": profile.name, "scope": scope, "status": "EVALUATED",
            "activation": "EXACT_IDENTITY", "compatibility": mismatch,
            "coverage": coverage,
            "review_alerts": ([{"code": "PROFILE_ANATOMY_MISMATCH",
                                "message": "Extracted anatomy may not match the exam."}]
                              if mismatch == "POSSIBLE_ANATOMY_MISMATCH" else []),
            "references": [r.to_dict() for r in profile.references]}
