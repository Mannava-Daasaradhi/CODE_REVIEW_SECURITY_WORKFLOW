"""
AST-based bug grader for the CLI code reviewer.

Analyzes Python source code using the ast module to detect common bugs.
No LLM calls, no side effects, fully deterministic.

Returns a list of finding dicts:
    {"line": int, "severity": str, "description": str, "fix": str}
"""

import ast


class ASTGrader:
    def analyze(self, code: str) -> list[dict]:
        """
        Analyze Python source code and return a list of bug findings.
        Never raises — returns empty list on parse failure.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        findings = []
        for node in ast.walk(tree):
            findings.extend(self._check_node(node))
        return findings

    def _check_node(self, node: ast.AST) -> list[dict]:
        findings = []

        # Bare except: except: with no exception type — swallows all errors
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append({
                "line": node.lineno,
                "severity": "MEDIUM",
                "description": "Bare except clause swallows all exceptions including KeyboardInterrupt",
                "fix": "Use 'except Exception:' or catch specific exception types",
            })

        # Mutable default argument: def f(x=[]) or def f(x={})
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append({
                        "line": node.lineno,
                        "severity": "HIGH",
                        "description": f"Mutable default argument in '{node.name}' — shared across all calls",
                        "fix": "Use None as default and initialise inside the function body",
                    })

        # Assert on non-empty tuple: assert (cond, msg) always True
        if isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Tuple):
                findings.append({
                    "line": node.lineno,
                    "severity": "HIGH",
                    "description": "assert with a tuple is always True — likely meant 'assert cond, msg'",
                    "fix": "Replace assert (cond, msg) with assert cond, msg",
                })

        # Unreachable code after return/raise/continue/break
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For,
                              ast.While, ast.If)):
            body = getattr(node, "body", [])
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                    next_stmt = body[i + 1]
                    findings.append({
                        "line": getattr(next_stmt, "lineno", 0),
                        "severity": "MEDIUM",
                        "description": "Unreachable code detected after return/raise/continue/break",
                        "fix": "Remove or restructure the unreachable statements",
                    })

        # == None comparison instead of is None
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq) and isinstance(comparator, ast.Constant) \
                        and comparator.value is None:
                    findings.append({
                        "line": node.lineno,
                        "severity": "LOW",
                        "description": "Use 'is None' instead of '== None'",
                        "fix": "Replace '== None' with 'is None'",
                    })

        return findings
