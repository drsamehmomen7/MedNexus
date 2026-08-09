# MedNexus

Enterprise Healthcare AI Platform

---

## Overview

MedNexus is an enterprise healthcare AI platform for medical document intelligence powered by open-source medical AI engines.

The current module is **Medical Document Intelligence – De-identification**. It uses a hybrid architecture combining:

- AI-based candidate entity detection
- Deterministic identifier detection
- Healthcare-aware role and context validation
- Configurable privacy policies
- MedNexus-owned output construction

OpenMed is a candidate detector only. Its detections are treated as suggestions and do not directly determine privacy actions or final output. MedNexus owns intelligence decisions, false-positive rejection, policy application, and construction of the final de-identified text.

---

## Current De-identification Architecture

The MedNexus Intelligence Core currently includes:

- `MedNexusCandidateEntity`
- `EntityCanonicalizer`
- `OpenMedCandidateAdapter`
- `RoleResolver`
- `ContextValidator`
- `DetectionMerger`
- `MedNexusIntelligenceOrchestrator`
- `MedNexusOutputBuilder`

The MedNexus Deterministic Identifier Detector is integrated into the real de-identification service alongside the OpenMed candidate path. MedNexus merges and evaluates detections before producing the final output.

---

## Project Structure

```text
backend/
frontend/
docs/
requirements/
Validation/
```

---

## Current Status

**Medical Document Intelligence – De-identification Phase 1**

Completed and integrated:

- MedNexus Intelligence Core
- OpenMed candidate adaptation
- Deterministic identifier detection in the real service
- MedNexus-owned final output construction

Current confirmed regression baseline:

- **645 passing tests**
- **8 warnings**

Phase 1 real-document validation completed successfully across samples from:

- Radiology
- Emergency
- Discharge Summary
- Pathology
- Laboratory
- Referral
- Operative Note
- Notification Form
- Death Certificate
- Admission
- ICU

This validation is Phase 1 evidence for the current implementation. It does not claim that de-identification is complete or production-certified.

Known minor output-quality debt is tracked in `backend/TECH_DEBT.md`.
