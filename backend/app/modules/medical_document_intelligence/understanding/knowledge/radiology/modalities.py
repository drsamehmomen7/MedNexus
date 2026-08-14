from ...models import DocumentDomain, DocumentSubtype
from ..models import RecognitionConcept, RecognitionConceptCategory as Category
from ..references import ReferenceFamily as Ref


_MODALITY_REFS = (Ref.DICOM.value, Ref.RADLEX.value, Ref.RADLEX_PLAYBOOK.value)

RADIOLOGY_MODALITY_CONCEPTS = (
    RecognitionConcept("RAD_MODALITY_CT", "Computed tomography", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "CT", "أشعة مقطعية", ("computed tomography",), ("التصوير المقطعي",), 2,
                       external_references=_MODALITY_REFS),
    RecognitionConcept("RAD_MODALITY_MRI", "Magnetic resonance imaging", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "MRI", "الرنين المغناطيسي", ("magnetic resonance",), ("التصوير بالرنين المغناطيسي",), 2,
                       external_references=_MODALITY_REFS),
    RecognitionConcept("RAD_MODALITY_XRAY", "X-ray", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "x-ray", "أشعة سينية", ("x ray", "radiograph"), evidence_strength=2,
                       external_references=_MODALITY_REFS),
    RecognitionConcept("RAD_MODALITY_ULTRASOUND", "Ultrasound", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "ultrasound", "الموجات فوق الصوتية", ("sonography",), ("الألتراساوند",), 2,
                       external_references=_MODALITY_REFS),
    RecognitionConcept("RAD_MODALITY_MAMMOGRAPHY", "Mammography", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "mammography", "تصوير الثدي", ("mammogram",), ("الماموجرام",), 2,
                       external_references=_MODALITY_REFS),
    RecognitionConcept("RAD_MODALITY_NUCLEAR_MEDICINE", "Nuclear medicine", Category.MODALITY, DocumentDomain.RADIOLOGY,
                       "nuclear medicine", None, ("pet scan", "scintigraphy"), evidence_strength=2,
                       external_references=_MODALITY_REFS),
)

RADIOLOGY_SUBTYPE_SIGNALS = {
    DocumentSubtype.CT: RADIOLOGY_MODALITY_CONCEPTS[0].aliases,
    DocumentSubtype.MRI: RADIOLOGY_MODALITY_CONCEPTS[1].aliases,
    DocumentSubtype.X_RAY: RADIOLOGY_MODALITY_CONCEPTS[2].aliases,
    DocumentSubtype.ULTRASOUND: RADIOLOGY_MODALITY_CONCEPTS[3].aliases,
    DocumentSubtype.MAMMOGRAPHY: RADIOLOGY_MODALITY_CONCEPTS[4].aliases,
    DocumentSubtype.NUCLEAR_MEDICINE: RADIOLOGY_MODALITY_CONCEPTS[5].aliases,
}
