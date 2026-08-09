# MedNexus Technical Debt

## TD-0001 — Generalize the de-identification service method name

**Current:** `deidentify_text()`

**Proposed:** `deidentify()`

**Reason:** Support future document types beyond plain text.

**Priority:** Medium

**Status:** Planned; not implemented.

---

## TD-0002 — Normalize repeated relative-name placeholders

**Issue:** Multi-part next-of-kin names may produce repeated `[RELATIVE_NAME]` placeholders in final output.

**Classification:** Minor output-normalization and readability issue. It is not currently considered a privacy failure.

**Future work:** Evaluate consolidation of adjacent or repeated relative-name spans and placeholders without weakening entity coverage.

**Priority:** Low

**Status:** Planned; not implemented.
