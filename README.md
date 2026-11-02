# AlgoMentor-AI 

**An AI-powered DSA learning platform that mentors, not just judges.**

AlgoMentor AI combines an online coding judge with a persistent AI mentor: instead of static hints or handing over solutions, it guides you through a gated, execution-trace-aware hint ladder, tracks your topic mastery over time (with realistic forgetting/decay), and adapts what you practice next — including resurfacing weak topics via spaced repetition using structurally similar (not repeated) problems.

> Full product spec: [`docs/PRD.md`](./docs/PRD.md) — read this before proposing architecture changes.

---

## Why AlgoMentor?

Most platforms help you solve more problems. AlgoMentor is built to help you become a better problem solver — by remembering how you learn, not just what you've solved.

- **Execution-aware hints** — hints are generated from the actual variable state at your point of failure, not just a static guess from your code.
- **Hint gating that's structurally enforced** — the AI literally cannot see the full solution at low hint levels; it's not just told to withhold it.
- **Decay-based mastery tracking** — a "seen vs. owned" distinction, so hint-assisted solves don't fake out your progress dashboard.
- **Isomorphic spaced repetition** — reinforcement uses structurally similar problems, not repeats, so you practice the underlying skill, not memorized tricks.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (+ pgvector) |
| Cache | Redis |
| Code Execution | Judge0 (self-hosted) / Piston / E2B, behind a swappable adapter |
| AI Layer | Tiered LLM routing — cheap hosted model for early hints, frontier model for deep hints & code review |
| Auth | Clerk |

Current phase deliberately avoids custom sandbox infrastructure (no self-built Firecracker/microVM orchestration) — see `docs/PRD.md` for the reasoning.

---

## Project Structure

```
algomentor-ai/
├── frontend/                 # Next.js app
├── backend/
│   ├── api/                  # FastAPI routes
│   ├── sandbox_adapter/      # Code execution provider abstraction
│   ├── mentor/               # Hint orchestration & gating
│   ├── mastery/              # Decay model, confidence scoring, variant mapping
│   ├── problem_ingestion/    # Test-case generation pipeline
│   └── recommendation/       # Adaptive scheduling logic
├── docs/
│   └── PRD.md
├── infra/                    # Deployment configs
└── tests/
```

---

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ (with `pgvector` extension)
- Redis
- Docker (for running Judge0 locally)

### Setup

```bash
# clone
git clone https://github.com/<your-org>/algomentor-ai.git
cd algomentor-ai

# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB, Redis, LLM API keys

# frontend
cd ../frontend
npm install
cp .env.local.example .env.local

# sandbox (Judge0, local dev)
docker compose -f infra/judge0-compose.yml up -d
```

### Windows (PowerShell)

Start the database, Redis, and Judge0 services from the repository root:

```powershell
docker compose up -d postgres redis judge0-server judge0-worker
```

In a backend terminal:

```powershell
Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.problem_ingestion.seed_problems
python -m uvicorn app.main:app --reload
```

In a separate frontend terminal:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`. Level 1 hints use a local template; Levels 2–4 need a configured provider API key in `backend/.env`.

### Running locally

```bash
# backend
cd backend && uvicorn api.main:app --reload

# frontend
cd frontend && npm run dev
```

### Running tests

```bash
# backend
cd backend && pytest

# frontend
cd frontend && npm test
```

---

## Contributing

Before contributing, read [`AGENTS.md`](./AGENTS.md) — it documents architectural guardrails (e.g. hint-gating enforcement, sandbox abstraction) that are load-bearing product decisions, not arbitrary style preferences. This applies whether you're a human contributor or an AI coding agent.

Areas open for contribution:
- Frontend UI/UX
- Hint-orchestration prompt engineering (within the gating constraints in `AGENTS.md`)
- Problem bank curation + test-case generation
- Recommendation/spaced-repetition logic

---

## License

MIT License
