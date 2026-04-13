# Roadmap: Beancount Bot — Skill Framework, Dedup & Transfer Detection

## Overview

This milestone extends the existing import, classification, and reporting system so users can import overlapping records from multiple channels and still get an accurate cash-flow view. The delivery sequence starts by introducing a reusable skill framework, then adds cross-channel duplicate detection before classification, then adds internal transfer detection on the deduplicated transaction set, and finally corrects the UI so it shows flow-based statistics instead of misleading balance figures. By the end of the roadmap, the import pipeline becomes: Parse → Cross-Channel Dedup → Duplicate Review → Internal Transfer Detection → Classification → Beancount.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Skill Directory Scaffold** - Establish `backend/skills/` structure and skill packaging rules
- [ ] **Phase 2: Skill Loader** - Implement `load_skill()` so skills can be discovered from disk without hardcoding
- [ ] **Phase 3: Skill Result Contract** - Standardize every skill response as structured output plus reasoning and confidence
- [ ] **Phase 4: Cross-Channel Dedup Skill** - Build the `cross-channel-dedup` skill with weekly batching and concurrent LLM comparison
- [ ] **Phase 5: Dedup Pipeline Gate** - Run cross-channel dedup before classification and produce the clean transaction set for later stages
- [ ] **Phase 6: Cross-Channel Duplicate Review UI** - Let users review suspected duplicate groups and decide what to keep
- [ ] **Phase 7: Internal Transfer Skill** - Build the `internal-transfer-detection` skill on deduplicated transactions
- [ ] **Phase 8: Internal Transfer Pipeline Integration** - Run transfer detection before classification and exclude those records from income/expense stats
- [ ] **Phase 9: Flow-Based Display Corrections** - Remove balance displays and show income/expense/internal-transfer views everywhere

## Phase Details

### Phase 1: Skill Directory Scaffold
**Goal**: Skills live in a dedicated `backend/skills/` directory with a clear on-disk structure that is independent from application business logic
**Depends on**: Nothing (first phase)
**Requirements**: SKILL-01
**Success Criteria** (what must be TRUE):
  1. `backend/skills/` exists and contains skill subdirectories rather than embedding prompts inside application code
  2. Each skill directory contains a `SKILL.md` file describing the skill and at least one schema file defining its input or output shape
  3. A developer can add a new skill by creating a new subdirectory under `backend/skills/` without modifying existing feature code
  4. No existing import, classification, or report logic is required to know skill prompt text directly
**Plans**: 2 plans
Plans:
- [x] 01-01-PLAN.md — TDD test scaffold: create failing tests for SKILL-01 structural assertions (Wave 0)
- [x] 01-02-PLAN.md — Implementation: create backend/skills/ directory with README.md and cross-channel-dedup skill skeleton (Wave 1)

### Phase 2: Skill Loader
**Goal**: The system can dynamically load a named skill from disk and prepare it for execution without per-skill code branches
**Depends on**: Phase 1
**Requirements**: SKILL-02
**Success Criteria** (what must be TRUE):
  1. Calling `load_skill("cross-channel-dedup")` loads that skill from `backend/skills/` rather than from hardcoded Python definitions
  2. Adding a new skill directory does not require changing the loader implementation to make it discoverable
  3. Missing or malformed skills fail with a clear loader error that identifies the skill name and the missing file or schema
  4. A loaded skill can be invoked by application code using its declared schema instead of custom parsing logic
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md — TDD red phase: test scaffold, exception types, loader stub (Wave 0)
- [ ] 02-02-PLAN.md — Implementation: full load_skill(), SkillRunner, SkillResult (Wave 1)

### Phase 3: Skill Result Contract
**Goal**: All skill executions return the same result envelope so downstream workflows can consume skills consistently
**Depends on**: Phase 2
**Requirements**: SKILL-03
**Success Criteria** (what must be TRUE):
  1. Any successful skill call returns a result containing `structured_output`, `reasoning`, and `confidence`
  2. Downstream callers can read those three fields without checking which specific skill produced them
  3. Invalid model output is rejected as a skill-contract failure instead of being accepted as partial or ambiguous data
  4. Dedup and transfer workflows can preserve reasoning and confidence for later review or debugging
**Plans**: TBD

### Phase 4: Cross-Channel Dedup Skill
**Goal**: The `cross-channel-dedup` skill can compare already-imported transactions against the current upload and identify suspected duplicate pairs
**Depends on**: Phase 3
**Requirements**: DEDUP-01, DEDUP-02, DEDUP-03
**Success Criteria** (what must be TRUE):
  1. The skill accepts two inputs — previously imported transactions and currently uploading transactions — and groups them into 7-day windows before comparison
  2. Multiple weekly windows are analyzed concurrently instead of one-by-one
  3. The skill identifies suspected duplicates across payment-channel vs funding-bank records, bank-to-bank transfers, and same-channel overlaps
  4. Each suspected duplicate pair includes `similarity_score`, `reasoning`, and a suggested record to keep
  5. The skill can run in isolation in tests without requiring a full import job to execute
**Plans**: TBD

### Phase 5: Dedup Pipeline Gate
**Goal**: Cross-channel dedup becomes a required stage before classification, and only the deduplicated transaction set can continue downstream
**Depends on**: Phase 4
**Requirements**: DEDUP-05
**Success Criteria** (what must be TRUE):
  1. During import, cross-channel dedup runs after parsing and before the classification pipeline starts
  2. If no suspected duplicates are found, the import continues directly into classification with the deduplicated transaction list
  3. If suspected duplicates are found, the import pauses in duplicate-review state instead of classifying unresolved records
  4. Transactions excluded by the dedup decision path are not available to later classification or Beancount generation steps
**Plans**: TBD

### Phase 6: Cross-Channel Duplicate Review UI
**Goal**: Users can review suspected cross-channel duplicates inside the import flow and explicitly choose what should remain in the final ledger
**Depends on**: Phase 5
**Requirements**: DEDUP-04
**Success Criteria** (what must be TRUE):
  1. The import detail page shows cross-channel duplicate groups during the review step
  2. Each review group displays both candidate records with enough context for a human to decide, including source, amount, date, and merchant or description
  3. User can resolve each group with keep-one, keep-all, or skip-style actions supported by the flow
  4. After all groups are resolved, the import resumes automatically and proceeds to the next pipeline stage
  5. Records the user excludes from a duplicate group do not appear in transaction statistics or later transaction lists
**Plans**: TBD
**UI hint**: yes

### Phase 7: Internal Transfer Skill
**Goal**: The `internal-transfer-detection` skill can scan a deduplicated transaction set and identify internal fund movements with transfer-type labels
**Depends on**: Phase 6
**Requirements**: TRNF-01, TRNF-02, TRNF-03
**Success Criteria** (what must be TRUE):
  1. The skill accepts one deduplicated transaction list and groups it into 7-day windows before LLM analysis
  2. Multiple weekly windows are analyzed concurrently
  3. The skill recognizes bank-to-wallet recharge, bank-to-bank transfer, wallet withdrawal to bank, and investment purchase scenarios
  4. Each identified internal-transfer record includes a `transfer_type` value and `reasoning`
  5. The skill can run in isolation in tests without requiring a full import job to execute
**Plans**: TBD

### Phase 8: Internal Transfer Pipeline Integration
**Goal**: Internal transfer detection runs after dedup and before classification, tagging those records as "内部资金流动" and removing them from income/expense totals
**Depends on**: Phase 7
**Requirements**: TRNF-04, TRNF-05
**Success Criteria** (what must be TRUE):
  1. The import pipeline runs internal transfer detection only after dedup has produced the clean transaction set
  2. Transactions identified as internal transfers are assigned the new first-level category `内部资金流动`
  3. Internal transfer records do not enter normal expense or income classification flows
  4. Expense totals and income totals exclude internal transfer amounts in summary and report calculations
  5. The category API and stored transaction data both reflect `内部资金流动` as a valid category users can see later
**Plans**: TBD

### Phase 9: Flow-Based Display Corrections
**Goal**: The product shows only honest flow-based metrics: no current balance or total-assets display, plus clear income, expense, and internal-transfer summaries
**Depends on**: Phase 8
**Requirements**: DISP-01, DISP-02, DISP-03
**Success Criteria** (what must be TRUE):
  1. No page in the application displays "当前余额", "总资产", or any balance-style metric
  2. The dashboard and monthly report pages each show three summary cards: total income, total expense, and total internal transfer amount for the selected period
  3. Internal transfer amounts are not merged into either income or expense cards
  4. The transaction list includes an `内部资金流动` filter alongside the existing income and expense filtering choices
  5. When the internal-transfer filter is selected, the transaction list shows only internal transfer records
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skill Directory Scaffold | 0/TBD | Not started | - |
| 2. Skill Loader | 0/TBD | Not started | - |
| 3. Skill Result Contract | 0/TBD | Not started | - |
| 4. Cross-Channel Dedup Skill | 0/TBD | Not started | - |
| 5. Dedup Pipeline Gate | 0/TBD | Not started | - |
| 6. Cross-Channel Duplicate Review UI | 0/TBD | Not started | - |
| 7. Internal Transfer Skill | 0/TBD | Not started | - |
| 8. Internal Transfer Pipeline Integration | 0/TBD | Not started | - |
| 9. Flow-Based Display Corrections | 0/TBD | Not started | - |
