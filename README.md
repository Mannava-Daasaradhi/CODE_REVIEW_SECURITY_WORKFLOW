# Code Review & Security Audit CLI

A personal offline code reviewer powered by [Ollama](https://ollama.ai). No internet. No cloud. No API keys. Runs entirely on your machine.

---

## How It Works

```
your file → reader → prompter → Ollama (local) → parser → colored report
```

1. Reads your code file and detects the language from the extension
2. Builds a structured prompt and sends it to Ollama at `localhost:11434`
3. Parses the response into bugs, security findings, and a summary
4. Prints a colored report to the terminal (and optionally saves it)

---

## Requirements

- Python 3.11
- [Ollama](https://ollama.ai) installed and running
- A code model pulled (e.g. `codellama`, `deepseek-coder`)

---

## Setup

```bash
git clone https://github.com/Mannava-Daasaradhi/CODE_REVIEW_SECURITY_WORKFLOW.git
cd CODE_REVIEW_SECURITY_WORKFLOW

python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Start Ollama and pull a model:

```bash
ollama serve
ollama pull codellama
```

---

## Usage

```bash
# Full review (bugs + security + summary)
python review.py myfile.py

# Bugs only
python review.py myfile.py --mode bugs

# Security only
python review.py myfile.py --mode security

# Use a different model
python review.py myfile.py --model deepseek-coder

# Save report to file (no color codes)
python review.py myfile.py --output report.txt

# Combine flags
python review.py myfile.py --mode full --model deepseek-coder --output report.txt
```

### Options

| Flag | Default | Description |
|---|---|---|
| `file` | required | Path to the code file to review |
| `--mode` | `full` | `bugs`, `security`, or `full` |
| `--model` | `codellama` | Ollama model name |
| `--output` | none | Save plain-text report to this path |

---

## Example Output

```
 ══════════════════════════════════════
  CODE REVIEW REPORT: example.py
 ══════════════════════════════════════
  🐛 BUGS  (1 found)
    Line 4 : infinite loop — n incremented instead of decremented
 ──────────────────────────────────────
  🔒 SECURITY  (1 found)
    SQL_INJECTION : user input passed directly to db.execute()
 ──────────────────────────────────────
  📋 SUMMARY
    The function contains a critical infinite loop on line 4 and
    passes unsanitized user input directly to a database query.
 ══════════════════════════════════════
```

---

## Supported Languages

`.py` → python, `.js` → javascript, `.ts` → typescript, `.java` → java,
`.go` → go, `.rb` → ruby, `.php` → php, `.c` / `.cpp` → c/c++

Any other extension is accepted and labeled `unknown`.

---

## Folder Structure

```
CODE_REVIEW_SECURITY_WORKFLOW/
│   review.py              ← entry point
│   requirements.txt       ← requests, colorama
│   README.md
│
├── cli/
│   │   args.py            ← argparse
│   │   reader.py          ← file reading + language detection
│   │   prompter.py        ← builds Ollama prompt
│   │   ollama_client.py   ← POST to localhost:11434
│   │   parser.py          ← parses LLM response into structured findings
│   └── reporter.py        ← colored terminal output + file saving
│
├── app/
│   └── graders/           ← original bug detection + OWASP logic (kept)
│       │   base_grader.py
│       │   task1_grader.py
│       │   task2_grader.py
│       └── task3_grader.py
│
└── tests/
```

---

## Troubleshooting

**`ConnectionError: Ollama not running`**
→ Run `ollama serve` in a separate terminal.

**`ValueError: Model 'x' not found`**
→ Run `ollama pull x` to download the model first.

**`FileNotFoundError`**
→ Check the file path. Relative paths are resolved from where you run the command.

**Output looks garbled on Windows**
→ Colors use colorama which handles Windows terminals automatically. If issues persist, use `--output` to save to a plain text file instead.

---

*Rebuilt from Scalar Hackathon codebase — server deleted, CLI added, graders kept.*
