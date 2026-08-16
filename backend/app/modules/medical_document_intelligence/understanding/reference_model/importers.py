from __future__ import annotations

import csv, hashlib, io, json, re, zipfile
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import CanonicalConcept, ConceptFamily, ConceptRelationship, ExternalMapping, ReferenceSource, RelationshipType
from .normalization import normalize_reference_term


class ArtifactError(ValueError): pass
class RestrictedSourceNotAvailable(RuntimeError): pass


class ReferenceImporter(ABC):
    """Offline parsers only; acquisition is never part of recognition runtime."""
    @abstractmethod
    def supports(self, source: ReferenceSource) -> bool: ...
    @abstractmethod
    def import_artifact(self, source: ReferenceSource, artifact: Path, **options) -> tuple[CanonicalConcept, ...]: ...


def _stable_id(prefix: str, *parts: str) -> str:
    key = "|".join(normalize_reference_term(x) for x in parts if x)
    return f"{prefix}_{hashlib.sha256(key.encode()).hexdigest()[:16].upper()}"


def _files(path: Path, patterns: tuple[str, ...]):
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if any(re.search(p, name, re.I) for p in patterns):
                    yield name, io.BytesIO(archive.read(name))
        return
    for item in ((path,) if path.is_file() else path.rglob("*")):
        if item.is_file() and any(re.search(p, item.name, re.I) for p in patterns):
            yield str(item), item.open("rb")


def _rows(stream, delimiter=","):
    return csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace", newline=""), delimiter=delimiter)


def _value(row, *names):
    norm = {re.sub(r"[^a-z0-9]", "", str(k).lower()): str(v or "").strip() for k, v in row.items()}
    return next((norm[re.sub(r"[^a-z0-9]", "", n.lower())] for n in names if norm.get(re.sub(r"[^a-z0-9]", "", n.lower()))), "")


_PART_FAMILIES = {
    "MODALITY": ConceptFamily.IMAGING_MODALITY, "MODALITY_SUBTYPE": ConceptFamily.MODALITY_SUBTYPE,
    "REGION_IMAGED": ConceptFamily.BODY_REGION, "IMAGING_FOCUS": ConceptFamily.IMAGING_FOCUS,
    "LATERALITY": ConceptFamily.LATERALITY, "VIEW": ConceptFamily.VIEW, "TIMING": ConceptFamily.TIMING,
    "PHARMACEUTICAL": ConceptFamily.PHARMACEUTICAL, "ROUTE": ConceptFamily.ROUTE,
    "GUIDANCE": ConceptFamily.GUIDANCE, "MANEUVER": ConceptFamily.MANEUVER,
    "REASON_FOR_EXAM": ConceptFamily.REASON_FOR_EXAM,
}


class LoincRsnaImporter(ReferenceImporter):
    def supports(self, source): return source.reference_family == "LOINC_RSNA_PLAYBOOK"

    def import_artifact(self, source, artifact, **options):
        artifact = Path(artifact)
        playbooks = list(_files(artifact, (r"LoincRsnaRadiologyPlaybook\.csv$",)))
        if not playbooks: raise ArtifactError("Official LOINC/RSNA Radiology Playbook CSV was not found in the package.")
        rows = []
        with playbooks[0][1] as stream: rows.extend(_rows(stream))
        by_loinc = defaultdict(list)
        for row in rows:
            code = _value(row, "LoincNumber", "LOINC_NUM", "LOINC")
            if code: by_loinc[code].append(row)
        part_catalog = self._part_catalog(artifact)
        related_mappings = self._part_related_mappings(artifact)
        concepts, parts = [], {}
        for code, records in by_loinc.items():
            long_name = _value(records[0], "LongCommonName", "LONG_COMMON_NAME", "LongName") or code
            proc_id = _stable_id("MNX_LOINC_PROC", code, long_name)
            relations, mappings = [], [ExternalMapping(source.source_id, code, long_name)]
            attrs = [("record_type", "RADIOLOGY_PROCEDURE")]
            for row in records:
                pnum = _value(row, "PartNumber")
                ptype = _value(row, "PartTypeName").upper().replace(" ", "_")
                pname = _value(row, "PartName", "PreferredName")
                order = _value(row, "PartSequenceOrder")
                rid, rpid = _value(row, "RID"), _value(row, "RPID")
                if pnum and pname:
                    part = self._part_concept(source, pnum, ptype, pname, part_catalog, related_mappings, rid, _value(row, "PreferredName"))
                    part_id = part.mednexus_concept_id
                    parts.setdefault(part_id, part)
                    relations.append(ConceptRelationship(RelationshipType.CAN_COMPOSE, part_id, (source.source_id,), ptype, order, pnum))
                    attrs.extend(((f"part.{pnum}.type", ptype), (f"part.{pnum}.sequence", order)))
                if rid: mappings.append(ExternalMapping("RADLEX_CURRENT", rid, _value(row, "PreferredName"), "AUTHORITATIVE_PLAYBOOK"))
                if rpid: mappings.append(ExternalMapping("RADLEX_CURRENT", rpid, _value(row, "LongName"), "AUTHORITATIVE_PLAYBOOK_PROCEDURE"))
            concepts.append(CanonicalConcept(proc_id, long_name, ConceptFamily.IMAGING_PROCEDURE, "RADIOLOGY", (long_name,), (), ("en",),
                                             tuple(dict.fromkeys(mappings)), tuple(relations), (source.source_id,), "ACTIVE", tuple(attrs)))
        documents, document_parts = self._document_concepts(source, artifact, part_catalog, related_mappings)
        parts.update(document_parts)
        concepts.extend(parts.values())
        concepts.extend(documents)
        if not by_loinc: raise ArtifactError("The Playbook contained no recognizable LOINC procedures.")
        return tuple(concepts)

    def _part_catalog(self, artifact):
        catalog = {}
        for _, stream in _files(artifact, (r"/Part\.csv$", r"^Part\.csv$")):
            with stream:
                for row in _rows(stream):
                    number = _value(row, "PartNumber")
                    if number: catalog[number] = row
        return catalog

    def _part_related_mappings(self, artifact):
        result = defaultdict(list)
        for _, stream in _files(artifact, (r"PartRelatedCodeMapping\.csv$",)):
            with stream:
                for row in _rows(stream):
                    number, system = _value(row, "PartNumber"), _value(row, "ExtCodeSystem")
                    external_id = _value(row, "ExtCodeId")
                    if not number or not external_id: continue
                    source_id = "RADLEX_CURRENT" if "radlex.org" in system.lower() else (
                        "SNOMED_INT_20260701" if "snomed.info" in system.lower() else f"LOINC_RELATED:{system}"
                    )
                    result[number].append(ExternalMapping(source_id, external_id, _value(row, "ExtCodeDisplayName"),
                                                          _value(row, "Equivalence") or "LOINC_PART_RELATED_CODE"))
        return result

    def _part_concept(self, source, number, part_type, name, catalog, related_mappings, rid="", rid_name=""):
        official = catalog.get(number, {})
        official_name = _value(official, "PartName") or name or number
        display_name = _value(official, "PartDisplayName")
        official_type = (_value(official, "PartTypeName") or part_type).upper().replace(" ", "_").replace(".", "_")
        synonyms = tuple(x for x in (display_name, name) if x and x != official_name)
        mappings = [ExternalMapping(source.source_id, number, official_name)]
        mappings.extend(related_mappings.get(number, ()))
        if rid: mappings.append(ExternalMapping("RADLEX_CURRENT", rid, rid_name or official_name, "AUTHORITATIVE_PLAYBOOK"))
        part_id = _stable_id("MNX_LOINC_PART", official_type, number, official_name)
        return CanonicalConcept(part_id, official_name, _PART_FAMILIES.get(official_type, ConceptFamily.PROCEDURE_ATTRIBUTE),
            "RADIOLOGY", (official_name,), tuple(dict.fromkeys(synonyms)), ("en",), tuple(dict.fromkeys(mappings)), (),
            (source.source_id,), _value(official, "Status") or "ACTIVE", (("record_type", "LOINC_PART"), ("part_type", official_type)))

    def _document_concepts(self, source, artifact, part_catalog, related_mappings):
        names = {}
        for _, stream in _files(artifact, (r"LoincTable/Loinc\.csv$",)):
            with stream:
                for row in _rows(stream):
                    code = _value(row, "LOINC_NUM", "LoincNumber")
                    term = _value(row, "LONG_COMMON_NAME", "LongCommonName")
                    if code and term: names[code] = term
        documents, parts = {}, {}
        for name, stream in _files(artifact, (r"DocumentOntology/DocumentOntology\.csv$",)):
            grouped = defaultdict(list)
            with stream:
                for row in _rows(stream):
                    if _value(row, "LoincNumber"): grouped[_value(row, "LoincNumber")].append(row)
            for code, rows in grouped.items():
                term = names.get(code, code)
                relations = []
                for row in rows:
                    number = _value(row, "PartNumber")
                    ptype = _value(row, "PartTypeName").upper().replace(" ", "_").replace(".", "_")
                    pname = _value(row, "PartName")
                    if not number: continue
                    part = self._part_concept(source, number, ptype, pname, part_catalog, related_mappings)
                    parts.setdefault(part.mednexus_concept_id, part)
                    relations.append(ConceptRelationship(RelationshipType.CAN_COMPOSE, part.mednexus_concept_id, (source.source_id,),
                        ptype, _value(row, "PartSequenceOrder"), number))
                documents[code] = CanonicalConcept(_stable_id("MNX_LOINC_DOC", code, term), term, ConceptFamily.DOCUMENT_REPORT,
                    "RADIOLOGY", (term,), (), ("en",), (ExternalMapping(source.source_id, code, term),), tuple(relations),
                    (source.source_id,), "ACTIVE", (("record_type", "DOCUMENT_ONTOLOGY"), ("source_artifact", name)))
        for name, stream in _files(artifact, (r"ImagingDocumentCodes\.csv$", r"ImagingDocuments\.csv$")):
            with stream:
                for row in _rows(stream):
                    code = _value(row, "LOINC_NUM", "LoincNumber", "LOINC")
                    term = _value(row, "LONG_COMMON_NAME", "LongCommonName", "DocumentTypeName", "Term")
                    if not code or not term: continue
                    existing = documents.get(code)
                    attrs = (("record_type", "IMAGING_DOCUMENT"), ("source_artifact", name))
                    documents[code] = CanonicalConcept(_stable_id("MNX_LOINC_DOC", code, term), term, ConceptFamily.DOCUMENT_REPORT,
                        "RADIOLOGY", (term,), (), ("en",), (ExternalMapping(source.source_id, code, term),),
                        existing.relationships if existing else (), (source.source_id,), "ACTIVE", attrs)
        return list(documents.values()), parts


_DICOM_RELEVANT = re.compile(r"^(Modality|ModalitiesInStudy|BodyPartExamined|AnatomicRegionSequence|ProtocolName|SeriesDescription|ContrastBolus.*|ScanningSequence|SequenceVariant|ScanOptions|MRAcquisitionType|SliceThickness|RepetitionTime|EchoTime|InversionTime|MagneticFieldStrength|AcquisitionContrast|ImageType|PerformedProcedureStepDescription|RequestedProcedureDescription|StudyDescription)$")


class DicomPart6Importer(ReferenceImporter):
    def supports(self, source): return source.reference_family == "DICOM"
    def import_artifact(self, source, artifact, **options):
        try: root = ET.parse(artifact).getroot()
        except (ET.ParseError, OSError) as exc: raise ArtifactError(f"Malformed or unreadable DICOM XML: {exc}") from exc
        concepts = []
        for row in root.iter():
            if not row.tag.endswith(("row", "tr")): continue
            cells = [" ".join("".join(c.itertext()).split()) for c in row if c.tag.endswith(("entry", "td"))]
            if len(cells) < 5: continue
            tag, name, keyword, vr, vm = cells[:5]; keyword = re.sub(r"[^A-Za-z0-9]", "", keyword)
            if not _DICOM_RELEVANT.match(keyword): continue
            family = ConceptFamily.BODY_REGION if keyword in {"BodyPartExamined", "AnatomicRegionSequence"} else ConceptFamily.ACQUISITION
            concepts.append(CanonicalConcept(_stable_id("MNX_DICOM", keyword), name, family, "RADIOLOGY", (name,), (keyword,), ("en",),
                (ExternalMapping(source.source_id, tag, name),), (), (source.source_id,), "ACTIVE", (("record_type", "PS3.6"), ("keyword", keyword), ("vr", vr), ("vm", vm))))
        if not concepts: raise ArtifactError("No controlled Radiology-relevant attributes were found in DICOM PS3.6 XML.")
        return tuple(concepts)


DCMR_RADIOLOGY_CIDS = frozenset({2,4,12,13,29,33,62,63,100,101,102,108,109,1001,1002,1003,1004,1005,1006,3850,4009,4013,4030,4031,4050,6052,6053,6101,6109,7000,7001,7002,7021,7035,7260,8134,9233,10013,10014,12024,12100,12245,12320})


def _dc_family(title):
    text = title.lower()
    if "report heading" in text or "report element" in text or "report section" in text: return ConceptFamily.REPORT_COMPONENT
    if "report" in text or "document title" in text: return ConceptFamily.DOCUMENT_REPORT
    if "anatom" in text: return ConceptFamily.BODY_REGION
    if "modalit" in text: return ConceptFamily.IMAGING_MODALITY
    if "contrast" in text or "agent" in text: return ConceptFamily.CONTRAST
    if "finding" in text: return ConceptFamily.IMAGING_OBSERVATION
    if "procedure" in text: return ConceptFamily.IMAGING_PROCEDURE
    if "measurement" in text: return ConceptFamily.PROPERTY
    return ConceptFamily.IMAGING_TECHNIQUE


class DicomDcmrImporter(ReferenceImporter):
    def supports(self, source): return source.reference_family == "DICOM_DCMR"
    def import_artifact(self, source, artifact, **options):
        try: root = ET.parse(artifact).getroot()
        except (ET.ParseError, OSError) as exc: raise ArtifactError(f"Malformed DICOM PS3.16 XML: {exc}") from exc
        concepts = []
        member_count = 0
        for section in root.iter():
            xid = next((v for k,v in section.attrib.items() if k.endswith("id")), "")
            match = re.fullmatch(r"sect_CID_(\d+)", xid, re.I)
            if not match or int(match.group(1)) not in DCMR_RADIOLOGY_CIDS: continue
            cid = match.group(1)
            title_node = next((c for c in section if c.tag.endswith("title")), None)
            title = " ".join("".join(title_node.itertext()).split()) if title_node is not None else f"DICOM CID {cid}"
            group_id = _stable_id("MNX_DCMR_CID", cid, title)
            concepts.append(CanonicalConcept(group_id, title, _dc_family(title), "RADIOLOGY", (title,), (), ("en",),
                (ExternalMapping(source.source_id, f"CID:{cid}", title),), (), (source.source_id,), "ACTIVE", (("record_type", "DCMR_CONTEXT_GROUP"), ("cid", cid))))
            for row in section.iter():
                if not row.tag.endswith(("tr", "row")): continue
                cells = [" ".join("".join(c.itertext()).split()) for c in row if c.tag.endswith(("td", "entry"))]
                if len(cells) < 3: continue
                scheme, code, meaning = cells[:3]
                if not code or not meaning or "Coding Scheme" in scheme: continue
                mapping_source = "SNOMED_INT_20260701" if scheme in {"SCT", "SRT"} else "LOINC_RSNA_2_82" if scheme == "LN" else source.source_id
                concept_id = _stable_id("MNX_DCMR", cid, scheme, code, meaning)
                concepts.append(CanonicalConcept(concept_id, meaning, _dc_family(title), "RADIOLOGY", (meaning,), (), ("en",),
                    (ExternalMapping(mapping_source, code, meaning, "DCMR_MEMBER"), ExternalMapping(source.source_id, f"CID:{cid}:{scheme}:{code}", meaning, "DCMR_MEMBERSHIP")),
                    (ConceptRelationship(RelationshipType.MEMBER_OF, group_id, (source.source_id,), "DCMR_CONTEXT_GROUP", None, f"CID:{cid}"),),
                    (source.source_id,), "ACTIVE", (("record_type", "DCMR_CODE"), ("cid", cid), ("coding_scheme", scheme))))
                member_count += 1
        if not member_count: raise ArtifactError("No coded DCMR members were found in selected PS3.16 Context Groups.")
        return tuple(concepts)


def _radlex_family(label, semantic):
    text = f"{label} {semantic}".lower()
    if "anatom" in text: return ConceptFamily.BODY_REGION
    if "report component" in text: return ConceptFamily.REPORT_COMPONENT
    if "report" in text: return ConceptFamily.DOCUMENT_REPORT
    if "observation" in text: return ConceptFamily.IMAGING_OBSERVATION
    if "finding" in text: return ConceptFamily.CLINICAL_FINDING
    if "procedure" in text: return ConceptFamily.IMAGING_PROCEDURE
    if "property" in text: return ConceptFamily.PROPERTY
    if "temporal" in text: return ConceptFamily.TEMPORAL_ENTITY
    if "modality" in text: return ConceptFamily.IMAGING_MODALITY
    return ConceptFamily.DOMAIN_SIGNAL


class RadLexOwlImporter(ReferenceImporter):
    def supports(self, source): return source.reference_family == "RADLEX"
    def import_artifact(self, source, artifact, **options):
        root_path = Path(artifact)
        csv_candidates = list(_files(root_path, (r"Radlex\.csv$",)))
        owl_candidates = list(_files(root_path, (r"PunRadLex.*\.owl$", r"RadLex\.owl$", r"\.rdf$")))
        # When a directory contains an official OWL ZIP, inspect it without extraction.
        if root_path.is_dir() and not owl_candidates:
            zips = list(root_path.glob("*.zip"))
            for item in zips:
                owl_candidates.extend(_files(item, (r"PunRadLex.*\.owl$", r"RadLex\.owl$")))
        if not csv_candidates or not owl_candidates: raise ArtifactError("RadLex import requires the official OWL and Radlex.csv artifacts.")
        records = []
        with csv_candidates[0][1] as stream:
            for row in _rows(stream):
                values = {re.sub(r"[^a-z0-9]", "", str(k).lower()): str(v or "").strip() for k,v in row.items()}
                rid = (values.get("classid") or values.get("radlexid") or "").rsplit("/",1)[-1]
                label = values.get("preferredlabel") or values.get("preferredname") or ""
                if not rid or not label or values.get("obsolete","").lower() in {"true","1","yes"}: continue
                synonyms = tuple(dict.fromkeys(x.strip() for x in re.split(r"\||;", values.get("synonyms","") or values.get("synonym","")) if x.strip() and x.strip()!=label))
                parents = tuple(x.strip().rsplit("/",1)[-1] for x in re.split(r"\||;", values.get("parents","")) if x.strip())
                semantic = values.get("semantictypes","")
                attributes = [("record_type","RADLEX_ONTOLOGY"),("semantic_types",semantic),("definition",values.get("definitions","") or values.get("definition",""))]
                for key,value in row.items():
                    if value and "/RID/" in key and not key.endswith(("RadLexID","Preferred_name","Synonym","Definition")):
                        attributes.append((f"relationship.{key.rsplit('/',1)[-1]}",str(value)))
                records.append((rid,label,semantic,synonyms,parents,tuple(attributes)))
        id_map = {rid:_stable_id("MNX_RADLEX", label, semantic) for rid,label,semantic,_,_,_ in records}
        label_map = {rid: label for rid,label,_,_,_,_ in records}
        parent_map = {rid: parents for rid,_,_,_,parents,_ in records}
        ancestor_cache = {}
        def ancestor_context(rid, trail=frozenset()):
            if rid in ancestor_cache: return ancestor_cache[rid]
            if rid in trail: return ""
            values = []
            for parent in parent_map.get(rid, ()):
                values.append(label_map.get(parent, ""))
                values.append(ancestor_context(parent, trail | {rid}))
            ancestor_cache[rid] = " ".join(values)
            return ancestor_cache[rid]
        concepts = []
        for rid,label,semantic,synonyms,parents,attrs in records:
            relationships = [ConceptRelationship(RelationshipType.IS_A, id_map.get(p,_stable_id("MNX_RADLEX_EXTERNAL",p)), (source.source_id,), "rdfs:subClassOf", None, p) for p in parents]
            concepts.append(CanonicalConcept(id_map[rid],label,_radlex_family(label,f"{semantic} {ancestor_context(rid)}"),"RADIOLOGY",(label,),synonyms,("en",),
                (ExternalMapping(source.source_id,rid,label),),tuple(relationships),(source.source_id,),"ACTIVE",attrs))
        # OWL is the authority gate and structural QA source; every imported RID must occur in it.
        owl_rids = {item.decode() for item in re.findall(rb"RID\d+", owl_candidates[0][1].read())}
        concepts = [c for c in concepts if c.external_mappings[0].external_id in owl_rids]
        if not concepts: raise ArtifactError("No active RadLex classes could be reconciled between OWL and CSV.")
        return tuple(concepts)


class SnomedRf2Importer(ReferenceImporter):
    def supports(self, source): return source.reference_family == "SNOMED_CT"
    def import_artifact(self, source, artifact, **options):
        subset=options.get("subset_ids")
        if not subset: raise ArtifactError("SNOMED import requires an explicit MedNexus subset of concept IDs.")
        wanted={str(x).strip() for x in subset if str(x).strip()}; descriptions={}; synonyms=defaultdict(list)
        for _,stream in _files(Path(artifact),(r"sct2_Description_.*Snapshot.*\.txt$",)):
            with stream:
                for row in _rows(stream,"\t"):
                    cid=row.get("conceptId","")
                    if cid in wanted and row.get("active")=="1":
                        if row.get("typeId")=="900000000000003001": descriptions[cid]=row.get("term","")
                        elif row.get("term"): synonyms[cid].append(row["term"])
        concepts=[CanonicalConcept(_stable_id("MNX_SNOMED",descriptions[cid]),descriptions[cid],ConceptFamily.DOMAIN_SIGNAL,"RADIOLOGY",(descriptions[cid],),tuple(dict.fromkeys(synonyms[cid])),("en",),(ExternalMapping(source.source_id,cid,descriptions[cid]),),(),(source.source_id,),"ACTIVE",(("active","1"),)) for cid in sorted(wanted) if cid in descriptions]
        if not concepts: raise ArtifactError("No active requested SNOMED concepts were found in RF2 Snapshot descriptions.")
        return tuple(concepts)


IMPORTERS=(LoincRsnaImporter(),DicomPart6Importer(),DicomDcmrImporter(),RadLexOwlImporter(),SnomedRf2Importer())
def importer_for(source): return next((x for x in IMPORTERS if x.supports(source)),None) or (_ for _ in ()).throw(ArtifactError(f"No importer for {source.source_id}"))
