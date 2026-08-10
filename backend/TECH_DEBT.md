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

---

## TD-0003 — Replace placeholder-only advanced policy actions with genuine transformers

**Issue:** `GENERALIZE` and `SHIFT_DATE` remain enum-level extension points, but genuine generalization, derivation, date shifting, geography reduction, and pseudonymization transformers are not implemented. The current four executable profiles intentionally use only `KEEP`, `REPLACE`, `HASH`, `MASK`, and `REMOVE`.

**Risk:** Future code could incorrectly present an advanced action as implemented without the required transformation semantics, reference context, or audit evidence.

**Required control:** Keep unsupported actions unavailable at runtime until dedicated, tested transformers exist. Future transformers must reuse the unified privacy pipeline.

**Priority:** Medium

**Status:** Planned; not implemented.
