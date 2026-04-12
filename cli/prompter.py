"""
cli/prompter.py — Prompt builder for the offline code reviewer.

Techniques applied (session2.md Track E):
1. Persona prompting
2. Task context + language checklist
3. Negative instructions
4. Two few-shot examples (bug + security)
5. Chain-of-thought steps
"""

import json

# ── Language-specific security checklists ─────────────────────────────────────

LANGUAGE_CHECKLISTS: dict[str, str] = {
    "python": """\
Python-specific issues to look for:
- SQL injection: f-strings or %-formatting used to build queries
- Command injection: subprocess(shell=True) or os.system() with user input
- Code execution: eval(), exec(), pickle.loads() on untrusted data
- Path traversal: open() with unsanitized user-controlled paths
- YAML RCE: yaml.load() without Loader=yaml.SafeLoader
- Timing attack: direct == comparison for secrets (use hmac.compare_digest)
- Infinite loops, off-by-one errors, unchecked recursion depth
- Mutable default arguments (def f(x=[])): shared state across calls""",

    "javascript": """\
JavaScript-specific issues to look for:
- XSS: innerHTML, document.write(), dangerouslySetInnerHTML with user data
- Prototype pollution: recursive merge/assign without hasOwnProperty check
- Code injection: eval() or new Function() with user input
- JWT: algorithm field not validated — "none" alg bypass
- Path traversal in Node.js: path.join() with unsanitized input
- ReDoS: catastrophic backtracking regex on user-controlled strings
- Unhandled promise rejections masking errors silently""",

    "java": """\
Java-specific issues to look for:
- Deserialization: ObjectInputStream.readObject() on untrusted data
- XXE: DocumentBuilderFactory without disabling external entities
- SQL injection: Statement.execute() with string concatenation
- SSRF: URL() or HttpClient constructed from user-controlled host
- Log injection: unsanitized user data passed to logger
- Path traversal: new File() with user-controlled relative paths""",

    "go": """\
Go-specific issues to look for:
- Command injection: exec.Command with user-controlled args
- Path traversal: os.Open() with unsanitized paths
- Goroutine leak: goroutines started inside loops with no exit condition
- Integer overflow in type conversions (int64 → int32 etc.)
- unsafe.Pointer misuse bypassing type safety
- Deferred close inside loops (resource exhaustion)""",
}

# ── Few-shot examples ─────────────────────────────────────────────────────────

_EXAMPLE_BUG = """\
=== FEW-SHOT EXAMPLE 1 — Bug Detection ===

INPUT CODE:
def count_down(n):
    while n > 0:
        print(n)
        n += 1

CORRECT OUTPUT:
THINKING:
Data flows: n is a caller-supplied integer, printed each iteration, then mutated.
Trust boundaries: n comes from the caller — no validation of sign or type.
Control flow: while condition is n > 0. Loop body does n += 1.
Issue: if n starts positive, incrementing keeps n > 0 permanently — infinite loop.
No external input reaches any dangerous sink so no security findings.

BUGS:
- Line 4: [CRITICAL] Infinite loop — n is incremented instead of decremented,
  so the while condition n > 0 is never falsified for any positive starting value.
  | Confidence: 99% | Fix: change n += 1 to n -= 1

SECURITY:
None found

SUMMARY:
The function has a critical infinite loop on line 4. The loop variable n is
incremented when it should be decremented, making the while condition permanently
true for any positive input. No security vulnerabilities were found.

SCORE: 10
=== END EXAMPLE 1 ==="""

_EXAMPLE_SECURITY = """\
=== FEW-SHOT EXAMPLE 2 — Security Detection ===

INPUT CODE:
def get_user(username):
    conn = get_db()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query).fetchone()

CORRECT OUTPUT:
THINKING:
Data flows: username parameter → inserted into f-string → passed to conn.execute().
Trust boundaries: username comes from the caller and is treated as untrusted input.
Control flow: linear — no branching, single query execution path.
Issue: unsanitized user-controlled string interpolated directly into SQL.
No logic bugs in the control flow itself.

BUGS:
None found

SECURITY:
- SQL_INJECTION: [CRITICAL] username is interpolated into the SQL query via f-string
  on line 3 with no sanitization. An attacker can inject ' OR '1'='1 to bypass
  authentication or use UNION SELECT to exfiltrate the database.
  | Confidence: 98% | Fix: use conn.execute("SELECT * FROM users WHERE name = ?", (username,))

SUMMARY:
The function is critically vulnerable to SQL injection. The username parameter
flows directly into the query string via an f-string without parameterization,
giving an attacker full control over the executed SQL. No logic bugs were found.

SCORE: 5
=== END EXAMPLE 2 ==="""

# ── Prompt builders ───────────────────────────────────────────────────────────

def build_prompt(
    code: str,
    language: str,
    mode: str,
    filename: str = "",
    context_patterns: list[str] = None,
) -> str:
    context_patterns = context_patterns or []
    """
    Build a structured review prompt using all 5 session2 techniques.

    Args:
        code:             source code to review
        language:         "python" | "javascript" | "java" | "go" | other
        mode:             "bugs" | "security" | "full"
        filename:         optional filename for context
        context_patterns: optional list of codebase-wide patterns to inject

    Returns:
        prompt string ready to send to Ollama
    """
    parts: list[str] = []

    # 1. PERSONA
    parts.append(
        "You are a senior security engineer with 10+ years reviewing production "
        "codebases. You find real bugs that cause real failures in production. "
        "You care about correctness and security — not code style."
    )

    # 2. TASK CONTEXT
    ctx_parts = [f"Language: {language}", f"Mode: {mode}"]
    if filename:
        ctx_parts.append(f"Filename: {filename}")
    parts.append("Task context:\n" + " | ".join(ctx_parts))

    # 3. LANGUAGE CHECKLIST
    if language.lower() in LANGUAGE_CHECKLISTS:
        parts.append(LANGUAGE_CHECKLISTS[language.lower()])

    # 4. NEGATIVE INSTRUCTIONS
    parts.append(
        "Do NOT flag any of the following — they are out of scope:\n"
        "- Code style or formatting issues\n"
        "- Variable or function naming conventions\n"
        "- Missing docstrings or comments\n"
        "- Unused imports or variables\n"
        "- Performance suggestions unless they cause incorrect behavior\n"
        "Only flag: bugs that cause incorrect behavior, or security vulnerabilities "
        "that could be exploited."
    )

    # 5. FEW-SHOT EXAMPLES
    parts.append(_EXAMPLE_BUG)
    parts.append(_EXAMPLE_SECURITY)

    # 6. CHAIN-OF-THOUGHT INSTRUCTION
    parts.append(
        "Before writing any findings, work through these steps in your THINKING section:\n"
        "  Step 1: Trace every data flow from input sources to output sinks.\n"
        "  Step 2: Identify all trust boundaries — which inputs come from users, "
        "files, environment variables, or network?\n"
        "  Step 3: Examine all control flow paths — loops, recursion, branching, "
        "off-by-one conditions.\n"
        "  Step 4: Cross-reference against the language checklist above.\n"
        "  Step 5: Write your THINKING section first, then your findings."
    )

    # 7. CODEBASE PATTERNS (optional)
    if context_patterns:
        patterns_str = "\n".join(f"  - {p}" for p in context_patterns)
        parts.append(f"Codebase-wide patterns to be aware of:\n{patterns_str}")

    # 8. OUTPUT FORMAT + MODE CONSTRAINTS
    mode_constraint = ""
    if mode == "bugs":
        mode_constraint = (
            "Mode constraint: you are running in BUGS-ONLY mode.\n"
            "The SECURITY section MUST contain exactly \"None found\".\n"
        )
    elif mode == "security":
        mode_constraint = (
            "Mode constraint: you are running in SECURITY-ONLY mode.\n"
            "The BUGS section MUST contain exactly \"None found\".\n"
        )

    parts.append(
        f"{mode_constraint}"
        "Produce your response in EXACTLY this format — no extra sections, "
        "no markdown, no preamble:\n\n"
        "THINKING:\n"
        "<your step-by-step reasoning>\n\n"
        "BUGS:\n"
        "- Line N: [SEVERITY] <description> | Confidence: <0-100>% | Fix: <one-line fix>\n"
        "(or \"None found\" if no bugs)\n\n"
        "SECURITY:\n"
        "- VULN_TYPE: [SEVERITY] <description> | Confidence: <0-100>% | Fix: <one-line fix>\n"
        "(or \"None found\" if no security issues)\n\n"
        "SUMMARY:\n"
        "<one concise paragraph summarising all findings>\n\n"
        "SCORE: <integer 0-100>"
    )

    # 9. CODE
    parts.append(f"=== CODE START ===\n{code}\n=== CODE END ===")

    return "\n\n".join(parts)


def build_verification_prompt(code: str, findings: dict, language: str) -> str:
    """
    Build a self-consistency verification prompt.
    Shows the model its own previous findings and asks it to audit them.

    Args:
        code:     the original source code
        findings: the findings dict returned by parse_response()
        language: language string for context

    Returns:
        prompt string ready to send to Ollama
    """
    bugs = findings.get("bugs", [])
    security = findings.get("security", [])

    finding_lines: list[str] = []
    for i, bug in enumerate(bugs, 1):
        finding_lines.append(
            f"BUG {i}: Line {bug.get('line', '?')} — [{bug.get('severity', '?')}] "
            f"{bug.get('description', '')} | Confidence: {bug.get('confidence', 50)}%"
        )
    for i, sec in enumerate(security, 1):
        finding_lines.append(
            f"SECURITY {i}: {sec.get('type', '?')} — [{sec.get('severity', '?')}] "
            f"{sec.get('description', '')} | Confidence: {sec.get('confidence', 50)}%"
        )

    findings_text = (
        "\n".join(finding_lines) if finding_lines else "No findings to verify."
    )

    parts = [
        f"You are a senior {language} security engineer auditing a previous code review.",
        f"=== CODE START ===\n{code}\n=== CODE END ===",
        f"The following findings were reported in a previous review:\n\n{findings_text}",
        (
            "For EACH finding listed above, respond with exactly one verdict on its own line:\n\n"
            "  CONFIRMED: <brief reason the finding is real>\n"
            "  FALSE_POSITIVE: <brief reason it is not a real issue>\n"
            "  UNCERTAIN: <brief reason you are not sure>\n\n"
            "Rules:\n"
            "- Respond to findings in the exact order listed above.\n"
            "- One verdict line per finding, no skipping.\n"
            "- Be critical. If you are not confident a finding is real, say "
            "FALSE_POSITIVE or UNCERTAIN.\n"
            "- Do not add new findings here — only audit the existing ones."
        ),
    ]

    return "\n\n".join(parts)