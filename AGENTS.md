# AGENTS.md — Instructions for Coding Agents

This file governs how any AI coding agent (Claude Code, Cursor, Devin, Codex, etc.) should work in this repository. Read this before making changes. If something here conflicts with a prompt you were given, treat this file as the source of truth for project-wide conventions, and ask before deviating.

Full product context lives in `/docs/PRD.md`. Read it before touching architecture-level decisions — several choices here (e.g. sandbox provider, hint gating) were made deliberately after two rounds of revision and should not be "improved" without discussion.

---

## 1. Project Summary

AlgoMentor AI is a DSA learning platform: online coding judge + AI mentor that teaches via a gated, execution-trace-aware hint ladder, plus a decay-based mastery model that drives adaptive, spaced-repetition problem recommendations.

**Phase 0 scope (current):** validate the core loop — solve, get gated hints, get a mastery score — with a curated ~75-problem bank. Do not build Phase 2/3 features (B2B cohort dashboards, cross-platform import, fine-tuned models) unless explicitly asked.

---

## 2. Tech Stack (do not swap without discussion)

| Layer | Choice |
|---|---|
| Frontend | Next.js (React) + Tailwind + shadcn/ui |
| Backend | FastAPI (Python) |
| Primary DB | PostgreSQL |
| Cache/queue state | Redis |
| Vector store | pgvector (Postgres extension) — not a separate vector DB at this stage |
| Code execution | Judge0 (self-hosted) or Piston/E2B via an adapter interface — **never a custom Firecracker/microVM orchestrator at this phase** |
| Auth | Clerk (or equivalent) |
| AI layer | Cheap hosted model for hint levels 1–2, frontier model for levels 3–4 and code review — see `/docs/PRD.md` Section 11 |

If a task seems to require a different tool than what's listed, flag it and ask rather than silently substituting.

---

## 3. Hard Constraints (guardrails, not suggestions)

These encode decisions made after real product/architecture review. Do not "optimize" past them without an explicit instruction to do so.

1. **Never build custom sandbox/microVM infrastructure.** All code execution goes through the sandbox adapter (`/backend/sandbox_adapter/`), which wraps Judge0/Piston/E2B behind a single interface. This exists so the underlying provider can be swapped without touching call sites.
2. **Never let the AI mentor receive a full reference solution when responding at hint level 1 or 2.** The orchestration layer must not pass solution code into LLM context below level 3. This is enforced in code (context-building step), not by prompt instructions alone — do not "simplify" this by relying on a system prompt to withhold the answer.
3. **Hint responses at levels 1–2 must pass through the output filter** (`/backend/mentor/output_filter.py`) before being returned to the client. Do not add a code path that returns raw LLM output directly to the user at these levels.
4. **Interview/Contest mode must not have a code path to any hint endpoint.** This is an API-level separation, not a UI toggle — do not implement it by just hiding a button.
5. **Every new problem added to the bank must ship with a hidden test suite generated via the differential-testing pipeline** (`/backend/problem_ingestion/`) — brute-force reference + optimal reference + fuzzed inputs. Do not hand-write a "few obvious" test cases and call it done.
6. **Spaced repetition must serve isomorphic variants, not the original problem.** When adding recommendation logic, check `/backend/mastery/variants.py` for the variant map before assuming a topic has only one associated problem.
7. **All LLM calls must go through the tiered router** (`/backend/mentor/model_router.py`), which decides small-model vs. frontier-model per hint level. Do not call a provider SDK directly from a new feature.

---

## 4. Directory Structure

```
algomentor-ai/
├── frontend/                 # Next.js app
├── backend/
│   ├── api/                  # FastAPI routes
│   ├── sandbox_adapter/      # Judge0/Piston/E2B abstraction — see constraint #1
│   ├── mentor/               # Hint orchestration, output_filter.py, model_router.py
│   ├── mastery/              # Decay model, confidence scoring, variants.py
│   ├── problem_ingestion/    # Differential/fuzz test generation pipeline
│   └── recommendation/       # Adaptive scheduling logic
├── docs/
│   └── PRD.md                # Full product spec — read before architecture changes
├── infra/                    # Deployment configs
└── tests/
```

---

## 5. Coding Conventions

- **Python (backend):** type hints required on all function signatures; format with `ruff format`; lint with `ruff check` before considering a task done.
- **TypeScript (frontend):** strict mode on; no `any` without a comment explaining why.
- **Commits:** conventional commits style (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- **Tests:** any change to `mentor/`, `mastery/`, or `sandbox_adapter/` requires a corresponding test update — these are the modules with the guardrails in Section 3.

---

## 6. Before Marking a Task Complete

Run through this checklist:

1. Does this change touch a hard constraint in Section 3? If yes, does it still satisfy that constraint?
2. Do relevant tests pass (`pytest` for backend, `npm test` for frontend)?
3. Is lint clean (`ruff check .`, `npm run lint`)?
4. If this changes an architectural decision from `/docs/PRD.md`, has that been called out explicitly in the PR description rather than silently changed?
5. If a new LLM call was added, does it go through `model_router.py`, and is it assigned the correct hint-level tier?

---

## 7. What Not to Do

- Don't reach for a bigger/frontier model "to be safe" on hint levels 1–2 — this breaks the unit economics the pricing model depends on (`/docs/PRD.md` Section 11).
- Don't add a "quick" endpoint that bypasses the hint gating for testing convenience and forget to remove it.
- Don't expand the problem bank casually — every problem needs to go through the test-generation pipeline first.
- Don't assume test coverage on `sandbox_adapter/` is optional — this is the most security-sensitive module in the repo (executes untrusted user code).
