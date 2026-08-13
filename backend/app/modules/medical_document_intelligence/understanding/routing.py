from .models import ConfidenceBand, DocumentType, UnderstandingRoute


_ROUTES = {
    DocumentType.RADIOLOGY_REPORT: ("radiology_extraction", "radiology_terminology"),
    DocumentType.PATHOLOGY_REPORT: ("pathology_extraction", "pathology_terminology"),
    DocumentType.LABORATORY_REPORT: ("laboratory_extraction", "laboratory_terminology"),
    DocumentType.EMERGENCY_REPORT: ("emergency_extraction", "emergency_terminology"),
    DocumentType.ADMISSION_NOTE: ("admission_extraction", "general_clinical_terminology"),
    DocumentType.DISCHARGE_SUMMARY: ("discharge_extraction", "general_clinical_terminology"),
    DocumentType.PUBLIC_HEALTH_DOCUMENT: ("public_health_extraction", "public_health_terminology"),
}


class UnderstandingRouter:
    @staticmethod
    def route(document_type: DocumentType, confidence_band: ConfidenceBand) -> UnderstandingRoute:
        if document_type is DocumentType.UNKNOWN or confidence_band in {ConfidenceBand.LOW, ConfidenceBand.UNKNOWN}:
            return UnderstandingRoute(
                "mednexus_clinical", "manual_review", "general_clinical_terminology", ("PROTECT",), True
            )
        extraction, terminology = _ROUTES[document_type]
        return UnderstandingRoute(
            "mednexus_clinical", extraction, terminology,
            ("PROTECT", "EXTRACT", "STANDARDIZE"), False,
        )
