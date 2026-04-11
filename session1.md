# SESSION1.MD — Code Review & Security Audit CLI (Personal Tool)
## Rebuilt from Scalar Hackathon codebase | Offline-first | Ollama-powered
### Last updated: Session 1 | Status: Plan locked, ready to start coding

---

## ⚡ CONTEXT RECOVERY PROMPT
If starting a new Claude or Gemini session, paste this first:

> "I'm converting a hackathon FastAPI project into a personal CLI tool for
> offline code review and security auditing using Ollama (local LLM, no internet).
> Gemini codes, Claude reviews. Here is session1.md and the relevant files.
> Read the CURRENT TASK section and continue from there."

---

## STRATEGY: SURGICAL MODIFICATION (not a rewrite)

The graders in `app/graders/` contain real bug-detection and OWASP security logic.
We keep them. We delete the server. We build a CLI wrapper on top.

### What gets DELETED (do this first, manually)
```
app/main.py
app/config.py
app/routes/          (entire folder)
app/environment/     (entire folder)
app/models/          (entire folder)
baseline/            (entire folder)
data/tasks/          (the 3 JSON files — keep the folder)
openenv.yaml
Dockerfile
sast_check.sh
temp.txt
```

### What gets KEPT (do not touch)
```
app/graders/base_grader.py     ← abstract base class
app/graders/task1_grader.py    ← bug detection logic (AST-based)
app/graders/task2_grader.py    ← OWASP security regex matching
app/graders/task3_grader.py    ← composite scorer
_context/                      ← reference only
tests/                         ← keep structure, tests rewritten later
```

### What gets CREATED (new files)
```
review.py            ← CLI entry point
cli/__init__.py
cli/args.py          ← argparse
cli/reader.py        ← read code file, detect language
cli/prompter.py      ← build Ollama prompt
cli/ollama_client.py ← POST to localhost:11434
cli/parser.py        ← parse LLM response into structured findings
cli/reporter.py      ← print colored report to terminal
```

### What gets MODIFIED
```
requirements.txt     ← replace with: requests, colorama
README.md            ← rewrite for CLI usage
```

---

## FINAL FOLDER STRUCTURE (after changes)

```
CODE_REVIEW_SECURITY_WORKFLOW/
│   review.py
│   requirements.txt
│   README.md
│
├── cli/
│   │   __init__.py
│   │   args.py
│   │   reader.py
│   │   prompter.py
│   │   ollama_client.py
│   │   parser.py
│   └── reporter.py
│
├── app/
│   └── graders/
│       │   __init__.py
│       │   base_grader.py
│       │   task1_grader.py
│       │   task2_grader.py
│       └── task3_grader.py
│
└── tests/
```

---

## HOW THE TOOL WORKS

```bash
python review.py myfile.py                         # full review
python review.py myfile.py --mode bugs             # bugs only
python review.py myfile.py --mode security         # security only
python review.py myfile.py --model deepseek-coder  # different model
python review.py myfile.py --output report.txt     # save to file
```

**Flow:**
1. `args.py` parses the command
2. `reader.py` reads the file, detects language
3. `prompter.py` builds a prompt for Ollama
4. `ollama_client.py` sends it to `localhost:11434` (fully offline)
5. `parser.py` parses LLM response into structured findings
6. `reporter.py` prints a clean colored report (and optionally saves it)

---

## INTERFACE CONTRACTS

### cli/args.py
```
parse_args() -> argparse.Namespace
  .file: str          # path to code file (positional, required)
  .mode: str          # "bugs" | "security" | "full" (default: "full")
  .model: str         # ollama model name (default: "codellama")
  .output: str|None   # file path to save report, or None
```

### cli/reader.py
```
read_file(path: str) -> dict
  returns: { "code": str, "language": str, "filename": str, "lines": int }
  language from extension: .py→python, .js→javascript, .ts→typescript,
    .java→java, .go→go, .rb→ruby, .php→php, .c/.cpp→c/c++, else→"unknown"
  raises: FileNotFoundError if path doesn't exist
  raises: ValueError if file is empty
```

### cli/prompter.py
```
build_prompt(code: str, language: str, mode: str) -> str
  Builds prompt asking Ollama to respond in EXACTLY this format:

  BUGS:
  - Line N: <description>
  (or "None found")

  SECURITY:
  - <VULN_TYPE>: <description>
  (or "None found")

  SUMMARY:
  <one paragraph>

  mode="bugs"     → instruct model to fill BUGS section only
  mode="security" → instruct model to fill SECURITY section only
  mode="full"     → all three sections
```

### cli/ollama_client.py
```
query_ollama(prompt: str, model: str) -> str
  POST http://localhost:11434/api/generate
  body: {"model": model, "prompt": prompt, "stream": False}
  returns: response["response"] as string
  raises: ConnectionError("Ollama not running. Start it with: ollama serve")
  raises: ValueError(f"Model '{model}' not found. Run: ollama pull {model}")
  timeout: 120 seconds
```

### cli/parser.py
```
parse_response(raw: str, mode: str) -> dict
  returns: {
    "bugs":     [ {"line": int|None, "description": str} ],
    "security": [ {"type": str, "description": str} ],
    "summary":  str
  }
  Never raises. Returns empty lists/string for missing sections.
  Handles messy LLM output gracefully.
```

### cli/reporter.py
```
print_report(findings: dict, filename: str) -> None
  Terminal output:
  ══════════════════════════════════════
   CODE REVIEW REPORT: filename.py
  ══════════════════════════════════════
   🐛 BUGS  (2 found)
     Line 4 : infinite loop — n incremented instead of decremented
  ──────────────────────────────────────
   🔒 SECURITY  (1 found)
     SQL_INJECTION : user input passed directly to db.execute()
  ──────────────────────────────────────
   📋 SUMMARY
     The function has a critical infinite loop...
  ══════════════════════════════════════

save_report(findings: dict, filename: str, output_path: str) -> None
  Saves same content (no color codes) to output_path
```

### review.py (entry point)
```python
# from cli.args import parse_args
# from cli.reader import read_file
# from cli.prompter import build_prompt
# from cli.ollama_client import query_ollama
# from cli.parser import parse_response
# from cli.reporter import print_report, save_report
#
# args = parse_args()
# file_data = read_file(args.file)
# prompt = build_prompt(file_data["code"], file_data["language"], args.mode)
# raw = query_ollama(prompt, args.model)
# findings = parse_response(raw, args.mode)
# print_report(findings, file_data["filename"])
# if args.output:
#     save_report(findings, file_data["filename"], args.output)
```

---

## GEMINI PROMPT TEMPLATE

For each file, give Gemini this:

```
You are coding one file of a personal CLI tool: a local offline code reviewer
powered by Ollama. No frameworks, no FastAPI, no servers.
Python 3.11. Only allowed dependencies: requests, colorama.

Here is the interface contract for the file you are writing:
[paste the relevant contract from INTERFACE CONTRACTS above]

Rules:
- Follow the contract exactly — function names, parameters, return shapes
- No silent exception swallowing — surface errors clearly
- No internet calls — Ollama only at localhost:11434
- Keep it under 80 lines
- Return ONLY the file content, no explanation.

Write [filename] now.
```

---

## CLAUDE'S REVIEW CHECKLIST

After Gemini writes each file, paste it here. Claude checks:
- [ ] Function signatures match contract
- [ ] Return types match contract
- [ ] Errors raised match contract
- [ ] No silent failures
- [ ] No hardcoded model names or paths
- [ ] `ollama_client.py`: reads `response["response"]`, not `response["text"]`
- [ ] `parser.py`: handles empty/missing sections without crashing
- [ ] `reporter.py`: uses colorama for Windows-compatible color

---

## TASK REGISTRY

| # | File | Action | Status | Notes |
|---|------|--------|--------|-------|
| 0 | Repo cleanup | DELETE files listed above | NOT STARTED | Manual step — do first |
| 1 | `cli/__init__.py` | CREATE (empty) | NOT STARTED | |
| 2 | `cli/args.py` | CREATE | NOT STARTED | |
| 3 | `cli/reader.py` | CREATE | NOT STARTED | |
| 4 | `cli/ollama_client.py` | CREATE | NOT STARTED | |
| 5 | `cli/prompter.py` | CREATE | NOT STARTED | |
| 6 | `cli/parser.py` | CREATE | NOT STARTED | |
| 7 | `cli/reporter.py` | CREATE | NOT STARTED | |
| 8 | `review.py` | CREATE | NOT STARTED | |
| 9 | `requirements.txt` | REPLACE | NOT STARTED | requests, colorama |
| 10 | `app/graders/` | VERIFY | NOT STARTED | Check for env coupling |
| 11 | `README.md` | REWRITE | NOT STARTED | |

---

## SESSION LOG

### Session 1
- Completed: Architecture decision (surgical mod), contracts written, task registry created
- Deleted: NOT YET (manual step)
- Files coded: NONE YET
- Next: Manual deletion → Task 1 (cli/__init__.py) → Task 2 (args.py) via Gemini

---

## CURRENT TASK

### Step 0 — YOU do this manually right now:
Delete from your repo:
```
app/main.py
app/config.py
app/routes/         (whole folder)
app/environment/    (whole folder)
app/models/         (whole folder)
baseline/           (whole folder)
data/tasks/task1_episodes.json
data/tasks/task2_episodes.json
data/tasks/task3_episodes.json
openenv.yaml
Dockerfile
sast_check.sh
temp.txt
```
Create folder: `cli/` with an empty `cli/__init__.py` inside it.

### Step 1 — Give Gemini this prompt for `cli/args.py`:

```
You are coding one file of a personal CLI tool: a local offline code reviewer
powered by Ollama. No frameworks, no FastAPI, no servers.
Python 3.11. Only allowed dependencies: requests, colorama.

Interface contract:

parse_args() -> argparse.Namespace
  .file: str          # path to code file (positional, required)
  .mode: str          # "bugs" | "security" | "full" (default: "full")
  .model: str         # ollama model name (default: "codellama")
  .output: str|None   # file path to save report, or None

Rules:
- Follow the contract exactly
- Add a helpful description string for the tool
- Validate that .mode is one of the three allowed values (argparse choices)
- No silent exception swallowing
- Under 80 lines

Write cli/args.py now. Return ONLY the file content, no explanation.
```

### After Gemini writes args.py → paste it here for Claude to review.

---

*Claude updates this file after reviewing each file Gemini produces.*
*Always attach this file + current task's files when switching sessions.*
