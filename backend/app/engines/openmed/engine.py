from openmed import DeidentificationResult, deidentify


def deidentify_text(
    text: str,
    *,
    method: str = "mask",
    language: str = "en",
    confidence_threshold: float = 0.7,
) -> DeidentificationResult:
    """
    De-identify medical text using the OpenMed engine.

    The complete OpenMed result is returned so MedNexus can use:
    - deidentified_text
    - detected PII entities
    - entity mapping
    - metadata
    - audit report
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty.")

    return deidentify(
        text=text,
        method=method,
        lang=language,
        confidence_threshold=confidence_threshold,
        cache_results=False,
    )