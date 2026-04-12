"""
OWASP-based security grader for the CLI code reviewer.

Scans Python source code line-by-line using regex patterns drawn from the
session2.md language-specific security checklist for Python.
No LLM calls, no side effects, fully deterministic.

Returns a list of finding dicts:
    {"line": int, "severity": str, "type": str, "description": str, "fix": str}
"""

import re

# Each entry: (pattern, severity, vuln_type, description, fix)
_RULES: list[tuple] = [
    (
        re.compile(r"\beval\s*\("),
        "CRITICAL",
        "CODE_EXECUTION",
        "eval() can execute arbitrary code if called with untrusted input",
        "Remove eval(); use ast.literal_eval() for safe literal parsing",
    ),
    (
        re.compile(r"\bexec\s*\("),
        "CRITICAL",
        "CODE_EXECUTION",
        "exec() executes arbitrary Python code — dangerous with any user input",
        "Refactor to avoid exec(); use explicit logic instead",
    ),
    (
        re.compile(r"\bpickle\.loads?\s*\("),
        "CRITICAL",
        "INSECURE_DESERIALIZATION",
        "pickle.load/loads on untrusted data allows arbitrary code execution",
        "Use json or a safe serialisation format for untrusted data",
    ),
    (
        re.compile(r"\byaml\.load\s*\((?![^)]*Loader\s*=\s*yaml\.SafeLoader)"),
        "HIGH",
        "YAML_RCE",
        "yaml.load() without SafeLoader can execute arbitrary Python objects",
        "Use yaml.safe_load() or pass Loader=yaml.SafeLoader",
    ),
    (
        re.compile(r"subprocess\.[^\n]*shell\s*=\s*True"),
        "HIGH",
        "COMMAND_INJECTION",
        "subprocess with shell=True enables shell injection if args contain user input",
        "Pass a list of arguments and set shell=False (the default)",
    ),
    (
        re.compile(r"\bos\.system\s*\("),
        "HIGH",
        "COMMAND_INJECTION",
        "os.system() is vulnerable to command injection with user-controlled input",
        "Use subprocess.run() with a list of args and shell=False",
    ),
    (
        re.compile(r'f["\'].*SELECT|INSERT|UPDATE|DELETE.*\{'),
        "HIGH",
        "SQL_INJECTION",
        "f-string used to build SQL query — direct SQL injection risk",
        "Use parameterised queries with placeholders (?, %s) instead of f-strings",
    ),
    (
        re.compile(r'%\s*["\'].*SELECT|INSERT|UPDATE|DELETE'),
        "HIGH",
        "SQL_INJECTION",
        "%-formatting used to build SQL query — SQL injection risk",
        "Use parameterised queries with placeholders instead of string formatting",
    ),
    (
        re.compile(r"\bopen\s*\([^)]*\+[^)]*\)"),
        "MEDIUM",
        "PATH_TRAVERSAL",
        "open() called with a concatenated path — possible path traversal",
        "Validate and sanitise paths with pathlib.Path.resolve() before opening",
    ),
    (
        re.compile(r"\bhmac\b.*==|==.*\bhmac\b|[\"'][^\"']{8,}[\"']\s*==\s*\w+secret\w*"
                   r"|\w+secret\w*\s*==\s*[\"']", re.IGNORECASE),
        "MEDIUM",
        "TIMING_ATTACK",
        "Direct string comparison for secrets is vulnerable to timing attacks",
        "Use hmac.compare_digest() for constant-time secret comparison",
    ),
]


class OWASPGrader:
    def analyze(self, code: str) -> list[dict]:
        """
        Scan Python source line-by-line and return OWASP security findings.
        Never raises — returns empty list on any failure.
        """
        try:
            lines = code.splitlines()
        except Exception:
            return []

        findings = []
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # skip comments
            for pattern, severity, vuln_type, description, fix in _RULES:
                if pattern.search(line):
                    findings.append({
                        "line": lineno,
                        "severity": severity,
                        "type": vuln_type,
                        "description": description,
                        "fix": fix,
                    })
                    break  # one finding per line max
        return findings
