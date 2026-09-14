# AlgoMentor AI — [REFERENCES.md](http://REFERENCES.md)

This technical reference manual provides complete architecture designs, explicit schemas, sequence flows, production code templates, and theoretical foundations matching every milestone in `GUIDE.md`# AlgoMentor AI — Engineering References & Technical Blueprints

**Purpose of this document:** this is the companion reference to `GUIDE.md`, `AGENTS.md`, and `docs/PRD.md`. It provides the exact database schemas, data contracts, environment variables, algorithms, and interface signatures required to implement AlgoMentor AI completely from scratch without prompting an AI for boilerplate or architecture decisions.

---



## 1. Environment Variables (`.env.example`)



### Backend (`backend/.env.example`)

```bash
# App Configuration
APP_ENV=development
DEBUG=True
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# PostgreSQL & pgvector
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/algomentor

# Redis (Caching & Rate Limiting)
REDIS_URL=redis://localhost:6379/0

# Code Execution Sandbox (Judge0)
SANDBOX_PROVIDER=judge0
JUDGE0_API_URL=http://localhost:2358
JUDGE0_API_KEY=                                 # Leave blank for local self-hosted instance
SANDBOX_TIMEOUT_SECONDS=5
SANDBOX_MEMORY_LIMIT_KB=256000

# Authentication (Clerk)
CLERK_JWKS_URL=https://<clerk-domain>/.well-known/jwks.json
CLERK_API_KEY=sk_test_...

# LLM Providers (Model Router)
TIER1_PROVIDER=openai
TIER1_MODEL=gpt-4o-mini
TIER1_API_KEY=sk-...

TIER2_PROVIDER=anthropic
TIER2_MODEL=claude-3-5-sonnet-20241022
TIER2_API_KEY=sk-ant-...

```



### Frontend (`frontend/.env.local.example`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

```

---



## 2. Database DDL (`backend/infra/schema.sql`)

PostgreSQL 15+ schema with constraints and `pgvector` indexing.

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Problem Bank
CREATE TABLE problems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    difficulty VARCHAR(16) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    pattern_tag VARCHAR(64) NOT NULL,           -- e.g., 'monotonic_stack', 'sliding_window'
    time_limit_ms INT NOT NULL DEFAULT 2000,
    memory_limit_kb INT NOT NULL DEFAULT 256000,
    optimal_time_complexity VARCHAR(32) NOT NULL,   -- e.g., 'O(N)'
    optimal_space_complexity VARCHAR(32) NOT NULL,  -- e.g., 'O(N)'
    starter_code JSONB NOT NULL,                -- {"python": "def solution()...", "cpp": "..."}
    hidden_tests_path VARCHAR(255) NOT NULL,    -- Path to differential-fuzzed tests
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);TABLE problems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    difficulty VARCHAR(16) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    pattern_tag VARCHAR(64) NOT NULL,           -- e.g., 'monotonic_stack', 'sliding_window'
    time_limit_ms INT NOT NULL DEFAULT 2000,
    memory_limit_kb INT NOT NULL DEFAULT 256000,
    optimal_time_complexity VARCHAR(32) NOT NULL,   -- e.g., 'O(N)'
    optimal_space_complexity VARCHAR(32) NOT NULL,  -- e.g., 'O(N)'
    starter_code JSONB NOT NULL,                -- {"python": "def solution()...", "cpp": "..."}
    hidden_tests_path VARCHAR(255) NOT NULL,    -- Path to differential-fuzzed tests
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_problems_pattern ON problems(pattern_tag);

-- 3. Isomorphic Variants Mapping (AGENTS.md Constraint #6)
CREATE TABLE problem_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_tag VARCHAR(64) NOT NULL,
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    variant_tier INT NOT NULL CHECK (variant_tier BETWEEN 1 AND 3),
    invariant_description TEXT NOT NULL,
    UNIQUE(pattern_tag, problem_id)
);

-- 4. Vector Store for Retrieval-Augmented Pattern Hints
CREATE TABLE hint_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_tag VARCHAR(64) NOT NULL,
    hint_level INT NOT NULL CHECK (hint_level BETWEEN 1 AND 2),
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL             -- text-embedding-3-small or equivalent
);

CREATE INDEX idx_hint_embeddings_vector ON hint_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- 5. User Submissions & Attempts
CREATE TYPE failure_category AS ENUM (
    'none', 
    'off_by_one', 
    'wrong_pattern', 
    'wrong_complexity', 
    'edge_case', 
    'syntax', 
    'timeout', 
    'memory_limit'
);

CREATE TABLE attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE RESTRICT,
    passed BOOLEAN NOT NULL,
    max_hint_level_used INT NOT NULL DEFAULT 0 CHECK (max_hint_level_used BETWEEN 0 AND 4),
    mistake_type failure_category NOT NULL DEFAULT 'none',
    runtime_ms INT,
    memory_kb INT,
    source_code TEXT NOT NULL,
    language VARCHAR(32) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attempts_user_problem ON attempts(user_id, problem_id);

-- 6. Topic Mastery Model (Decay & Confidence)
CREATE TABLE mastery_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_tag VARCHAR(64) NOT NULL,
    score FLOAT NOT NULL DEFAULT 0.0 CHECK (score >= 0.0 AND score <= 1.0),
    confidence_interval FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence_interval >= 0.0 AND confidence_interval <= 1.0),
    attempt_count INT NOT NULL DEFAULT 0,
    interval_days FLOAT NOT NULL DEFAULT 1.0,    -- SM-2 based interval
    ease_factor FLOAT NOT NULL DEFAULT 2.5 CHECK (ease_factor >= 1.3),
    last_practiced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, pattern_tag)
);

```

---



## 3. Sandbox Execution Contract (`backend/sandbox_adapter/interface.py`)

A strictly isolated interface adhering to **Constraint #1**. It separates execution details from consuming callers.

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ExecutionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    INTERNAL_SANDBOX_ERROR = "INTERNAL_SANDBOX_ERROR"

class VariableSnapshot(BaseModel):
    line_number: int
    variables: Dict[str, Any] = Field(default_factory=dict)

class ExecutionTrace(BaseModel):
    failed_input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error_message: Optional[str] = None
    snapshots: List[VariableSnapshot] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    status: ExecutionStatus
    runtime_ms: int
    memory_kb: int
    stdout: str
    stderr: str
    trace: Optional[ExecutionTrace] = None

class SandboxAdapter(ABC):
    @abstractmethod
    async def run_code(
        self,
        source_code: str,
        language: str,
        stdin: str,
        expected_output: Optional[str] = None,
        timeout_seconds: int = 5,
        memory_limit_kb: int = 256000
    ) -> ExecutionResult:
        """Executes source code safely within the provider's sandbox."""
        pass

```

---



## 4. Hint Ladder Implementation & Guardrails (`backend/mentor/`)

Enforces **Constraint #2**, **Constraint #3**, and **Constraint #7**.

### Architecture Matrix


| Level  | Purpose             | Model Tier                | Solution Code Allowed | Context Provided |
| ------ | ------------------- | ------------------------- | --------------------- | ---------------- |
| **L1** | Clarifying Question | Small / Hosted (`Tier 1`) |                       |                  |


 | **NEVER (Filtered)**  
 | Failing I/O, variable trace summary

 |
| **L2** | Algorithmic Pattern Nudge | Small / Hosted (`Tier 1`)

 | **NEVER (Filtered)**  
 | Pattern metadata, failure category

 |
| **L3** | Structural Pseudocode Skeleton | Frontier (`Tier 2`)

 | Pseudocode outline only | Failure state + optimal design invariants

 |
| **L4** | Full Walkthrough + Explain-Back | Frontier (`Tier 2`)

 | Full Solution | Reference code, complete diff, line trace

 |

### Context Builder (`backend/mentor/context_builder.py`)

```python
from typing import Dict, Any

def build_mentor_context(
    hint_level: int,
    problem_metadata: Dict[str, Any],
    user_code: str,
    failure_trace: Dict[str, Any],
    reference_solution: str
) -> str:
    # HARD CONSTRAINT #2: Reference solution NEVER exists in LLM context below Level 3[cite: 1, 3]
    solution_payload = reference_solution if hint_level >= 3 else "[REDACTED - GATED_BELOW_L3]"

    context = (
        f"Problem: {problem_metadata['title']}\n"
        f"Difficulty: {problem_metadata['difficulty']}\n"
        f"User Submission:\n```\n{user_code}\n```\n"
        f"Failure State: Input={failure_trace.get('failed_input')}, "
        f"Expected={failure_trace.get('expected_output')}, "
        f"Actual={failure_trace.get('actual_output')}\n"
        f"Failing Trace Variables: {failure_trace.get('snapshots', [])}\n"
    )

    if hint_level >= 3:
        context += f"Reference Solution:\n```\n{solution_payload}\n```\n"
        
    return context

```



### Output Filter (`backend/mentor/output_filter.py`)

```python
import re
from typing import Tuple

LEAK_PATTERNS = [
    r"(def\s+[a-zA-Z_]\w*\s*\(.*?\):)",               # Python function signatures
    r"(class\s+[a-zA-Z_]\w*(\s*:\s*|\s*\{))",        # Class declarations
    r"(return\s+[^;]+[;|\n])",                         # Direct returns
    r"(\w+\s*=\s*\[[^\]]*\])",                         # Explicit collection setups
]

def sanitize_mentor_output(raw_output: str, hint_level: int) -> Tuple[bool, str]:
    """
    Enforces AGENTS.md Constraint #3.
    Screens L1-L2 hint responses for implementation leaks before returning to client[cite: 1, 3].
    """
    if hint_level >= 3:
        return True, raw_output

    for pattern in LEAK_PATTERNS:
        if re.search(pattern, raw_output):
            return False, "Let's pause on the raw code. What invariant broke on that failing step?"

    return True, raw_output

```

---



## 5. Spaced Repetition & Decay Mathematical Model (`backend/mastery/decay.py`)

Implementation of the SM-2 adaptation detailed in PRD Section 9.

### Equation Suite

$$\text{Decayed Score: } S(t) = S_0 \cdot e^{-\lambda t}$$

Where:

- $S_0$: Base mastery score $\in [0, 1]$.
- $t$: Days elapsed since `last_practiced_at`.
- $\lambda$: Decay rate, inversely proportional to interval stability:

$$\lambda = \frac{\ln(2)}{\text{intervaldays}}$$

### Performance Rating Matrix ($q \in [0, 5]$)


| Condition               | Grade ($q$) | Mastery Impact |
| ----------------------- | ----------- | -------------- |
| Clean Pass ($L0$ hints) |             |                |


 | 5 | Score increase, interval extended ($I_{n+1} = I_n \times EF$) |
| Pass with $L1$ hints

 | 4 | Moderate increase, interval extended |
| Pass with $L2$ hints

 | 3 | Marked "seen", minimal interval change

 |
| Solved with $L3$ hints

 | 2 | Partial reset: $I_1 = 1$  
 |
| Solved with $L4$ hints / Failed

 | 1 | Complete reset: $I_1 = 1$, Ease Factor reduced

 |

### Implementation

```python
import math
from datetime import datetime, timezone

def calculate_decay(base_score: float, interval_days: float, last_practiced_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    delta_days = max(0.0, (now - last_practiced_at).total_seconds() / 86400.0)
    
    half_life = max(1.0, interval_days)
    decay_rate = math.log(2) / half_life
    decayed_score = base_score * math.exp(-decay_rate * delta_days)
    return round(max(0.0, min(1.0, decayed_score)), 4)

def update_sm2(q: int, interval_days: float, ease_factor: float) -> tuple[float, float]:
    """Calculates next interval and ease factor based on performance grade q (0-5)."""
    new_ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(1.3, new_ef)

    if q < 3:
        new_interval = 1.0
    else:
        if interval_days == 1.0:
            new_interval = 6.0
        else:
            new_interval = interval_days * new_ef

    return round(new_interval, 2), round(new_ef, 4)

```

---



## 6. Differential Fuzzing Pipeline (`backend/problem_ingestion/fuzzer.py`)

Enforces **Constraint #5**: hidden test cases are derived via differential execution between brute-force and optimal references.

```python
import random
from typing import Callable, Any, List, Dict

class DifferentialFuzzer:
    @staticmethod
    def fuzz_array_inputs(
        num_tests: int,
        min_size: int = 1,
        max_size: int = 1000,
        val_range: tuple[int, int] = (-1000, 1000)
    ) -> List[List[int]]:
        tests = []
        # Edge cases explicitly included
        tests.append([])
        tests.append([val_range[0]])
        tests.append([val_range[1]])
        
        for _ in range(num_tests):
            size = random.randint(min_size, max_size)
            test_arr = [random.randint(val_range[0], val_range[1]) for _ in range(size)]
            tests.append(test_arr)
        return tests

    @classmethod
    def run_differential_test(
        cls,
        brute_force_fn: Callable[[Any], Any],
        optimal_fn: Callable[[Any], Any],
        inputs: List[Any]
    ) -> List[Dict[str, Any]]:
        verified_cases = []
        for inp in inputs:
            expected = brute_force_fn(inp)
            optimal_res = optimal_fn(inp)
            
            if expected != optimal_res:
                raise ValueError(
                    f"Differential divergence detected! Input: {inp} | "
                    f"Brute-force: {expected} | Optimal: {optimal_res}"
                )
            
            verified_cases.append({"input": inp, "expected_output": expected})
        return verified_cases

```

---



## 7. Contest-Mode Route Guard (`backend/api/deps.py`)

Enforces **Constraint #4**: API-level blocking of hint requests during active contests.

```python
from fastapi import HTTPException, Header, Depends, status
import redis.asyncio as redis

async def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)

async def verify_not_in_contest_mode(
    user_id: str,
    r: redis.Redis = Depends(get_redis_client)
):
    """
    Enforces AGENTS.md Constraint #4.
    Rejects hint requests at the API layer if user has an active contest session[cite: 1, 3].
    """
    is_in_contest = await r.get(f"session:contest:{user_id}")
    if is_in_contest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hints are strictly disabled during an active contest session."
        )

```

---



## 8. Development Verification Scripts

Run these direct CLI commands to validate your core architecture without firing up external wrappers or asking for verification:

```bash
# 1. Verify PostgreSQL pgvector Extension
psql -d algomentor -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 2. Assert Zero Hardcoded Provider SDK Calls Outside model_router.py (Constraint #7)
grep -rnE "(from openai|import openai|from anthropic|import anthropic)" backend/ \
  --exclude-dir=tests \
  --exclude="model_router.py"

# 3. Assert Reference Solution Never Exists in Level 1 Context Builder (Constraint #2)
pytest backend/tests/test_mentor_context.py -k "test_solution_exclusion_below_level_3"

# 4. Check for Leaked Solution Code in L1/L2 Output Filter (Constraint #3)
pytest backend/tests/test_output_filter.py

```

---



## 9. System Architecture & Responsibility Boundaries

AlgoMentor AI is best understood as a set of independently testable subsystems rather than a single backend application.

```text
                         ┌──────────────────────┐
                         │      Next.js UI      │
                         │ Editor / Problems /  │
                         │ Mentor / Dashboard   │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI API      │
                         │ Auth / Problems /    │
                         │ Attempts / Mentor    │
                         └───────┬──────┬───────┘
                                 │      │
                ┌────────────────┘      └─────────────────┐
                ▼                                         ▼
      ┌──────────────────┐                      ┌──────────────────┐
      │   PostgreSQL     │                      │      Redis       │
      │ users/problems/  │                      │ cache/rate limit │
      │ attempts/mastery │                      │ contest state    │
      └──────────────────┘                      └──────────────────┘
                │
                ▼
      ┌──────────────────┐
      │     pgvector     │
      │ hint embeddings  │
      └──────────────────┘

                         ┌──────────────────────┐
                         │   Sandbox Adapter    │
                         │ provider-independent │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ Judge0 / future      │
                         │ isolated executor    │
                         └──────────────────────┘

                         ┌──────────────────────┐
                         │    Model Router      │
                         │ Tier 1 / Tier 2      │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ LLM Provider(s)      │
                         └──────────────────────┘
```



### Responsibility matrix


| Component         | Owns                                      | Must not own                        |
| ----------------- | ----------------------------------------- | ----------------------------------- |
| Frontend          | UI state, editor state, API presentation  | Provider secrets, sandbox execution |
| API               | Authentication, orchestration, validation | Direct provider-specific LLM logic  |
| PostgreSQL        | Durable relational state                  | Temporary rate-limit state          |
| Redis             | Ephemeral state, caching, rate limits     | Source-of-truth user records        |
| Sandbox Adapter   | Execution contract                        | Mentor decisions                    |
| Model Router      | Model/provider selection                  | Business authorization              |
| Mentor            | Hint policy and context construction      | Raw provider SDK configuration      |
| Mastery Engine    | Score/interval calculations               | UI rendering                        |
| Problem Ingestion | Problem validation and test generation    | User authentication                 |


The purpose of these boundaries is to keep infrastructure replaceable and make failures easier to isolate.

---



## 10. End-to-End Submission Flow

A normal code submission follows this sequence:

```text
Browser
  │
  │ POST /attempts
  ▼
API
  │
  ├── Authenticate user
  ├── Validate problem/language
  ├── Load limits
  │
  ▼
Sandbox Adapter
  │
  ├── Compile
  ├── Execute
  ├── Apply timeout/memory limits
  ├── Compare output
  │
  ▼
ExecutionResult
  │
  ├── accepted?
  ├── runtime
  ├── memory
  └── trace/failure
  │
  ▼
Attempt Persistence
  │
  ├── attempts
  └── mastery_scores
  │
  ▼
API Response
  │
  ▼
Browser
```



### Important invariant

The browser must never be treated as a trusted execution environment.

The server-side execution layer must enforce:

- execution timeout
- memory limit
- language restrictions
- input restrictions
- output restrictions
- process isolation
- resource cleanup

The exact isolation mechanism can change later because callers interact only with `SandboxAdapter`.

---



## 11. Mentor Request Flow

A mentor request should not simply send the entire application state to an LLM.

Instead:

```text
User requests hint
       │
       ▼
Contest-mode check
       │
       ├── active contest → reject
       │
       ▼
Determine requested hint level
       │
       ▼
Load problem metadata
       │
       ▼
Load latest attempt/failure trace
       │
       ▼
Retrieve relevant hint/pattern context
       │
       ▼
Build level-specific context
       │
       ▼
Select model through Model Router
       │
       ▼
Generate mentor response
       │
       ▼
Apply output guardrails
       │
       ├── leak detected → replace/reject
       │
       ▼
Return hint
```



### Why context must be level-dependent

A beginner-level hint should not accidentally receive the reference solution.

The context builder therefore acts as a security and product-policy boundary:

```text
L1 → problem + failure state
L2 → problem + pattern/failure information
L3 → additional structural information
L4 → reference solution + full walkthrough
```

This is stronger than relying on an LLM prompt saying:

> "Do not reveal the solution."

The application should enforce the restriction **before the request reaches the model**.

---



## 12. MapReduce Mental Model for Distributed Data Processing

MapReduce is useful as a conceptual model when thinking about large-scale data processing.

The pattern is:

```text
             INPUT DATA
                 │
                 ▼
               MAP
                 │
          key-value pairs
                 │
                 ▼
              SHUFFLE
                 │
       same keys grouped
                 │
                 ▼
              REDUCE
                 │
                 ▼
              RESULT
```



### Example: counting solved problems by pattern

Suppose attempts contain:

```text
attempt 1 → sliding_window
attempt 2 → graph
attempt 3 → sliding_window
attempt 4 → dp
attempt 5 → graph
```

A conceptual Map phase produces:

```text
("sliding_window", 1)
("graph", 1)
("sliding_window", 1)
("dp", 1)
("graph", 1)
```

Shuffle groups them:

```text
sliding_window → [1, 1]
graph          → [1, 1]
dp             → [1]
```

Reduce aggregates:

```text
sliding_window → 2
graph          → 2
dp             → 1
```

In SQL, the equivalent analytical operation is conceptually close to:

```sql
SELECT pattern_tag, COUNT(*)
FROM attempts
GROUP BY pattern_tag;
```



### Important distinction

MapReduce is a **distributed processing model**, not a requirement for ordinary relational queries.

A PostgreSQL query optimizer can execute:

```sql
GROUP BY
COUNT
SUM
AVG
```

using database-specific execution operators such as scans, sorting, hashing, and aggregation.

The MapReduce analogy becomes especially useful when reasoning about:

- partitioned datasets
- parallel computation
- distributed aggregation
- data locality
- shuffle cost
- fault tolerance

---



## 13. Database Access Patterns

The schema should be designed around the application's most common queries.

### 13.1 Fetch a problem

```sql
SELECT
    id,
    slug,
    title,
    description,
    difficulty,
    pattern_tag,
    time_limit_ms,
    memory_limit_kb,
    starter_code
FROM problems
WHERE slug = $1;
```

The unique `slug` provides a natural lookup key.

### 13.2 Fetch user's recent attempts

```sql
SELECT
    id,
    problem_id,
    passed,
    mistake_type,
    runtime_ms,
    memory_kb,
    language,
    submitted_at
FROM attempts
WHERE user_id = $1
ORDER BY submitted_at DESC
LIMIT $2;
```

The `(user_id, problem_id)` index already supports the important user/problem lookup pattern.

### 13.3 Fetch mastery by pattern

```sql
SELECT
    pattern_tag,
    score,
    confidence_interval,
    attempt_count,
    interval_days,
    ease_factor,
    last_practiced_at
FROM mastery_scores
WHERE user_id = $1;
```



### 13.4 Find weak topics

```sql
SELECT
    pattern_tag,
    score,
    confidence_interval,
    attempt_count
FROM mastery_scores
WHERE user_id = $1
ORDER BY score ASC
LIMIT 5;
```

The application can then use these topics when constructing a personalized practice queue.

---



## 14. Transaction Boundaries

An attempt is a logical unit of work.

A successful submission may require:

```text
1. Execute code
2. Persist attempt
3. Update mastery
4. Update practice metadata
```

Database writes that must remain consistent should be performed inside an appropriate transaction.

Conceptually:

```python
async with db.begin():
    attempt = await create_attempt(...)
    await update_mastery(...)
```

The sandbox execution itself should **not** be held open inside a database transaction.

Bad pattern:

```text
BEGIN TRANSACTION
      │
      ▼
Run user code
      │
      │ potentially several seconds
      ▼
Update database
      │
COMMIT
```

Better:

```text
Execute outside DB transaction
      │
      ▼
Obtain trusted ExecutionResult
      │
      ▼
Short DB transaction
      ├── insert attempt
      └── update mastery
      ▼
COMMIT
```

This prevents long-running external work from unnecessarily holding database resources.

---



## 15. Idempotency & Duplicate Submissions

Network requests can be retried.

A client may send:

```text
POST /attempts
```

and fail to receive the response even though the server successfully processed it.

For important write operations, an idempotency key can prevent accidental duplicate processing.

Conceptual request:

```http
POST /attempts
Idempotency-Key: 01JXYZ...
```

Server behavior:

```text
first request
    ↓
process + store result

same key again
    ↓
return previously stored result
```

The exact implementation can use a durable table or another controlled persistence mechanism.

The key principle is:

> Retrying a request should not unintentionally create multiple logical operations.

---



## 16. Redis Usage Model

Redis is appropriate for **short-lived or frequently accessed state**.

Recommended responsibilities:

```text
Redis
├── rate limits
├── contest session state
├── short-lived caches
├── temporary execution metadata
└── distributed coordination where required
```

PostgreSQL remains the durable source of truth for:

```text
PostgreSQL
├── users
├── problems
├── attempts
└── mastery_scores
```



### Example rate-limit key

```text
ratelimit:hints:{user_id}
```

A conceptual policy could be:

```text
N requests / time window
```

The exact values belong in configuration rather than hardcoded business logic.

---



## 17. Caching Strategy

Caching should be applied only where stale data is acceptable or where invalidation is explicit.

Good cache candidates:

- problem metadata
- starter code
- static hint metadata
- frequently requested problem lists

Poor cache candidates:

- authoritative attempt history
- current mastery score immediately after an update
- authentication state that must be strongly consistent

Conceptual cache flow:

```text
GET problem
    │
    ▼
Redis?
 ┌──┴──┐
 │ HIT │──────► return cached problem
 └─────┘
    │ MISS
    ▼
PostgreSQL
    │
    ▼
store in Redis
    │
    ▼
return
```

---



## 18. pgvector Retrieval Model

`hint_embeddings` allows hints to be retrieved based on semantic similarity rather than only exact keyword matching.

Each stored record contains:

```text
pattern_tag
hint_level
content
embedding
```

Conceptually:

```text
User failure
    │
    ▼
Build retrieval query
    │
    ▼
Embedding model
    │
    ▼
Query vector
    │
    ▼
pgvector similarity search
    │
    ▼
Top relevant hints
    │
    ▼
Mentor context builder
```

The retrieved text should still be filtered by:

- pattern
- hint level
- product policy
- contest mode
- access rules

Vector similarity is a retrieval mechanism, not an authorization mechanism.

---



## 19. Failure Classification

The `failure_category` enum provides a normalized vocabulary for analyzing attempts.

```text
none
off_by_one
wrong_pattern
wrong_complexity
edge_case
syntax
timeout
memory_limit
```

A useful classification pipeline is:

```text
ExecutionResult
      │
      ├── compilation error → syntax / compilation category
      ├── timeout            → timeout
      ├── memory violation   → memory_limit
      ├── wrong output       → deeper diagnosis
      └── accepted           → none
```

For wrong answers, the system can use:

```text
failed input
expected output
actual output
variable snapshots
user code
problem metadata
```

to determine whether the failure is likely related to:

- boundary conditions
- incorrect invariant
- wrong algorithmic pattern
- complexity
- special cases

Classification should be treated as a diagnostic signal, not as an infallible truth.

---



## 20. Differential Testing Architecture

The problem-ingestion pipeline uses two independent implementations:

```text
                 Generated Input
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Brute-force          Optimal
          solver              solver
              │                 │
              └────────┬────────┘
                       ▼
                    Compare
                       │
                ┌──────┴──────┐
                │             │
             Match         Mismatch
                │             │
                ▼             ▼
             Accept       Reject / inspect
```

The reason for maintaining a brute-force implementation is that it provides an independent correctness oracle for smaller generated inputs.

### Important properties

A good differential test suite should include:

```text
empty input
minimum input
maximum relevant values
duplicate values
negative values
already sorted input
reverse sorted input
single-element input
boundary-sized input
randomized input
```

The exact edge cases depend on the problem's input domain.

---



## 21. Problem Ingestion Lifecycle

A problem should not become available to users immediately after being imported.

Recommended lifecycle:

```text
RAW
 │
 ▼
PARSED
 │
 ▼
VALIDATED
 │
 ▼
REFERENCE SOLUTIONS VERIFIED
 │
 ▼
HIDDEN TESTS GENERATED
 │
 ▼
DIFFERENTIAL TESTING
 │
 ▼
MENTOR METADATA CREATED
 │
 ▼
EMBEDDINGS GENERATED
 │
 ▼
PUBLISHED
```

A problem should be publishable only after its required invariants pass.

### Validation checklist

```text
[ ] Unique slug
[ ] Valid difficulty
[ ] Valid pattern tag
[ ] Starter code compiles
[ ] Reference solution passes
[ ] Brute-force solution passes small cases
[ ] Differential tests agree
[ ] Hidden tests are stored correctly
[ ] Complexity metadata is present
[ ] Mentor metadata is present
[ ] Required embeddings are available
```

---



## 22. Authentication Boundary

Authentication and authorization are different concerns.

### Authentication

Answers:

> Who is this user?

The application receives a verified identity from the configured authentication provider.

### Authorization

Answers:

> What is this user allowed to do?

Examples:

```text
Can access problem?
Can submit?
Can request hint?
Can access contest resources?
Can view another user's data?
```

Never rely on a frontend boolean such as:

```javascript
isAdmin = true
```

for authorization.

Authorization must be enforced on the server.

---



## 23. API Contract Principles

Every API endpoint should define:

```text
HTTP method
path
authentication requirement
request schema
response schema
error schema
rate limit
side effects
```

Example conceptual endpoint:

```text
POST /api/v1/problems/{problem_id}/attempts
```

Request:

```json
{
  "language": "cpp",
  "source_code": "...",
  "stdin": "..."
}
```

Response:

```json
{
  "attempt_id": "...",
  "status": "WRONG_ANSWER",
  "runtime_ms": 41,
  "memory_kb": 18240,
  "failure": {
    "category": "edge_case",
    "failed_input": "...",
    "expected_output": "...",
    "actual_output": "..."
  }
}
```

The exact API versioning and route names can be adjusted during implementation, but contracts should remain explicit.

---



## 24. Error Handling Contract

Internal exceptions should not automatically become raw stack traces in API responses.

Use a controlled error model:

```json
{
  "error": {
    "code": "SANDBOX_TIMEOUT",
    "message": "Execution exceeded the configured time limit.",
    "request_id": "..."
  }
}
```

Useful categories include:

```text
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
VALIDATION_ERROR
PROBLEM_NOT_FOUND
CONTEST_HINT_DISABLED
SANDBOX_TIMEOUT
SANDBOX_MEMORY_LIMIT
SANDBOX_RUNTIME_ERROR
SANDBOX_INTERNAL_ERROR
MODEL_PROVIDER_ERROR
RATE_LIMITED
INTERNAL_ERROR
```

A request ID should be propagated through logs so a user-facing error can be correlated with backend diagnostics.

---



## 25. Observability

Production debugging requires more than application logs.

Track at least:

### API metrics

```text
request count
request latency
error rate
status-code distribution
```



### Sandbox metrics

```text
execution count
compile failures
timeouts
runtime errors
average runtime
queue/execution latency
```



### Mentor metrics

```text
hint requests
requests by hint level
model latency
provider failures
output-filter rejections
```



### Database metrics

```text
query latency
connection pool utilization
slow queries
transaction duration
```



### Correlation

A request should carry a correlation/request ID:

```text
HTTP Request
     │
     ├── API log
     ├── sandbox log
     ├── model-router log
     └── DB operation log
```

This makes tracing a single user action across services possible.

---



## 26. Security Checklist

The platform executes **untrusted user code**, so sandbox security is a first-class concern.

### Never assume submitted code is safe

A submission may attempt to:

```text
read local files
consume excessive CPU
consume excessive memory
spawn processes
open network connections
fork repeatedly
write large amounts of output
run indefinitely
```

The execution environment therefore needs multiple independent controls.

### Defense layers

```text
                  User Code
                     │
                     ▼
              Language filter
                     │
                     ▼
               Process limit
                     │
                     ▼
              Time limitation
                     │
                     ▼
             Memory limitation
                     │
                     ▼
              Filesystem policy
                     │
                     ▼
              Network policy
                     │
                     ▼
             Output limitation
                     │
                     ▼
               Cleanup
```

No single control should be treated as sufficient isolation.

---



## 27. Secret Management

Never commit:

```text
API keys
database passwords
authentication secrets
provider credentials
private signing keys
```

to Git.

Use:

```text
.env
secret manager
deployment environment variables
```

and commit only safe templates such as:

```text
.env.example
```

The existing environment-variable section should remain the canonical list of required configuration names.

---



## 28. Testing Pyramid

The project should use multiple levels of testing.

```text
                 /\
                /  \
               / E2E\
              /------\
             /Integr. \
            /----------\
           /   Unit     \
          /--------------\
```



### Unit tests

Test deterministic functions such as:

```text
calculate_decay()
update_sm2()
sanitize_mentor_output()
failure classification
input validation
```



### Integration tests

Test boundaries:

```text
API ↔ PostgreSQL
API ↔ Redis
API ↔ Sandbox Adapter
Mentor ↔ Model Router
pgvector retrieval
```



### End-to-end tests

Test complete workflows:

```text
login
  ↓
open problem
  ↓
submit code
  ↓
receive result
  ↓
request hint
  ↓
receive allowed hint
  ↓
mastery updated
```

---



## 29. Reference Implementation Rules

The following rules should be treated as architectural invariants.

### Rule 1 — Sandbox abstraction

Callers must depend on:

```python
SandboxAdapter
```

rather than directly on Judge0-specific implementation details.

### Rule 2 — Hint gating

The reference solution must not enter L1/L2 model context.

### Rule 3 — Output filtering

L1/L2 output must be checked for implementation leakage.

### Rule 4 — Contest isolation

Active contest sessions must reject hint requests at the API boundary.

### Rule 5 — Differential correctness

Generated hidden cases should be checked against an independent correctness oracle.

### Rule 6 — Provider abstraction

Provider-specific SDK calls belong behind the model-router boundary.

### Rule 7 — Durable source of truth

PostgreSQL owns durable user/problem/attempt/mastery state.

---



## 30. Suggested Backend Module Layout

```text
backend/
├── api/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── problems.py
│   │   ├── attempts.py
│   │   ├── mentor.py
│   │   └── mastery.py
│   └── deps.py
│
├── db/
│   ├── models.py
│   ├── session.py
│   └── repositories/
│
├── sandbox_adapter/
│   ├── interface.py
│   ├── judge0.py
│   └── factory.py
│
├── mentor/
│   ├── context_builder.py
│   ├── output_filter.py
│   ├── hint_policy.py
│   └── retrieval.py
│
├── model_router/
│   ├── router.py
│   ├── providers/
│   └── schemas.py
│
├── mastery/
│   ├── decay.py
│   ├── sm2.py
│   └── scoring.py
│
├── problem_ingestion/
│   ├── parser.py
│   ├── validator.py
│   ├── fuzzer.py
│   └── publisher.py
│
├── tests/
└── main.py
```

The purpose of this structure is separation of concerns, not forcing every future implementation to use exactly these filenames.

---



## 31. Data Lifecycle

A typical user interaction changes data through the following lifecycle:

```text
Problem
   │
   ▼
User opens problem
   │
   ▼
User writes code
   │
   ▼
Submission
   │
   ▼
Sandbox execution
   │
   ▼
ExecutionResult
   │
   ▼
Attempt stored
   │
   ▼
Failure classified
   │
   ▼
Mastery updated
   │
   ▼
Optional mentor request
   │
   ▼
Hint interaction recorded
```

This gives AlgoMentor AI the historical information required to move from a simple coding platform toward an adaptive learning platform.

---



## 32. Performance Principles

Optimize based on measured bottlenecks rather than assumptions.

### Database

Prefer:

```text
proper indexes
bounded queries
pagination
connection pooling
batch operations
```

Avoid:

```text
SELECT *
unbounded history queries
N+1 queries
long transactions
```



### API

Prefer:

```text
async I/O
bounded payloads
timeouts
caching where appropriate
```



### Sandbox

Prefer:

```text
preconfigured execution environments
bounded queues
resource limits
cleanup after execution
```



### LLM

Prefer:

```text
small model for simple hints
larger model for complex reasoning
retrieval for relevant context
strict context budgets
provider abstraction
```

---



## 33. Scaling Path

The first version does not need every component to be distributed.

A sensible evolution is:

```text
Stage 1
Single API
PostgreSQL
Redis
Sandbox
LLM provider
        │
        ▼
Stage 2
Separate execution workers
        │
        ▼
Stage 3
Queue-based asynchronous execution
        │
        ▼
Stage 4
Multiple sandbox workers
        │
        ▼
Stage 5
Independent mentor/model workers
        │
        ▼
Stage 6
Horizontal API + worker scaling
```

The abstraction boundaries in this document are intended to make this evolution possible without rewriting the entire application.

---



## 34. Failure Modes & Recovery



### Database unavailable

```text
API
 │
 └── PostgreSQL unavailable
       │
       ├── fail safely
       ├── log request ID
       └── do not claim persistence succeeded
```



### Redis unavailable

The application should define explicitly which features can degrade.

For example:

```text
cache unavailable → bypass cache if safe
rate limiter unavailable → fail closed for security-sensitive limits
contest state unavailable → do not accidentally enable forbidden hints
```



### Model provider unavailable

The model router can:

```text
retry transient failures
switch configured provider/model
return controlled error
```

It should never expose provider credentials or raw internal exceptions.

### Sandbox unavailable

Return a controlled execution infrastructure error rather than treating the submission as a wrong answer.

---



## 35. Recommended Development Order

Build from deterministic infrastructure toward AI features.

```text
1. PostgreSQL schema
        ↓
2. Authentication
        ↓
3. Problem CRUD/read APIs
        ↓
4. Sandbox Adapter
        ↓
5. Submission pipeline
        ↓
6. Attempt persistence
        ↓
7. Mastery calculations
        ↓
8. Redis/rate limiting
        ↓
9. Mentor context builder
        ↓
10. Model Router
        ↓
11. L1/L2 guardrails
        ↓
12. L3/L4 mentor flow
        ↓
13. pgvector retrieval
        ↓
14. Problem ingestion + fuzzing
        ↓
15. Observability
        ↓
16. Integration/E2E testing
        ↓
17. Production hardening
```

This ordering minimizes the risk of building an AI layer on top of unstable execution or data infrastructure.

---



## 36. Engineering Principle

The central engineering philosophy of AlgoMentor AI should be:

> **Make correctness deterministic wherever possible, and use AI only where reasoning or personalization is genuinely required.**

Therefore:

```text
Code correctness
       → deterministic sandbox

Authentication
       → deterministic verification

Contest restriction
       → deterministic API guard

Hint-level access
       → deterministic policy

Mastery calculation
       → deterministic mathematical model

Semantic retrieval
       → vector search

Explanation / Socratic guidance
       → LLM
```

This division reduces hallucination risk, improves testability, and keeps the AI component from becoming responsible for decisions that ordinary software can enforce more reliably.