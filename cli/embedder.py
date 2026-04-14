import requests


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    try:
        resp = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,
        )
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError("Ollama is not running on localhost:11434") from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e

    if resp.status_code == 404:
        raise ValueError(f"Model '{model}' not found. Run: ollama pull {model}")
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error: {resp.status_code}")

    try:
        return resp.json()["embedding"]
    except (ValueError, KeyError) as e:
        raise RuntimeError(f"Unexpected Ollama response: {e}") from e


def embed_finding(finding: dict) -> str:
    type_or_line = finding.get("type") or (
        f"line {finding['line']}" if finding.get("line") is not None else "unknown"
    )
    description = finding.get("description") or ""
    fix = finding.get("fix") or ""
    return f"{type_or_line} {description} {fix}".strip()