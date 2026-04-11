import os

def read_file(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
        
    if os.path.getsize(path) == 0:
        raise ValueError(f"File is empty: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
    except UnicodeDecodeError as e:
        raise ValueError(f"Unable to read file as text: {path}") from e

    if not code.strip():
        raise ValueError(f"File is empty or contains only whitespace: {path}")

    filename = os.path.basename(path)
    _, ext = os.path.splitext(filename)
    
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c/c++",
        ".cpp": "c/c++"
    }
    
    language = language_map.get(ext.lower(), "unknown")
    lines = len(code.splitlines())

    return {
        "code": code,
        "language": language,
        "filename": filename,
        "lines": lines
    }