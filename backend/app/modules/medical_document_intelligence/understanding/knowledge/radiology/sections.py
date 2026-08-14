from ...models import DocumentDomain
from ..models import RecognitionConcept, RecognitionConceptCategory as Category
from ..references import ReferenceFamily as Ref


_SECTION_REFS = (Ref.DICOM_SR.value, Ref.RADREPORT.value, Ref.HL7_CDA.value)

RADIOLOGY_SECTION_CONCEPTS = (
    RecognitionConcept("RAD_SECTION_EXAMINATION", "Radiology examination", Category.SECTION, DocumentDomain.RADIOLOGY,
                       "examination", "الفحص", evidence_strength=2, external_references=_SECTION_REFS),
    RecognitionConcept("RAD_SECTION_TECHNIQUE", "Technique", Category.SECTION, DocumentDomain.RADIOLOGY,
                       "technique", "الطريقة", aliases_ar=("التقنية",), evidence_strength=2, external_references=_SECTION_REFS),
    RecognitionConcept("RAD_SECTION_FINDINGS", "Findings", Category.SECTION, DocumentDomain.RADIOLOGY,
                       "findings", "النتائج", aliases_ar=("الموجودات",), evidence_strength=2, external_references=_SECTION_REFS),
    RecognitionConcept("RAD_SECTION_IMPRESSION", "Impression", Category.SECTION, DocumentDomain.RADIOLOGY,
                       "impression", "الانطباع", aliases_ar=("الخلاصة",), evidence_strength=3, external_references=_SECTION_REFS),
    RecognitionConcept("RAD_SECTION_COMPARISON", "Comparison", Category.SECTION, DocumentDomain.RADIOLOGY,
                       "comparison", "المقارنة", evidence_strength=1.5, external_references=_SECTION_REFS),
)

RADIOLOGY_SECTION_ALIASES = {
    "radiology_examination": RADIOLOGY_SECTION_CONCEPTS[0].aliases,
    "technique": RADIOLOGY_SECTION_CONCEPTS[1].aliases,
    "findings": RADIOLOGY_SECTION_CONCEPTS[2].aliases,
    "impression": RADIOLOGY_SECTION_CONCEPTS[3].aliases,
    "comparison": RADIOLOGY_SECTION_CONCEPTS[4].aliases,
    "radiologist_authentication": ("radiologist", "طبيب الأشعة", "اختصاصي الأشعة", "أخصائي الأشعة"),
}
