"""
apply_fixes.py
Run from the repo root:  python apply_fixes.py
Applies all fixes identified in the PR #2 code review.
"""

import sys
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def patch(filepath: str, old: str, new: str, description: str) -> bool:
    p = Path(filepath)
    if not p.exists():
        print(f"  ⚠️  SKIP  {filepath}  (file not found)")
        return False
    text = p.read_text(encoding="utf-8")
    if old not in text:
        print(f"  ⚠️  SKIP  {filepath}  — pattern not found (already fixed?)")
        return False
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  ✅  FIXED {filepath}  — {description}")
    return True


# ── fixes ─────────────────────────────────────────────────────────────────────

fixes = []

# 1. review.py — parse_verification argument order (confirmed crash)
fixes.append((
    "review.py",
    "findings = parse_verification(vraw, findings)",
    "findings = parse_verification(findings, vraw)",
    "parse_verification argument order (would crash with --verify)",
))

# 2. cli/scanner.py — missing ValueError in exception handler
fixes.append((
    "cli/scanner.py",
    "except IOError:\n            continue",
    "except (IOError, ValueError):\n            continue",
    "catch ValueError from read_file() so empty files don't abort directory scan",
))

# 3. cli/scanner.py — remove unused `from unittest import result`
fixes.append((
    "cli/scanner.py",
    "from unittest import result\n",
    "",
    "remove unused `from unittest import result` (shadows local variable)",
))

# 4. cli/ollama_client.py — add connect timeout for streaming requests
fixes.append((
    "cli/ollama_client.py",
    'kwargs = {"stream": True} if stream else {"timeout": 120}',
    'kwargs = {"stream": True, "timeout": (10, None)} if stream else {"timeout": 120}',
    "add connect timeout for streaming so CLI can't hang forever",
))

# 5. cli/ollama_client.py — broaden exception handling to catch timeouts etc.
fixes.append((
    "cli/ollama_client.py",
    "except requests.exceptions.ConnectionError:\n        raise ConnectionError(\"Ollama is not running on localhost:11434\")",
    (
        "except requests.exceptions.ConnectionError:\n"
        "        raise ConnectionError(\"Ollama is not running on localhost:11434\")\n"
        "    except requests.exceptions.RequestException as e:\n"
        "        raise RuntimeError(f\"Ollama request failed: {e}\") from e"
    ),
    "catch all RequestExceptions (timeouts etc.) instead of only ConnectionError",
))

# 6. cli/differ.py — meaningful git error message
fixes.append((
    "cli/differ.py",
    'raise RuntimeError("Not a git repository")',
    'raise RuntimeError(result.stderr.strip() or "Failed to read git diff")',
    "surface real git error message instead of always saying 'Not a git repository'",
))

# 7. cli/differ.py — raise when diff has content but no reviewable hunks (binary files)
fixes.append((
    "cli/differ.py",
    "    return files",
    "    if not files:\n        raise RuntimeError(\"No reviewable diff hunks found (binary-only changes?)\")\n    return files",
    "raise when diff produces no reviewable hunks instead of silently returning empty",
))

# 8. cli/reporter.py — unknown severity should be excluded, not included in all filters
fixes.append((
    "cli/reporter.py",
    'SEV_ORDER.get(i.get("severity", "unknown").lower(), 99) >= m_idx',
    'SEV_ORDER.get(i.get("severity", "unknown").lower(), -1) >= m_idx',
    "map unknown severity to -1 so it's excluded by severity filter, not included",
))

# 9. cli/router.py — add codellama to model preference lists
fixes.append((
    "cli/router.py",
    '"bugs": ["qwen3-coder", "qwen3", "deepseek-r1", "llama"],',
    '"bugs": ["qwen3-coder", "qwen3", "deepseek-r1", "codellama", "llama"],',
    "add codellama to bugs preference list",
))
fixes.append((
    "cli/router.py",
    '"security": ["qwen3-coder", "deepseek-r1", "qwen3", "llama"],',
    '"security": ["qwen3-coder", "deepseek-r1", "qwen3", "codellama", "llama"],',
    "add codellama to security preference list",
))
fixes.append((
    "cli/router.py",
    '"full": ["qwen3-coder", "deepseek-r1", "qwen3", "llama"],',
    '"full": ["qwen3-coder", "deepseek-r1", "qwen3", "codellama", "llama"],',
    "add codellama to full preference list",
))

# 10. cli/prompter.py — fix mutable default argument
fixes.append((
    "cli/prompter.py",
    "context_patterns: list[str] = [],",
    "context_patterns: list[str] = None,",
    "fix mutable default argument (list) — use None instead",
))
# Also add the None→[] normalisation inside the function body
fixes.append((
    "cli/prompter.py",
    "context_patterns: list[str] = None,\n) -> str:",
    "context_patterns: list[str] = None,\n) -> str:\n    context_patterns = context_patterns or []",
    "normalise context_patterns to [] inside function body",
))

# 11. app/graders/owasp_grader.py — fix SQL injection regex precedence
fixes.append((
    "app/graders/owasp_grader.py",
    r"re.compile(r'f[\"\'].*SELECT|INSERT|UPDATE|DELETE.*\{')",
    r"re.compile(r'f[\"\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{')",
    "fix SQL f-string regex alternation precedence (was causing false positives)",
))
fixes.append((
    "app/graders/owasp_grader.py",
    r"re.compile(r'%\s*[\"\']\.*SELECT|INSERT|UPDATE|DELETE')",
    r"re.compile(r'%\s*[\"\'].*(?:SELECT|INSERT|UPDATE|DELETE)')",
    "fix SQL %-format regex alternation precedence",
))

# ── run ───────────────────────────────────────────────────────────────────────

print("\n🔧  Applying PR review fixes...\n")
ok = sum(1 for args in fixes if patch(*args))
print(f"\n{'─'*55}")
print(f"  {ok}/{len(fixes)} fixes applied.")
if ok < len(fixes):
    print("  Run the script again to see which patterns were not found.")
print()