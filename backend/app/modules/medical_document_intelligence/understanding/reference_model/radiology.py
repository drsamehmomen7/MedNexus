from __future__ import annotations

from .models import (
    CanonicalConcept as Concept, ConceptFamily as Family, ConceptRelationship as Rel,
    ExternalMapping as Map, RelationshipType as RT,
)
from .registry import build_default_reference_registry


REFS = ("LOINC_RSNA_2_82", "DICOM_2026_CURRENT", "RADLEX_CURRENT", "MNX_RAD_REF_V1")


def _c(concept_id, name, family, terms, synonyms=(), mappings=(), relationships=(), languages=("en",)):
    return Concept(concept_id, name, family, "RADIOLOGY", tuple(terms), tuple(synonyms), languages,
                   tuple(mappings), tuple(relationships), REFS)


def _modality(concept_id, name, code, terms, synonyms=()):
    return _c(concept_id, name, Family.IMAGING_MODALITY, terms, synonyms,
              (Map("DICOM_2026_CURRENT", code, name),),
              (Rel(RT.IS_A, "RAD_MODALITY_ROOT", ("DICOM_2026_CURRENT", "LOINC_RSNA_2_82")),))


RADIOLOGY_CANONICAL_CONCEPTS = (
    _c("RAD_MODALITY_ROOT", "Imaging modality", Family.IMAGING_MODALITY, ("imaging modality",)),
    _modality("RAD_MODALITY_MRI", "Magnetic resonance imaging", "MR", ("MRI", "magnetic resonance imaging"), ("MR imaging", "magnetic resonance")),
    _modality("RAD_MODALITY_CT", "Computed tomography", "CT", ("CT", "computed tomography")),
    _modality("RAD_MODALITY_XRAY", "Radiography", "DX", ("X-ray", "radiograph"), ("x ray", "radiography")),
    _modality("RAD_MODALITY_ULTRASOUND", "Ultrasound", "US", ("ultrasound", "sonography")),
    _c("RAD_MODALITY_DOPPLER", "Doppler ultrasound", Family.IMAGING_MODALITY, ("Doppler", "Doppler ultrasound"),
       ("duplex ultrasound",), (Map("DICOM_2026_CURRENT", "US", "Ultrasound"),),
       (Rel(RT.IS_A, "RAD_MODALITY_ULTRASOUND", ("LOINC_RSNA_2_82",)),)),
    _modality("RAD_MODALITY_MAMMOGRAPHY", "Mammography", "MG", ("mammography", "mammogram")),
    _modality("RAD_MODALITY_NUCLEAR_MEDICINE", "Nuclear medicine", "NM", ("nuclear medicine",), ("scintigraphy",)),
    _c("RAD_ANAT_HEAD", "Head", Family.BODY_REGION, ("head",)),
    _c("RAD_ANAT_BRAIN", "Brain", Family.BODY_REGION, ("brain",)),
    _c("RAD_ANAT_NECK", "Neck", Family.BODY_REGION, ("neck",)),
    _c("RAD_ANAT_CHEST", "Chest", Family.BODY_REGION, ("chest",), ("thorax",)),
    _c("RAD_ANAT_ABDOMEN", "Abdomen", Family.BODY_REGION, ("abdomen",), ("abdominal",)),
    _c("RAD_ANAT_PELVIS", "Pelvis", Family.BODY_REGION, ("pelvis",), ("pelvic",)),
    _c("RAD_ANAT_SPINE", "Spine", Family.BODY_REGION, ("spine",)),
    _c("RAD_ANAT_BREAST", "Breast", Family.BODY_REGION, ("breast",)),
    _c("RAD_ANAT_EXTREMITY", "Extremity", Family.BODY_REGION, ("extremity",), ("limb",)),
    _c("RAD_ANAT_WHOLE_BODY", "Whole body", Family.BODY_REGION, ("whole body",)),
    _c("RAD_TECH_T1", "T1-weighted imaging", Family.IMAGING_TECHNIQUE, ("T1-weighted",), ("T1 weighted", "T1WI", "T1"),
       relationships=(Rel(RT.USED_WITH, "RAD_MODALITY_MRI", ("RADLEX_CURRENT", "MNX_RAD_REF_V1")),)),
    _c("RAD_TECH_T2", "T2-weighted imaging", Family.IMAGING_TECHNIQUE, ("T2-weighted",), ("T2 weighted", "T2WI", "T2"),
       relationships=(Rel(RT.USED_WITH, "RAD_MODALITY_MRI", ("RADLEX_CURRENT", "MNX_RAD_REF_V1")),)),
    _c("RAD_TECH_DWI", "Diffusion-weighted imaging", Family.IMAGING_TECHNIQUE, ("diffusion-weighted", "DWI"), ("diffusion weighted", "ADC"),
       relationships=(Rel(RT.USED_WITH, "RAD_MODALITY_MRI", ("DICOM_2026_CURRENT", "RADLEX_CURRENT")),)),
    _c("RAD_TECH_FAT_SUPPRESSION", "Fat-suppressed imaging", Family.IMAGING_TECHNIQUE, ("fat suppression",), ("fat saturation", "fat-suppressed", "fat suppressed"),
       relationships=(Rel(RT.USED_WITH, "RAD_MODALITY_MRI", ("RADLEX_CURRENT",)),)),
    _c("RAD_ACQ_MULTIPLANAR", "Multiplanar imaging", Family.ACQUISITION, ("multiplanar",), ("axial", "sagittal", "coronal")),
    _c("RAD_ACQ_SCANNER", "Magnetic field strength", Family.ACQUISITION, ("Tesla",), ("1.5T", "3T", "MR scanner"),
       relationships=(Rel(RT.SUPPORTS, "RAD_MODALITY_MRI", ("DICOM_2026_CURRENT",)),)),
    _c("RAD_CONTRAST_WITH", "With contrast", Family.CONTRAST, ("with contrast",), ("post-contrast", "contrast-enhanced", "after contrast")),
    _c("RAD_CONTRAST_WITHOUT", "Without contrast", Family.CONTRAST, ("without contrast",), ("non-contrast", "pre-contrast")),
    _c("RAD_CONTRAST_PRE_POST", "Pre/post contrast", Family.CONTRAST, ("pre/post contrast",), ("pre- and post-contrast", "before and after contrast", "without and with contrast")),
    _c("RAD_PURPOSE_STAGING", "Oncologic staging", Family.CLINICAL_PURPOSE, ("oncologic staging", "cancer staging"), ("tumor staging", "tumour staging", "staging")),
    _c("RAD_DOC_REPORT", "Radiology report", Family.DOCUMENT_REPORT, ("radiology report", "imaging report")),
)

RADIOLOGY_REFERENCE_MODEL = build_default_reference_registry(RADIOLOGY_CANONICAL_CONCEPTS)
