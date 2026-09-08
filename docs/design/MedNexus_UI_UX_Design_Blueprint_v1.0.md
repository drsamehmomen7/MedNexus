# MedNexus UI/UX Design Blueprint v1.0

**Status:** ACCEPTED DESIGN BLUEPRINT

**Milestone:** M1 — MedNexus UI/UX Design Blueprint

**Architecture checkpoint:** `081e8b178f63850beb18f41a09494452aeacc4fc`

**Prepared:** 2026-09-08

**Scope:** Future presentation for `/app`, `/understanding`, and `/privacy`; no runtime, API, route, clinical, or policy changes.

## 1. Design principles

MedNexus should present clinical intelligence with clarity before spectacle. The interface should feel calm, credible, precise, spacious, and understandable to clinical and non-clinical users.

1. **Clinical clarity first.** The primary result, action, or status must be understandable within seconds.
2. **Authority must be visible.** Distinguish MedNexus decisions from candidate evidence, future engines, and planned capabilities.
3. **Progressive disclosure.** Present a simple result first, an understandable explanation second, and technical detail last.
4. **One product system.** Radiology and Public Health receive restrained accents within one shared MedNexus identity; MEDNEXUS Seven must not become seven unrelated visual themes.
5. **Evidence without noise.** Provenance, warnings, abstention, and human review remain visible without making the default interface feel like a classifier console.
6. **Readable clinical documents.** Long medical text uses a highly legible interface typeface, controlled line length, comfortable line height, and selectable text.
7. **Honest product status.** Implemented, in-development, planned, candidate, and research-watch capabilities must be clearly differentiated.
8. **Presentation is not clinical authority.** Frontend code displays authoritative backend output; it does not recreate recognition, policy, privacy, or routing decisions.
9. **Accessible by default.** Keyboard access, visible focus, contrast, reduced motion, semantic structure, and readable status messages are design requirements.
10. **Responsive by composition.** Reflow and prioritization take precedence over shrinking dense desktop layouts.

The target character is light, clinical, premium, calm, modern, high-trust, and professional. It must not feel cyber-security themed, hacker-like, gaming-like, neon, or futuristic for its own sake.

## 2. EdgeCase reference audit

Primary reference: <https://www.edgecase.site/>

The homepage HTML, operative `styles.css?v=57`, `app.js?v=15`, and same-origin font endpoints were retrieved read-only on 2026-09-08. The source values below are the authority for exact tokens. A product-owner-supplied full-page mobile screenshot was reviewed only as supplementary evidence for hierarchy, spacing rhythm, surface relationships, card composition, typography scale, and stacking; no exact value was inferred from the screenshot.

### 2.1 Verified EdgeCase reference values

#### Active typography and hosting

EdgeCase declares two same-origin variable TTF fonts:

| Family | Declared range | Operative homepage use |
|---|---|---|
| `Mona Sans` | Weight `200–900`; width `75%–125%` | Active body, display, navigation, and button font |
| `Bricolage` | Weight `200–800` | Declared by `@font-face`, but unused by the operative homepage CSS |

The operative variables are:

```css
--font: "Mona Sans", sans-serif;
--display: "Mona Sans", sans-serif;
```

Both fonts are self-hosted by EdgeCase. No external font host or Google Fonts dependency appears in the inspected homepage source. This verification does not grant redistribution rights.

#### Light / Oak palette

| Role | Verified value |
|---|---:|
| Page background | `#EAD6B8` |
| Card surface | `#F6E6CC` |
| Primary text | `#1C140C` |
| Muted text | `#6E5C48` |
| Border | `rgba(28, 20, 12, 0.14)` |
| Primary accent | `#E23B2B` |
| Nested paper surface | `#F6E6CC` |
| Secondary nested surface | `#F3E0C4` |
| Large muted surface | `#D4BC96` |
| Scrolled navigation | `rgba(234, 214, 184, 0.78)` |
| Supporting teal | `#2A9B8F` |
| Paper/image background | `#F3EDE3` |
| Light paper | `#FFF8EE` |
| Warm white | `#FFF8F0` |
| Dark-red label | `#9A2418` |
| Light-red label | `#F0A098` |

The primary Oak CTA uses `#1C140C` for its background and `#EAD6B8` for its text. The ghost treatment is transparent with primary text and the theme border.

#### Dark / Ink palette — reference only

| Role | Verified value |
|---|---:|
| Background | `#070706` |
| Surface | `#0E0D0B` |
| Primary text | `#EAD6B8` |
| Muted text | `#B9A48A` |
| Border | `rgba(234, 214, 184, 0.14)` |
| Accent | `#E23B2B` |
| Secondary dark surface | `#1A1916` |
| Large muted surface | `#1A1917` |
| Scrolled navigation | `rgba(7, 7, 6, 0.72)` |

#### Typographic scale

| Role | Verified size | Weight | Line height / constraint |
|---|---|---:|---|
| Hero H1 | `clamp(56px, 9vw, 96px)` | 620 | `1.08` |
| Section H2 | `clamp(36px, 5.5vw, 64px)` | 620 | `1.15` |
| Primary card H3 | `32px` | 560 | Source-defined card treatment |
| Lead | `20px` | Inherited | `1.4`; maximum `42ch` |
| Regular card copy | `15px` | Inherited | `1.45` |
| Navigation | `14px` | 650 | Muted-to-primary interaction |
| Button | `14px` | 650 | Standard height `42px` |
| Large button | `16px` | 650 | Height `52px` |

#### Layout, geometry, and spacing

| Property | Verified value |
|---|---:|
| Main content maximum width | `1120px` |
| CTA panel maximum width | `920px` |
| Desktop horizontal content padding | `24px` |
| Mobile horizontal content padding | `16px` |
| Desktop navigation padding | `16px 28px` |
| Navigation gap | `28px` |
| Navigation-link gap | `22px` |
| Standard button height | `42px` |
| Large control height | `52px` |
| Brand mark | `36px × 36px` |
| Primary card radius | `28px` |
| Large feature radius | `36px` |
| Nested panel radius | `18px` |
| Input radius | `16px` |
| Small-card radius | `14px` |
| Standard pill radius | `999px` |
| Primary width breakpoint | `860px` |
| Hero padding, desktop | `40px 24px 56px` |
| Hero padding, mobile | `20px 16px 28px` |
| Standard section, desktop | `40px 24px 88px` |
| Standard section, mobile | `28px 16px 64px` |
| CTA panel, desktop | `56px 28px` |
| CTA panel, mobile | `40px 18px` |
| Bento gap | `18px` |
| Button-row gap | `10px` |

Verified representative shadows include `0 24px 48px rgba(0, 0, 0, 0.28)` on major chroma cards, `0 8px 18px rgba(28, 20, 12, 0.06)` on light mini cards, `0 4px 10px rgba(0, 0, 0, 0.22)` on paper stacks, and `0 6px 16px rgba(226, 59, 43, 0.28)` on a highlighted statistic.

#### Motion

| Behavior | Verified value |
|---|---|
| Primary easing | `cubic-bezier(0.22, 1, 0.36, 1)` |
| Section reveal | `900ms`; opacity `0`; `translateY(28px)`; blur `8px` |
| Navigation transition | `400ms` |
| Navigation blur after scroll | `16px` |
| Button hover | `brightness(1.06)` |
| Button active | `scale(0.98)` |
| Reveal observer threshold | `0.16` |
| Reveal observer root margin | `0px 0px -8% 0px` |

The inspected CSS also contains a `prefers-reduced-motion: reduce` mode that disables its principal decorative animations and section reveal.

#### Supplementary screenshot findings

The mobile screenshot confirms a centered, single-column hierarchy; generous separation between major sections; vertically stacked cards; warm page/card/paper surface relationships; rounded containers; strong heading-to-copy scale contrast; simple dark CTAs; and compact icon groups. These are compositional observations only. The screenshot is not the source of any token or measurement above.

### 2.2 MedNexus adaptation decisions

- Use the Light / Oak direction as the primary near-term MedNexus identity.
- Treat the Ink palette as optional future-theme reference material, not the product foundation.
- Adopt Mona Sans as the principal MedNexus visual, interface, and clinical-document font.
- Do not copy either font binary from EdgeCase. Obtain Mona Sans later from an authoritative licensed source and retain its applicable license/notice.
- Reuse Oak values where they support clinical readability, while adding distinct accessible semantic state colors where clinical meaning requires them.
- Use `#E23B2B` as a restrained signature accent, not the dominant application color and not a universal error, danger, review, or destructive-action color.
- Use the verified supporting teal `#2A9B8F` as the restrained Radiology accent.
- Give Public Health a compatible restrained green accent without creating a separate product identity.
- UNDERSTAND and PROTECT may use Oak as their application shell, but medical-document reading surfaces should primarily use `#FFF8EE` or `#FFF8F0` for readability.
- Preserve EdgeCase's spacious rhythm and surface layering while reducing decorative motion and dense marketing scale inside clinical workspaces.
- Do not copy EdgeCase content, branding, illustrations, logos, or product-specific composition.

## 3. Proposed MedNexus clinical design tokens

The following system adapts the verified EdgeCase reference values for MedNexus. Each non-reference semantic extension is labeled as a MedNexus decision.

### 3.1 Color tokens

| Token | Value | Intended use |
|---|---:|---|
| `--mnx-bg` | `#EAD6B8` | Primary Oak application background; verified reference value |
| `--mnx-bg-muted` | `#D4BC96` | Large quiet background areas; verified reference value |
| `--mnx-surface` | `#F6E6CC` | Primary card and workspace surface; verified reference value |
| `--mnx-surface-nested` | `#F3E0C4` | Nested grouping; verified reference value |
| `--mnx-document` | `#FFF8EE` | Clinical/document paper surface; verified reference value |
| `--mnx-document-warm` | `#FFF8F0` | Alternate clinical paper surface; verified reference value |
| `--mnx-text-primary` | `#1C140C` | Primary ink text; verified reference value |
| `--mnx-text-secondary` | `#6E5C48` | Supporting text; verified reference value |
| `--mnx-border` | `rgba(28, 20, 12, 0.14)` | Default border; verified reference value |
| `--mnx-action` | `#1C140C` | Primary CTA background; verified Oak role |
| `--mnx-action-text` | `#EAD6B8` | Primary CTA label; verified Oak role |
| `--mnx-signature` | `#E23B2B` | MedNexus signature accent; verified reference color |
| `--mnx-radiology` | `#2A9B8F` | Radiology accent; verified supporting reference color |
| `--mnx-radiology-soft` | `#DCEBE3` | Radiology soft surface; MedNexus semantic extension |
| `--mnx-public-health` | `#4F6F49` | Public Health accent; MedNexus semantic extension compatible with Oak |
| `--mnx-public-health-soft` | `#E3E8D3` | Public Health soft surface; MedNexus semantic extension |
| `--mnx-success` | `#2D6848` | Successful completion/readiness; MedNexus semantic extension |
| `--mnx-success-soft` | `#DFEBDD` | Success surface; MedNexus semantic extension |
| `--mnx-warning` | `#895A00` | Non-blocking warning; MedNexus semantic extension |
| `--mnx-warning-soft` | `#F8E7B7` | Warning surface; MedNexus semantic extension |
| `--mnx-review` | `#664A78` | Review-required/abstention; MedNexus semantic extension |
| `--mnx-review-soft` | `#EDE1F0` | Review surface; MedNexus semantic extension |
| `--mnx-error` | `#9E332C` | Error state; MedNexus semantic extension |
| `--mnx-error-soft` | `#F2D9D2` | Error surface; MedNexus semantic extension |

Color must never be the only carrier of meaning. Every status also requires text and, where helpful, an icon. Contrast must be verified against WCAG 2.2 AA before implementation; proposed values are not a substitute for implementation-time contrast testing.

### 3.2 Spacing and geometry

| Token | Value |
|---|---:|
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-6` | `24px` |
| `--space-8` | `32px` |
| `--space-12` | `48px` |
| `--space-16` | `64px` |
| `--space-24` | `96px` |
| `--radius-small-card` | `14px` |
| `--radius-input` | `16px` |
| `--radius-nested` | `18px` |
| `--radius-card` | `28px` |
| `--radius-feature` | `36px` |
| `--radius-pill` | `999px` |
| `--content-max` | `1120px` |
| `--feature-max` | `920px` |
| `--workspace-max` | `1440px` |
| `--reading-max` | `72ch` |
| `--control-height-reference` | `42px` |
| `--control-height-accessible` | `44px` |
| `--control-height-large` | `52px` |
| `--shadow-subtle` | `0 8px 18px rgba(28, 20, 12, 0.06)` |
| `--shadow-feature-reference` | `0 24px 48px rgba(0, 0, 0, 0.28)` |

The spacing scale remains a MedNexus organizational layer over the verified EdgeCase rhythm. Marketing sections may use the verified `40px 24px 88px` desktop and `28px 16px 64px` mobile rhythm. Clinical workspaces may extend to `1440px` and add intermediate breakpoints where report readability requires them.

Use one-pixel borders for most separation. EdgeCase's major-card shadow is verified, but MedNexus clinical workspaces should prefer no shadow or the verified restrained light-card shadow `0 8px 18px rgba(28, 20, 12, 0.06)`. Elevation should communicate hierarchy, not decoration.

### 3.3 Component language

- Primary buttons: at least `44px` high for MedNexus accessibility, pill or restrained rounded treatment, `#1C140C` background, `#EAD6B8` label, and clear hover/focus states. The verified EdgeCase reference height is `42px`.
- Large actions and inputs: `52px` high where the hierarchy requires them.
- Secondary buttons: transparent or paper surface, theme border, and primary ink text.
- Quiet/text actions: no enclosing pill unless needed for selection; minimum 44px interactive target.
- Cards: Oak/paper surface, one-pixel theme border, `28px` primary radius or smaller nested radii, restrained or absent shadow in clinical workspaces.
- Tabs: contained within a quiet neutral surface or represented by an underline; selected state must include text/shape, not color alone.
- Status: short label plus icon and plain-language description; reserve filled badges for compact metadata.
- Forms: persistent labels, concise help text, visible error association, and 48px minimum control height.
- Technical data: tabular numerals where useful; monospace only for IDs, JSON, offsets, and machine values.
- Document panes: selectable text, 16px minimum body size, approximately 65–78 characters per line, no display typography.

### 3.4 Future shared token structure

Implementation should later expose one shared MedNexus token layer organized by:

- Color: Oak backgrounds, paper surfaces, ink text, border, action, and signature accent.
- Typography: Mona Sans family, role-based scale, weights, line heights, and reading constraints.
- Spacing: the common spacing scale plus verified landing section rhythm.
- Radius: small card, input, nested panel, primary card, feature, and pill.
- Shadow: no-shadow default, subtle clinical elevation, and separately governed feature elevation.
- Layout: `1120px` marketing content, `920px` focused feature, `1440px` maximum clinical workspace, and readable text measure.
- Controls: reference `42px`, accessible MedNexus minimum `44px`, and large `52px`.
- Motion: verified easing, landing reveal, shorter workspace transitions, and reduced-motion overrides.
- Domain accent: Radiology teal and compatible Public Health green.
- Semantic state: success, warning, review required, and error, kept separate from the signature accent.

This is a blueprint for future variables and primitives. No CSS token implementation is authorized here.

## 4. Typography system

### 4.1 MedNexus family decision

- **Primary interface, display, navigation, button, and clinical-document font:** `Mona Sans`, obtained from an authoritative licensed source during implementation, with `Segoe UI`, `Arial`, and `sans-serif` fallbacks.
- **Technical-only fallback:** `ui-monospace`, `SFMono-Regular`, `Consolas`, `Liberation Mono`, and `monospace`. This is not a MedNexus brand font and remains visually subordinate.

Inter and IBM Plex Mono are removed from the proposed visual identity. Do not copy EdgeCase font binaries. Implementation must obtain Mona Sans from its original/authoritative licensed source and preserve the applicable font license and notice.

### 4.2 Type roles

| Role | Size | Weight | Line height | Tracking |
|---|---|---:|---:|---:|
| Landing Hero | `clamp(52px, 8vw, 88px)` | 620 | 1.08 | `-0.02em` |
| Landing H2 | `clamp(36px, 5vw, 60px)` | 620 | 1.15 | `-0.02em` |
| Workspace H1 | `clamp(32px, 4vw, 48px)` | 620 | 1.12 | `-0.02em` |
| Workspace H2 | `clamp(26px, 3vw, 36px)` | 600 | 1.20 | `-0.02em` |
| H3 | `22–28px` | 560 | 1.25 | `-0.02em` |
| Section eyebrow | `12px` | 700 | 1.4 | `0.12em` |
| Body large | `18–20px` | 500 | 1.50 | `-0.01em` |
| Body | `16px` | 500 | 1.55 | `-0.01em` |
| Clinical report | `16px` | 400–500 | 1.65 | normal |
| Small/meta | `13–14px` | 500 | 1.45 | `0.01em` |
| Button | `14–16px` | 650 | 1.2 | `-0.01em` |
| Data/value | `24–40px` | 650 | 1.15 | `-0.02em` |
| Technical | `13px` | 400 | 1.55 | normal |

The landing scale adapts the verified EdgeCase hierarchy without automatically carrying its `96px` maximum into task-focused pages. Clinical report text, results, warnings, and evidence explanations always prioritize reading comfort over visual impact.

## 5. Shared product shell

### 5.1 Header

- Reference height: approximately `74px` on desktop and `60px` on mobile, derived from the verified EdgeCase controls, mark, and navigation padding rather than an explicit fixed height.
- MedNexus logo: left aligned and linked to `/app`.
- Primary navigation: Radiology, Public Health, How MedNexus Works, Privacy / Governance.
- Radiology may route to the current UNDERSTAND workspace.
- Public Health must carry an honest status if no dedicated live workspace exists; it must not masquerade as an implemented route.
- How MedNexus Works may link to the journey section on `/app`.
- Privacy / Governance may link to `/privacy` or the appropriate landing section.
- One right-aligned workspace/action CTA where useful. Do not display competing primary actions.
- Active route: restrained underline, side marker, or soft background with an explicit `aria-current="page"` state.

### 5.2 Page frame

- Landing content width: verified reference maximum `1120px`; focused CTA features may use the verified `920px` maximum.
- Complex document workspaces may extend to `1440px` as a MedNexus readability adaptation.
- Horizontal content padding: verified reference `24px` desktop and `16px` mobile.
- Marketing section rhythm: verified reference `40px 24px 88px` desktop and `28px 16px 64px` mobile.
- Use the Oak background with card and clinical-paper surfaces; reserve domain and semantic-state accents for orientation and meaning.

### 5.3 Footer

- Compact MedNexus identity and enterprise medical intelligence description.
- Product navigation and concise status/governance links where real destinations exist.
- No cinematic closing treatment or large repeated product claim.

### 5.4 Mobile navigation

- Replace desktop links with one labeled menu control.
- Preserve access to `/app`, `/understanding`, and `/privacy`.
- Show capability status next to unavailable destinations.
- Maintain 44px minimum targets, visible focus, Escape-to-close behavior, and focus return.

## 6. Landing Page blueprint (`/app`)

### Section 1 — Hero

- Minimal Oak composition with Mona Sans, MedNexus as the primary identity, and “Clinical Intelligence Platform” as the positioning line.
- Core message: understand medical documents and imaging, protect sensitive clinical data, and transform evidence into structured intelligence.
- Radiology is the primary near-term emphasis; Public Health is the secondary strategic vertical.
- Maximum two CTAs: **Understand a Document** (`/understanding`) and **Protect Clinical Data** (`/privacy`).
- The current hero video is not a structural requirement. Use the verified EdgeCase hero spacing rhythm and strong type-to-copy contrast without copying its illustration or product composition.

### Section 2 — Two flagship domains

1. **Radiology Intelligence** — first and visually primary. Clearly distinguish implemented Radiology UNDERSTAND capabilities from future image intelligence, extraction, and concordance.
2. **Public Health Intelligence** — second. Describe the active strategic track without implying production completion or a live workspace where none exists.

Use the verified supporting teal for Radiology and the compatible MedNexus Public Health green extension. Both remain recognizably part of the same Oak/Mona system.

### Section 3 — MEDNEXUS Seven

Present the complete public journey in order:

`UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE → ANALYZE → VISUALIZE → INDICATORS`

Use a compact horizontal sequence that reflows vertically on small screens. Show current availability explicitly: UNDERSTAND and PROTECT are current capabilities; subsequent stages must retain accurate status. Do not use seven unrelated colors or the existing cinematic scroll-stage treatment.

On mobile, use the screenshot-validated single-column rhythm and clear section separation rather than compressing the seven stages into unreadable horizontal tiles.

### Section 4 — Multi-Engine Intelligence

Lead with: **“Models generate evidence. MedNexus determines authority.”**

Represent four contributor groups without implying equivalence or integration:

- MedNexus Native — authoritative orchestration and decision ownership.
- External Foundation Models — candidate evidence, subject to adapters and governance.
- Specialized Imaging Engines — future candidate contributors.
- Future Medical AI Engines — research/adapter candidates.

MedGemma and MedUAG, if named, must be labeled planned/candidate and watch/benchmark respectively, never integrated or live.

### Section 5 — Governed Clinical Intelligence

Explain in broad-audience language that MedNexus preserves privacy, source traceability, grounding, validation, abstention, human review, and final authority. Avoid internal pipeline jargon as the primary message.

### Section 6 — From Reports to Intelligence

Show the future value chain without claiming full implementation:

`Clinical Evidence → Structured Clinical Data → ANALYZE → VISUALIZE → INDICATORS`

Emphasize that downstream interpretation and product value remain MedNexus-owned rather than being delegated to a foundation model.

### Section 7 — Closing and footer

Use one concise closing statement and one relevant live dark-ink CTA on a warm Oak/paper surface. Follow with the shared compact footer.

## 7. Radiology UNDERSTAND blueprint (`/understanding`)

The page becomes a focused clinical workspace while retaining all current contracts.

Use a warm Oak application background, Mona Sans, dark-ink typography, restrained Radiology teal, generous whitespace, minimal shadow, and clean paper-like document surfaces. This is a clinical workspace adaptation of the verified reference system, not a marketing-card page.

### Input state

- Compact page header with UNDERSTAND purpose and current support boundaries.
- Accessible Paste Text and Upload Document tabs.
- Clear accepted formats and no-OCR limitation.
- One primary Analyze action and one shared status/error region.

### Result state hierarchy

#### A. Document Identity

Display immediately, in this order:

1. Domain
2. Canonical subdomain/modality
3. Human-readable document type
4. Language
5. Confidence and confidence band

Use human labels in the primary surface. Raw enums remain available only in Technical Details. UNKNOWN must remain a valid abstention state rather than being visually treated as a processing failure.

Use the strongest workspace type scale here, but keep it materially below the landing hero maximum. Domain and modality should remain identifiable without forcing the user to scan decorative panels.

#### B. What MedNexus Understood

Show only bounded document-level context supported by the authoritative `MedNexusDocumentContext`, such as performed examination, authoritative anatomy, contrast context, and document nature. Do not display field-level clinical facts or turn UNDERSTAND into EXTRACT.

Use nested Oak surfaces and one-pixel borders rather than heavy elevation. Radiology teal may orient this section but must not recolor every component.

#### C. Document Structure

Present semantic regions in source order with readable labels. Offsets and canonical identifiers belong in Technical Details.

Use document-paper surfaces and stable vertical rhythm suitable for long section labels and bilingual content.

#### D. Why MedNexus Recognized It

Translate backend-provided evidence messages into a readable list. Do not create clinical inferences, evidence weights, or explanations in the browser.

#### E. Processing Readiness

Show explicit backend-supported states such as Ready for PROTECT, Ready for EXTRACT, or Review required. Journey continuation must use the backend-provided URL and remain unavailable when the document requires review or is not eligible.

#### F. Warnings

Warnings should be visible, concise, non-alarmist, and associated with the relevant result or action. Severity cannot be communicated by color alone.

#### G. Technical Details

Collapsed by default. Preserve canonical context, compatibility payload, semantic offsets, evidence categories and weights, concept/reference identifiers, raw matched signals, and routing metadata.

## 8. PROTECT blueprint (`/privacy`)

The future page is a task-focused clinical workspace, not a long marketing demonstration. The current raster hotspot hero is excluded from the future structure.

Use the same Oak/Mona product shell as `/app` and `/understanding`. Original and protected documents should read as clean clinical paper surfaces against the warm application background. Avoid decorative motion while medical text is being read.

### A. Compact page header

- Title: Clinical Privacy / PROTECT.
- One short sentence explaining purpose-based protection.
- Shared navigation and accurate support/format boundary.

### B. Policy selection

Present the four current canonical policies as a concise selectable group:

- Clinical
- Research
- Analytics / Public Health
- Strict Privacy

Preserve backend IDs and default Clinical selection. Explain the use case and supported action set without invented privacy/utility scores.

### C. Document workspace

- Standalone mode: Paste Text or Upload Document.
- Journey mode: retained UNDERSTAND document, filename, context availability, workflow/status, and “Use another document instead.”
- Only one source is visible and active at a time.
- Do not process automatically after source or policy selection.

### D. Privacy result summary

Show only backend-supported values: protection status, selected policy, processing time, warning/review state, source type, and MedNexus output ownership. Do not invent entity counts, risk scores, or policy-decision summaries.

### E. Side-by-side document view

- Desktop/laptop: Original Document and Protected Document in two columns where width permits.
- Tablet/mobile: stacked with unambiguous labels.
- Preserve the protected output byte-for-byte as delivered for display.
- Retain progressive reveal, reduced-motion behavior, and Show full result.
- Use minimal or no shadow around document panes; distinguish them through verified paper surfaces, restrained borders, and clear labels.

### F. Result details

Provide the current privacy report, warnings, copy action, and supported source metadata. Do not add download or entity-level actions until supported by real behavior and contract.

### G. Technical Details

Collapsed by default. Preserve raw metadata for technical users without making it part of the primary result.

## 9. Responsive behavior

The verified EdgeCase homepage uses one primary width breakpoint at `860px`, where navigation and multi-column content simplify to a mobile composition. MedNexus retains `860px` as a reference breakpoint but may introduce additional breakpoints because clinical document comparison and evidence layouts have materially different readability needs.

| Range | Intended composition |
|---|---|
| Large desktop, `≥1440px` | Full shared shell; multi-column hero/domain layouts; workspace up to `1440px`; side-by-side documents |
| Normal laptop, `1024–1439px` | Reduced margins; two-column result layouts only where text remains readable; no decorative sidebars that compress report text |
| Tablet, `768–1023px` | Simplified navigation; cards reflow to one or two columns; identity remains above context; document comparison may stack |
| Mobile, `<768px` | Single-column flow; menu navigation; full-width controls; stacked documents; technical detail last |

Additional rules:

- Clinical report panes should not exceed approximately 78 characters per line.
- Avoid horizontal scrolling except inside deliberately technical code/JSON regions.
- Sticky actions must not cover report text, warnings, or browser controls.
- Confidence, review state, and active policy must remain visible without relying on hover.
- Long filenames and bilingual labels must wrap safely.
- Touch targets must be at least 44px.

## 10. Accessibility

- Target WCAG 2.2 AA for contrast and interaction.
- Use one semantic H1 per page and preserve a logical heading outline.
- Provide a skip-to-content link in the shared shell.
- Every input has a persistent label and associated help/error text.
- Tabs use correct tab roles, keyboard arrow navigation, selected state, and focus management.
- Policy selection is keyboard operable and exposes its selected state programmatically.
- Focus indicators use at least a 2px visible outline with adequate contrast and offset.
- Processing and error messages use appropriate live regions without excessive announcements.
- Status never depends on color alone.
- Collapsed technical details remain operable through a semantic disclosure control.
- Progressive result reveal must honor `prefers-reduced-motion` and expose the complete authoritative result immediately in reduced-motion mode.
- Text zoom to 200% and browser reflow must not lose functionality or obscure content.
- Bilingual and right-to-left document content must preserve source direction where detected or explicitly supplied; interface chrome remains stable.

## 11. Motion principles

Motion should explain state change, not create atmosphere.

### 11.1 Verified EdgeCase reference motion

| Reference behavior | Verified value |
|---|---|
| Primary easing | `cubic-bezier(0.22, 1, 0.36, 1)` |
| Section reveal | `900ms`; opacity `0`; `translateY(28px)`; blur `8px` |
| Navigation transition | `400ms` |
| Navigation blur after scroll | `16px` |
| Button hover | `brightness(1.06)` |
| Button active | `scale(0.98)` |
| Reveal threshold | `0.16` |
| Reveal root margin | `0px 0px -8% 0px` |

### 11.2 MedNexus adaptation

| Future token | Proposed value | Use |
|---|---:|---|
| `--mnx-motion-fast` | `160ms` | Hover, focus, tab selection |
| `--mnx-motion-standard` | `220ms` | Workspace state transitions |
| `--mnx-motion-landing-reveal` | Up to `900ms` | Restrained landing-only reveal where approved |
| `--mnx-motion-ease` | `cubic-bezier(0.22, 1, 0.36, 1)` | Shared reference easing |

- The Landing Page may use restrained reveal motion derived from the verified reference.
- UNDERSTAND and PROTECT should use substantially less decorative motion and shorter state transitions.
- Clinical results must prioritize stability and readability.
- No result may require animation to become available or understandable.
- Prefer opacity and small positional changes; avoid glow pulses, continuous orbiting, cinematic parallax, and scroll-gated content.
- Content must remain readable when motion is disabled.
- Progressive protected-output reveal remains a bounded presentation of completed output, not backend streaming.
- Hover motion must have equivalent keyboard-focus feedback.

## 12. Current versus future UI representation rules

Use explicit status language:

- **Available now** — implemented route and verified behavior.
- **Reference implementation** — implemented within a bounded domain or POC scope.
- **In development** — active work without an accepted complete capability.
- **Planned** — architecture/product intention, not runtime functionality.
- **Candidate engine** — potential evidence provider, not integrated authority.
- **Research watch** — monitored technology with no product integration claim.

Representation requirements:

- MEDNEXUS Seven remains the full target journey; the UI must not imply all seven stages are live.
- UNDERSTAND and PROTECT may be presented as current capabilities according to their accepted boundaries.
- Radiology is the first reference domain and near-term primary focus.
- Public Health is the secondary strategic priority and active parallel domain work, not production-complete.
- MedGemma remains a planned candidate engine.
- MedUAG remains watch/benchmark/future-adapter material.
- Evidence Fusion & Arbitration and Image–Report Concordance remain future MedNexus-owned capabilities.
- PROTECT and STANDARDIZE remain MedNexus-owned authority boundaries.

## 13. Technical preservation boundaries

The visual redesign must preserve:

- `/app`, `/understanding`, and `/privacy` routes.
- Existing request and response contracts.
- Text, file, and retained-journey processing modes.
- Existing supported-file validation and no-OCR behavior.
- `MedNexusDocumentContext` authority and compatibility handling.
- UNKNOWN, warnings, abstention, confidence, review, and readiness semantics.
- Backend-provided recognition explanations and semantic regions.
- Backend-provided journey continuation and one-active-source behavior.
- Canonical privacy policy IDs and the default Clinical profile.
- Original/protected output fidelity and MedNexus-owned output authority.
- Progressive reveal, Show full result, copy behavior, and reduced-motion path.
- Technical metadata and progressive disclosure.
- Existing error conventions and mobile behavior.

No clinical recognition, evidence qualification, confidence calculation, privacy decision, policy mapping, or routing authority may move into the browser.

### Future `privacy.html` refactoring boundary

The active Privacy page is currently a large monolithic file containing embedded CSS, JavaScript, and raster assets. A later implementation may separate presentation code only when all of these conditions are met:

- API behavior remains unchanged.
- Canonical policy IDs remain unchanged.
- Journey behavior remains unchanged.
- Authoritative protected output remains unchanged.
- Existing functional tests are preserved; changes to tests are limited to deliberate visual-structure updates.
- No clinical or policy decision logic is introduced into the browser.
- The inactive/legacy role of `privacy-styles.css` is resolved deliberately rather than assumed.
- Raster-hotspot interaction is replaced with accessible semantic controls before the raster is removed.

## 14. Implementation sequence

No implementation is authorized by this blueprint. If approved, use this order:

1. **UX-FOUNDATION** — introduce shared visual tokens and a reusable shell; establish accessible primitives without changing page contracts.
2. **LANDING** — redesign `/app`; preserve route truth and capability status.
3. **UNDERSTAND** — redesign `/understanding`; retain authoritative context interpretation and journey behavior.
4. **PROTECT** — redesign `/privacy`; replace the raster-hotspot presentation and separate presentation code within the preservation boundary.
5. **POLISH** — verify responsive behavior, keyboard/accessibility behavior, reduced motion, visual consistency, and full regression.

Each stage requires focused browser review and relevant automated tests before advancing. Do not combine clinical or backend changes with visual implementation batches.

## 15. Acceptance criteria

### Design review

- The system reads as light, clinical, premium, calm, spacious, and high-trust.
- Mona Sans is the principal MedNexus visual, interface, and clinical-document font, sourced later through an authoritative licensed distribution.
- Oak/light is the primary visual identity; the Ink palette remains reference or optional future-theme material.
- Major black, dark, cinematic, glow, and neon surfaces are removed from the near-term redesign.
- Radiology is clearly primary and Public Health clearly secondary without fragmenting the brand.
- MEDNEXUS Seven remains intact and is presented as one coherent journey rather than seven visual identities.
- Implemented, planned, candidate, and research-watch capabilities are visually distinguishable.
- Clinical workspaces prioritize readability and stable results over animation.
- No page depends on cinematic video or gaming/cyber-security cues.
- One shared shell and token language can serve all three routes.
- A broad-audience user can identify the page purpose and primary action within approximately five seconds.
- Verified EdgeCase reference values and MedNexus adaptation decisions remain explicitly distinguishable.
- No EdgeCase branding, assets, content, illustration, logo, or font binary is copied.

### Product truth

- MEDNEXUS Seven remains unchanged and future stages are labeled accurately.
- Current, planned, candidate, and research-watch capabilities cannot be confused.
- External engines are presented as candidate evidence contributors; MedNexus authority remains explicit.
- UNDERSTAND does not display EXTRACT-level claims.
- PROTECT does not display unsupported entity counts, risk scores, or fabricated policy decisions.

### Functional preservation

- Existing routes, APIs, canonical policy IDs, and response contracts are unchanged.
- No clinical or backend behavior changes as part of visual implementation.
- Text, upload, and journey handoff flows remain functional.
- UNKNOWN, review, warning, and error states remain accessible.
- Original and protected document output is unchanged.
- Technical details remain available and collapsed by default.
- No clinical decision logic moves into client code.

### Responsive and accessibility review

- Large desktop, laptop, tablet, and mobile compositions are reviewed independently.
- Medical text remains comfortably readable and does not become excessively wide or compressed.
- Keyboard navigation, focus order, focus visibility, status announcements, contrast, 200% zoom, and reduced motion pass review.
- Controls remain at least 44px and do not depend on hover or color alone.

### Engineering gate for later implementation

- Focused frontend/API-contract tests pass after each implementation stage.
- The complete regression suite passes before an accepted UI checkpoint.
- Only intentional visual/presentation files and deliberately updated visual-structure tests enter each review.
- Documentation is synchronized after an accepted implementation checkpoint, not during this proposed-design review.

## 16. Review decision

Human design review accepted this document as **MedNexus UI/UX Design Blueprint v1.0** on 2026-09-08. Acceptance establishes the design direction and implementation guardrails; it does not implement or authorize production frontend, presentation refactor, route, API, clinical, dependency, or font changes. The next step is a visual Landing Page prototype/mockup for review before production frontend implementation.
