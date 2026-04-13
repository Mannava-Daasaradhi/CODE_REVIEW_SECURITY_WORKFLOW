# SESSION2.MD — Code Review & Security Audit CLI
## Making it competitive | Offline-first | Ollama-powered
### Last updated: Session 2 (revised) | Status: Plan locked, ready to build

---

## ⚡ CONTEXT RECOVERY PROMPT
If starting a new Claude or Gemini session, paste this first:

> "I'm building a personal offline CLI code reviewer powered by Ollama.
> Session 1 built the core pipeline. Session 2 upgrades it to be competitive
> with tools like CodeRabbit — engineered prompts with few-shot examples and
> chain-of-thought, streaming output, self-consistency verification, model routing,
> multi-file support, git diff, severity/confidence/fix, and a full test suite.
> Gemini codes, Claude reviews. Here is session2.md. Read CURRENT TASK and continue."

---

## WHAT SESSION 1 BUILT (do not touch unless upgrading)

```
review.py                  ← entry point, wires everything together
cli/args.py                ← argparse: --mode, --model, --output
cli/reader.py              ← reads file, detects language
cli/prompter.py            ← builds Ollama prompt
cli/ollama_client.py       ← POSTs to localhost:11434
cli/parser.py              ← parses BUGS/SECURITY/SUMMARY from LLM response
cli/reporter.py            ← colored terminal output + plain file save
app/graders/               ← AST bug detection + OWASP regex (kept from hackathon)
```

**Known issues from Session 1 to fix before anything else:**
- `app/graders/` imports `from app.models.action import Action` — remove (Track A)
- `tests/` has broken files (test_models.py, test_routes.py) — gut them (Track A)
- `prompter.py` security mode sets SUMMARY to "None found" — fix (Track A)

---

## WHY THE PROMPT IS THE MOST IMPORTANT THING

Research on LLM code review automation shows few-shot prompting achieves
up to 659% higher accuracy than zero-shot for the same model. A well-prompted
codellama:7b will outperform a badly-prompted deepseek-coder:33b.
Prompt engineering is our highest-ROI investment — zero cost, maximum impact.

**Five techniques applied in Session 2:**

1. **Few-shot examples** — 2 concrete input→output examples baked into every prompt.
   Model learns exact format and quality bar from examples, not just instructions.

2. **Chain-of-thought (CoT)** — instruct model to reason before outputting.
   "First trace the data flow. Then identify trust boundaries. Then list findings."
   Improves finding quality 20-40% on local models for logic-based tasks.

3. **Persona prompting** — "You are a senior security engineer who has reviewed
   thousands of production codebases. You care about real bugs, not style issues."

4. **Negative instructions** — tell the model what NOT to do.
   "Do not flag missing docstrings. Do not flag variable naming. Only flag bugs
   that cause incorrect behavior or create exploitable security vulnerabilities."
   Local models hallucinate style warnings constantly without this.

5. **Language-specific security checklists** — injected per language.
   Python: eval/pickle/shell=True/f-string SQL/yaml.load
   JS: innerHTML/prototype pollution/JWT none alg/eval
   Java: deserialization/XXE/SSRF/reflection
   Go: goroutine leaks/unsafe pointer/integer overflow

---

## SESSION 2 STRATEGY

Five tracks, done in order:

### Track A — Fix broken things (manual, ~15 min)
### Track B — Upgrade existing files (Gemini codes, Claude reviews)
### Track C — New files (Gemini codes, Claude reviews)
### Track D — Tests (always last)
### Track E — Prompt templates (Claude writes directly into prompter.py contract)

---

## UPGRADED OUTPUT FORMAT

The new structured format Ollama must produce:

```
THINKING:
<model's reasoning about data flow, trust boundaries, control flow>

BUGS:
- Line N: [SEVERITY] <description> | Confidence: <0-100>% | Fix: <one-line fix>
(or "None found")

SECURITY:
- <VULN_TYPE>: [SEVERITY] <description> | Confidence: <0-100>% | Fix: <one-line fix>
(or "None found")

SUMMARY:
<one paragraph>

SCORE: <0-100>
```

THINKING = chain-of-thought reasoning. Parser preserves it internally but
doesn't show it unless --show-thinking flag. Models that reason before
answering produce measurably better findings.

---

## NEW INTERFACE CONTRACTS

### cli/args.py (UPGRADE)
```
parse_args() -> argparse.Namespace
  .file: str|None     # positional, nargs="?", required unless --dir or --diff
  .mode: str          # "bugs"|"security"|"full", default "full"
  .model: str         # ollama model, default "auto" (triggers router)
  .output: str|None   # save path, default None
  .severity: str      # "critical"|"high"|"medium"|"low", default "low"
  .json: bool         # store_true, output JSON
  .dir: str|None      # directory to scan
  .diff: bool         # store_true, review git diff
  .stream: bool       # store_true, stream tokens to stderr
  .verify: bool       # store_true, run self-consistency verification pass
  .show_thinking: bool # store_true, show model reasoning in report

Validation after parse:
  count = sum([bool(args.file), bool(args.dir), args.diff])
  if count > 1: parser.error("--dir, --diff, and file are mutually exclusive")
  if count == 0: parser.error("provide a file, --dir, or --diff")
```

### cli/prompter.py (FULL REWRITE — most important file)
```
build_prompt(code: str, language: str, mode: str,
             filename: str = "", context_patterns: list[str] = []) -> str

  Prompt structure (in this order):
  1. PERSONA — "You are a senior security engineer with 10+ years reviewing
     production codebases. You find real bugs that cause real failures."
  2. TASK CONTEXT — filename, language, mode being run
  3. LANGUAGE CHECKLIST — language-specific vuln types (see Track E below)
  4. NEGATIVE INSTRUCTIONS — "Do not flag: style, naming, missing docs,
     unused imports, or anything that does not cause incorrect behavior
     or a security vulnerability."
  5. FEW-SHOT EXAMPLES — 2 examples showing exact input→output format
  6. CHAIN-OF-THOUGHT INSTRUCTION — "Before writing findings:
     Step 1: Trace all data flows from input to output.
     Step 2: Identify all trust boundaries (user input, file input, env vars).
     Step 3: Look for control flow issues (loops, recursion, off-by-one).
     Step 4: Now write your THINKING section, then your findings."
  7. CODEBASE PATTERNS — injected if context_patterns non-empty
  8. OUTPUT FORMAT — exact template
  9. CODE — delimited with === CODE START === / === CODE END ===

  All 3 section headers always present.
  THINKING always requested.
  SUMMARY always filled regardless of mode.
  mode="bugs" → SECURITY says "None found"
  mode="security" → BUGS says "None found"

build_verification_prompt(code: str, findings: dict, language: str) -> str
  Shows model its own findings and asks it to audit them:
  "Below are findings from your previous review of this code.
   For each finding, respond with one of:
   CONFIRMED: <reason>
   FALSE_POSITIVE: <reason>
   UNCERTAIN: <reason>
   Be critical. If you are not confident a finding is real, say so."
  Returns prompt string.
```

### cli/ollama_client.py (UPGRADE)
```
query_ollama(prompt: str, model: str, stream: bool = False) -> str
  stream=False: existing behavior
  stream=True:
    POST with stream:true
    Read newline-delimited JSON, each chunk has "response" field
    Print each token to sys.stderr as it arrives (stdout stays clean)
    Assemble full string and return
  Same error handling. No timeout for stream mode.

list_models() -> list[str]
  GET http://localhost:11434/api/tags
  Returns list of model name strings from response["models"][*]["name"]
  Returns [] (never raises) if Ollama down or request fails
```

### cli/router.py (NEW)
```
PREFERRED = {
  "bugs":     ["deepseek-coder", "qwen2.5-coder", "codellama", "llama"],
  "security": ["qwen2.5-coder", "deepseek-coder", "codellama", "llama"],
  "full":     ["deepseek-coder", "qwen2.5-coder", "codellama", "llama"],
}

select_model(mode: str, available: list[str]) -> str
  For each name in PREFERRED[mode]:
    if any model in available starts with that name: return it
  Falls back to available[0] if nothing preferred found
  Falls back to "codellama" if available is empty
  Never raises
```

### cli/parser.py (UPGRADE)
```
parse_response(raw: str, mode: str) -> dict
  returns: {
    "bugs":     [ {"line": int|None, "description": str,
                   "severity": str, "confidence": int, "fix": str} ],
    "security": [ {"type": str, "description": str,
                   "severity": str, "confidence": int, "fix": str} ],
    "summary":  str,
    "score":    int,      # default 50
    "thinking": str       # raw THINKING section, "" if missing
  }
  severity default "UNKNOWN", confidence default 50, fix default ""
  Never raises.

parse_verification(raw: str, findings: dict) -> dict
  Parses verification output.
  Removes FALSE_POSITIVE findings.
  Reduces confidence by 20 for UNCERTAIN findings (floor 0).
  Returns adjusted findings dict (same shape).
  Never raises.
```

### cli/reporter.py (UPGRADE)
```
print_report(findings: dict, filename: str, min_severity: str = "low",
             show_thinking: bool = False) -> None

  Score color: green ≥70, yellow 40-69, red <40
  Severity colors: CRITICAL=red+bright, HIGH=red, MEDIUM=yellow, LOW=white
  Confidence bar: 10 blocks, █=filled ░=empty

  Layout:
  ══════════════════════════════════════════════
   CODE REVIEW REPORT: myfile.py    SCORE: 42/100
  ══════════════════════════════════════════════
   🐛 BUGS  (2 found)
    [CRITICAL] Line 4: infinite loop
               Confidence: ████████░░ 80%
               Fix: change n += 1 to n -= 1
  ──────────────────────────────────────────────
   🔒 SECURITY  (1 found)
    [HIGH] SQL_INJECTION: user input in db.execute()
               Confidence: ██████░░░░ 60%
               Fix: use parameterized queries
  ──────────────────────────────────────────────
   📋 SUMMARY
     ...
   📊 SCORE: 42/100
  ══════════════════════════════════════════════

print_json(findings: dict, filename: str) -> None
  Formatted JSON to stdout, no color codes.

save_report(findings: dict, filename: str, output_path: str) -> None
  Plain text, no color. Raises OSError on failure (not swallowed).
```

### cli/scanner.py (NEW)
```
SKIP_DIRS = {"__pycache__",".git","node_modules","venv",".venv",
             "dist","build",".mypy_cache",".pytest_cache","coverage"}
SUPPORTED_EXT = {".py",".js",".ts",".java",".go",".rb",".php",".c",".cpp"}

scan_directory(dirpath: str, model: str, mode: str, stream: bool = False) -> list[dict]
  Walk dirpath, skip SKIP_DIRS, collect SUPPORTED_EXT files.
  For each: read_file → build_prompt → query_ollama → parse_response
  Show progress as it goes.
  Returns: [ {"filename": str, "filepath": str, "findings": dict} ]
  raises FileNotFoundError if dirpath missing.
  raises ValueError if no supported files found.
```

### cli/differ.py (NEW)
```
get_diff_files() -> list[dict]
  Runs: git diff HEAD --unified=5
  Parses unified diff per file.
  Returns: [ {"filename": str, "language": str, "diff_content": str} ]
  raises RuntimeError("Not a git repository") if git fails
  raises RuntimeError("No changes to review") if diff empty
  Uses subprocess.run, NOT os.system.
```

### cli/progress.py (NEW)
```
show_progress(current: int, total: int, filename: str) -> None
  Prints to stderr only (stdout stays clean for --json).
  Format: Reviewing 3/12: utils.py  [████████░░░░░░░░░░░░] 25%
  Uses \r to overwrite same line.
  current == total → clear the line.
```

### review.py (UPGRADE)
```
Flow:
1.  parse args
2.  if model == "auto": list_models() → select_model(mode, available)
3.  determine mode: file / dir / diff
4.  for each file:
      read_file
      build_prompt (CoT + few-shot + language checklist)
      query_ollama (streaming if --stream)
      parse_response → findings
      if --verify:
        build_verification_prompt → query_ollama → parse_verification → findings
      print_report or print_json (with min_severity filter)
      if --output: save_report
5.  dir/diff mode: print multi-file summary at end

Errors: FileNotFoundError, ValueError, ConnectionError, RuntimeError
→ all caught separately, printed to stderr, sys.exit(1)
```

---

## TRACK E — PROMPT TEMPLATES (reference for prompter.py)

### Few-shot example 1 — Bug detection
```
--- EXAMPLE INPUT ---
def count_down(n):
    while n > 0:
        print(n)
        n += 1

--- EXAMPLE OUTPUT ---
THINKING:
Data flows: n is a parameter, printed each iteration, modified in loop body.
Trust boundaries: n comes from caller, no validation.
Control flow: while loop condition is n > 0. Loop body increments n.
Issue: if n starts positive, n > 0 stays true forever — infinite loop.

BUGS:
- Line 4: [CRITICAL] Infinite loop — n is incremented instead of decremented.
  While n > 0 will never become false if n starts positive.
  | Confidence: 99% | Fix: change n += 1 to n -= 1

SECURITY:
None found

SUMMARY:
The function contains a critical infinite loop on line 4. The loop variable n
is incremented when it should be decremented, causing the while condition to
remain permanently true for any positive input.

SCORE: 10
```

### Few-shot example 2 — Security detection
```
--- EXAMPLE INPUT ---
def get_user(username):
    conn = get_db()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query).fetchone()

--- EXAMPLE OUTPUT ---
THINKING:
Data flows: username parameter → string formatted into SQL query → executed.
Trust boundaries: username comes from caller (likely user input) — untrusted.
Control flow: simple linear function, no branching.
Issue: unsanitized user input directly concatenated into SQL string.

BUGS:
None found

SECURITY:
- SQL_INJECTION: [CRITICAL] User-controlled input concatenated into SQL query
  via f-string on line 3. Attacker can inject ' OR '1'='1 to bypass auth
  or use UNION to dump the database.
  | Confidence: 98% | Fix: use conn.execute("SELECT * FROM users WHERE name = ?", (username,))

SUMMARY:
The function is critically vulnerable to SQL injection. The username parameter
is interpolated directly into the query string without sanitization or
parameterization, allowing an attacker to execute arbitrary SQL.

SCORE: 5
```

### Language checklists (Python shown — others in prompter.py)
```python
LANGUAGE_CHECKLISTS = {
    "python": """
Python-specific issues to look for:
- SQL injection via f-strings or %-formatting in db queries
- Command injection: subprocess(shell=True) or os.system() with user input
- Code execution: eval(), exec(), pickle.loads() on untrusted data
- Path traversal: open() with unsanitized user-controlled paths
- YAML RCE: yaml.load() without Loader=yaml.SafeLoader
- Timing attack: string == comparison for secrets (use hmac.compare_digest)
- Infinite loops, off-by-one errors, unchecked recursion depth
""",
    "javascript": """
JavaScript-specific issues to look for:
- XSS: innerHTML, document.write(), dangerouslySetInnerHTML with user data
- Prototype pollution: recursive merge without hasOwnProperty check
- Code injection: eval() or Function() with user input
- JWT: verify alg field is not "none"
- Path traversal in Node.js: path.join() with unsanitized input
- ReDoS: complex regex on user-controlled strings
""",
    "java": """
Java-specific issues to look for:
- Deserialization: ObjectInputStream on untrusted data
- XXE: DocumentBuilderFactory without disabling external entities
- SQL injection: Statement.execute() with string concatenation
- SSRF: URL() or HttpClient with user-controlled host
- Log injection: unsanitized user data in log statements
""",
    "go": """
Go-specific issues to look for:
- Command injection: exec.Command with user-controlled args
- Path traversal: os.Open() with unsanitized paths
- Goroutine leak: goroutines started with no clear termination
- Integer overflow in type conversions
- unsafe.Pointer misuse
""",
}
```

---

## TASK REGISTRY

| # | File | Action | Status | Notes |
|---|------|--------|--------|-------|
| A1 | `app/graders/*.py` | FIX imports | NOT STARTED | Remove Action type hints manually |
| A2 | `cli/prompter.py` | FIX summary bug | NOT STARTED | security mode SUMMARY fix |
| A3 | `tests/test_models.py` | GUT | NOT STARTED | Empty the file |
| A4 | `tests/test_routes.py` | GUT | NOT STARTED | Empty the file |
| B1 | `cli/args.py` | UPGRADE | NOT STARTED | All new flags |
| B2 | `cli/prompter.py` | FULL REWRITE | NOT STARTED | The most important file |
| B3 | `cli/ollama_client.py` | UPGRADE | NOT STARTED | streaming + list_models |
| B4 | `cli/parser.py` | UPGRADE | NOT STARTED | new fields + verification parser |
| B5 | `cli/reporter.py` | UPGRADE | NOT STARTED | severity colors + confidence bar |
| C1 | `cli/router.py` | CREATE | NOT STARTED | model auto-selection |
| C2 | `cli/scanner.py` | CREATE | NOT STARTED | multi-file scan |
| C3 | `cli/differ.py` | CREATE | NOT STARTED | git diff reader |
| C4 | `cli/progress.py` | CREATE | NOT STARTED | progress indicator |
| C5 | `review.py` | UPGRADE | NOT STARTED | wire all new pieces |
| D1 | `tests/conftest.py` | REWRITE | NOT STARTED | shared fixtures |
| D2 | `tests/test_args.py` | CREATE | NOT STARTED | |
| D3 | `tests/test_reader.py` | CREATE | NOT STARTED | |
| D4 | `tests/test_parser.py` | CREATE | NOT STARTED | |
| D5 | `tests/test_reporter.py` | CREATE | NOT STARTED | |
| D6 | `tests/test_graders.py` | REWRITE | NOT STARTED | keep determinism tests |
| D7 | `tests/test_router.py` | CREATE | NOT STARTED | |

---

## CLAUDE'S REVIEW CHECKLIST (upgraded)

**args.py:**
- [ ] mutual exclusion validated at runtime (parser.error)
- [ ] model default is "auto" not "codellama"
- [ ] all store_true flags present: json, diff, stream, verify, show_thinking
- [ ] choices= used for mode and severity

**prompter.py (most critical):**
- [ ] THINKING section requested in prompt
- [ ] Persona present
- [ ] Language checklist injected based on language param
- [ ] 2 few-shot examples present (one bug, one security)
- [ ] Chain-of-thought steps present ("Step 1: trace data flow...")
- [ ] Negative instructions present
- [ ] Code delimited with === CODE START === / === CODE END ===
- [ ] All 3 headers always present
- [ ] SUMMARY always filled regardless of mode
- [ ] build_verification_prompt() present and correct

**ollama_client.py:**
- [ ] stream=True reads chunked JSON (not full response at once)
- [ ] streaming tokens go to stderr not stdout
- [ ] list_models() returns [] on failure (never raises)
- [ ] list_models() reads response["models"][*]["name"]

**parser.py:**
- [ ] "thinking" key present in return dict
- [ ] severity default "UNKNOWN"
- [ ] confidence default 50
- [ ] score default 50
- [ ] parse_verification removes FALSE_POSITIVE, reduces UNCERTAIN by 20
- [ ] Never raises

**reporter.py:**
- [ ] Score color: green/yellow/red thresholds correct
- [ ] Confidence bar exactly 10 blocks
- [ ] min_severity filter correct (low=show all, critical=show only critical)
- [ ] show_thinking param respected
- [ ] print_json produces valid JSON

**router.py:**
- [ ] startswith used (not ==) for model matching
- [ ] Falls back to available[0] then "codellama"

---

## ORDER OF ATTACK

Track A first (manual, ~15 min). Then:
1. B1 args.py
2. C1 router.py
3. B3 ollama_client.py
4. **B2 prompter.py ← review this one most carefully**
5. B4 parser.py
6. B5 reporter.py
7. C2 scanner.py
8. C3 differ.py
9. C4 progress.py
10. C5 review.py
11. Track D tests

---

## SESSION LOG

### Session 1
- Built: full CLI pipeline
- Fixed: repo cleanup, requirements, README
- Known issues: grader imports, prompter summary bug, broken test files

### Session 2
- Completed: NOT STARTED
- Next: Track A manual fixes → B1 args.py via Gemini

---

## CURRENT TASK

### Track A — Do these manually before anything else

**A1:** In all 4 grader files — remove `from app.models.action import Action`
and replace `action: Action` with `action` (no annotation).

**A2:** In `cli/prompter.py`:
```python
# mode == "security" — change:
"For the BUGS and SUMMARY sections, write EXACTLY 'None found'."
# to:
"For the BUGS section, write EXACTLY 'None found'. Write a brief SUMMARY of security findings."

# mode == "bugs" — change:
"For the SECURITY and SUMMARY sections, write EXACTLY 'None found'."
# to:
"For the SECURITY section, write EXACTLY 'None found'. Write a brief SUMMARY of bug findings."
```

**A3+A4:** Delete all content from `tests/test_models.py` and `tests/test_routes.py`.

### Then: Give Gemini the B1 prompt for upgraded `cli/args.py`

```
You are coding one file of a personal CLI tool: a local offline code reviewer
powered by Ollama. No frameworks, no FastAPI, no servers.
Python 3.11. Only allowed dependencies: requests, colorama.

Interface contract:

parse_args() -> argparse.Namespace
  .file: str|None     nargs="?" positional, required unless --dir or --diff
  .mode: str          "bugs"|"security"|"full", default "full", choices enforced
  .model: str         ollama model name, default "auto"
  .output: str|None   save path, default None
  .severity: str      "critical"|"high"|"medium"|"low", default "low", choices enforced
  .json: bool         store_true, default False
  .dir: str|None      directory to scan, default None
  .diff: bool         store_true, default False
  .stream: bool       store_true, default False
  .verify: bool       store_true, default False
  .show_thinking: bool store_true, default False

Validation (after parse, before return):
  count = sum([bool(args.file), bool(args.dir), args.diff])
  if count > 1: parser.error("--dir, --diff, and file are mutually exclusive. Pick one.")
  if count == 0: parser.error("Provide a file path, --dir <directory>, or --diff.")

Rules:
- choices= for mode and severity
- store_true for all boolean flags
- helpful description and 3-line epilog showing usage examples
- under 90 lines

Write cli/args.py now. Return ONLY the file content, no explanation.
```

### After Gemini writes → paste here for Claude to review.

---

*Claude updates this file after reviewing each file Gemini produces.*
*Always attach session2.md when switching sessions.*
