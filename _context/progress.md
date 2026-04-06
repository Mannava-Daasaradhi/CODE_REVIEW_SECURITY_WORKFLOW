# PROGRESS.MD — PR Review & Security Audit OpenEnv Environment
## Phase 5 Live Execution State
### Last updated: [not started] | Updated by: Antigravity

---

## ⚠️ ANTIGRAVITY: READ THIS BEFORE WRITING ANY CODE

This file is your memory across sessions. Before doing anything:

1. Read the full task table below
2. Only work on tasks marked `NOT STARTED`
3. If a task is `DONE` — do not touch that file under any circumstance
4. If a task is `IN PROGRESS` — read the notes column, continue from there
5. When you finish a task, update its row before ending the session
6. Never mark a task `DONE` unless its tests pass

If unsure what to do next: read `_context/claude.md` Section 10 (Phase Build Sequence),
then find the first `NOT STARTED` task below.

---

## Current Phase

**Active**: Phase 5 — Coding
**Build gate**: Phase 1 automated checks must all pass before submission

---

## Task Registry

| # | Step | Task | Status | File(s) | Test | Notes |
|---|------|------|--------|---------|------|-------|
| 1 | Models + spec | Pydantic models (Observation, Action, Reward, State) + openenv.yaml | NOT STARTED | app/models/*.py, openenv.yaml | tests/test_models.py | Gate: openenv validate must pass after this step |
| 2 | API skeleton | FastAPI app factory + reset() + state() with static dummy data | NOT STARTED | app/main.py, app/routes/reset.py, app/routes/state.py, app/environment/env.py | manual: curl /reset, /state | Gate: API starts and all routes respond |
| 3 | Task 1 grader | AST-based bug location detection + determinism tests | NOT STARTED | app/graders/task1_grader.py | tests/test_graders.py | Gate: same input → same output verified ≥ 3 times |
| 4 | Task 2 + 3 graders | OWASP regex grader + composite PR review grader | NOT STARTED | app/graders/task2_grader.py, app/graders/task3_grader.py | tests/test_graders.py | Gate: partial rewards verified — not same score every time |
| 5 | Episode data | Populate task1/2/3_episodes.json with real code snippets | NOT STARTED | data/tasks/task1_episodes.json, data/tasks/task2_episodes.json, data/tasks/task3_episodes.json | tests/test_graders.py | Human task — needs real buggy/vulnerable code examples |
| 6 | Baseline script | run_baseline.py: loads env via HTTP, runs OpenAI agent, prints scores | NOT STARTED | baseline/run_baseline.py | manual run in clean venv | OPENAI_API_KEY from env only — never hardcoded |
| 7 | Dockerfile | Docker build + run locally on port 7860 | NOT STARTED | Dockerfile, requirements.txt | docker build && docker run -p 7860:7860 | linux/amd64 target — test locally before pushing |
| 8 | HuggingFace deploy | Deploy Space, confirm openenv validate passes against live URL | NOT STARTED | — | openenv validate {HF_URL} | Gate: live URL responds and spec passes |
| 9 | Baseline vs live | Run baseline script against live HuggingFace Space, lock scores | NOT STARTED | README.md | baseline scores match local run | Lock scores into README before submission |

---

## Critical Rules for This Project

- **Graders must NEVER call any LLM** — non-deterministic output = disqualification
- **exec() and eval() on code snippets are forbidden** — use AST parsing only
- **OPENAI_API_KEY never in any file** — read from environment variable only
- **Ground truth never in any API response** — not in Observation, StepResult, or state
- **Port must be 7860** — any other port fails HuggingFace Space binding
- **requirements.txt uses == only** — no >= anywhere

---

## What Currently Exists and Works

- Project structure created (app/, data/, baseline/, tests/)
- Pydantic models: not yet written
- API: not yet running
- Graders: not yet implemented
- Docker: not yet tested
- HuggingFace: not yet deployed

---

## Active Blockers

| # | Task | Blocked by | Escalated? |
|---|------|-----------|-----------|
| 5 | Episode data | Needs human to write real buggy code examples | No |

---

## Session Log

### Session 1 — [DATE]
- Started: —
- Completed: —
- Left off at: —
- Next session should start with: Task #1 (Pydantic models + openenv.yaml)

---

## File Ownership Map

| File | Owner Task # | Status |
|------|-------------|--------|
| app/models/observation.py | #1 | NOT STARTED |
| app/models/action.py | #1 | NOT STARTED |
| app/models/reward.py | #1 | NOT STARTED |
| app/models/state.py | #1 | NOT STARTED |
| openenv.yaml | #1 | NOT STARTED |
| app/main.py | #2 | NOT STARTED |
| app/config.py | #2 | NOT STARTED |
| app/routes/reset.py | #2 | NOT STARTED |
| app/routes/step.py | #2 | NOT STARTED |
| app/routes/state.py | #2 | NOT STARTED |
| app/environment/env.py | #2 | NOT STARTED |
| app/environment/episode_loader.py | #2 | NOT STARTED |
| app/graders/base_grader.py | #3 | NOT STARTED |
| app/graders/task1_grader.py | #3 | NOT STARTED |
| app/graders/task2_grader.py | #4 | NOT STARTED |
| app/graders/task3_grader.py | #4 | NOT STARTED |
| data/tasks/task1_episodes.json | #5 | NOT STARTED |
| data/tasks/task2_episodes.json | #5 | NOT STARTED |
| data/tasks/task3_episodes.json | #5 | NOT STARTED |
| baseline/run_baseline.py | #6 | NOT STARTED |
| Dockerfile | #7 | NOT STARTED |
| requirements.txt | #7 | NOT STARTED |

---

*Updated by Antigravity at end of every session.*
*Never manually edited by human except for Task #5 (episode data).*
