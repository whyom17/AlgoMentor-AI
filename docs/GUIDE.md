# AlgoMentor AI — Build-It-Yourself Guide

**Purpose of this document:** this is not a spec you hand to an AI to implement. It's a sequence
you follow yourself. At each step you read the "what" and "why" here in English, then go write
the code in your editor. Before moving to the next step, you answer the checkpoint questions —
if you can't answer them, you don't understand what you just built well enough to move on.

Keep `README.md`, `AGENTS.md`, and `docs/PRD.md` open alongside this. This guide tells you *when*
to consult which section of those; it doesn't replace them.

---

## 0. How to use this guide

1. Do the milestones **in order**. Each one exists because the next one depends on it.
2. Before writing any code in a milestone, answer the "Before you code" questions — in writing,
   in a `notes/` folder in your repo, not just in your head. This is the part that actually builds
   understanding; skipping it is how you end up with code you can't explain in an interview.
3. After finishing a milestone, answer the "Explain it back" questions. If you're stuck, that's a
   signal to re-read the relevant PRD section, not to move on.
4. Each milestone maps to one git branch. Don't let branches balloon to cover two milestones.
5. Nothing here contains implementation code. If you get stuck on *how*, that's normal — go look
   up the specific technique (e.g. "FastAPI dependency injection", "Postgres check constraints"),
   but come back and write it in your own words in your notes before pasting anything into your repo.

---

## 1. Environment & repo scaffolding

**Goal:** a repo that runs, does nothing interesting yet, and is structured the way `AGENTS.md`
describes.

**Before you code:**
- Why does the README separate `sandbox_adapter/` from `mentor/` from `mastery/` instead of one
  `backend/app/` folder? (Hint: re-read AGENTS.md Section 3 — each of those folders corresponds to
  a *guardrail*, not just a topic.)
- What's the actual difference between Judge0, Piston, and E2B that made the PRD choose "adapter
  interface, pick one, stay swappable" instead of committing to one? Write one sentence per option.

**Do this:**
- `git init`, create the folder structure from the README's tree (empty folders with `.gitkeep` or
  a stub `__init__.py` are fine for now).
- Set up Python venv + FastAPI "hello world" endpoint, Next.js "hello world" page, Postgres running
  locally (with `pgvector` extension enabled — check it with `CREATE EXTENSION pgvector;`), Redis
  running locally.
- Write `.env.example` for both frontend and backend — even before you know every var you'll need,
  start the file. You'll append to it as you go.
- Set up `ruff` (format + lint) and a pre-commit hook that runs it. Set up TypeScript strict mode.

**Git:**
```
main            (protected, always deployable)
  └── dev       (integration branch, everything merges here first)
        └── setup/scaffolding   ← you are here
```
Merge `setup/scaffolding` → `dev` → `main` once both hello-worlds run and lint is clean.

**Explain it back:**
- If a teammate cloned this repo right now, what's the exact sequence of commands that gets them
  to a running dev environment? Is that sequence *written down* anywhere, or only in your head?

---

## 2. Database schema — before any feature code

**Goal:** the Postgres schema for users, problems, attempts, and mastery scores. No API yet — this
is pure data modeling.

**Why schema before endpoints:** every other milestone reads or writes this schema. Designing it
under the pressure of "I need an endpoint that works" produces schemas that don't survive contact
with the mastery model in Milestone 6. Design it now, deliberately.

**Before you code:**
- List every entity PRD Section 9 implies you need to track per user, per topic: a raw score, a
  recency weight, a sample-size/confidence signal, a "seen vs owned" distinction. What are the
  actual columns? What's the primary key of a "mastery record" — is it `(user_id, topic)`, or does
  a topic have sub-variants that also need tracking (re-read Section 9's "isomorphic variants" note
  — does that push you toward tracking mastery per *pattern*, with problems just being instances)?
- An "attempt" needs to know: which problem, which user, pass/fail, how many hints used at which
  levels, mistake-taxonomy category (Section 9 lists five: off-by-one, wrong pattern, wrong
  complexity, edge case, syntax). Sketch this table's columns on paper before touching SQL.
- Where does `pgvector` actually get used? (Section 14's architecture diagram tells you — it's not
  storing your relational data, it's one specific lookup.) If you can't say what that lookup is,
  re-read Section 11's Level 2 hint description.

**Do this:**
- Write the schema as SQL migrations (use Alembic if you want migration history, or raw SQL files
  numbered in order — pick one and be consistent).
- Add foreign keys and check constraints that encode your actual invariants (e.g. can a mastery
  score be negative? Can it exceed 1.0? Put that constraint in the DB, not just in application code).
- Seed script with 2-3 fake users and 1 fake problem, enough to sanity-check the schema by hand in
  `psql`.

**Git:** branch `feature/db-schema` off `dev`.

**Explain it back:**
- Draw (on paper or in a `.md` file) the relationship between `problems`, `problem_variants` (if
  you added that table), `attempts`, and `mastery_scores`. Can you trace, from a single failed
  attempt row, exactly which mastery score it should update and how?
- What happens to mastery data if a problem is later replaced with a corrected version? Did your
  schema make that an easy case or a painful one? (You don't have to fix it now — just know the
  answer.)

---

## 3. Sandbox adapter — the security-sensitive core

**Goal:** `backend/sandbox_adapter/` with a single interface (e.g. `run_code(code, language,
stdin, test_cases) -> ExecutionResult`) backed by Judge0 running in Docker locally.

**Why this is Milestone 3, not later:** almost everything else — hints, mastery, submissions —
consumes an `ExecutionResult`. If you build the shape of that result sloppily now, you'll be
retrofitting it under every other module later.

**Before you code:**
- AGENTS.md constraint #1 says "never build custom microVM infra" and "wraps Judge0/Piston/E2B
  behind a single interface... so the underlying provider can be swapped without touching call
  sites." Design the interface's function signature and return type *before* wiring up Judge0 —
  if you design it Judge0-shaped, you've failed the actual requirement. Ask yourself: would this
  same interface work unchanged if you swapped in E2B next month?
- What does an `ExecutionResult` need to carry for Milestone 5 (execution-trace hints) to work
  later? Re-read PRD Section 8's pipeline diagram — it needs more than "pass/fail," it needs
  variable state at the point of failure. Does Judge0 give you that natively, or do you need to
  think now about how you'll get it (e.g. instrumenting submitted code, or a debugger-style trace)?
  Write down your plan even if you don't implement trace extraction yet — the interface shape
  needs to leave room for it.
- What's your timeout and resource-limit strategy for untrusted code? What happens on infinite
  loops? (AGENTS.md calls this "the most security-sensitive module in the repo" — treat it that way.)

**Do this:**
- `docker compose up` a local Judge0 instance.
- Implement the adapter interface, one concrete `Judge0Adapter` implementation.
- Write tests that submit deliberately broken code (infinite loop, huge memory alloc, syntax error)
  and confirm the adapter degrades safely (times out, doesn't crash your API process).

**Git:** branch `feature/sandbox-adapter` off `dev`.

**Explain it back:**
- If you swapped Judge0 for Piston tomorrow, list every file you'd need to touch. If that list is
  more than "one new adapter class + one config line," your abstraction leaked.
- Walk through, out loud, what happens end-to-end when a user submits code that infinite-loops.

---

## 4. Problem ingestion pipeline

**Goal:** `backend/problem_ingestion/` — given a problem statement, a brute-force reference
solution, and an optimal reference solution, generate a hidden test suite via differential/fuzz
testing (PRD Section 10).

**Before you code:**
- Why is "write a few obvious test cases by hand" explicitly forbidden in both AGENTS.md and PRD
  Section 10? What specific failure mode does differential testing catch that hand-written cases
  don't? (Answer this in terms of the mastery model — Section 10 tells you exactly why weak test
  suites are dangerous *for that specific downstream system*, not just "testing is good practice.")
- Sketch the fuzz-input generation strategy for one concrete problem (e.g. Two Sum). What's your
  input space? How do you know when you've fuzzed "enough"?

**Do this:**
- Build the pipeline: brute force + optimal reference + fuzzer → hidden test case file per problem.
- Run it on 1 real problem end-to-end, manually inspect the generated cases.
- Only after that works, run it on a small batch (aim for the ~75-problem Blind-75-style core set
  from Phase 0 scope — but don't feel obligated to do all 75 before moving on to Milestone 5;
  10-15 is enough to unblock later milestones, expand the bank later).

**Git:** branch `feature/problem-ingestion` off `dev`.

**Explain it back:**
- For your one worked example, what specific asymmetry (if any) did the fuzzer find between brute
  force and optimal that you wouldn't have thought to test by hand?

---

## 5. Submission flow (judge integration end-to-end)

**Goal:** a user can submit code for a problem via the API, it runs through the sandbox adapter
against the hidden test suite, and a pass/fail attempt record lands in the DB.

**Before you code:**
- This is the first milestone that touches three modules at once (`api/`, `sandbox_adapter/`,
  `attempts` table). What's your plan for partial failure — e.g. the sandbox call succeeds but the
  DB write fails? Do you need a transaction boundary, a retry, or is "best effort, log and move on"
  acceptable at this stage? Decide deliberately, don't let it be accidental.

**Do this:**
- FastAPI route: submit → sandbox adapter → grade against hidden tests → write attempt row →
  return result to client.
- Minimal frontend: a code editor (even a plain `<textarea>` at this stage, polish later) + submit
  button + pass/fail display.

**Git:** branch `feature/submission-flow` off `dev`.

**Explain it back:**
- Trace one submission from button click to DB row, naming every function call in between. Where
  exactly does `ExecutionResult` (Milestone 3) get consumed?

---

## 6. Hint ladder — orchestration, gating, output filter, model router

**Goal:** `backend/mentor/` — this is the module with the most hard constraints in AGENTS.md
(Section 3, items 2, 3, 7). Build it carefully; this is the actual product differentiator.

**Before you code — this is the most important checkpoint in the whole guide:**
- Re-read AGENTS.md constraint #2 twice: *"Never let the AI mentor receive a full reference
  solution when responding at hint level 1 or 2... enforced in code (context-building step), not
  by prompt instructions alone."* Concretely: what function builds the LLM context for a given
  hint request? Where, structurally, does it decide whether to include solution code — and can you
  point to the exact `if hint_level >= 3` (or equivalent) that makes this a code-level gate rather
  than something you're trusting the prompt to respect?
- Constraint #3: the output filter (`output_filter.py`) runs *before* the client sees a level 1-2
  response. What is it actually filtering for? Sketch 3 example LLM outputs it should catch and
  block (e.g. one that leaks a variable name that gives away the algorithm).
- Constraint #7: the model router decides small-model vs. frontier-model per level. Sketch this as
  a simple table before coding: level → model tier → why.
- What does "explain-back check" mean for level 4 (PRD Section 8, gate 4)? What are you actually
  checking the user's explanation against, and what happens if they can't explain it back?

**Do this:**
- `model_router.py`: routes by hint level, does NOT let any other module call a provider SDK
  directly (AGENTS.md constraint #7 — this is a real thing to grep for later: search your repo for
  raw LLM SDK calls outside this file).
- Context-builder: takes an `ExecutionResult` (from Milestone 3) + hint level, builds the LLM
  prompt, structurally excludes solution code below level 3.
- `output_filter.py`: post-processes level 1-2 responses before they reach the client.
- Wire it into the submission flow: on failure, offer a hint; gate by level; log hint usage
  (feeds Milestone 7's mastery model).

**Git:** branch `feature/hint-ladder` off `dev`. Given how many constraints this touches, keep
commits small and write a test for each constraint (e.g. a test that asserts level-1 context
never contains the solution string).

**Explain it back:**
- Without looking at your code, describe out loud the exact code path that prevents a level-1
  hint from ever seeing the reference solution. If you have to go check the code to answer this,
  the design isn't in your head yet — sit with it a bit longer.
- What's the failure mode if `output_filter.py` has a bug and lets something through? How would
  you notice?

---

## 7. Mastery model — decay, confidence, "seen vs owned"

**Goal:** `backend/mastery/` — per-topic score, decay function, confidence bands, hint-adjusted
scoring.

**Before you code:**
- SM-2 (the spaced-repetition algorithm PRD Section 9 references) was designed for flashcards, not
  code problems. What has to change? Specifically: what's your analog of a flashcard "difficulty
  rating" for a DSA problem attempt?
- "Seen vs owned" — write your own precise definition. If a user solves a problem using a level-3
  hint, is that "owned"? What about level-1? Where's the line, and why there?
- Cold start: PRD says default to tag-frequency until 15-20 logged attempts. What does the
  confidence band formula actually look like at attempt #1 vs attempt #20? Sketch the curve shape
  you want (doesn't need to be exact yet).

**Do this:**
- Decay function + confidence scoring, driven by attempt events from Milestone 5-6.
- Hook hint usage (from Milestone 6's logging) into the score calculation.
- Basic dashboard endpoint returning per-topic scores.

**Git:** branch `feature/mastery-model` off `dev`.

**Explain it back:**
- Two users both "pass" the same problem — one cold, one after a level-4 walkthrough. Walk through
  how their resulting mastery scores differ and why that difference is the right one.

---

## 8. Recommendation engine — isomorphic variants

**Goal:** `backend/recommendation/`, backed by `backend/mastery/variants.py` (the variant map
AGENTS.md constraint #6 tells you to check before assuming one problem per topic).

**Before you code:**
- Pick one pattern (e.g. Monotonic Stack) and write out 2-3 variant problems yourself, the way PRD
  Section 9 does for that exact pattern. What makes them "the same invariant, different skin" and
  not just "vaguely related"? If you can't articulate the shared invariant precisely, you can't
  build the variant map correctly.

**Do this:**
- `variants.py`: maps pattern → list of problem IDs.
- Scheduler: given a user's mastery scores + decay, picks what to serve next — weak/decayed topics
  get a variant, not a repeat.

**Git:** branch `feature/recommendation` off `dev`.

**Explain it back:**
- For a user who's decayed on two topics simultaneously, what's your tie-breaking logic for which
  one to serve next? Is that a deliberate choice or an accident of iteration order?

---

## 9. Interview/Contest mode

**Goal:** a mode with hints disabled **at the API level**, per AGENTS.md constraint #4 — not a
hidden button.

**Before you code:**
- Constraint #4 explicitly warns against a UI-only toggle. Concretely: what does your API do right
  now if a request hits the hint endpoint during an active contest-mode session? Design that check
  to happen in middleware or a route guard that has no code path around it, not in a `disabled={...}`
  prop in the frontend.

**Do this:** implement the check, write a test that directly hits the hint endpoint with a valid
token during a contest session and asserts it's rejected — not just that the button is hidden.

**Git:** branch `feature/contest-mode` off `dev`.

---

## 10. Frontend integration & polish

By now every backend module has a working endpoint. This milestone is wiring the Next.js app to
all of them properly (auth via Clerk, code editor component, hint UI, mastery dashboard UI) and
is a good place to branch by *screen* rather than by backend module if you bring in collaborators
(see Section 11 below).

---

## 11. Working with collaborators — branching model

Your repo's folder structure already draws the ownership lines (`sandbox_adapter/`, `mentor/`,
`mastery/`, `problem_ingestion/`, `recommendation/`, plus `frontend/`). Use them as the branch
namespace so it's always obvious what a branch touches and who reviews it.

```
main                          protected; only merges from dev, always deployable
  dev                         integration branch; feature branches merge here via PR
    feature/sandbox-adapter        (Milestone 3 owner)
    feature/problem-ingestion      (Milestone 4 owner)
    feature/hint-ladder            (Milestone 6 owner — touches the most guardrails, review carefully)
    feature/mastery-model          (Milestone 7 owner)
    feature/recommendation         (Milestone 8 owner)
    frontend/editor-ui
    frontend/mastery-dashboard
```

Rules worth setting from day one, solo or with others:
- **One feature branch = one milestone (or sub-piece of one), never two.** Makes review and
  rollback sane.
- **PR into `dev`, never straight into `main`.** Even solo, this forces you to review your own diff
  before it's "official," which is its own comprehension check.
- **Branches that touch `mentor/`, `mastery/`, or `sandbox_adapter/` require a test update in the
  same PR** — this is literally AGENTS.md Section 5's rule; enforce it on yourself even solo.
- If you bring in another person later, hand them exactly one milestone's branch and this guide's
  section for it — they get the same "explain before you code" checkpoints you did.
- Naming convention: `feature/<module>-<short-description>`, e.g. `feature/mentor-output-filter`.

---

## 12. The checklist you run before calling *anything* done

Lifted straight from AGENTS.md Section 6 — literally run through this for every PR:

1. Does this change touch a hard constraint in AGENTS.md Section 3? If yes, does it still satisfy
   that constraint — can you point to the exact line of code that enforces it?
2. Do relevant tests pass?
3. Is lint clean?
4. If this changes an architectural decision from the PRD, is that called out explicitly, not
   silently changed?
5. If you added a new LLM call, does it go through `model_router.py`?

---

## 13. A reusable template for the "before you code" step

Copy this into a `notes/<milestone>.md` file every time you start a new piece of logic, fill it in
before writing the function:

```
Function/module: ___
What it does, in one sentence: ___
What it's given (inputs) and what it must never leak (e.g. solution code below level 3): ___
What happens on the unhappy path (bad input, timeout, empty result)? ___
Which existing constraint (AGENTS.md Section 3, #___) does this touch, if any? ___
How will I test that the constraint actually holds, not just that the happy path works? ___
```

If you can fill this out confidently, you're ready to code it. If you can't, that gap *is* the
next thing to think about — not a reason to start typing and figure it out via trial and error.
