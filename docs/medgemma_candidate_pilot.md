# MedGemma candidate-engine pilot

MedGemma is an **optional, local, review-only candidate engine** for Radiology report text. MRJ Native (RadGraph plus MRJ clinical synthesis) remains the source of the governed clinical record. MedGemma candidates do not write or replace `ReviewedClinicalRecord` data; human review remains required for the native record. This pilot does not establish clinical superiority.

Set `MRJ_MEDGEMMA_ENABLED=true` in the server process to enable the pilot. The default is disabled, which leaves EXTRACT and the Report Workspace on their prior path. No MedGemma packages are imported into the MRJ `.venv`.

The Journey checks an eligible Radiology PROTECT result, its integrity digest, and protected section boundaries before EXTRACT. `ClinicalExtractionService` gives the MedGemma adapter only the protected text and protected sections. The adapter verifies those slices and sends only protected text as JSON stdin to `D:\MedNexus\Environments\mrj-medgemma\Scripts\python.exe -B medgemma_worker.py`. No original identified report text or Gold annotation is sent. The worker loads only the pinned local `google/medgemma-1.5-4b-it` snapshot at revision `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`, with offline flags, `local_files_only=True`, `trust_remote_code=False`, BF16, and all-GPU placement. There is no cloud inference.

A single server-process worker is reused for nearby reports, serializes MedGemma inference, and unloads after five idle minutes. Startup and inference have bounded waits; timeout terminates the worker. This avoids reloading the 4B model for every closely spaced invocation, but the GPU memory held during the idle interval may compete with other local GPU work. The pilot has no distributed scheduler.

The product prompt requests only clinical candidate fields. MRJ assigns IDs and model provenance, validates types/enumerations, and derives offsets only for a quote that occurs exactly once in the complete protected text and lies within an eligible protected section. Missing or repeated quotes remain visible in technical warnings and are not promoted to review suggestions; no fuzzy repair occurs. Every raw model candidate and the raw decoded response remain in the EXTRACT technical `raw_engine_evidence.medgemma` pathway. Exact duplicate candidates remain in that audit trail; the review-only list displays one copy, with raw, validated, duplicate, and final suggestion counts retained. No MedGemma suggestion is inserted into canonical facts or durable records by this pilot.

The existing Report Workspace shows a small candidate-engine status and exactly grounded, review-only suggestions when enabled. Raw JSON, paths, hashes, and CUDA details are absent from the normal clinician view. The clinician's Accept & Save action continues to accept only the governed MRJ clinical record; MedGemma suggestions are explicitly labeled as excluded from it.

If the model is absent, fails to load, times out, runs out of memory, returns malformed output, or yields no valid candidates, the pilot reports `UNAVAILABLE`, `FAILED`, `TIMEOUT`, or `NO_VALID_CANDIDATES` while MRJ Native extraction and review remain available. The feature can be disabled without removing the external environment.

Known limitations: BF16 uses substantial GPU memory; the non-benchmark smoke observed about 8.76 GiB peak VRAM and 80.235 seconds for 1,536 generated tokens. Longer reports may consume more memory and time. Repeated raw candidates occurred in smoke testing. The product prompt has not been benchmarked against Frozen Gold, and this pilot does not make MedGemma a clinical authority. Review suggestions cannot yet be individually accepted into a durable record; that would require a separately governed, tested review action.

## Evidence + Addendum Validation Layer V1

**Status: ACCEPTED / HUMAN CLINICALLY REVIEWED.** Human review accepted the retained CT Chest, Doppler, and Mammography comparisons. This evaluation-only layer governs MedGemma candidate output before MRJ-versus-MedGemma classification. It does not make MedGemma authoritative or write to `ReviewedClinicalRecord`.

Retained Comparison Mode reuses the Report Workspace title projection. It prefers a recognized exam title, then standardized modality and body region, then an available original filename. A generic title is used only when none of those identifiers is available; retained previews remain read-only and never start extraction.

The final pipeline is: MedGemma raw output → clinical section projection → deterministic atomic clinical claim decomposition → source/addendum validation → deduplication by canonical claim identity → MRJ-versus-MedGemma comparison. The raw model response and each projected parent statement remain immutable and auditable. Atomic children retain their parent and occurrence provenance. Repeated section occurrences and measurements count once, while their raw occurrences remain available for review.

Validation assigns each atomic child one of `SUPPORTED`, `UNSUPPORTED`, `SUPERSEDED`, or `UNRESOLVED`. Comparison assigns each validated child exactly one primary category: `AGREEMENT`, `MRJ_ONLY`, `MEDGEMMA_ONLY`, `CONFLICT`, `UNSUPPORTED`, or `UNRESOLVED`. Superseded content stays visible for audit and cannot become positive agreement or a MedGemma-only addition.

The governance rules are evidence before engine agreement; agreement is not proof; **not mentioned is not negative**; later authoritative addendum/final text supersedes conflicting earlier interpretation; unsupported model content cannot become MedGemma-only; and recommendations require explicit source support. A measurement is checked independently from its base finding. Composite model sentences are decomposed so an unsupported qualifier cannot erase a supported component. Incomplete or token-capped generation invalidates head-to-head scoring. `MODEL_CONTENT_FAILURE` is distinguished from input and runtime failure.

Human-reviewed retained cases established the following boundaries:

- **CT Chest:** Atomic validation recovered source-supported interval findings. Invented measurements and workup remained rejected, and addendum authority remained intact.
- **Doppler:** A source-grounded ultrasound follow-up in 3–6 months remained a genuine MedGemma-only addition. The repeated 3.5 cm measurement counted once.
- **Mammography:** Grounded measurements remained available; the unsupported no-further-workup interpretation was not promoted.
- **USG:** The protected input was complete, but the retained output remains `MODEL_CONTENT_FAILURE`, not an input failure.
- **X-ray:** Retained generation reached the 2,000-token cap; comparison remains invalid rather than receiving normal head-to-head scores.

This evaluation does **not** establish MedGemma as a replacement for MRJ Native. It supports the multi-engine architecture: specialized engines may contribute candidate evidence, while MRJ owns orchestration, source authority, provenance, addendum handling, validation, conflicts, human review, and final clinical authority. A unified multi-engine clinical result may be investigated later; fusion and merge policy are not implemented in V1.

### Follow-up items, outside V1 closure

1. **Runtime stability:** A later live Doppler invocation reached the 240-second failure limit despite an earlier successful retained run.
2. **Content variability:** USG returned `MODEL_CONTENT_FAILURE` with complete protected input.
3. **Generation stability:** The retained X-ray output reached the 2,000-token cap.
4. **Comparison scope:** Deterministic V1 comparison is conservative; it is not a general-purpose semantic NLI engine.
5. **Fusion policy:** Governed merger of multiple engine results remains future work.
