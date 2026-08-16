# MedNexus Reference Model

This package separates external reference metadata, MedNexus canonical concepts, and proprietary runtime reasoning. Recognition is offline: runtime code reads the local canonical model and never queries terminology services.

## Controlled source acquisition

- LOINC/RSNA Radiology Playbook: obtain LOINC 2.82 through the authenticated official download at `https://loinc.org/downloads/`, accept the LOINC License, verify the published checksum, and import only the required Playbook accessory subset.
- DICOM: obtain the relevant current-edition XML or other machine-readable parts from `https://www.dicomstandard.org/current`. Implementation is free; copying/excerpts remain subject to NEMA copyright terms.
- RadLex: register and accept the RadLex Ontology License at `https://www.rsna.org/radlex`. Preserve its license, NOTICE, version, and artifact checksum. No RadLex distribution is committed here.
- SNOMED CT: acquire an authorized RF2 release through the applicable National Release Centre or MLDS at `https://mlds.ihtsdotools.org/`. Never commit licensed RF2 content unless the applicable license explicitly permits distribution.

Each controlled import must update `manifest.json` with its pinned version, release date, retrieval and verification dates, checksum, and enabled state. Import into a reviewable normalized derivative, compare source versions, validate affected MedNexus concept mappings and relationships, run focused reasoning tests, then run full regression. A source is not active merely because metadata exists in the manifest.

Validation reports are fixtures, not terminology sources. Concepts or aliases may enter the runtime model only through independently justified reference knowledge or a general MedNexus normalization rule.

## Local ingestion and activation

Raw artifacts and normalized local stores live under `D:\MedNexus\Reference_Data`. From the repository root:

```text
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli status
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli import dicom --path D:\MedNexus\Reference_Data\DICOM\2026c\part06.xml
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli import loinc --path <official-package>
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli import radlex --path <official-owl-or-rdf>
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli import snomed --path <official-rf2-package> --subset-file <concept-id-file>
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli verify [source]
python -m backend.app.modules.medical_document_intelligence.understanding.reference_model.cli activate <source> [version]
```

Import records the artifact path, SHA-256 checksum, import time, concept count and mapping count. Activation changes only `Reference_Data\active.json`; recognition remains offline. Imported exact concepts are resolved before the MedNexus curated compatibility layer. Deduplication is conservative and no cross-standard mapping is invented.

Controlled destinations and packages:

- LOINC 2.82: download the Complete LOINC package containing `AccessoryFiles/LoincRsnaRadiologyPlaybook` from `https://loinc.org/downloads/` after login/license acceptance; save under `D:\MedNexus\Reference_Data\LOINC\2.82`.
- DICOM 2026c: official PS3.6 DocBook XML is `https://dicom.nema.org/medical/dicom/current/source/docbook/part06/part06.xml`; save under `D:\MedNexus\Reference_Data\DICOM\2026c`.
- RadLex: register and accept the RSNA license, download the official OWL/RDF artifact, and save under `D:\MedNexus\Reference_Data\RadLex\<version-from-artifact>`. The importer never fabricates a version.
- SNOMED CT International 20260701: acquire `SnomedCT_InternationalRF2_PRODUCTION_20260701T120000Z.zip` through MLDS/NRC and save under `D:\MedNexus\Reference_Data\SNOMED_CT\International\20260701`. Import requires an explicit subset-ID file; the entire terminology is not loaded into runtime memory.
