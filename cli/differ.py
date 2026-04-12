import subprocess
import os

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "javascript",
    ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php",
    ".c": "c", ".cpp": "cpp"
}

def get_diff_files() -> list[dict]:
    result = subprocess.run(
        ["git", "diff", "HEAD", "--unified=5"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Not a git repository")
    
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("No changes to review")

    files = []
    curr_file = None
    curr_diff = []
    in_hunk = False

    for line in output.splitlines():
        if line.startswith("diff --git"):
            if curr_file and curr_diff:
                ext = os.path.splitext(curr_file)[1].lower()
                files.append({"filename": curr_file, "language": LANG_MAP.get(ext, "unknown"), "diff_content": "\n".join(curr_diff)})
            parts = line.split()
            curr_file = parts[-1][2:] if len(parts) >= 4 and parts[-1].startswith("b/") else "unknown"
            curr_diff = []
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
            curr_diff.append(line)
        elif in_hunk:
            curr_diff.append(line)

    if curr_file and curr_diff:
        ext = os.path.splitext(curr_file)[1].lower()
        files.append({"filename": curr_file, "language": LANG_MAP.get(ext, "unknown"), "diff_content": "\n".join(curr_diff)})

    return files