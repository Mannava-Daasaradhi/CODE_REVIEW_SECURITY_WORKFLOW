# === cli/scanner.py ===
import os
from unittest import result
from cli.reader import read_file
from cli.prompter import build_prompt
from cli.ollama_client import query_ollama
from cli.parser import parse_response
from cli.progress import show_progress

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv",
             "dist", "build", ".mypy_cache", ".pytest_cache", "coverage"}
SUPPORTED_EXT = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".c", ".cpp"}

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "javascript",
    ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php",
    ".c": "c", ".cpp": "cpp"
}

def scan_directory(dirpath: str, model: str, mode: str, stream: bool = False) -> list[dict]:
    if not os.path.exists(dirpath):
        raise FileNotFoundError(f"Directory not found: {dirpath}")

    files_collected = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT:
                files_collected.append(os.path.join(root, f))

    if not files_collected:
        raise ValueError("No supported files found")

    results = []
    total = len(files_collected)
    for i, filepath in enumerate(files_collected, 1):
        filename = os.path.basename(filepath)
        try:
            result = read_file(filepath)
            code = result["code"]
            language = result["language"]
        except IOError:
            continue

        ext = os.path.splitext(filename)[1].lower()
        

        prompt = build_prompt(code, language, mode, filename=filepath)
        raw = query_ollama(prompt, model, stream=stream)
        findings = parse_response(raw, mode)

        show_progress(i, total, filename)
        results.append({"filename": filename, "filepath": filepath, "findings": findings})

    return results