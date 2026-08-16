from ...models import DocumentDomain
from ..models import RecognitionConcept, RecognitionConceptCategory as Category
from ..references import ReferenceFamily as Ref


_REFS = (Ref.DICOM.value, Ref.RADLEX.value, Ref.RADLEX_PLAYBOOK.value, Ref.SNOMED_CT.value)


def _concept(concept_id, name, family, canonical, aliases=(), strength=1.0):
    return RecognitionConcept(
        concept_id, name, family, DocumentDomain.RADIOLOGY,
        canonical_en=canonical, aliases_en=aliases, evidence_strength=strength,
        external_references=_REFS,
    )


RADIOLOGY_CONTEXT_DETAIL_CONCEPTS = (
    _concept("RAD_TECH_T1", "T1-weighted imaging", Category.IMAGING_TECHNIQUE, "T1-weighted", ("T1 weighted", "T1WI", "T1")),
    _concept("RAD_TECH_T2", "T2-weighted imaging", Category.IMAGING_TECHNIQUE, "T2-weighted", ("T2 weighted", "T2WI", "T2")),
    _concept("RAD_TECH_FLAIR", "FLAIR imaging", Category.IMAGING_TECHNIQUE, "FLAIR"),
    _concept("RAD_TECH_STIR", "STIR imaging", Category.IMAGING_TECHNIQUE, "STIR"),
    _concept("RAD_TECH_DWI", "Diffusion-weighted imaging", Category.IMAGING_TECHNIQUE, "diffusion-weighted", ("diffusion weighted", "DWI", "ADC"), 1.3),
    _concept("RAD_TECH_FAT_SUPPRESSION", "Fat-suppressed imaging", Category.IMAGING_TECHNIQUE, "fat saturation", ("fat-suppressed", "fat suppressed", "fat suppression")),
    _concept("RAD_ACQ_MULTIPLANAR", "Multiplanar imaging", Category.ACQUISITION, "multiplanar", ("axial", "sagittal", "coronal")),
    _concept("RAD_ACQ_SCANNER", "MRI scanner field strength", Category.ACQUISITION, "Tesla", ("1.5T", "3T", "MR scanner")),
    _concept("RAD_ANAT_HEAD", "Head", Category.ANATOMY, "head"),
    _concept("RAD_ANAT_BRAIN", "Brain", Category.ANATOMY, "brain"),
    _concept("RAD_ANAT_NECK", "Neck", Category.ANATOMY, "neck"),
    _concept("RAD_ANAT_CHEST", "Chest", Category.ANATOMY, "chest", ("thorax", "الصدر", "صدرية")),
    _concept("RAD_ANAT_ABDOMEN", "Abdomen", Category.ANATOMY, "abdomen", ("abdominal", "البطن")),
    _concept("RAD_ANAT_PELVIS", "Pelvis", Category.ANATOMY, "pelvis", ("pelvic", "الحوض")),
    _concept("RAD_ANAT_SPINE", "Spine", Category.ANATOMY, "spine"),
    _concept("RAD_ANAT_BREAST", "Breast", Category.ANATOMY, "breast"),
    _concept("RAD_ANAT_EXTREMITY", "Extremity", Category.ANATOMY, "extremity", ("limb",)),
    _concept("RAD_ANAT_WHOLE_BODY", "Whole body", Category.ANATOMY, "whole body"),
    _concept("RAD_CONTRAST_WITH", "With contrast", Category.CONTRAST, "with contrast", ("post-contrast", "post contrast", "contrast-enhanced", "after contrast", "بالصبغة", "مع الصبغة", "بعد حقن الصبغة")),
    _concept("RAD_CONTRAST_WITHOUT", "Without contrast", Category.CONTRAST, "without contrast", ("non-contrast", "pre-contrast", "pre contrast", "بدون صبغة")),
    _concept("RAD_CONTRAST_PRE_POST", "Pre/post contrast", Category.CONTRAST, "pre/post contrast", ("pre- and post-contrast", "before and after contrast", "without and with contrast"), 1.5),
    _concept("RAD_PURPOSE_STAGING", "Oncologic staging", Category.CLINICAL_PURPOSE, "cancer staging", ("oncologic staging", "tumor staging", "tumour staging", "staging"), 1.2),
    _concept("RAD_PURPOSE_SCREENING", "Screening", Category.CLINICAL_PURPOSE, "screening"),
    _concept("RAD_PURPOSE_FOLLOWUP", "Follow-up", Category.CLINICAL_PURPOSE, "follow-up", ("follow up", "surveillance")),
    _concept("RAD_PURPOSE_POST_TREATMENT", "Post-treatment assessment", Category.CLINICAL_PURPOSE, "post-treatment", ("treatment response",)),
    _concept("RAD_PURPOSE_DIAGNOSTIC", "Diagnostic evaluation", Category.CLINICAL_PURPOSE, "diagnostic evaluation"),
)
