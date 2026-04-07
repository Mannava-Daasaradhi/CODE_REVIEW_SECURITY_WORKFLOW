# CLAUDE.MD — PR Review & Security Audit OpenEnv Environment
## Internal AI Passport | Phase 2 Complete | Pass to every future session

---

## 0. PROJECT IDENTITY

| Field | Value |
|---|---|
| **Project Name** | PR Review & Security Audit OpenEnv Environment |
| **Hackathon** | Scalar Hackathon by Meta |
| **Domain** | AI/ML + Cybersecurity |
| **One-line description** | An OpenEnv-compliant FastAPI environment that trains/evaluates AI agents on code review and security auditing across three deterministic difficulty tiers |
| **Phase Status** | Phase 1 (Research) ✅ \| Phase 2 (Architecture) ✅ \| Phase 3 (Env Setup) ✅ \| Phase 4 (Logic Verify) ⬜ \| Phase 5 (Coding) ⬜ |

---

## 1. ARCHITECTURAL ASSUMPTIONS

These were inferred from gemini.md and the hackathon brief. Any future session that changes these must update this block.

1. **Dataset format**: Task episodes are JSON files stored locally at `data/tasks/`. Each episode has: `task_id`, `difficulty`, `code_snippet`, `ground_truth` (structured dict). No external dataset API is assumed.
2. **Review quality rubric (Task 3)**: Deterministic keyword/structure rubric scoring presence of: severity labels (`critical/high/medium/low`), line number references, actionable language (`should`, `must`, `recommend`), and category labels (`bug`, `security`, `style`). Max 4 points — normalized to 0.0–1.0. This was an open question in gemini.md — this is the chosen resolution.
3. **One episode per task per reset()**: `reset()` cycles through the episode dataset sequentially with a fixed seed. Not streamed from an external source.
4. **Baseline script uses OpenAI API**: `OPENAI_API_KEY` is injected via environment variable only. Never hardcoded, never in any file.
5. **Single-container deployment**: Everything runs in one Docker container on port 7860. No sidecar services, no databases.
6. **No auth on the OpenEnv API**: The environment API is unauthenticated (standard for OpenEnv spec). The only secret in the system is `OPENAI_API_KEY` for the baseline script, which is external to the environment server.

---

## 2. THREAT MODEL

**Trust boundaries:**
- Outside → FastAPI endpoint: untrusted. All `Action` inputs are validated by Pydantic v2 strict mode before reaching graders.
- Grader internals: trusted (pure Python, no external calls, no user input reaches eval()/exec()).
- Baseline script → OpenAI API: API key must never be logged, never appear in responses, never be part of environment state.

**Key risks:**
- Malformed action payloads: mitigated by Pydantic v2 strict validation at route boundary.
- Code snippets that could be harmful if executed: graders use AST parsing only, never exec() the analyzed code.
- Supply chain: all deps pinned at exact versions (==) in requirements.txt.

**Out of scope:** Auth/authz on the API (not required by OpenEnv spec), PII handling (none in this system).

---

## 3. TECH STACK DECISIONS

| Component | Chosen | Why | Rejected |
|---|---|---|---|
| Language | Python 3.11 | Spec requirement | — |
| API framework | FastAPI | Spec requirement; async, Pydantic-native | Flask (no native Pydantic v2) |
| Data models | Pydantic v2 | Spec requirement; strict mode | dataclasses (no validation) |
| Grader logic | `ast` + `re` stdlib | CPU-safe, deterministic, zero extra deps | LLM grading (disqualifies submission) |
| Config | `pydantic-settings` + `.env` | Consistent with Pydantic v2 stack | dynaconf (overkill here) |
| Logging | `loguru` | Structured output, single import | structlog (overkill at this scale) |
| Testing | `pytest` | Standard | — |
| Secret management | `python-dotenv` locally; HF Spaces secrets in prod | No vault needed at this scale | AWS Secrets Manager |

---

## 4. MODULE MAP

```
pr-review-env/
│
├── app/
│   ├── main.py                  # FastAPI app factory + route registration
│   ├── config.py                # pydantic-settings Config; reads .env
│   │
│   ├── models/
│   │   ├── observation.py       # Observation model (returned by reset/step)
│   │   ├── action.py            # Action model (agent's structured output)
│   │   ├── reward.py            # Reward + StepResult models
│   │   └── state.py             # EnvironmentState model
│   │
│   ├── environment/
│   │   ├── env.py               # Core env: reset(), step(), state() logic
│   │   └── episode_loader.py    # Loads episodes from data/tasks/; manages cycling
│   │
│   ├── graders/
│   │   ├── base_grader.py       # Abstract base: grade(action, ground_truth) -> float
│   │   ├── task1_grader.py      # Easy: AST-based bug location detection
│   │   ├── task2_grader.py      # Medium: regex OWASP vuln matching, partial reward
│   │   └── task3_grader.py      # Hard: composite (bug + security + review quality)
│   │
│   └── routes/
│       ├── reset.py             # POST /reset -> Observation
│       ├── step.py              # POST /step -> StepResult
│       └── state.py             # GET /state -> EnvironmentState
│
├── data/
│   └── tasks/
│       ├── task1_episodes.json  # Easy bug detection episodes + ground truth
│       ├── task2_episodes.json  # Medium OWASP vuln episodes + ground truth
│       └── task3_episodes.json  # Hard PR diff episodes + ground truth
│
├── baseline/
│   └── run_baseline.py          # Standalone: loads env via HTTP, runs OpenAI agent
│
├── tests/
│   ├── test_graders.py          # Unit tests: determinism + correctness
│   ├── test_models.py           # Pydantic validation tests
│   └── test_routes.py           # Integration tests for all endpoints
│
├── openenv.yaml                 # OpenEnv spec metadata
├── Dockerfile                   # linux/amd64, port 7860
├── requirements.txt             # Pinned exact versions (==)
├── .env.example                 # OPENAI_API_KEY=your_key_here
├── .gitignore                   # .env, __pycache__, *.pyc, venv/
├── README.md                    # Human + agent guide
└── claude.md                    # This file
```

---

## 5. DATA FLOW

```
Agent -> POST /reset
  episode_loader loads episode from data/tasks/taskN_episodes.json
  env.py stores episode in state, constructs Observation
  <- Observation { task_id, difficulty, code_snippet, instructions }
     (ground_truth is NEVER included in Observation)

Agent -> POST /step { action: { findings: [...], review_text: "..." } }
  Pydantic validates Action (strict mode) at route boundary
  env.py routes to correct grader by task difficulty
  grader scores action against ground_truth deterministically
  <- StepResult { observation, reward: float, done: bool, info: dict }

Agent -> GET /state
  <- EnvironmentState { current episode metadata, step_count, last_reward }
```

**Critical**: Ground truth never leaves the server. Never in Observation, StepResult, or state response.

---

## 6. INTERFACE CONTRACTS

**BaseGrader.grade(action: Action, ground_truth: dict) -> float**
- Output: float in [0.0, 1.0], pure, no side effects, no external calls
- Same input MUST always produce same output
- Must NOT: call any LLM, read/write disk, use randomness

**EpisodeLoader.get_episode(task_difficulty: str, index: int) -> Episode**
- Returns episode at index for given difficulty
- Raises EpisodeNotFoundError if out of range

**Environment.reset(task_difficulty: str | None) -> Observation**
- Resets internal state, loads new episode
- task_difficulty: "easy" | "medium" | "hard" | None (cycles round-robin)

**Environment.step(action: Action) -> StepResult**
- Raises EnvironmentNotInitializedError if reset() not called first
- done=True after single step (one episode = one interaction)

---

## 7. GRADER DESIGN

### Task 1 — Bug Detection (Easy)
- Agent submits: `flagged_lines: list[int]`
- Ground truth: `bug_lines: list[int]`
- Score = `len(intersection) / len(bug_lines)` (recall-based)
- Penalty: -0.1 if `len(flagged_lines) > 3 * len(bug_lines)` (spam guard)
- Floor: 0.0

### Task 2 — OWASP Vulnerability Detection (Medium)
- Agent submits: `findings: list[{ type: str, description: str }]`
- Ground truth: `vuln_types: list[str]` e.g. ["sql_injection", "hardcoded_secret"]
- Score = matched types / total ground truth types (partial credit per finding)
- Match: case-insensitive substring on normalized type strings
- Penalty: -0.05 per false positive beyond 2x the ground truth count

### Task 3 — PR Review Composite (Hard)
- Bug score (40%): Task 1 logic on `flagged_lines`
- Security score (40%): Task 2 logic on `findings`
- Review quality score (20%): keyword rubric on `review_text`
  - +0.25 if contains severity label: critical|high|medium|low
  - +0.25 if contains line reference: pattern `line \d+` or `L\d+`
  - +0.25 if contains actionable language: should|must|recommend|suggest|consider
  - +0.25 if contains category label: bug|security|vulnerability|style|performance
- Final = 0.4 * bug + 0.4 * security + 0.2 * quality

---

## 8. ANTI-PATTERNS — HARD STOPS

| Anti-Pattern | Consequence |
|---|---|
| Any LLM call inside a grader | Disqualification — non-deterministic |
| exec() or eval() on code snippets | Security vulnerability |
| Hardcoding OPENAI_API_KEY | Credential leak |
| Returning ground_truth in any API response | Agents can cheat |
| Using >= in requirements.txt | Silent breaking changes |
| All logic in one file | Breaks agent context window and module contracts |
| Non-deterministic episode order | Baseline scores won't reproduce |
| Port other than 7860 | HuggingFace Space bind failure |
| Grader that always returns same score | Fails Phase 1 automated check |

---

## 9. OPEN QUESTIONS

1. **Episode data**: Who populates task1/2/3_episodes.json? Needs real code snippets with known bugs/vulns. Human task before Phase 5.
2. **Episode count**: Architecture assumes ≥10 per task. Minimum viable is 3 (one per difficulty to demo graders).
3. **Review quality rubric**: Resolved as keyword-based (Section 7). Flag before Phase 5 if team disagrees.
4. **[Phase 4 Blocker] Lifespan handler**: main.py needs asynccontextmanager lifespan wiring EpisodeLoader + Environment into app.state.env.
5. **[Phase 4 Blocker] Concurrency lock**: asyncio.Lock needed in Environment for reset() and step().
6. **[Phase 4 Blocker] Episode clear after step**: set self._current_episode = None after step() completes.
7. **[Phase 4 Should-Fix] difficulty=None cycling**: Replace rng.choice() with a deterministic cycling index.

---

## 10. PHASE BUILD SEQUENCE

| Step | What | Gate |
|---|---|---|
| 1 | Pydantic models + openenv.yaml | openenv validate passes |
| 2 | reset() + state() with static dummy data | API starts, routes respond |
| 3 | Task 1 grader + determinism tests | Same input → same output verified |
| 4 | Task 2 + Task 3 graders + tests | Partial rewards verified |
| 5 | Populate episode JSON files | Graders have real data |
| 6 | Baseline script | Runs cleanly in fresh venv |
| 7 | Dockerfile — build + run locally | docker run works on port 7860 |
| 8 | Deploy to HuggingFace Spaces | openenv validate passes against live URL |
| 9 | Run baseline against live Space | Lock scores for README |

---

- Python version: 3.11.9 (pyenv)
- Virtual environment: venv/ (python3.11)
- Key dependency versions: as pinned in requirements.txt
- GitHub repo: Mannava-Daasaradhi/CODE_REVIEW_SECURITY_WORKFLOW
- API confirmed running on port 7860

*claude.md v1.0 | Phase 2 Architecture | Produced by Claude Master Architect*
*Next: Phase 4 (Claude: logic verify against actual repo)*
