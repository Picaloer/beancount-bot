# Beancount Bot

## What This Is

Beancount Bot is an AI-powered personal finance management system. It ingests bill exports from WeChat Pay, Alipay, bank cards (CMB, ICBC, CEB, etc.) and other payment channels, automatically classifies transactions using a rule+LLM pipeline, and generates Beancount double-entry journal entries. It provides monthly spend summaries and AI insights — without requiring accounting expertise from the user.

## Core Value

A user can import all their bills from multiple channels and get an accurate, deduplicated picture of where their money actually went this month.

## Requirements

### Validated

- ✓ WeChat Pay CSV/XLSX bill import — existing
- ✓ Alipay CSV bill import (GBK/GB18030 encoding) — existing
- ✓ CMB (招商银行) PDF bill import with OCR fallback — existing
- ✓ Rule + LLM (Claude/DeepSeek) 4-stage classification pipeline — existing
- ✓ Beancount double-entry entry generation — existing
- ✓ Monthly spend report with AI insights — existing
- ✓ Merchant ranking report — existing
- ✓ Manual transaction reclassification — existing
- ✓ Async import pipeline (Celery + Redis) — existing
- ✓ Duplicate transaction review during import — existing

### Active

- [ ] Cross-channel duplicate detection: same spend appearing in both a payment channel (WeChat, Alipay) and the funding bank card produces two records — AI should identify suspected duplicates and present them for user confirmation during the import flow
- [ ] Internal transfer detection: bank card → WeChat/Alipay wallet top-ups should be auto-classified as "资金转移" (internal transfer) and excluded from spend statistics
- [ ] Flow-based display: do not show "current balance" on any page; the system has no opening balance data for first-time users — only show income/expense flows for the imported period

### Out of Scope

- Current account balance display — no opening balance data available for first-time users; would produce negative net worth; by design excluded
- Full beancount balance-sheet reconciliation — the app is cash-flow tracking, not full bookkeeping
- Real-time bank data sync — only CSV/PDF file imports

## Context

- **Single-user MVP**: `DEFAULT_USER_ID=0000000000000000001`; no auth system
- **Multi-channel reality**: users typically import 3-5 sources per month (WeChat + Alipay + 1-2 bank cards); duplicates are structurally inevitable because downstream channel + upstream funding bank each record the same transaction
- **Wallet flow**: WeChat/Alipay balances can be topped up from bank cards; those top-up events in bank records are NOT expenses — they are internal transfers that must not double-count
- **No opening balance**: first-time users have no prior period snapshot; displaying net worth is misleading; the app should only report on what was imported
- **Classification pipeline**: 4-stage chain (user rules → system rules → LLM → fallback); duplicate detection is a new upstream stage before classification
- **Existing duplicate review**: there is already a `DuplicateReviewGroup` mechanism in the import flow for same-source duplicates; cross-channel detection is an extension of this concept

## Constraints

- **Tech stack**: Python 3.13 / FastAPI / SQLAlchemy / PostgreSQL / Celery + Redis (backend); Next.js 16 App Router / TypeScript / Tailwind CSS / SWR (frontend) — no new runtimes
- **Package managers**: `uv` (backend), `pnpm` (frontend)
- **LLM**: Claude (claude-haiku-4-5-20251001 default) or DeepSeek via OpenAI-compatible client
- **Deployment**: Docker Compose, single-node

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cross-channel dedup: AI identify + user confirm | False positives in auto-dedup are worse than missed duplicates; user trust requires transparency | — Pending |
| Wallet top-ups: auto-classify as internal transfer | Users never intend these as expenses; heuristic detection (source + counterparty patterns) is reliable enough | — Pending |
| No balance display | No opening balance data; showing negative net worth damages trust; flow-only view is honest | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-13 after initialization*
