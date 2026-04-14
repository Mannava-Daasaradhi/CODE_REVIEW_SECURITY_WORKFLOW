def chunk_code(code: str, chunk_size: int = 150, overlap: int = 20) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    lines = code.splitlines()
    if not lines:
        return [{"chunk": "", "start_line": 1, "end_line": 1}]

    chunks = []
    step = chunk_size - overlap
    i = 0
    while i < len(lines):
        start = i
        end = min(i + chunk_size, len(lines))
        chunks.append({
            "chunk": "\n".join(lines[start:end]),
            "start_line": start + 1,
            "end_line": end,
        })
        if end == len(lines):
            break
        i += step
    return chunks


def merge_findings(chunk_results: list[dict], chunk_map: list[dict]) -> dict:
    if len(chunk_results) != len(chunk_map):
        raise ValueError(
            f"chunk_results and chunk_map lengths differ: "
            f"{len(chunk_results)} vs {len(chunk_map)}"
        )

    merged_bugs: dict[tuple, dict] = {}
    merged_security: dict[tuple, dict] = {}
    summaries = []
    scores = []
    thinking_parts = []

    for result, chunk_info in zip(chunk_results, chunk_map, strict=True):
        offset = chunk_info["start_line"] - 1

        for bug in result.get("bugs", []):
            line = bug.get("line")
            abs_line = (line + offset) if isinstance(line, int) else line
            bug_copy = {**bug, "line": abs_line}
            if isinstance(abs_line, int):
                key = ("line", abs_line)
            else:
                key = ("no_line", (bug_copy.get("description") or "").strip().lower(),
                       (bug_copy.get("fix") or "").strip().lower())
            if key not in merged_bugs or bug_copy.get("confidence", 0) > merged_bugs[key].get("confidence", 0):
                merged_bugs[key] = bug_copy

        for sec in result.get("security", []):
            key = (
                (sec.get("type") or "").lower(),
                (sec.get("description") or "").strip().lower(),
            )
            if key not in merged_security or sec.get("confidence", 0) > merged_security[key].get("confidence", 0):
                merged_security[key] = sec

        if result.get("summary"):
            summaries.append(result["summary"])
        if isinstance(result.get("score"), (int, float)):
            scores.append(result["score"])
        if result.get("thinking"):
            thinking_parts.append(result["thinking"])

    return {
        "bugs": list(merged_bugs.values()),
        "security": list(merged_security.values()),
        "summary": "\n".join(summaries),
        "score": int(sum(scores) / len(scores)) if scores else 50,
        "thinking": "\n".join(thinking_parts),
    }