from __future__ import annotations

from dataclasses import dataclass

from .models import DocumentDomain, DocumentSubtype, DocumentType


@dataclass(frozen=True, slots=True)
class WeightedSignal:
    phrase: str
    weight: float
    category: str


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    domain: DocumentDomain
    document_type: DocumentType
    signals: tuple[WeightedSignal, ...]


def _signals(*items):
    return tuple(WeightedSignal(*item) for item in items)


PROFILES = (
    DocumentProfile(DocumentDomain.RADIOLOGY, DocumentType.RADIOLOGY_REPORT, _signals(
        ("radiology report", 5, "title"), ("imaging report", 4, "title"),
        ("technique", 2, "section"), ("findings", 2, "section"), ("impression", 3, "section"),
        ("comparison", 1.5, "section"), ("ct", 2, "modality"), ("mri", 2, "modality"),
        ("x-ray", 2, "modality"), ("ultrasound", 2, "modality"), ("mammography", 2, "modality"),
        ("تقرير الأشعة", 5, "title"), ("النتائج", 1.5, "section"), ("الانطباع", 2.5, "section"),
    )),
    DocumentProfile(DocumentDomain.PATHOLOGY, DocumentType.PATHOLOGY_REPORT, _signals(
        ("pathology report", 5, "title"), ("histopathology", 4, "title"),
        ("gross description", 3, "section"), ("microscopic description", 3, "section"),
        ("final diagnosis", 3, "section"), ("immunohistochemistry", 3, "lexical"),
        ("specimen", 1.5, "section"), ("margins", 1.5, "lexical"), ("تقرير الباثولوجي", 5, "title"),
    )),
    DocumentProfile(DocumentDomain.LABORATORY, DocumentType.LABORATORY_REPORT, _signals(
        ("laboratory report", 5, "title"), ("lab results", 4, "title"),
        ("reference range", 3, "structure"), ("test result", 2, "structure"),
        ("units", 1.5, "structure"), ("collected", 1, "lexical"), ("validated", 1, "lexical"),
        ("تقرير المختبر", 5, "title"), ("المدى المرجعي", 3, "structure"),
    )),
    DocumentProfile(DocumentDomain.EMERGENCY, DocumentType.EMERGENCY_REPORT, _signals(
        ("emergency department", 5, "title"), ("emergency report", 5, "title"),
        ("chief complaint", 2, "section"), ("triage", 2.5, "section"),
        ("history of present illness", 2.5, "section"), ("vital signs", 2, "section"),
        ("ed course", 3, "section"), ("disposition", 2, "section"), ("قسم الطوارئ", 5, "title"),
    )),
    DocumentProfile(DocumentDomain.ADMISSION_DISCHARGE, DocumentType.ADMISSION_NOTE, _signals(
        ("admission note", 5, "title"), ("reason for admission", 3, "section"),
        ("admitting diagnosis", 3, "section"), ("admission diagnosis", 3, "section"),
        ("assessment and plan", 2, "section"), ("ملاحظة الدخول", 5, "title"),
    )),
    DocumentProfile(DocumentDomain.ADMISSION_DISCHARGE, DocumentType.DISCHARGE_SUMMARY, _signals(
        ("discharge summary", 5, "title"), ("hospital course", 3, "section"),
        ("discharge diagnosis", 3, "section"), ("discharge medications", 3, "section"),
        ("condition on discharge", 2, "section"), ("follow-up", 1.5, "section"),
        ("ملخص الخروج", 5, "title"),
    )),
    DocumentProfile(DocumentDomain.PUBLIC_HEALTH, DocumentType.PUBLIC_HEALTH_DOCUMENT, _signals(
        ("public health notification", 5, "title"), ("communicable disease notification", 5, "title"),
        ("case notification", 4, "title"), ("epidemiological investigation", 4, "title"),
        ("surveillance report", 4, "title"), ("إخطار الصحة العامة", 5, "title"),
        ("ترصد وبائي", 4, "title"),
    )),
)


SECTION_ALIASES = {
    "clinical_history": ("clinical history", "history", "التاريخ السريري"),
    "comparison": ("comparison", "المقارنة"), "technique": ("technique", "التقنية"),
    "findings": ("findings", "النتائج"), "impression": ("impression", "الانطباع"),
    "recommendation": ("recommendation", "recommendations", "التوصية"),
    "clinical_information": ("clinical information",), "specimen": ("specimen", "العينة"),
    "gross_description": ("gross description",), "microscopic_description": ("microscopic description",),
    "diagnosis": ("diagnosis", "التشخيص"), "final_diagnosis": ("final diagnosis",),
    "comment": ("comment", "comments"), "patient_information": ("patient information",),
    "results": ("results", "lab results"), "reference_range": ("reference range",),
    "interpretation": ("interpretation",), "authorization": ("authorization", "authorized by"),
    "chief_complaint": ("chief complaint", "الشكوى الرئيسية"), "triage": ("triage", "الفرز"),
    "history_of_present_illness": ("history of present illness", "hpi"),
    "vital_signs": ("vital signs", "العلامات الحيوية"), "examination": ("physical examination", "examination"),
    "investigations": ("investigations",), "assessment": ("assessment",), "treatment": ("treatment",),
    "disposition": ("disposition",), "admission_diagnosis": ("admission diagnosis", "admitting diagnosis"),
    "hospital_course": ("hospital course",), "procedures": ("procedures",),
    "discharge_diagnosis": ("discharge diagnosis",), "discharge_medications": ("discharge medications",),
    "follow_up": ("follow-up", "follow up"), "notification_details": ("notification details", "case notification"),
    "surveillance_summary": ("surveillance summary", "epidemiological investigation"),
}


SUBTYPE_SIGNALS = {
    DocumentSubtype.CT: ("ct", "computed tomography"), DocumentSubtype.MRI: ("mri", "magnetic resonance"),
    DocumentSubtype.X_RAY: ("x-ray", "x ray", "radiograph"), DocumentSubtype.ULTRASOUND: ("ultrasound", "sonography"),
    DocumentSubtype.MAMMOGRAPHY: ("mammography", "mammogram"),
    DocumentSubtype.NUCLEAR_MEDICINE: ("nuclear medicine", "pet scan", "scintigraphy"),
}
