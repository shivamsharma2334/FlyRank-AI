# RuleGuard AI

AI-assisted technical risk assessment for API and backend change requests.

RuleGuard AI takes one technical request ("allow users to reset a password after
verifying account ownership"), retrieves relevant internal security/API rules with
FAISS + LangChain, asks Gemini for a judgement, validates that judgement against a
strict schema, and returns one structured risk assessment. It is **not a chatbot**:
no conversation history, no memory between requests, no assistant persona — one
request in, one validated JSON judgement out.

## Contents

- [Architecture](#architecture)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Backend setup](#backend-setup)
- [Frontend setup](#frontend-setup)
- [API usage](#api-usage)
- [Testing](#testing)
- [Evaluation](#evaluation)
- [Reliability strategy](#reliability-strategy)
- [Cost and usage logging](#cost-and-usage-logging)
- [Kill switch and stub mode](#kill-switch-and-stub-mode)
- [Prompt versioning](#prompt-versioning)
- [Security notes](#security-notes)
- [Limitations](#limitations)
- [Future improvements](#future-improvements)
- [Suggested commit plan](#suggested-commit-plan)

## Architecture

```
React UI  ->  FastAPI  ->  Pydantic input validation  ->  Risk Service
                                                              |
                                    +-------------------------+-----------------------+
                                    v                                                 v
                          kill switch / stub mode                       LangChain RAG (FAISS)
                                    |                                                 |
                                    |                                       Security/API rules KB
                                    |                                                 |
                                    +---------------> Gemini Service <----------------+
                                                     (timeout, bounded
                                                      retries, JSON parse,
                                                      schema validate,
                                                      1 repair attempt,
                                                      quarantine)
                                                              |
                                                    Pydantic RiskJudgement
                                                              |
                                                      Clean, validated JSON
                                                              |
                                                          React UI
```

A valid HTTP 200 from Gemini never reaches the caller directly — it is parsed,
schema-validated, optionally repaired once, and only then returned.

## Features

- Single endpoint: `POST /api/v1/risk/judge` — one request, one structured judgement
- LangChain RAG pipeline over a 6-file Markdown security/API knowledge base, indexed with FAISS
- Gemini (`langchain-google-genai`) as the judgement LLM, with the user request and system
  instructions kept in separate messages (prompt-injection resistant by construction)
- Closed-enum Pydantic schema (`RiskLevel`, `RiskCategory`) — the model cannot invent new values
- Explicit async timeout + bounded, jittered exponential-backoff retries, classified by error
  type (429/5xx retried, 400/401/403 never retried)
- Exactly one schema-repair attempt on invalid model output, then quarantine + HTTP 422
- Kill switch (`LLM_ENABLED=false` -> HTTP 503, no model call) and stub mode
  (`LLM_STUB=1` -> deterministic fixture, no model call)
- Structured JSON logging of every model call: prompt version, model, token counts,
  duration, repair count, status
- Versioned prompt file (`prompts/risk-v1.md`) with role, exact output shape, rules,
  a when-unsure instruction, and four worked examples
- 8-case evaluation set with a scoring runner
- React assessment UI — single screen, idle/loading/success/error states, no chat UI

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Vitest + React Testing Library |
| Backend | FastAPI, Uvicorn |
| Validation | Pydantic v2 |
| AI orchestration | LangChain (`langchain-core`, `langchain-community`, `langchain-text-splitters`) |
| LLM + embeddings | Gemini via `langchain-google-genai` |
| Vector store | FAISS (`faiss-cpu`) |
| Knowledge base | Plain Markdown files |
| Testing | Pytest + pytest-asyncio (backend), Vitest (frontend) |

## Project structure

```
ruleguard-ai/
├── JOB-CARD.md
├── README.md
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes.py
│   │   ├── schemas/risk.py
│   │   ├── services/{risk_service,rag_service,gemini_service}.py
│   │   ├── core/{config,exceptions,logging_utils}.py
│   │   └── prompts/risk-v1.md
│   ├── kb/{authentication,authorization,api_security,input_validation,rate_limiting,sensitive_data}.md
│   ├── data/faiss_index/        (generated by scripts/build_index.py, git-ignored)
│   ├── scripts/build_index.py
│   ├── evals/{cases.json,run_eval.py}
│   ├── tests/{test_api,test_schema,test_rag,test_gemini_service}.py
│   └── logs/                    (quarantine.jsonl written here at runtime, git-ignored)
└── frontend/
    ├── .env.example
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── api/riskClient.js
        ├── hooks/useRiskAssessment.js
        ├── components/RiskAssessment.jsx
        └── test/setup.js, *.test.js(x)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- A Gemini API key (Google AI Studio) — required for real RAG indexing and real judgements.
  Not required to run `pytest` (fully mocked) or to use stub mode.

## Backend setup

```bash
cd ruleguard-ai/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `backend/.env`:

| Variable | Meaning | Default |
|---|---|---|
| `GEMINI_API_KEY` | Your Gemini API key | *(empty — required for real calls)* |
| `GEMINI_MODEL` | Chat model for judgements | `gemini-2.5-flash` |
| `EMBEDDING_MODEL` | Embedding model for FAISS | `models/embedding-001` |
| `LLM_ENABLED` | Kill switch | `true` |
| `LLM_STUB` | Stub mode | `0` |
| `LLM_TIMEOUT_SECONDS` | Per-call timeout | `30` |
| `LLM_MAX_RETRIES` | Bounded provider retries | `2` |
| `RAG_TOP_K` | Chunks retrieved per request | `4` |
| `PROMPT_VERSION` | Which `prompts/<version>.md` to load | `risk-v1` |
| `REVIEW_THRESHOLD` | Confidence below this forces `requires_review=true` | `0.75` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |

### Knowledge base

Six Markdown files under `backend/kb/`: `authentication.md`, `authorization.md`,
`api_security.md`, `input_validation.md`, `rate_limiting.md`, `sensitive_data.md`. Each
holds a handful of short, numbered rules (`AUTH-001`, `AUTHZ-002`, ...). Edit or add
`.md` files here to change what RuleGuard AI knows — then rebuild the index (below).

### Build the FAISS index

Requires a real `GEMINI_API_KEY` (uses embedding quota — a handful of calls for 6 files):

```bash
python scripts/build_index.py
```

Rerun this any time `kb/*.md` changes. The index is saved to `backend/data/faiss_index/`
and is `.gitignore`d — every environment builds its own copy.

### Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

## Frontend setup

```bash
cd ruleguard-ai/frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

Open the printed local URL (default `http://localhost:5173`). Single screen: paste a
technical request, click **Assess Risk**, read the result. No chat history, no threads.

## API usage

```
POST /api/v1/risk/judge
Content-Type: application/json

{ "request": "string, 1-2000 characters" }
```

### Valid request

```bash
curl -X POST http://localhost:8000/api/v1/risk/judge \
  -H "Content-Type: application/json" \
  -d "{\"request\":\"Allow any logged-in user to delete another user's account.\"}"
```

**Response — run the command above yourself and paste the real output here. The
example below is the expected shape only, not an actual recorded run:**

```
<PASTE ACTUAL RESPONSE JSON HERE>
```

### Invalid request (rejected before any model call)

```bash
curl -X POST http://localhost:8000/api/v1/risk/judge \
  -H "Content-Type: application/json" \
  -d "{\"request\":\"\"}"
```

```json
{ "error": "validation_error", "message": "request: String should have at least 1 character" }
```

### Error contract

| Situation | HTTP |
|---|---:|
| Successful judgement | 200 |
| Invalid input (before any model call) | 400 |
| Model output invalid after 1 repair attempt | 422 |
| Provider failure (non-retryable, or retries exhausted) | 502 |
| LLM timeout (after bounded retries) | 504 |
| AI disabled (`LLM_ENABLED=false`) | 503 |
| Unexpected server error | 500 |

Raw Gemini text and raw provider error bodies are never returned to the caller — every
response, success or failure, is one of the shapes above.

## Testing

Backend — fully mocked, no API key or network needed:

```bash
cd backend
pytest -v                                # everything
pytest tests/test_schema.py -v           # Pydantic contract: enums, bounds, extra=forbid
pytest tests/test_api.py -v              # input validation, kill switch, stub mode, /health
pytest tests/test_rag.py -v              # loader -> splitter -> FAISS build/save/load -> retrieve
pytest tests/test_gemini_service.py -v   # timeout, retry classification, repair, quarantine
```

**Run the command above yourself and record the real result — do not assume all
tests pass without running them:**

```
<PASTE `pytest -v` SUMMARY LINE HERE, e.g. "38 passed in 4.10s">
```

Frontend:

```bash
cd frontend
npm test
```

```
<PASTE `npm test` SUMMARY HERE>
```

## Evaluation

`backend/evals/cases.json` — 8 hand-labelled cases (normal authentication, an
authorization violation, input validation, rate limiting, sensitive data exposure, a
normal API design change, an ambiguous request, and a prompt-injection attempt).
`backend/evals/run_eval.py` posts each case to a running server and scores on
`category` — the spec's key field. `risk_level` is checked and printed as an
informational note only, except case-08, which is failed outright if the model
returns `risk_level: "low"` for the injection attempt (i.e., if it simply complied).

```bash
# with the backend running, a real GEMINI_API_KEY, and a built FAISS index:
python evals/run_eval.py
```

**Evaluation score — not run. This has not been generated and must not be assumed.
Run the command above and paste the real output below, with the date and prompt
version:**

```
Date: <run date>
Prompt version: risk-v1
Score: <PASTE — e.g. "6/8, 75.0%">
Failures: <PASTE case ids and expected/received, if any>
```

## Reliability strategy

1. Pydantic validates the request before any model call (`RiskRequest`, 1-2000 chars).
2. The kill switch (`LLM_ENABLED`) is checked before stub mode, before RAG, before Gemini.
3. Stub mode returns a fixed, schema-valid response with zero model calls.
4. Each Gemini call is wrapped in `asyncio.wait_for(timeout=LLM_TIMEOUT_SECONDS)`.
5. Failures are classified retryable vs. not (`gemini_service._classify_error`) —
   timeouts/429/5xx retry with exponential backoff + jitter, bounded by
   `LLM_MAX_RETRIES`; 400/401/403 never retry.
6. The model's raw text is parsed for a JSON object and validated against
   `RiskJudgement` (`extra="forbid"`, closed enums, bounded confidence/reason).
7. On the first invalid response, exactly one repair call is made with the original
   task, the previous answer, and the validation error attached.
8. If the repair is also invalid, the raw output is quarantined to
   `backend/logs/quarantine.jsonl` and the API returns 422 — never a guess.
9. `requires_review` is forced `true` whenever confidence is below
   `REVIEW_THRESHOLD` **or** the category is `other`, regardless of what the model
   itself reported — a business-rule safety net that doesn't depend on model
   compliance (system design section 38).
10. Any unclassified failure (a bug, a missing FAISS index, etc.) is caught by a
    last-resort handler, logged, and returned as a controlled 500 — never a raw
    traceback.

## Cost and usage logging

Every model call (success, retry, or failure) emits one structured JSON log line to
stdout, e.g.:

```json
{"event": "llm_call", "prompt_version": "risk-v1", "model": "gemini-2.5-flash", "input_tokens": 812, "output_tokens": 96, "duration_ms": 1830, "repair_count": 0, "status": "success"}
```

`input_tokens`/`output_tokens` come from the response's `usage_metadata`; if a given
SDK path doesn't expose one, it is logged as `null`, never invented.

**Cost estimate — methodology only, this is not a measured result.** Once you have a
real `llm_call` log line, look up current per-token pricing for your `GEMINI_MODEL`
(do not reuse any numbers you've seen elsewhere — pricing and models both change) and
fill in:

```
cost per request    = (input_tokens / 1,000,000 x input_$/M) + (output_tokens / 1,000,000 x output_$/M)
cost per 10,000/day  = cost per request x 10,000

<PASTE: input_tokens, output_tokens, $/M input, $/M output, computed cost/request, cost/10k/day>
```

## Kill switch and stub mode

- `LLM_ENABLED=false` -> every call to `/api/v1/risk/judge` returns `503 llm_disabled`
  immediately, zero model calls, zero RAG calls. For outages, runaway spend, or a
  model behaving badly in production.
- `LLM_STUB=1` (with `LLM_ENABLED=true`) -> returns a fixed schema-valid response, zero
  model calls, zero RAG calls, zero FAISS index dependency. For local frontend
  development and CI smoke tests without spending quota.
- The kill switch is checked **before** stub mode — disabling the feature always wins.

## Prompt versioning

The prompt lives in `backend/app/prompts/<PROMPT_VERSION>.md` (currently `risk-v1.md`),
never as a string in application code. It is loaded fresh per request from disk. To
change behavior: copy to `risk-v2.md`, edit, set `PROMPT_VERSION=risk-v2` in `.env`,
re-run the eval, and compare scores before adopting it.

## Security notes

- `GEMINI_API_KEY` lives only in `backend/.env` (git-ignored); never sent to the
  frontend, never logged, never in this README.
- Request text is capped at 2000 characters before it reaches any expensive operation.
- The user's request is always sent as a separate message from the system prompt —
  never string-concatenated into it — and the system prompt explicitly instructs the
  model to treat embedded instructions in the request as content, not commands (see
  evaluation case-08).
- `logs/quarantine.jsonl` stores failed raw model output for debugging; it is
  git-ignored and should be treated as containing request content.
- CORS is restricted to `CORS_ORIGINS` (default `http://localhost:5173`) — never use
  `allow_origins=["*"]` outside local development.

## Limitations

RuleGuard AI can claim: AI-assisted technical risk assessment, retrieval of relevant
internal rules, validated model output, handling of common provider failures, a
human-review signal, and a measurable evaluation set.

It cannot claim: perfect security detection, guaranteed correctness, autonomous
security enforcement, correct interpretation of every possible request, or
human-level security expertise. `confidence` is the model's self-reported estimate,
not a calibrated probability of correctness. This is an engineering demonstration of
a trustworthy AI-integration pattern, not a substitute for human security review.

## Future improvements

Provider abstraction (swap Gemini for another OpenAI-compatible or local model behind
one interface); a larger (25+ case) evaluation set with easy/hard splits; prompt v1
vs. v2 comparison tooling; response caching on `hash(request + prompt_version)`;
persistent assessment history (would need a database — intentionally out of scope for
this MVP); API authentication and endpoint-level rate limiting for real production
exposure; latency/failure-rate/token-usage monitoring dashboards.

## Suggested commit plan

```
Stage 0: project setup, job card, Gemini provider config
Stage 1: FastAPI endpoint, schemas, stub mode
Stage 2: LangChain RAG, FAISS knowledge base, versioned prompt, Gemini wired up
Stage 3: output parsing, validation, repair flow, quarantine
Stage 4: timeout, retries, usage logging, kill switch
Stage 5: eval set, backend tests, README
Stage 6: React assessment UI + frontend tests
```
