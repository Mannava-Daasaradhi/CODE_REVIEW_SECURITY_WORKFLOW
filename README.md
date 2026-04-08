# PR Review & Security Audit — OpenEnv Environment

An OpenEnv-compliant AI training environment built for the Scalar Hackathon by Meta. It evaluates AI agents on two high-value engineering tasks — code review and security auditing — across three difficulty tiers, using fully deterministic, LLM-free graders.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     AI Agent (external)                  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (OpenEnv API)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                                                          │
│  POST /reset ──► episode_loader ──► env.py ──► Obs.     │
│  POST /step  ──► Pydantic validate ──► env.py            │
│                         │                               │
│              ┌──────────▼──────────┐                    │
│              │   Grader Router     │                    │
│              ├─────────────────────┤                    │
│              │ Task 1: bug detect  │ (line matching)    │
│              │ Task 2: OWASP vulns │ (regex-based)      │
│              │ Task 3: PR review   │ (composite)        │
│              └──────────┬──────────┘                    │
│                         │ reward: float [0.0, 1.0]      │
│                         ▼                               │
│                    StepResult                           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              data/tasks/*.json (episode store)           │
│   task1_episodes.json | task2_episodes.json             │
│   task3_episodes.json                                   │
└─────────────────────────────────────────────────────────┘
```

**Key design principle**: Ground truth never leaves the server. It is loaded internally by the grader and never included in any API response. Agents cannot cheat.

---

## Folder Structure

```
pr-review-env/
│
├── app/
│   ├── main.py                  # FastAPI app factory, route registration, lifespan
│   ├── config.py                # pydantic-settings Config class; all env vars here
│   │
│   ├── models/
│   │   ├── observation.py       # Observation — what the agent sees after reset/step
│   │   ├── action.py            # Action — the agent's structured analysis output
│   │   ├── reward.py            # Reward, StepResult returned from /step
│   │   └── state.py             # EnvironmentState returned from /state
│   │
│   ├── environment/
│   │   ├── env.py               # Core environment logic: reset(), step(), state()
│   │   └── episode_loader.py    # Reads episode JSON files, manages episode cycling
│   │
│   ├── graders/
│   │   ├── base_grader.py       # Abstract base class all graders inherit from
│   │   ├── task1_grader.py      # Easy: recall-based bug line detection
│   │   ├── task2_grader.py      # Medium: OWASP vulnerability keyword matching
│   │   └── task3_grader.py      # Hard: weighted composite of bug + vuln + review quality
│   │
│   └── routes/
│       ├── reset.py             # POST /reset
│       ├── step.py              # POST /step
│       └── state.py             # GET /state
│
├── data/
│   └── tasks/
│       ├── task1_episodes.json  # Easy difficulty episodes (populate before Phase 5)
│       ├── task2_episodes.json  # Medium difficulty episodes
│       └── task3_episodes.json  # Hard difficulty episodes
│
├── baseline/
│   └── run_baseline.py          # Standalone Gemini agent script for benchmarking
│
├── tests/
│   ├── test_graders.py          # Determinism tests + correctness tests per grader
│   ├── test_models.py           # Pydantic model validation edge cases
│   └── test_routes.py           # HTTP integration tests for all three routes
│
├── openenv.yaml                 # OpenEnv metadata (required for openenv validate)
├── Dockerfile                   # Production container, linux/amd64, port 7860
├── requirements.txt             # All deps pinned at exact versions
├── .env.example                 # Safe template — copy to .env, fill GEMINI_API_KEY
├── .gitignore
├── README.md                    # This file
└── claude.md                    # Internal AI passport (architecture decisions)
```

---

## Prerequisites

- Python 3.11 (exact — not 3.10, not 3.12)
- Docker (for containerization and local testing)
- `openenv` CLI installed (`pip install openenv`)
- A Gemini API key (for the baseline script only — not needed to run the environment)
- A HuggingFace account with Spaces access (for deployment)

---

## Setup

### 1. Clone and create environment

```bash
git clone https://github.com/your-org/pr-review-env.git
cd pr-review-env

python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=AI...
# Never commit .env
```

### 3. Verify OpenEnv spec compliance

```bash
openenv validate openenv.yaml
# Expected: PASSED — all checks green
```

---

## Running the Environment

### Development (local, with auto-reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

### Production (via Docker)

```bash
docker build -t pr-review-env .
docker run -p 7860:7860 --env-file .env pr-review-env
```

Environment is now available at `http://localhost:7860`.

### Validate against live local instance

```bash
openenv validate http://localhost:7860
```

---

## API Reference

All endpoints follow the OpenEnv specification.

### `POST /reset`

Starts a new episode. Returns an Observation containing the code snippet and task instructions.

**Request body (optional):**
```json
{ "task_difficulty": "easy" }
```
`task_difficulty` accepts `"easy"`, `"medium"`, `"hard"`, or omit for round-robin cycling.

**Response:**
```json
{
  "task_id": "task1_ep_003",
  "difficulty": "easy",
  "code_snippet": "def get_user(id):\n    return db.query(f'SELECT * FROM users WHERE id={id}')",
  "instructions": "Identify all bugs in the following function. Return the line numbers where bugs occur."
}
```

---

### `POST /step`

Submit the agent's analysis. Returns a reward score and episode completion status.

**Request body:**
```json
{
  "flagged_lines": [2],
  "findings": [
    { "type": "sql_injection", "description": "User input directly interpolated into SQL query on line 2." }
  ],
  "review_text": "Line 2 contains a critical SQL injection vulnerability. Must use parameterized queries."
}
```

All fields are optional at the schema level — the grader awards partial credit for what is provided. For Task 1, only `flagged_lines` is scored. For Task 2, only `findings` is scored. For Task 3, all three are scored in a weighted composite.

**Response:**
```json
{
  "observation": { "task_id": "task1_ep_003", "difficulty": "easy", "code_snippet": "...", "instructions": "..." },
  "reward": 0.85,
  "done": true,
  "info": { "bug_score": 1.0, "security_score": 0.75, "review_quality_score": 0.75 }
}
```

`done` is always `true` after one step. Each episode is a single-turn interaction.

---

### `GET /state`

Returns internal environment state for debugging. Does not include ground truth.

**Response:**
```json
{
  "current_task_id": "task1_ep_003",
  "difficulty": "easy",
  "step_count": 1,
  "last_reward": 0.85,
  "initialized": true
}
```

---

## Reward Design

Rewards are partial-credit and deterministic. The same agent action on the same episode always returns the same score.

### Task 1 — Easy (Bug Detection)

| Scenario | Score |
|---|---|
| All bug lines correctly identified | 1.0 |
| Half the bug lines found | 0.5 |
| No bugs found | 0.0 |
| Flagged every line (spam) | score − 0.1 penalty |

Formula: `recall = len(correct_flags ∩ ground_truth_bugs) / len(ground_truth_bugs)`

Spam penalty applies when `len(flagged_lines) > 3 × len(ground_truth_bugs)`.

### Task 2 — Medium (OWASP Vulnerability Detection)

| Scenario | Score |
|---|---|
| All 3 vulnerabilities found | 1.0 |
| 2 of 3 found | ~0.67 |
| 1 of 3 found | ~0.33 |
| 0 found | 0.0 |
| Excessive false positives | − 0.05 per FP beyond 2× ground truth count |

### Task 3 — Hard (PR Review Composite)

| Sub-score | Weight | Logic |
|---|---|---|
| Bug detection | 40% | Task 1 formula |
| Security findings | 40% | Task 2 formula |
| Review quality | 20% | Keyword rubric (see below) |

**Review quality rubric** (each criterion worth 0.25):
- Contains severity label: `critical`, `high`, `medium`, or `low`
- Contains line reference: matches `line \d+` or `L\d+`
- Contains actionable language: `should`, `must`, `recommend`, `suggest`, or `consider`
- Contains category label: `bug`, `security`, `vulnerability`, `style`, or `performance`

Final score: `0.4 × bug_score + 0.4 × security_score + 0.2 × review_quality_score`

---

## Running Tests

```bash
pytest tests/ -v
```

Every grader has a determinism test — it runs the same input 100 times and asserts the output never varies. This is the most important test in the suite. If it fails, the submission is invalid.

```bash
# Run only determinism tests
pytest tests/test_graders.py -v -k "determinism"
```

---

## Running the Baseline Script

The baseline script sends each task episode to the environment via HTTP, calls Gemini to generate an agent response, and records the scores. It is used to produce the baseline numbers reported in the README and required for Phase 1 pass.

```bash
# Environment must be running first (local or deployed)
export GEMINI_API_KEY=AI...

# Against local instance
python baseline/run_baseline.py --env-url http://localhost:7860

# Against deployed HuggingFace Space
python baseline/run_baseline.py --env-url https://your-space.hf.space
```

Output is written to `baseline/results.json`. The scores from this file are what go into the README's Baseline Scores section below.

**Note**: The baseline script is the only component that calls Gemini. The environment server itself never calls any external API.

---

## Baseline Scores

> Populated after Phase 9 (live deployment + baseline run). Fill these in before submission.

| Task | Difficulty | Baseline Score (Gemini 2.0 Flash) | Episodes |
|---|---|---|---|
| Task 1 | Easy | TBD | TBD |
| Task 2 | Medium | TBD | TBD |
| Task 3 | Hard | TBD | TBD |

---

## Episode Data Format

Episodes live in `data/tasks/`. Each file is a JSON array of episode objects.

### Task 1 episode schema

```json
{
  "task_id": "task1_ep_001",
  "difficulty": "easy",
  "code_snippet": "def divide(a, b):\n    return a / b",
  "instructions": "Identify the line numbers where bugs exist in the following function.",
  "ground_truth": {
    "bug_lines": [2]
  }
}
```

### Task 2 episode schema

```json
{
  "task_id": "task2_ep_001",
  "difficulty": "medium",
  "code_snippet": "def login(username, password):\n    query = f\"SELECT * FROM users WHERE username='{username}'\"\n    API_KEY = 'sk-hardcoded-key-here'",
  "instructions": "Identify all OWASP Top 10 vulnerabilities present in this web route.",
  "ground_truth": {
    "vuln_types": ["sql_injection", "hardcoded_secret"]
  }
}
```

### Task 3 episode schema

```json
{
  "task_id": "task3_ep_001",
  "difficulty": "hard",
  "code_snippet": "--- a/auth.py\n+++ b/auth.py\n@@ -12,6 +12,8 @@\n+    token = request.args.get('token')\n+    db.execute(f'SELECT * FROM sessions WHERE token={token}')",
  "instructions": "Review this PR diff. Identify bugs, security vulnerabilities, and provide a structured code review.",
  "ground_truth": {
    "bug_lines": [],
    "vuln_types": ["sql_injection"],
    "review_quality_keywords": ["critical", "line", "must", "security"]
  }
}
```

**Populating episodes is a human task (Phase 3).** The architecture requires at least 3 episodes per task (minimum viable). 10+ per task is recommended for meaningful baseline variance.

---

## Deployment (HuggingFace Spaces)

1. Create a new HuggingFace Space with Docker SDK
2. Set `GEMINI_API_KEY` in the Space's Secrets settings (not in the Dockerfile)
3. Push the repository to the Space's git remote
4. Confirm the Space builds and the health check at `/` responds
5. Run `openenv validate https://your-space.hf.space`

**Port**: The Dockerfile exposes port 7860. HuggingFace Spaces requires exactly this port. Do not change it.

---

## Phase-Wise Development Guide

| Phase | Owner | What was done |
|---|---|---|
| 1 — Research | Gemini | Synthesized project brief into gemini.md: tech stack, risks, build sequence, open questions |
| 2 — Architecture | Claude (Master Architect) | Produced claude.md (module map, data flow, contracts, anti-patterns) and this README |
| 3 — Environment | Human | Create venv, install deps, create GitHub repo, populate episode JSON files |
| 4 — Logic Verify | Claude (Master Architect) | Audit actual repo files: architecture match, data flow trace, edge cases, security surface |
| 5 — Coding | Antigravity / Claude Code | Implement all modules following claude.md contracts |

---

## Configuration Reference

All configuration lives in `.env` and is read by `app/config.py`. Never set these in code.

| Key | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Baseline script only | — | Gemini API key for baseline inference. Not used by the environment server. |
| `ENV_HOST` | No | `0.0.0.0` | Host the FastAPI server binds to |
| `ENV_PORT` | No | `7860` | Port (must be 7860 for HuggingFace Spaces) |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `EPISODE_SEED` | No | `42` | Random seed for episode ordering when task_difficulty is None |

---

## Security Notes

- **Graders never execute analyzed code.** All analysis uses Python's `ast` module (parse tree only) and `re` (regex). No `exec()` or `eval()` is ever called on agent-submitted or episode code.
- **Ground truth is server-side only.** It is loaded from the episode JSON at grading time and never appears in any API response.
- **No secrets in code.** `GEMINI_API_KEY` is read exclusively from environment variables.
- **Input validation at every boundary.** All agent actions are validated by Pydantic v2 strict mode before reaching any grader logic.
- **Threat model**: See `claude.md` Section 2 for full trust boundary and threat actor analysis.

---

## Known Limitations

1. **Single-turn episodes**: Each episode is one `reset()` + one `step()`. Multi-turn agentic workflows (e.g., the agent asks clarifying questions) are not supported in this version.
2. **No authentication on the API**: The OpenEnv spec does not require it, but this means the environment is fully public when deployed. Do not put sensitive data in episodes.
3. **Review quality rubric is keyword-based**: Task 3's 20% review quality sub-score uses keyword presence detection. A sophisticated agent could game this by including the keywords without writing a useful review. Acceptable for a hackathon submission; a production system would need a more robust rubric.
4. **Episode dataset is static**: Episodes are baked into the JSON files at build time. Adding new episodes requires a redeployment.

---

## Glossary

| Term | Definition |
|---|---|
| **OpenEnv** | An API specification for AI agent training environments. Defines `reset()`, `step()`, and `state()` as the standard interface. |
| **Observation** | The data structure returned to an agent after `reset()` or `step()`. Contains the code snippet and task instructions. |
| **Action** | The structured output the agent submits to `/step`. Contains flagged lines, vulnerability findings, and/or a review text. |
| **Reward** | A float in [0.0, 1.0] returned with each step result, reflecting the accuracy of the agent's action. |
| **Deterministic Grader** | A grader implemented in pure Python (AST parsing, regex, string logic) with no randomness and no LLM calls. Same input always produces same output. |
| **OWASP Top 10** | The Open Web Application Security Project's list of the ten most critical web application security risks. Task 2 focuses on SQL injection, hardcoded secrets, and XSS. |
| **Episode** | One task instance: a code snippet, instructions, and associated ground truth. Loaded by `reset()`. |
| **HuggingFace Spaces** | The deployment platform used to host the environment. Requires Docker, port 7860. |
| **openenv validate** | The CLI command that checks an environment for spec compliance. Must pass before Phase 2 judging. |

---

## Future Work

- Multi-turn episode support (agent can query for more context before submitting a final action)
- Larger episode dataset with automated generation from real open-source PRs
- Leaderboard tracking across multiple baseline models (GPT-4o, Claude 3, Gemini)
- Streaming reward signals for multi-file PR diffs (intermediate rewards per file reviewed)
- More robust review quality rubric using structural analysis rather than keyword matching

---

*Scalar Hackathon by Meta | Built with FastAPI + Pydantic v2 + Docker + HuggingFace Spaces*
