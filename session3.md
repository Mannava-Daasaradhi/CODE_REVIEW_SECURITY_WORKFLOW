# SESSION3.MD — Code Review & Security Audit CLI
## GitHub Actions + ChromaDB Memory + Confidence Calibration + File Batching + Fix Mode
### Last updated: Session 3 (revised) | Status: Plan locked, do after Session 2

---

## ⚡ CONTEXT RECOVERY PROMPT
If starting a new Claude or Gemini session, paste this first:

> "I'm building a personal offline CLI code reviewer powered by Ollama.
> Sessions 1 and 2 built the full CLI pipeline with severity levels, confidence,
> few-shot prompting, streaming, model routing, multi-file scanning, and git diff.
> Session 3 adds: ChromaDB local memory (tool learns your codebase),
> cross-file impact analysis, file batching for large files, confidence calibration,
> GitHub Actions CI, and an interactive --fix mode that patches code.
> Gemini codes, Claude reviews. Here is session3.md. Read CURRENT TASK and continue."

---

## WHAT SESSIONS 1 + 2 BUILT

```
review.py                  ← entry: single file / --dir / --diff / --verify / --stream
cli/args.py                ← all flags including --severity, --json, --stream, --verify
cli/reader.py              ← file reading + language detection
cli/prompter.py            ← few-shot + CoT + language checklists + verification prompt
cli/ollama_client.py       ← streaming + list_models
cli/router.py              ← auto model selection per mode
cli/parser.py              ← severity, confidence, fix, score, thinking, verification
cli/reporter.py            ← severity colors, confidence bars, score, JSON output
cli/scanner.py             ← multi-file directory scan
cli/differ.py              ← git diff reader
cli/progress.py            ← progress indicator
app/graders/               ← AST (ast_grader.py) + OWASP (owasp_grader.py) logic
tests/                     ← full test suite (37 tests, all passing)
```

### ⚠️ KNOWN GOTCHAS FROM SESSION 2 — READ BEFORE CODING

**1. `parse_verification` argument order:**
The function signature is `parse_verification(findings: dict, raw: str)`.
Gemini wrote it backwards in the tests (`parse_verification(raw, findings)`).
Always call it as `parse_verification(findings, raw)` — findings dict first, raw
LLM string second.

**2. Windows UTF-8 file reads in tests:**
`reporter.py` writes box-drawing characters using UTF-8. On Windows, `pathlib`
defaults to `cp1252` which cannot decode them. Any test that reads a saved report
file must use `encoding="utf-8"`:
```python
out.read_text(encoding="utf-8")   # correct
out.read_text()                    # fails on Windows
```

**3. `select_model` argument order:**
Signature is `select_model(mode: str, available: list[str])`.
Call it as `select_model("bugs", ["model1", "model2"])` — mode first.

---

## SESSION 3 ADDITIONS — OVERVIEW

### What gets ADDED

```
cli/batcher.py             ← split large files into overlapping chunks
cli/embedder.py            ← get embeddings from Ollama (nomic-embed-text)
cli/memory.py              ← ChromaDB: store/retrieve findings, learn false positives
cli/calibrator.py          ← adjust confidence based on memory history
cli/cross_ref.py           ← cross-file impact analysis (NEW — not in session 2 plan)
cli/fixer.py               ← generate patches, show diff, apply interactively (NEW)
.github/workflows/
  code-review.yml          ← GitHub Actions: runs on every PR, posts comment

data/memory/               ← ChromaDB persists here (gitignored)
  .gitkeep
```

### What gets MODIFIED

```
cli/args.py                ← add --fix, --no-memory, --clear-memory, --batch-size, --ci
cli/prompter.py            ← inject cross_file_context param
cli/reporter.py            ← show "seen before" badge on findings
review.py                  ← full new flow: memory + batching + calibration + fix
requirements.txt           ← add: chromadb
```

---

## NEW FEATURES EXPLAINED

### 1. File Batching
Large files sent as one prompt confuse local models and exceed context limits.
`batcher.py` splits files into overlapping 150-line chunks (20-line overlap).
Each chunk reviewed independently. Findings merged and deduplicated by line.
Overlap ensures bugs at boundaries are never missed.

```
2000-line file → [1-150] [131-280] [261-410] ... → merge → deduplicate by line
```

### 2. ChromaDB Memory
After every review, each finding is stored as an embedding in ChromaDB (local, disk).
Before reviewing, similar past findings are retrieved.
If a finding was marked false positive before → suppress it.
If a finding appears 3+ times across codebase → escalate confidence.
Fully offline. Persists between runs. Gets smarter the more you use it.

### 3. Confidence Calibration
Local models report 90% confidence on everything — the score is meaningless raw.
`calibrator.py` adjusts based on:
- Historical accuracy from memory (confirmed vs false positive verdicts)
- Finding frequency across codebase
- Severity/confidence mismatch (CRITICAL at <40% confidence → downgrade to HIGH)

### 4. Cross-File Impact Analysis (NEW — key differentiator)
CodeRabbit's biggest advantage is cross-file awareness. We match it.
`cross_ref.py` reads the ChromaDB memory to find:
- Other files that call functions modified in the current file
- Similar patterns in other files that were previously flagged
- Security assumptions in other files that the current change may break
This context is injected into the prompt so the model reasons about impact,
not just the file in isolation.

### 5. Fix Mode (--fix flag)
After finding bugs and security issues, offer to patch them.
`fixer.py`:
1. Takes each finding with a Fix: suggestion
2. Builds a prompt asking Ollama to generate the patched code for that specific section
3. Shows a colored unified diff of the proposed change
4. Asks: "Apply this fix? [y/N/skip all]"
5. Applies approved patches directly to the file
This is what makes it an assistant, not just a reviewer.

### 6. GitHub Actions
`.github/workflows/code-review.yml` runs on every PR.
Uses `--diff --json --severity high --no-memory --ci` flags.
Posts findings as a formatted PR comment via GitHub API.
Uses `qwen2.5-coder:1.5b` in CI (small, fast, fits runner RAM).
Cost: zero. Free tier = 2000 min/month. One review ≈ 2 min = 1000 free reviews/month.

---

## NEW DEPENDENCIES

Add to `requirements.txt`:
```
requests
colorama
chromadb
```

Ollama handles embeddings via `nomic-embed-text`. Pull once:
```bash
ollama pull nomic-embed-text
```

---

## NEW INTERFACE CONTRACTS

### cli/batcher.py (NEW)
```
chunk_code(code: str, chunk_size: int = 150, overlap: int = 20) -> list[dict]
  Returns: [ { "chunk": str, "start_line": int, "end_line": int } ]
  Always at least one chunk. Last chunk may be smaller.
  Never raises.

merge_findings(chunk_results: list[dict], chunk_map: list[dict]) -> dict
  chunk_results: list of parse_response() dicts (one per chunk)
  chunk_map: output of chunk_code() — for line number remapping
  Remaps bug line numbers by adding (start_line - 1)
  Deduplicates: same absolute line → keep higher confidence
  Security findings deduplicated by type → keep higher confidence
  summary: join all non-empty summaries
  score: average of all chunk scores
  Returns single findings dict (same shape as parse_response())
  Never raises.
```

### cli/embedder.py (NEW)
```
get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]
  POST http://localhost:11434/api/embeddings
  body: {"model": model, "prompt": text}
  Returns response["embedding"] as list[float]
  raises ConnectionError if Ollama not running
  raises ValueError if model not found

embed_finding(finding: dict) -> str
  Returns: "{type_or_line} {description} {fix}" as single string for embedding
```

### cli/memory.py (NEW)
```
MEMORY_DIR = "data/memory"

class ReviewMemory:
  __init__(self, memory_dir: str = MEMORY_DIR) -> None
    PersistentClient pointing at memory_dir.
    Creates "findings" and "patterns" collections if missing.

  store_finding(self, filepath: str, finding: dict,
                verdict: str = "pending") -> None
    verdict: "pending"|"confirmed"|"false_positive"
    Metadata: { filepath, line, severity, type, verdict, timestamp }

  query_similar(self, finding: dict, n_results: int = 5) -> list[dict]
    Returns similar past findings with their verdicts and distances.
    Returns [] on empty collection or error. Never raises.

  is_false_positive(self, finding: dict, filepath: str,
                    threshold: float = 0.85) -> bool
    True if very similar finding (cosine dist < threshold) was marked
    false_positive for this filepath. Returns False on any error (fail open).

  get_codebase_patterns(self) -> list[str]
    Returns recurring finding descriptions seen 3+ times across codebase.

  get_related_files(self, filepath: str) -> list[str]
    Returns list of other filepaths that have findings similar to
    findings in filepath. Used by cross_ref.py.
    Returns [] on error. Never raises.

  mark_false_positive(self, filepath: str, line: int) -> None
    Updates verdict. Silent if not found.

  clear(self) -> None
    Deletes all stored findings.
```

### cli/cross_ref.py (NEW)
```
build_cross_file_context(filepath: str, memory: ReviewMemory,
                         reader_fn) -> str
  Gets related files from memory.
  For each related file (up to 3), reads a short summary:
    - filename
    - number of past findings
    - most severe finding type
  Returns a formatted context string to inject into the prompt:
  "Related files that interact with this code:
   - utils.py: 3 past findings (highest: SQL_INJECTION)
   - auth.py: 1 past finding (highest: HARDCODED_SECRET)
   Changes here may affect these files."
  Returns "" if no related files or memory empty.
  Never raises.
  reader_fn: callable that takes filepath, returns file dict (= read_file)
```

### cli/calibrator.py (NEW)
```
calibrate_confidence(finding: dict, similar: list[dict]) -> dict
  Returns copy of finding with adjusted confidence and possibly severity.
  Rules:
  - 0 similar: return unchanged
  - majority confirmed: +15 confidence (cap 100)
  - majority false_positive: -30 confidence (floor 0)
  - mixed: unchanged
  - CRITICAL + confidence < 40: downgrade severity to HIGH
  Returns copy, never mutates original. Never raises.

calibrate_findings(findings: dict, memory: ReviewMemory,
                   filepath: str) -> dict
  Applies calibrate_confidence to every finding.
  Filters out is_false_positive() == True findings.
  Returns new findings dict (same shape). Never raises.
```

### cli/fixer.py (NEW)
```
generate_fix(code: str, finding: dict, language: str,
             model: str) -> str|None
  Builds a prompt asking Ollama to produce the minimal patched version
  of the relevant code section.
  Returns the patched code string, or None if generation failed.
  Never raises.

show_diff(original: str, patched: str, filename: str) -> None
  Prints colored unified diff to terminal.
  Added lines: Fore.GREEN
  Removed lines: Fore.RED
  Context lines: default color

apply_fixes_interactive(filepath: str, findings: dict,
                        language: str, model: str) -> int
  For each finding that has a Fix: suggestion:
    1. generate_fix() → patched code
    2. show_diff()
    3. prompt: "Apply this fix? [y/N/q (quit)] "
    4. if y: write patched code to file
    5. if q: stop asking
  Returns number of fixes applied.
  raises FileNotFoundError if filepath not found.
  raises OSError on write failure.
```

### cli/args.py (UPGRADE from session 2)
```
New flags:
  --fix           store_true  interactive fix mode after review
  --no-memory     store_true  skip memory lookup and storage
  --clear-memory  store_true  wipe ChromaDB store and exit
  --batch-size    int         lines per chunk (default 150)
  --ci            store_true  CI mode: exit 1 if HIGH+ findings exist
```

### cli/prompter.py (UPGRADE from session 2)
```
build_prompt gains one more parameter:
  cross_file_context: str = ""   injected after codebase patterns
  (new section in prompt if non-empty):
  "Cross-file context — changes here may affect these files:
   {cross_file_context}
   Consider whether your findings in this file could be related to
   or worsen issues in the above files."

NOTE: build_verification_prompt(code, findings, language) signature unchanged.
Call parse_verification as: parse_verification(findings, raw)  ← findings first.
```

### cli/reporter.py (UPGRADE from session 2)
```
print_report gains "seen_before" awareness:
  Findings that exist in memory with verdict "confirmed":
    show badge: [↩ SEEN BEFORE]  in dim color after severity badge
  Findings that are new:
    show badge: [NEW] in bright color
```

### review.py (UPGRADE from session 2)
```
New complete flow:

1.  parse args
2.  if --clear-memory: ReviewMemory().clear(), print "Memory cleared.", exit
3.  if model == "auto": select_model()
4.  init ReviewMemory (unless --no-memory)
5.  determine input mode: file / dir / diff
6.  for each file:
      a. read_file
      b. if lines > batch_size: chunk_code, else single chunk
      c. get codebase patterns from memory
      d. get cross-file context from cross_ref (unless --no-memory)
      e. for each chunk:
           build_prompt (with context + cross-file context)
           query_ollama (stream if --stream)
           parse_response
      f. merge_findings if multiple chunks
      g. calibrate_findings (unless --no-memory)
      h. if --verify: build_verification_prompt → query_ollama → parse_verification(findings, raw)
      i. apply severity filter
      j. print_report (with seen_before badges) or print_json
      k. if --output: save_report (files written as UTF-8 — read with encoding="utf-8" in tests)
      l. store each finding in memory (unless --no-memory)
      m. if --fix: apply_fixes_interactive
7.  dir/diff mode: print summary
8.  if --ci and any HIGH/CRITICAL findings: sys.exit(1)

Errors: FileNotFoundError, ValueError, ConnectionError, RuntimeError
→ all caught separately, stderr, sys.exit(1)
```

### .github/workflows/code-review.yml (NEW)
```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install and start Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama serve &
          sleep 8
          ollama pull qwen2.5-coder:1.5b
          ollama pull nomic-embed-text

      - name: Run review
        run: |
          python review.py --diff --json --severity high \
            --no-memory --ci --model qwen2.5-coder:1.5b \
            > review_output.json 2>review_log.txt || true

      - name: Post PR comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            let body = '## 🔍 Automated Code Review\n\n';
            try {
              const raw = fs.readFileSync('review_output.json', 'utf8');
              const data = JSON.parse(raw);
              const bugs = data.bugs || [];
              const sec = data.security || [];
              if (bugs.length === 0 && sec.length === 0) {
                body += '✅ No HIGH or CRITICAL findings detected.\n';
              } else {
                if (bugs.length > 0) {
                  body += `### 🐛 Bugs (${bugs.length})\n`;
                  bugs.forEach(b => {
                    body += `- **[${b.severity}]** Line ${b.line ?? '?'}: ${b.description}\n`;
                    if (b.fix) body += `  - 💡 Fix: ${b.fix}\n`;
                  });
                }
                if (sec.length > 0) {
                  body += `### 🔒 Security (${sec.length})\n`;
                  sec.forEach(s => {
                    body += `- **[${s.severity}]** ${s.type}: ${s.description}\n`;
                    if (s.fix) body += `  - 💡 Fix: ${s.fix}\n`;
                  });
                }
                if (data.summary) body += `\n### 📋 Summary\n${data.summary}\n`;
                body += `\n📊 Score: ${data.score ?? '?'}/100`;
              }
            } catch(e) {
              body += '⚠️ Review output could not be parsed. Check Actions logs.';
            }
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body
            });
```

---

## FOLDER STRUCTURE AFTER SESSION 3

```
CODE_REVIEW_SECURITY_WORKFLOW/
│   review.py
│   requirements.txt        ← + chromadb
│   README.md
│
├── .github/
│   └── workflows/
│       └── code-review.yml ← NEW
│
├── cli/
│   │   __init__.py
│   │   args.py             ← + --fix, --no-memory, --clear-memory, --batch-size, --ci
│   │   reader.py           ← unchanged
│   │   prompter.py         ← + cross_file_context param
│   │   ollama_client.py    ← unchanged
│   │   parser.py           ← unchanged
│   │   reporter.py         ← + seen_before badges
│   │   router.py           ← unchanged
│   │   scanner.py          ← unchanged
│   │   differ.py           ← unchanged
│   │   progress.py         ← unchanged
│   │   batcher.py          ← NEW
│   │   embedder.py         ← NEW
│   │   memory.py           ← NEW
│   │   calibrator.py       ← NEW
│   │   cross_ref.py        ← NEW
│   └── fixer.py            ← NEW
│
├── app/graders/            ← unchanged (ast_grader.py + owasp_grader.py added S2)
│
├── data/
│   ├── tasks/
│   └── memory/             ← NEW (ChromaDB here, gitignored)
│       └── .gitkeep
│
└── tests/
    │   ...session 2 tests (37 passing)...
    │   test_batcher.py     ← NEW
    │   test_memory.py      ← NEW (mock ChromaDB)
    │   test_calibrator.py  ← NEW
    └── test_fixer.py       ← NEW
```

---

## .GITIGNORE ADDITIONS

```
data/memory/chroma.sqlite3
data/memory/chroma/
```

---

## TASK REGISTRY

| # | File | Action | Status | Notes |
|---|------|--------|--------|-------|
| A1 | `requirements.txt` | ADD chromadb | NOT STARTED | One line |
| A2 | `data/memory/` | CREATE + .gitkeep | NOT STARTED | Manual |
| A3 | `.gitignore` | ADD memory exclusions | NOT STARTED | Manual |
| B1 | `cli/batcher.py` | CREATE | NOT STARTED | chunk + merge |
| B2 | `cli/embedder.py` | CREATE | NOT STARTED | Ollama embeddings |
| B3 | `cli/memory.py` | CREATE | NOT STARTED | ReviewMemory class |
| B4 | `cli/calibrator.py` | CREATE | NOT STARTED | confidence adjustment |
| B5 | `cli/cross_ref.py` | CREATE | NOT STARTED | cross-file context |
| B6 | `cli/fixer.py` | CREATE | NOT STARTED | generate + apply patches |
| B7 | `cli/args.py` | UPGRADE | NOT STARTED | --fix, --no-memory, --ci, etc |
| B8 | `cli/prompter.py` | UPGRADE | NOT STARTED | cross_file_context param |
| B9 | `cli/reporter.py` | UPGRADE | NOT STARTED | seen_before badges |
| B10 | `review.py` | UPGRADE | NOT STARTED | full new flow |
| C1 | `.github/workflows/code-review.yml` | CREATE | NOT STARTED | |
| D1 | `tests/test_batcher.py` | CREATE | NOT STARTED | |
| D2 | `tests/test_memory.py` | CREATE | NOT STARTED | mock ChromaDB |
| D3 | `tests/test_calibrator.py` | CREATE | NOT STARTED | |
| D4 | `tests/test_fixer.py` | CREATE | NOT STARTED | |

---

## CLAUDE'S REVIEW CHECKLIST (session 3 additions)

**batcher.py:**
- [ ] Overlap correct: adjacent chunks share lines
- [ ] merge_findings remaps line numbers by (start_line - 1)
- [ ] Deduplication keeps higher confidence, not first-seen
- [ ] Single chunk returned for small files without crash

**embedder.py:**
- [ ] POSTs to /api/embeddings not /api/generate
- [ ] Returns response["embedding"] not response["response"]
- [ ] ConnectionError raised as builtin not requests type

**memory.py:**
- [ ] PersistentClient used (not in-memory)
- [ ] is_false_positive() returns False on any error (fail open)
- [ ] query_similar() returns [] on empty collection
- [ ] get_related_files() returns [] on error
- [ ] store_finding() includes timestamp in metadata

**calibrator.py:**
- [ ] Confidence capped 0-100
- [ ] CRITICAL→HIGH downgrade only when confidence < 40
- [ ] Returns copy, never mutates original dict

**cross_ref.py:**
- [ ] Returns "" on any error (never raises)
- [ ] Limits to 3 related files maximum
- [ ] Does not crash if memory is empty

**fixer.py:**
- [ ] generate_fix() returns None on failure (not raises)
- [ ] show_diff() uses colorama, not raw ANSI
- [ ] apply_fixes_interactive() handles 'q' to quit loop
- [ ] Applies patches atomically (full file rewrite, not partial)

**args.py:**
- [ ] --batch-size is int type with default 150
- [ ] --clear-memory is store_true
- [ ] --no-memory is store_true
- [ ] --fix is store_true
- [ ] --ci is store_true

**review.py:**
- [ ] --clear-memory exits after clearing (no review runs)
- [ ] --ci exits with code 1 if HIGH or CRITICAL findings present
- [ ] --no-memory skips BOTH query and storage
- [ ] batching only triggered when file lines > batch_size
- [ ] --fix runs after report is printed (not before)
- [ ] parse_verification called as parse_verification(findings, raw)
- [ ] save_report files written as UTF-8

**GitHub Actions yml:**
- [ ] fetch-depth: 0 present (needed for git diff)
- [ ] ollama serve runs in background (&) with sleep after
- [ ] --no-memory in CI command (no disk persistence on runners)
- [ ] || true prevents workflow failure on review findings

**Test files:**
- [ ] All read_text() calls use encoding="utf-8"
- [ ] parse_verification called as parse_verification(findings, raw) in all tests
- [ ] select_model called as select_model(mode, available) in all tests
- [ ] No Ollama or ChromaDB network calls in any test

---

## ORDER OF ATTACK

Track A manually first (~10 min). Then:
1. B1 batcher.py (no dependencies, good warmup)
2. B2 embedder.py (needed by memory)
3. B3 memory.py (depends on embedder)
4. B4 calibrator.py (depends on memory)
5. B5 cross_ref.py (depends on memory)
6. B6 fixer.py (standalone, depends only on ollama_client)
7. B7 args.py (new flags)
8. B8 prompter.py (add cross_file_context)
9. B9 reporter.py (seen_before badges)
10. B10 review.py (wire everything)
11. C1 GitHub Actions yml (standalone)
12. Track D tests (always last)

---

## SESSION LOG

### Session 1
- Built: full CLI pipeline
- Fixed: repo cleanup, requirements, README

### Session 2 ✅ COMPLETE
- Built: few-shot prompts, CoT, language checklists, streaming, model routing,
  verification pass, severity/confidence/fix/score, multi-file scan, git diff,
  progress indicator, full test suite (37 tests passing)
- Added: ast_grader.py + owasp_grader.py to app/graders/
- Fixed: parse_verification arg order, Windows UTF-8 encoding, select_model arg order
- Status: DONE

### Session 3
- Built: ChromaDB memory, cross-file awareness, confidence calibration,
  file batching, interactive fix mode, GitHub Actions
- Status: NOT STARTED YET (do after session 2)

---

## CURRENT TASK

### Track A — Manual setup before coding

**A1:** Add to `requirements.txt`:
```
chromadb
```

**A2:** Create `data/memory/` folder with `.gitkeep` file.

**A3:** Add to `.gitignore`:
```
data/memory/chroma.sqlite3
data/memory/chroma/
```

### Then: Give Gemini the B1 prompt for `cli/batcher.py`

```
You are coding one file of a personal CLI tool: a local offline code reviewer
powered by Ollama. No frameworks, no FastAPI, no servers.
Python 3.11. Allowed dependencies: requests, colorama, chromadb.

Interface contract:

chunk_code(code: str, chunk_size: int = 150, overlap: int = 20) -> list[dict]
  Splits code into overlapping line chunks.
  Returns: [ { "chunk": str, "start_line": int, "end_line": int } ]
  chunk_size: number of lines per chunk.
  overlap: lines shared between adjacent chunks.
  Always at least one chunk even if code shorter than chunk_size.
  Last chunk may be smaller. Never raises.

merge_findings(chunk_results: list[dict], chunk_map: list[dict]) -> dict
  chunk_results: list of dicts shaped like parse_response() output:
    { "bugs": [...], "security": [...], "summary": str, "score": int,
      "thinking": str }
  chunk_map: output of chunk_code() — for absolute line number remapping.
  Bugs: remap line numbers by adding (chunk's start_line - 1).
  Dedup bugs: same absolute line number → keep higher confidence.
  Dedup security: same type → keep higher confidence.
  summary: join all non-empty summaries with newline separator.
  score: average of all chunk scores (int).
  thinking: join all thinking sections.
  Returns single dict matching parse_response() shape.
  Never raises.

Rules:
- No silent exception swallowing
- Under 100 lines
- Return ONLY the file content, no explanation.

Write cli/batcher.py now.
```

### After Gemini writes → paste here for Claude to review.

---

*Claude updates this file after reviewing each file Gemini produces.*
*Always attach session3.md when switching to this session.*
